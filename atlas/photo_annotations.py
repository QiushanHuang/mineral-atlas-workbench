"""Validated, source-bound manual photo evidence. It never confirms physical indices."""
import base64
import copy
import hashlib
import io
import math
import re

KINDS=('edge','silhouette','face','occlusion','uncertain')
POLYGONS=('silhouette','face','occlusion')

def _cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def _area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2

def _intersects(a,b,c,d):
    def side(p,q,r):return _cross(p,q,r)
    def on(p,q,r):return abs(side(p,q,r))<1e-8 and min(p[0],q[0])<=r[0]<=max(p[0],q[0]) and min(p[1],q[1])<=r[1]<=max(p[1],q[1])
    values=(side(a,b,c),side(a,b,d),side(c,d,a),side(c,d,b))
    return (values[0]*values[1]<0 and values[2]*values[3]<0) or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b)

def _hull(points):
    ordered=sorted(map(tuple,points));lower=[];upper=[]
    for chain,items in ((lower,ordered),(upper,reversed(ordered))):
        for point in items:
            while len(chain)>=2 and _cross(chain[-2],chain[-1],point)<=0:chain.pop()
            chain.append(point)
    return lower[:-1]+upper[:-1]

def validate_annotation(value,raw):
    """Return an isolated annotation; sizes use EXIF-transposed display pixels."""
    if value is None:return None
    if not isinstance(value,dict) or set(value)!={'schema_version','image_size','source_sha256','features'}:
        raise ValueError('手工标注须包含且仅包含schema_version、image_size、source_sha256和features')
    if type(value['schema_version']) is not int or value['schema_version']!=1:raise ValueError('手工标注schema_version须为1')
    if value['source_sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('手工标注SHA256与原图绑定不一致，请重新载入对应照片')
    from PIL import Image,ImageOps
    try:
        image=Image.open(io.BytesIO(raw))
        if image.width*image.height>40_000_000:raise ValueError('图像超过4000万像素')
        size=list(ImageOps.exif_transpose(image).size)
    except Exception as error:raise ValueError('手工标注绑定的图像无法解码') from error
    supplied=value['image_size']
    if not isinstance(supplied,list) or len(supplied)!=2 or any(type(x) is not int for x in supplied) or supplied!=size:
        raise ValueError('手工标注image_size须匹配EXIF转正后的原图尺寸')
    features=value['features']
    if not isinstance(features,list) or len(features)>128:raise ValueError('每张照片最多128项手工特征')
    ids=set();silhouettes=0;total=0
    for feature in features:
        if not isinstance(feature,dict) or set(feature)-{'id','kind','points','face_id','model_fingerprint','evidence'} or not {'id','kind','points'}<=set(feature):raise ValueError('手工特征字段无效')
        fid=feature['id'];kind=feature['kind'];points=feature['points']
        if not isinstance(fid,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',fid) or fid in ids:raise ValueError('手工特征id须唯一且为1–64位字母、数字、横线或下划线')
        ids.add(fid)
        if kind not in KINDS:raise ValueError('手工特征kind无效')
        if 'face_id' in feature and (not isinstance(feature['face_id'],str) or not re.fullmatch(r'F\d{2,3}',feature['face_id'])):raise ValueError('face_id须为稳定内部面号，例如F01；不是米勒指数')
        if 'model_fingerprint' in feature and (not isinstance(feature['model_fingerprint'],str) or not re.fullmatch(r'[0-9a-f]{64}',feature['model_fingerprint'])):raise ValueError('model_fingerprint须为64位小写十六进制SHA256')
        if 'evidence' in feature and (not isinstance(feature['evidence'],str) or len(feature['evidence'])>2000):raise ValueError('标注来源说明须为不超过2000字的文字')
        minimum=3 if kind in POLYGONS else 2
        if not isinstance(points,list) or not minimum<=len(points)<=128:raise ValueError(f'{kind}须为{minimum}–128个原图点')
        total+=len(points)
        if total>2048:raise ValueError('每张照片手工特征合计最多2048个点')
        for point in points:
            if not isinstance(point,list) or len(point)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in point):raise ValueError('手工坐标须为有限数值[x,y]')
            if not 0<=point[0]<=size[0] or not 0<=point[1]<=size[1]:raise ValueError('手工坐标超出原图尺寸')
        if len({tuple(point) for point in points})!=len(points):raise ValueError('手工特征含重复点；闭合多边形无需重复首点')
        if kind in POLYGONS:
            if _area(points)<1:raise ValueError('手工多边形退化，面积至少1平方像素')
            edges=list(zip(points,points[1:]+points[:1]))
            for i,(a,b) in enumerate(edges):
                for j,(c,d) in enumerate(edges[i+1:],i+1):
                    if j==i+1 or (i==0 and j==len(edges)-1):continue
                    if _intersects(a,b,c,d):raise ValueError('手工多边形自交，请调整节点')
        silhouettes+=kind=='silhouette'
    if silhouettes>1:raise ValueError('一张照片只能有一条闭合手工外轮廓')
    return copy.deepcopy(value)

def apply_annotation(observation,annotation,raw):
    """Overlay manual evidence on an optional automatic observation."""
    if annotation is None:return observation
    result=copy.deepcopy(observation) if observation else {
        'image_size':annotation['image_size'],'source_sha256':annotation['source_sha256'],
        'display_orientation':'exif-transposed','segments':[],'warnings':[],
        'quality_weight':.75,'requires_review':True,'status':'usable'}
    result['manual_annotation']=copy.deepcopy(annotation)
    result['manual_provenance']={'source':'user_drawn','source_sha256':annotation['source_sha256'],
                                 'feature_ids':[f['id'] for f in annotation['features']],
                                 'claim_level':'unverified_manual_evidence'}
    result['manual_segments']=[];result['face_regions']=[];result['occlusion_regions']=[];result['uncertain_features']=[]
    for feature in annotation['features']:
        kind=feature['kind'];points=feature['points']
        if kind=='silhouette':
            if result.get('silhouette') is not None:result['automatic_silhouette']=result['silhouette']
            result['silhouette']=copy.deepcopy(points);result['manual_silhouette']=True
            result['solidity']=_area(points)/max(_area(_hull(points)),1)
            result['quality_weight']=.75
        elif kind=='edge':result['manual_segments'].extend([[a,b] for a,b in zip(points,points[1:])])
        elif kind=='face':
            region=copy.deepcopy(feature)
            region['model_binding_status']='requires_model_verification' if region.get('face_id') and region.get('model_fingerprint') else 'unbound'
            result['face_regions'].append(region)
        elif kind=='occlusion':result['occlusion_regions'].append(copy.deepcopy(feature))
        else:result['uncertain_features'].append(copy.deepcopy(feature))
    if not result.get('silhouette'):raise ValueError('自动分割失败时，请补一条闭合手工外轮廓')
    result['mode']='manual' if result.get('manual_silhouette') else 'manual-assisted'
    result['warnings'].append('含手工标注：棱、轮廓及面关联仍需核对；手工约束后的误差不是自动识别精度。')
    if result['face_regions']:result['warnings'].append('手工面区域和face_id仅为待核对关联，不自动确定面号、米勒指数或不可见面。')
    from PIL import Image,ImageOps,ImageDraw
    image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB')
    scale=min(1.,480/max(image.size));image.thumbnail((480,480));draw=ImageDraw.Draw(image)
    colors={'silhouette':'#f09828','edge':'#26bd96','face':'#68a3ff','occlusion':'#ef7777','uncertain':'#b995db'}
    for feature in annotation['features']:
        points=[(x*scale,y*scale) for x,y in feature['points']]
        if feature['kind'] in POLYGONS:points.append(points[0])
        draw.line(points,fill=colors[feature['kind']],width=2)
    buffer=io.BytesIO();image.save(buffer,format='PNG');result['preview']='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()
    return result
