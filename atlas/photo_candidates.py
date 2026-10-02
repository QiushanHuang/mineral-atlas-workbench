"""Photo-first, local template hypotheses. No filenames, face labels or test traces enter inference."""
import base64
import copy
import hashlib
import io
import json
import math
import importlib.metadata
import time
from functools import lru_cache
from .images import decode_image,decode_photo_input
from .core import build
from .photo_policy import MAX_PHOTOS,MAX_TOTAL_IMAGE_BYTES
from .photo_evidence import parse_morphology,morphology_penalties,fuse_scores,analysis_summary
from .photo_annotations import validate_annotation,apply_annotation


def dependencies():
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageOps
        from scipy.spatial import ConvexHull
        from scipy.spatial.transform import Rotation
        from scipy.optimize import least_squares
    except ImportError as e:
        raise ValueError('照片生成候选需要NumPy、SciPy、Pillow和OpenCV；请按requirements-photo.lock配置本地环境。') from e
    return cv2, np, Image, ImageOps, ConvexHull, Rotation, least_squares


def extract_outline(value, box=None):
    cv2,np,Image,ImageOps,_,_,_=dependencies()
    raw,_=decode_image(value)
    try:
        original=Image.open(io.BytesIO(raw))
        if original.width*original.height>40_000_000:raise ValueError('图像超过4000万像素')
        orientation=original.getexif().get(274,1)
        original=ImageOps.exif_transpose(original).convert('RGB')
    except Exception as e:raise ValueError('无法解码照片') from e
    W,H=original.size
    if min(W,H)<32:raise ValueError('照片尺寸过小，无法提取物体轮廓')
    factor=min(1.,480/max(W,H));w,h=round(W*factor),round(H*factor)
    rgb=np.array(original.resize((w,h)));bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
    sm=cv2.GaussianBlur(rgb,(5,5),0).astype(float)
    lab=cv2.cvtColor(sm.astype('uint8'),cv2.COLOR_RGB2LAB).astype(float)
    yy,xx=np.mgrid[:h,:w];border=(xx<w*.15)|(xx>w*.85)
    bg=np.median(lab[border],axis=0)
    region=(xx>w*.10)&(xx<w*.90)&(yy>h*.14)&(yy<h*.91)
    if box is not None:
        if not isinstance(box,list) or len(box)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in box):raise ValueError('物体框须为原图[x,y,width,height]')
        x,y,bw,bh=box
        if x<0 or y<0 or bw<10 or bh<10 or x+bw>W or y+bh>H:raise ValueError('物体框超出照片或过小')
        region=(xx>=x*factor)&(xx<(x+bw)*factor)&(yy>=y*factor)&(yy<(y+bh)*factor)
    # Distinguish yellow mineral/wood from redder skin. Dark brown is not automatically skin.
    rg=sm[:,:,0]-sm[:,:,1];gb=sm[:,:,1]-sm[:,:,2]
    skin=(rg>18)&(rg>1.05*gb)&(sm[:,:,0]>sm[:,:,2]*1.15)
    difference=(lab[:,:,0]<bg[0]-18)|(lab[:,:,2]>bg[2]+17)
    def component(excluded):
        seed=(difference&~excluded&region).astype('uint8')
        seed=cv2.morphologyEx(seed,cv2.MORPH_CLOSE,np.ones((5,5),'uint8'))
        seed=cv2.morphologyEx(seed,cv2.MORPH_OPEN,np.ones((3,3),'uint8'))
        count,labels,stats,centers=cv2.connectedComponentsWithStats(seed);choices=[]
        for i in range(1,count):
            area=stats[i,cv2.CC_STAT_AREA];x,y=centers[i]
            if area<w*h*.006 or area>w*h*.55:continue
            score=area*math.exp(-8*((x/w-.5)**2+(y/h-.5)**2))
            choices.append((score,i,area))
        if not choices:return None,0
        _,i,area=max(choices);return (labels==i).astype('uint8'),area
    mask,seed_area=component(skin)
    # Only use the dark-object hypothesis when the ordinary mask has no substantial object.
    if seed_area<w*h*.018:
        dark_skin=skin&(sm[:,:,0]>125);alternative,area=component(dark_skin)
        if area>seed_area:mask,seed_area,skin=alternative,area,dark_skin
    if mask is None:raise ValueError('未找到可信物体轮廓；请提供较清晰背景或物体框')
    baseline=mask.copy()
    expanded=(cv2.dilate(mask,np.ones((21,21),'uint8'))>0)&region
    gc=np.full((h,w),cv2.GC_BGD,'uint8');gc[expanded]=cv2.GC_PR_BGD
    gc[mask>0]=cv2.GC_PR_FGD;interior=cv2.erode(mask,np.ones((7,7),'uint8'))>0
    if interior.sum()<5:interior=cv2.erode(mask,np.ones((3,3),'uint8'))>0
    gc[interior]=cv2.GC_FGD;gc[skin&expanded]=cv2.GC_BGD
    try:
        cv2.setRNGSeed(611)
        cv2.grabCut(bgr,gc,None,np.zeros((1,65)),np.zeros((1,65)),3,cv2.GC_INIT_WITH_MASK)
        mask=((gc==cv2.GC_FGD)|(gc==cv2.GC_PR_FGD)).astype('uint8')
    except cv2.error:mask=baseline
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:raise ValueError('分割未形成有效物体轮廓，请指定物体框')
    contour=max(contours,key=cv2.contourArea);hull=cv2.convexHull(contour)
    area=cv2.contourArea(hull);solidity=cv2.contourArea(contour)/max(area,1)
    polygon=cv2.approxPolyDP(hull,.004*cv2.arcLength(hull,True),True)[:,0,:]
    if len(polygon)<3 or area<w*h*.008 or area>w*h*.6:raise ValueError('物体轮廓退化或占图比例异常，请检查背景或物体框')
    coarse_polygon=polygon.astype(float)/factor;native_polygon=coarse_polygon.copy()
    refinement={'method':'bounded_opencv_cornerSubPix','attempted':factor<1,'candidate_valid':False,'applied':False,'status':'diagnostic_candidate'}
    if factor<1:
        native_gray=cv2.cvtColor(np.array(original),cv2.COLOR_RGB2GRAY)
        corners=coarse_polygon.astype('float32').reshape(-1,1,2)
        window=max(3,min(15,round(3/factor)))
        try:
            refined=cv2.cornerSubPix(native_gray,corners,(window,window),(-1,-1),(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_MAX_ITER,30,.01))[:,0,:]
            shifts=np.linalg.norm(refined-coarse_polygon,axis=1)
            valid=np.isfinite(refined).all() and np.all(refined>=0) and np.all(refined<=[W,H]) and max(shifts)<=3/factor and cv2.isContourConvex(refined.reshape(-1,1,2))
            if valid:native_polygon=refined.astype(float);refinement.update(candidate_valid=True,median_shift_pixels=float(np.median(shifts)),max_shift_pixels=float(max(shifts)))
        except cv2.error:pass
    # Long internal lines are only weak supporting evidence; writing/texture are not face labels.
    solid=np.zeros((h,w),'uint8');cv2.fillPoly(solid,[polygon],1)
    inside=cv2.erode(solid,np.ones((9,9),'uint8'))
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY);edges=cv2.Canny(gray,55,140)*inside
    span=math.sqrt(area);lines=cv2.HoughLinesP(edges,1,np.pi/180,threshold=max(14,int(span*.15)),minLineLength=max(15,span*.2),maxLineGap=5)
    segments=[] if lines is None else (lines[:,0,:].reshape(-1,2,2)/factor).tolist()[:32]
    preview=rgb.copy();cv2.polylines(preview,[polygon],True,(240,152,40),2)
    for line in segments:cv2.line(preview,tuple(np.round(np.array(line[0])*factor).astype(int)),tuple(np.round(np.array(line[1])*factor).astype(int)),(38,189,150),1)
    b=io.BytesIO();Image.fromarray(preview).save(b,format='PNG')
    # Quality is a weighting heuristic, not an accuracy/confidence estimate.
    lap=cv2.Laplacian(gray,cv2.CV_64F);sharpness=float(np.var(lap[inside>0])) if np.any(inside) else 0.
    crop=cv2.boundingRect(polygon);x,y,cw,ch=crop
    patch=cv2.resize(gray[y:y+ch,x:x+cw],(32,32)).astype('float32')
    spectrum=cv2.dct(patch)[:8,:8].ravel()[1:];bits=spectrum>np.median(spectrum)
    perceptual_hash=format(sum(int(v)<<i for i,v in enumerate(bits)),'016x')
    quality_weight=max(.15,min(1.,solidity)*min(1.,max(.35,sharpness/70))*min(1.,area/(w*h*.04)))
    warnings=[]
    if sharpness<25:warnings.append('物体区域偏模糊，此视角将降低权重；建议补拍清晰照片')
    if solidity<.84:warnings.append('分割边界存在明显凹陷或遮挡；凸轮廓会补全不可见部分，请核对手指边界')
    if box is None:warnings.append('自动物体定位使用居中拍摄先验；选错物体时请提供物体框')
    return {'image_size':[W,H],'exif_orientation':orientation,'display_orientation':'exif-transposed',
            'silhouette':coarse_polygon.tolist(),'coarse_silhouette':coarse_polygon.tolist(),'refined_silhouette':native_polygon.tolist() if refinement['candidate_valid'] else None,'corner_refinement':refinement,'segments':segments,'solidity':float(solidity),
            'status':'usable','perceptual_hash':perceptual_hash,'quality_weight':quality_weight,'sharpness':sharpness,'foreground_fraction':float(area/(w*h)),'requires_review':True,'warnings':warnings,
            'preview':'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode(),
            'source_sha256':hashlib.sha256(raw).hexdigest(),'mode':'box-assisted' if box is not None else 'automatic'}


def samples(poly,n=40):
    import numpy as np
    p=np.asarray(poly,float);edge=np.roll(p,-1,axis=0)-p;lens=np.linalg.norm(edge,axis=1)
    keep=lens>1e-9
    if not all(keep):return samples(p[keep],n)
    cum=np.r_[0,np.cumsum(lens)];t=np.arange(n)*cum[-1]/n;j=np.searchsorted(cum,t,side='right')-1
    return p[j]+edge[j]*((t-cum[j])/lens[j])[:,None]


def distances(points,poly):
    import numpy as np
    p=np.asarray(poly);d=np.roll(p,-1,axis=0)-p;den=np.maximum(np.sum(d*d,axis=1),1e-12)
    t=np.clip(np.sum((points[:,None]-p)*d,axis=2)/den,0,1)
    return np.min(np.linalg.norm(points[:,None]-(p+t[:,:,None]*d),axis=2),axis=1)


def segment_residuals(observed,predicted,diagonal):
    """Endpoint-to-segment distance and unoriented angle; partial edges may be shorter."""
    import numpy as np
    observed=np.asarray(observed,float).reshape(-1,2,2)
    predicted=np.asarray(predicted,float).reshape(-1,2,2)
    if not len(observed):return np.empty((0,3))
    if not len(predicted):return np.full((len(observed),3),.25)
    delta=predicted[:,1]-predicted[:,0];lengths=np.linalg.norm(delta,axis=1)
    points=observed.reshape(-1,2)
    t=np.clip(np.sum((points[:,None]-predicted[:,0])*delta,axis=2)/np.maximum(lengths**2,1e-12),0,1)
    endpoint=np.linalg.norm(points[:,None]-(predicted[:,0]+t[:,:,None]*delta),axis=2).reshape(-1,2,len(predicted)).transpose(0,2,1)/diagonal
    directions=observed[:,1]-observed[:,0];observed_lengths=np.linalg.norm(directions,axis=1)
    sine=np.abs(directions[:,None,0]*delta[:,1]-directions[:,None,1]*delta[:,0])/np.maximum(observed_lengths[:,None]*lengths,1e-12)
    angle=sine*np.minimum(observed_lengths[:,None],lengths)*.5/diagonal
    residuals=np.concatenate([endpoint,angle[:,:,None]],axis=2)
    nearest=np.argmin(np.sum(residuals**2,axis=2),axis=1)
    return residuals[np.arange(len(observed)),nearest]


MANUAL_FACE_METRIC='visible_boundary_one_to_one_v1'


def _face_evaluator(model,regions,diagonal,occlusions=(),partial=False):
    """Prepare fixed-size residuals; no indices or template face-name assumptions."""
    cv2,np,*_=dependencies()
    from scipy.optimize import linear_sum_assignment
    masks=[np.asarray(region['points'],dtype='float32') for region in occlusions]
    def visible_points(points):
        return np.array([not any(cv2.pointPolygonTest(mask,tuple(map(float,p)),False)>=0 for mask in masks) for p in points])
    faces=model['faces'];face_ids={face['id']:i for i,face in enumerate(faces)}
    fingerprint=model.get('draftFingerprint');active=[];excluded=[]
    region_key=lambda region:json.dumps({key:region.get(key) for key in ('points','face_id','model_fingerprint')},sort_keys=True)
    for index,region in enumerate(sorted(regions,key=region_key)):
        record={'feature_id':region.get('id',f'manual-face-{index+1}'),'model_face_id':None,
                'method':'not_comparable','status':'not_comparable','ambiguity':False,'visible':False,'partial':bool(partial or masks),
                'boundary_rmse_pixels':None,'normalized_boundary_rmse':None,'binding_status':'unbound',
                'claim_level':'unverified_reference_face_correspondence'}
        locked=None;reason=None
        if region.get('face_id'):
            if fingerprint and region.get('model_fingerprint')==fingerprint:
                record['binding_status']='verified_model_binding';locked=face_ids.get(region['face_id'])
                if locked is None:reason='绑定模型中不存在所指定的面号'
            elif region.get('model_fingerprint'):record['binding_status']='stale_model_binding_ignored'
        points=np.asarray(region.get('points',[]),float)
        if points.ndim!=2 or points.shape[1:]!=(2,) or len(points)<3 or not np.isfinite(points).all():reason='面区域缺少有效多边形边界'
        if index>=16:reason='每图最多16个面区域参与拟合，其余保留待分批核对'
        if reason:record['reason']=reason;excluded.append(record);continue
        observed=samples(points,16);valid=visible_points(observed)
        if np.count_nonzero(valid)<3:record['reason']='遮挡后可用面边界不足，不能比较';excluded.append(record);continue
        active.append({'record':record,'points':points,'samples':observed,'mask':valid,'locked':locked})

    def evaluate(projected,R,D,summary=False):
        if not active:
            if not summary:return np.empty(0)
            return {'manual_face_error':None,'manual_faces_used':0,'manual_face_penalty':0.,'manual_face_metric':MANUAL_FACE_METRIC,'face_matches':excluded}
        normals=np.array([face['n'] for face in faces])@np.asarray(R).T
        centers=np.array([face['center'] for face in faces])@np.asarray(R).T
        visible=np.sum(normals*(np.array([0,0,D])-centers),axis=1)>1e-8
        polygons={};predicted_samples={};predicted_masks={}
        for i,face in enumerate(faces):
            if not visible[i]:continue
            polygon=np.asarray(projected)[face['ids']]
            area=abs(float(np.sum(polygon[:,0]*np.roll(polygon[:,1],-1)-polygon[:,1]*np.roll(polygon[:,0],-1))))/2
            if area<1:continue
            polygons[i]=polygon;predicted_samples[i]=samples(polygon,16);predicted_masks[i]=visible_points(predicted_samples[i])
        count=len(active);costs=np.full((count,len(faces)+count),.2);costs[:,:len(faces)]=1e6
        vectors={};reasons={}
        for row,item in enumerate(active):
            choices=[item['locked']] if item['locked'] is not None else list(polygons)
            if item['locked'] is not None and item['locked'] not in polygons:reasons[row]='绑定面在当前相机下不可见或投影退化'
            for column in choices:
                if column not in polygons:continue
                first=distances(item['samples'],polygons[column])*item['mask']
                if item['record']['partial']:
                    second=np.zeros(16);used=np.count_nonzero(item['mask'])
                else:
                    second=distances(predicted_samples[column],item['points'])*predicted_masks[column]
                    used=np.count_nonzero(item['mask'])+np.count_nonzero(predicted_masks[column])
                vector=np.r_[first,second]/diagonal*math.sqrt(32/max(used,1))
                vectors[row,column]=vector;costs[row,column]=float(np.sqrt(np.mean(vector**2)))
        rows,columns=linear_sum_assignment(costs)
        selected={int(row):int(column) for row,column in zip(rows,columns)}
        residual=np.concatenate([vectors.get((row,selected[row]),np.full(32,.2)) for row in range(count)])
        if not summary:return residual
        records=[];matched=[];total=float(costs[rows,columns].sum())
        for row,item in enumerate(active):
            column=selected[row];record=copy.deepcopy(item['record']);record['observed_polygon']=item['points'].tolist()
            if (row,column) not in vectors:
                record['reason']=reasons.get(row,'没有足够的一对一可见面对应；区域可能重复或与模型不符')
            else:
                error=float(costs[row,column]);matched.append(error)
                alternative=costs.copy();alternative[row,column]=1e6
                ar,ac=linear_sum_assignment(alternative);gap=float(alternative[ar,ac].sum())-total
                record.update(model_face_id=faces[column]['id'],status='candidate_match',method='bound_face' if item['locked'] is not None else 'geometric_one_to_one',
                              visible=True,ambiguity=gap<=max(.004,total*.05),assignment_gap=gap,
                              normalized_boundary_rmse=error,boundary_rmse_pixels=error*diagonal,
                              projected_polygon=polygons[column].tolist(),reason=None)
                if record['binding_status']=='stale_model_binding_ignored':record['binding_note']='模型指纹已过期；原面号未作为约束，仅作几何待确认匹配'
            records.append(record)
        return {'manual_face_error':float(np.sqrt(np.mean(np.square(matched)))) if matched else None,
                'manual_faces_used':len(matched),'manual_face_penalty':float(np.sqrt(np.mean(residual**2))),
                'manual_face_metric':MANUAL_FACE_METRIC,'face_matches':sorted(records+excluded,key=lambda r:r['feature_id'])}
    return evaluate


def match_face_regions(model,regions,projected,rotation,distance,diagonal,occlusions=(),partial=False):
    """Compare manual polygons with an explicitly supplied camera projection."""
    return _face_evaluator(model,regions,diagonal,occlusions,partial)(projected,rotation,distance,summary=True)


@lru_cache(maxsize=48)
def orientations(vertices):
    _,np,_,_,ConvexHull,_,_=dependencies();V=np.array(vertices);D=np.linalg.norm(V,axis=1).max()*8;result=[]
    for i in range(80):
        z=1-2*(i+.5)/80;a=i*math.pi*(3-math.sqrt(5));direction=np.array([math.sqrt(1-z*z)*math.cos(a),z,math.sqrt(1-z*z)*math.sin(a)])
        x=np.cross([0,1,0],direction);x/=np.linalg.norm(x);y=np.cross(direction,x);R=np.array([x,y,direction]);p=V@R.T;xy=p[:,:2]*[1,-1]/(1-p[:,2,None]/D);poly=xy[ConvexHull(xy).vertices];points=samples(poly);center=points.mean(axis=0);q=points-center;length=np.linalg.norm(q);result.append((R,points,center,length,q/length))
    return D,result


def match_outline(model,observation):
    cv2,np,_,_,ConvexHull,Rotation,least_squares=dependencies()
    V=np.array(model['vertices']);D,seeds=orientations(tuple(map(tuple,V)))
    target=np.array(observation['silhouette']);target=target[ConvexHull(target).vertices];q=samples(target);mean=q.mean(axis=0);qt=q-mean;length=np.linalg.norm(qt);norm=qt/length
    diagonal=max(float(np.linalg.norm(np.ptp(target,axis=0))),1)
    starts=[]
    complex_target=norm[:,0]+1j*norm[:,1];rotations=np.array([np.roll(complex_target,k) for k in range(len(q))])
    for R,p,center,L,pn in seeds:
        comp=pn[:,0]+1j*pn[:,1];correlations=(rotations*np.conj(comp)).sum(axis=1);i=int(np.argmax(abs(correlations)));angle=float(np.angle(correlations[i]));score=2-2*abs(correlations[i])
        RR=Rotation.from_rotvec([0,0,-angle]).as_matrix()@R;scale=length/L;c=complex(center[0],center[1])*complex(math.cos(angle),math.sin(angle));off=mean-np.array([c.real,c.imag])*scale
        starts.append((score,np.r_[Rotation.from_matrix(RR).as_rotvec(),math.log(scale),off]))
    def project(z):
        R=Rotation.from_rotvec(z[:3]).as_matrix();p=V@R.T;return p[:,:2]*[1,-1]*np.exp(z[3])/(1-p[:,2,None]/D)+z[4:6]
    occlusions=[np.asarray(region['points'],dtype='float32') for region in observation.get('occlusion_regions',[])]
    def obscured(point):return any(cv2.pointPolygonTest(region,tuple(map(float,point)),False)>=0 for region in occlusions)
    if observation.get('manual_silhouette'):q=samples(observation['silhouette'])
    if occlusions:
        q=np.asarray([point for point in q if not obscured(point)])
        if len(q)<3:raise ValueError('遮挡区覆盖了几乎全部轮廓，请保留至少一段可见外轮廓')
    manual_segments=[line for line in observation.get('manual_segments',[]) if not any(obscured(point) for point in [line[0],np.mean(line,axis=0),line[1]])]
    partial=observation.get('coverage') in ('partial','suspected_partial') or bool(occlusions)
    face_regions=observation.get('face_regions',[])
    face_evaluator=_face_evaluator(model,face_regions,diagonal,observation.get('occlusion_regions',[]),partial) if face_regions else None
    def visible_segments(z,internal=False):
        R=Rotation.from_rotvec(z[:3]).as_matrix();projected=project(z)
        normals=np.array([face['n'] for face in model['faces']])@R.T
        centers=np.array([face['center'] for face in model['faces']])@R.T
        rays=np.array([0,0,D])-centers;visible=np.sum(normals*rays,axis=1)>1e-8
        return [projected[edge['ids']] for edge in model['edges'] if (all if internal else any)(visible[face] for face in edge['faces'])]
    def outline_residual(z):
        p=project(z);hull=p[ConvexHull(p).vertices]
        if partial:return np.minimum(distances(q,hull)/diagonal,.035)
        return np.r_[distances(samples(hull),target),distances(q,hull)]/diagonal
    def residual(z):
        outline=outline_residual(z)
        if not manual_segments and face_evaluator is None:return outline
        parts=[outline]
        if manual_segments:parts.append(segment_residuals(manual_segments,visible_segments(z),diagonal).ravel()*.8)
        if face_evaluator is not None:parts.append(face_evaluator(project(z),Rotation.from_rotvec(z[:3]).as_matrix(),D)*.8)
        return np.concatenate(parts)
    results=[]
    ranked_starts=sorted(starts,key=lambda a:float(np.linalg.norm(residual(a[1]))) if face_evaluator is not None else a[0])
    for _,z in ranked_starts[:3]:
        kwargs={}
        if partial:
            W,H=observation['image_size']
            kwargs['bounds']=([-12]*3+[z[3]-math.log(1.25),-2*W,-2*H],[12]*3+[z[3]+math.log(1.5),3*W,3*H])
        fitted=least_squares(residual,z,max_nfev=55,loss='soft_l1',f_scale=.015,**kwargs)
        rmse=float(np.sqrt(np.mean(residual(fitted.x)**2)));results.append((rmse,fitted.x))
    _,z=min(results,key=lambda a:a[0]);R=Rotation.from_rotvec(z[:3]).as_matrix();proj=project(z)
    error=float(np.sqrt(np.mean(outline_residual(z)**2)))
    # Unsupported extra edges are not penalized: writing and invisible faces are unknown.
    internal=[]
    for e in model['edges']:
        if all((R@np.array(model['faces'][i]['n']))[2]>.08 for i in e['faces']):internal.append(proj[e['ids']])
    line_error=None;endpoint_error=None
    if internal and observation['segments']:
        endpoint_error=float(np.median(np.linalg.norm(segment_residuals(observation['segments'],internal,diagonal),axis=1)))
        # Unreviewed image lines include writing and texture. The stronger metric is
        # diagnostic until accepted: prior-photo ablations found ranking regressions.
        lines=np.array(internal);points=np.array(observation['segments']).mean(axis=1);delta=lines[:,1]-lines[:,0]
        t=np.clip(np.sum((points[:,None]-lines[:,0])*delta,axis=2)/np.maximum(np.sum(delta*delta,axis=1),1e-9),0,1)
        line_error=float(np.median(np.min(np.linalg.norm(points[:,None]-(lines[:,0]+t[:,:,None]*delta),axis=2),axis=1))/diagonal)
    manual_error=float(np.sqrt(np.mean(segment_residuals(manual_segments,visible_segments(z),diagonal)**2))) if manual_segments else None
    face_result=face_evaluator(proj,R,D,summary=True) if face_evaluator is not None else {'manual_face_error':None,'manual_faces_used':0,'manual_face_penalty':0.,'manual_face_metric':MANUAL_FACE_METRIC,'face_matches':[]}
    normals=np.array([f['n'] for f in model['faces']])@R.T;fi=int(np.argmax(normals[:,2]))
    view={'face':fi,'R':R.tolist(),'scale':float(np.exp(z[3])),'offset':z[4:6].tolist(),'D':float(D),'observed':target.tolist(),'predicted':proj[model['faces'][fi]['ids']].tolist(),'rmse':error*diagonal,'imageSize':observation['image_size'],'sourceSize':observation['image_size'],'silhouette':target.tolist(),'fitMetric':'partial_silhouette' if partial else 'silhouette','fit':'自动轮廓匹配；模型与面号均为未确认候选','status':'candidate_ambiguous','warnings':['单图轮廓不决定深度或不可见面；当前面号来自模板，并非照片识别']}
    if observation.get('manual_annotation') or manual_segments or face_regions:
        view['fit']='手工照片约束辅助拟合；模型与面号均为未确认候选'
        view['warnings'].append('手工约束参与拟合；该误差不作为自动识别精度。')
    if face_regions:
        view['warnings'].append('面区域边界参与拟合；当前误差不是独立留出精度，投影面对应仍需确认。' if face_result['manual_faces_used'] else '没有得到可比较的手工面对应；请查看各区域原因，不能把轮廓拟合误差当作面识别通过。')
        view['faceMatches']=face_result['face_matches']
    return {'normalized_silhouette_rmse':error,'metric':'clipped_one_sided_outline' if partial else 'symmetric_outline_rmse','line_error':line_error,'line_metric':'legacy_midpoint_weak_v1','endpoint_direction_error':endpoint_error,'manual_line_metric':'endpoint_direction_v1','manual_edge_error':manual_error,'manual_edges_used':len(manual_segments),**face_result,'score':error+(min(line_error,.1)*.06 if line_error is not None else 0)+(manual_error*.2 if manual_error is not None else 0)+face_result['manual_face_penalty']*.25,'view':view}


def candidate_spec(spec):
    s=copy.deepcopy(spec);template=s['id'];s['id']='photo-'+template;s['title']='照片候选 · '+str(spec.get('title',template))
    s['metadata']={'notes':['从照片轮廓检索的形态候选，需人工确认。','晶系、点群、指数、不可见面和面号均为模板先验，不是照片自动识别结果。'],'basis_note':'继承参考模板的基底与轴比；未从本次照片测定。','description':'照片生成的初始候选，可继续核对外形、补充标注并精修。','template_id':template}
    for f in s.get('faces',[]):
        f.pop('photo_label',None);f['label']='候选模板 '+f.get('id','晶面');f['evidence']='参考模板假设；当前照片未确认此面的编号或指数'
    s['evidence']=[{'type':'template_prior','source':template,'status':'assumed'}]
    return s


def from_photos(images,boxes=None,constraints=None,bank=None,evidence=None):
    start=time.perf_counter();cv2,np,*_=dependencies()
    if not isinstance(images,list) or not 1<=len(images)<=MAX_PHOTOS:raise ValueError(f'请选择1–{MAX_PHOTOS}张同一物体的照片')
    payloads=[decode_photo_input(im) for im in images]
    raw=[item[0] for item in payloads]
    if sum(map(len,raw))>MAX_TOTAL_IMAGE_BYTES:raise ValueError('多张照片合计不得超过64MiB，请先缩小照片')
    if boxes is not None and (not isinstance(boxes,list) or len(boxes)!=len(images)):raise ValueError('物体框列表须与照片逐项对应')
    evidence={} if evidence is None else evidence
    if not isinstance(evidence,dict) or set(evidence)-{'morphology','strength','coverage','annotations'}:raise ValueError('证据信息支持morphology、strength、coverage和annotations字段')
    parsed=parse_morphology(evidence.get('morphology',''));strength=evidence.get('strength','tentative')
    coverage=evidence.get('coverage',['unknown']*len(images))
    if not isinstance(coverage,list) or len(coverage)!=len(images) or any(v not in ('unknown','complete','partial') for v in coverage):raise ValueError('coverage须与照片逐项对应，取unknown、complete或partial')
    annotations=evidence.get('annotations',[None]*len(images))
    if not isinstance(annotations,list) or len(annotations)!=len(images):raise ValueError('annotations须与照片逐项对应，未标注项用null')
    annotations=[validate_annotation(annotation,data) for annotation,data in zip(annotations,raw)]
    constraints={} if constraints is None else constraints
    if not isinstance(constraints,dict):raise ValueError('已知约束须为JSON对象')
    if set(constraints)-{'crystal_system','expected_faces'}:raise ValueError('硬约束仅接受已确认晶系和总面数；不确定形态请放入evidence')
    if 'expected_faces' in constraints and (type(constraints['expected_faces']) is not int or constraints['expected_faces']<4):raise ValueError('已知面数须为不小于4的整数')
    if bank is None:
        from .project import ROOT
        bank=json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding='utf-8'))
    bank=[s for s in bank if all(s.get(k)==v for k,v in constraints.items())]
    if not bank:raise ValueError('已确认晶系/面数与形态库冲突；请核对硬约束，不能用未知信息强行过滤')
    penalties,morphology=morphology_penalties(bank,parsed,strength)
    observations=[];extraction_cache={}
    for i,image in enumerate(images):
        digest=hashlib.sha256(raw[i]).hexdigest();box=boxes[i] if boxes else None
        cache_key=(digest,json.dumps(box,sort_keys=True))
        try:
            if payloads[i][2]:raise ValueError(payloads[i][2])
            if cache_key not in extraction_cache:
                try:extraction_cache[cache_key]=extract_outline(image,box)
                except ValueError as error:
                    if box is not None and '物体框' in str(error):raise
                    if not annotations[i] or not any(f['kind']=='silhouette' for f in annotations[i]['features']):raise
                    extraction_cache[cache_key]=None
            automatic=copy.deepcopy(extraction_cache[cache_key])
            if automatic is None and not annotations[i]:raise ValueError('自动分割未形成可信轮廓；该照片尚无手工外轮廓')
            o=apply_annotation(automatic,annotations[i],raw[i]);o['input_coverage']=coverage[i]
            o['coverage']='suspected_partial' if coverage[i]=='unknown' and o['solidity']<.84 else coverage[i]
            if o.get('occlusion_regions') and o['coverage']=='unknown':o['coverage']='partial'
            if o['coverage'] in ('partial','suspected_partial'):o['quality_weight']*=.35
            o['source_index']=i
        except ValueError as error:
            # Bad hints are input errors, not low-quality photographs.
            if box is not None and '物体框' in str(error):raise
            o={'source_index':i,'source_sha256':digest,'status':'unusable','coverage':coverage[i],'input_coverage':coverage[i],'quality_weight':0.,'warnings':[str(error)],'error':str(error),'mode':'box-assisted' if box is not None else 'automatic'}
        observations.append(o)
    valid=[i for i,o in enumerate(observations) if o['status']=='usable']
    if not valid:raise ValueError('全部照片均未提取到可信物体轮廓；请检查原图或物体框')
    prior_digest=hashlib.sha256(json.dumps(bank,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    reproducibility={'template_bank_sha256':prior_digest,'morphology_catalogue_sha256':morphology['catalogue_sha256'],'template_ids':[s['id'] for s in bank],'dependencies':{'opencv':cv2.__version__,'numpy':np.__version__,'scipy':importlib.metadata.version('scipy'),'Pillow':importlib.metadata.version('Pillow')},'opencv_seed':611,'orientation_samples':80,'manual_annotation_schema':1,'corner_refinement':'diagnostic_candidate_not_applied','automatic_line_metric':'legacy_midpoint_weak_v1','manual_line_metric':'endpoint_direction_v1'}
    candidates=[];matrix={}
    for spec in bank:
        m,quality=build(spec)
        if not quality['ok']:continue
        fits=[None]*len(images);fit_cache={}
        for i in valid:
            o=observations[i];key=(o['source_sha256'],json.dumps(boxes[i] if boxes else None),o['coverage'],json.dumps(annotations[i],sort_keys=True))
            if key not in fit_cache:fit_cache[key]=match_outline(m,o)
            fits[i]=copy.deepcopy(fit_cache[key])
        matrix[spec['id']]=[f['score'] if f else None for f in fits]
        candidate=candidate_spec(spec)
        candidate['evidence'].append({'type':'user_information','source':{'constraints':constraints,'morphology':parsed},'status':'provided_with_uncertainty'})
        candidates.append({'template_id':spec['id'],'title':spec.get('title',spec['id']),'per_photo':[{k:f[k] for k in ('normalized_silhouette_rmse','metric','line_error','line_metric','endpoint_direction_error','manual_line_metric','manual_edge_error','manual_edges_used','manual_face_error','manual_faces_used','manual_face_penalty','manual_face_metric','face_matches','score')} if f else None for f in fits],'views':[f['view'] if f else None for f in fits],'spec':candidate,'representative_photo':valid[0],'requires_review':True})
    if not candidates:raise ValueError('没有通过几何检查的候选模型')
    image_fusion=fuse_scores(matrix,observations);fusion=fuse_scores(matrix,observations,penalties)
    rank={r['template_id']:r for r in fusion['ranking']}
    for c in candidates:c.update({k:v for k,v in rank[c['template_id']].items() if k!='template_id'})
    candidates.sort(key=lambda c:(c['score'],c['template_id']));gap=candidates[1]['score']-candidates[0]['score'] if len(candidates)>1 else None
    analysis=analysis_summary(observations,fusion,morphology,image_fusion['ranking'])
    warnings=['候选来自形态库，不能唯一恢复任意新物体；面号、晶系和指数保留为模板假设。','形态备选仅作为软提示，不会将未知或残缺信息补成确定事实。']
    if analysis['partial_photos'] or parsed['incomplete']:warnings.append('存在残缺或不完整证据；局部轮廓仅约束可见部分，不证明模型完整性。')
    if analysis['excluded_photos']:warnings.append('部分照片无法可靠分割，已保留原图和失败原因，不参与排序。')
    if fusion['redundant_photos']:warnings.append('重复/高度相似照片按一组计权，不增加独立证据。')
    if gap is None or gap<.008:warnings.append('候选误差接近或库太小，需更多不同方向或更明确的形态信息。')
    if fusion['conflicting_photos']:warnings.append('存在与当前首候选冲突的视角，请检查其轮廓、遮挡及是否为同一物体。')
    if candidates[0]['image_score']>.035:warnings.append('最佳候选仍有明显图像偏差，不建议直接采用。')
    return {'engine':'photo-evidence-series-v3','claim_level':'template_candidates','inputs':{'boxes':copy.deepcopy(boxes) if boxes is not None else [None]*len(images),'constraints':copy.deepcopy(constraints),'evidence':copy.deepcopy(evidence),'image_sha256':[o['source_sha256'] for o in observations]},'reproducibility':reproducibility,'status':'needs_review','observations':observations,'candidates':candidates[:3],'ranking':fusion['ranking'],'score_gap':gap,'fusion':fusion,'morphology':morphology,'analysis':analysis,'diagnostics':{'score_matrix':matrix,'image_only_ranking':image_fusion['ranking']},'warnings':warnings,'performance':{'elapsed_seconds':time.perf_counter()-start,'photos':len(images),'usable_photos':len(valid),'independent_views':fusion['independent_views'],'templates':len(bank)},'evaluation_boundary':'No filenames, case IDs, evaluation annotations or saved cameras enter inference. User morphology and source-bound manual annotations remain explicit, unverified evidence.'}
