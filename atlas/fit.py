"""Deterministic coarse-to-fine camera fitting in native image pixels. Optional NumPy/SciPy."""
import math,time

def fit_view(model,annotation):
 try:
  import numpy as np
  from scipy.optimize import least_squares
  from scipy.spatial import ConvexHull
  from scipy.spatial.transform import Rotation
 except ImportError as e:raise ValueError('相机拟合需要 NumPy 和 SciPy；核心建模与报告不需要它们。可用已有环境，或按离线依赖说明安装。') from e
 start=time.perf_counter();V=np.asarray(model['vertices'],float);faces=model['faces'];ids={f['id']:i for i,f in enumerate(faces)}
 if annotation.get('face_id') not in ids:raise ValueError('face_id不在模型中')
 fi=ids[annotation['face_id']];f=faces[fi];facepts=V[f['ids']];normal=np.asarray(f['n']);W,H=annotation.get('image_size',[0,0])
 if not (isinstance(W,int) and isinstance(H,int) and 10<=W<=20000 and 10<=H<=20000):raise ValueError('image_size须为原始显示方向下的像素宽高，范围10–20000')
 def xy(points,minimum=0):
  a=np.asarray(points,float)
  if not minimum and a.size==0:return np.empty((0,2))
  if a.ndim!=2 or a.shape[1]!=2 or not minimum<=len(a)<=500 or not np.all(np.isfinite(a)) or np.any(a<0) or np.any(a>np.array([W,H])):raise ValueError('标注坐标须位于图像内，且每项为[x,y]')
  return a
 target=xy(annotation.get('points',[]),3);mode=annotation.get('mode','cyclic');p=facepts
 if mode not in ('cyclic','correspondences'):raise ValueError('mode须为cyclic或correspondences')
 if mode=='cyclic':
  if len(target)!=len(p):raise ValueError(f'所选面有{len(p)}个角点，当前标注{len(target)}个；轮廓模糊时不要虚构角点')
  if abs(np.cross(target[1]-target[0],target[2]-target[0]))<1e-8 and len(target)==3:raise ValueError('角点共线，不能拟合一个面')
  signed=np.sum(target[:,0]*np.roll(target[:,1],-1)-target[:,1]*np.roll(target[:,0],-1))
  if signed>0:target=target[::-1]
  targets=[np.roll(target,s,axis=0) for s in range(len(target))]
 else:
  vi=annotation.get('vertex_ids',[])
  if len(vi)!=len(target) or len(set(vi))!=len(vi) or any(not isinstance(i,int) or not 0<=i<len(V) for i in vi):raise ValueError('vertex_ids须与points逐项对应，且是不重复的合法顶点')
  p=V[vi];targets=[target]
 radius=float(np.max(np.linalg.norm(V,axis=1)));D=float(annotation.get('distance_radii',8))*radius
 if not 2*radius<=D<=100*radius:raise ValueError('相机距离须为模型半径的2–100倍；无标定时使用默认值')
 outline=xy(annotation.get('silhouette',[]),0);centers=[]
 for fid,point in annotation.get('face_centers',{}).items():
  if fid not in ids:raise ValueError('face_centers含不存在的面')
  pt=xy([point],1)[0];centers.append((faces[ids[fid]],pt))
 def samples(poly,N=32):
  e=np.roll(poly,-1,axis=0)-poly;ls=np.linalg.norm(e,axis=1)
  if np.min(ls)<1e-10:raise ValueError('标注有重复的相邻角点')
  cum=np.r_[0,np.cumsum(ls)];t=np.arange(N)*cum[-1]/N;j=np.searchsorted(cum,t,side='right')-1
  return poly[j]+e[j]*((t-cum[j])/ls[j])[:,None]
 def dist(points,poly):
  d=np.roll(poly,-1,axis=0)-poly;den=np.maximum(np.sum(d*d,axis=1),1e-12);t=np.clip(np.sum((points[:,None]-poly)*d,axis=2)/den,0,1)
  return np.min(np.linalg.norm(points[:,None]-(poly+t[:,:,None]*d),axis=2),axis=1)
 # Cache the observed hull and samples outside the objective: they never change during optimization.
 obsHull=outline[ConvexHull(outline).vertices] if len(outline)>=3 else None;obsSamples=samples(obsHull) if obsHull is not None else None
 diag=math.hypot(W,H);visible_penalty=diag*.4
 def project(points,R,scale,offset):
  q=np.asarray(points)@R.T;return q[:,:2]*[1,-1]*scale/(1-q[:,2,None]/D)+offset
 def objective(z,q):
  R=Rotation.from_rotvec(z[:3]).as_matrix();scale=np.exp(z[3]);pred=project(p,R,scale,z[4:6]);parts=[(pred-q).ravel()]
  cam_center=R@np.asarray(f['center']);ray=np.array([-cam_center[0],-cam_center[1],D-cam_center[2]]);ray/=np.linalg.norm(ray);parts.append([max(0,.02-(R@normal)@ray)*visible_penalty])
  if obsHull is not None:
   pp=project(V,R,scale,z[4:6]);hp=pp[ConvexHull(pp).vertices];parts.extend([dist(samples(hp),obsHull)*.55,dist(obsSamples,hp)*.55])
  for face,pt in centers:
   parts.append((project([face['center']],R,scale,z[4:6])[0]-pt)*.25)
   n=R@np.asarray(face['n']);c=R@np.asarray(face['center']);r=np.array([-c[0],-c[1],D-c[2]]);r/=np.linalg.norm(r);parts.append([max(0,.01-n@r)*visible_penalty])
  return np.concatenate(parts)
 u=(facepts[1]-facepts[0]);u/=np.linalg.norm(u);v=np.cross(normal,u);base=np.array([u,v,normal]);pc=p@base.T;pc=pc[:,:2]-np.mean(pc[:,:2],axis=0)
 coarse=[];bounds=([-12]*3+[math.log(.01),-2*W,-2*H],[12]*3+[math.log(1e6),3*W,3*H]);loss=annotation.get('loss','soft_l1')
 if loss not in ('linear','soft_l1','huber'):raise ValueError('不支持的loss')
 fscale=max(1,diag*.002);calls=0
 for shift,q in enumerate(targets):
  qc=(q-q.mean(axis=0))*[1,-1];angle=math.atan2(np.sum(pc[:,0]*qc[:,1]-pc[:,1]*qc[:,0]),np.sum(pc*qc));spin=Rotation.from_rotvec([0,0,angle]).as_matrix();candidates=[]
  for tilt in [[0,0,0],[.65,0,0],[-.65,0,0],[0,.65,0],[0,-.65,0]]:
   R=spin@Rotation.from_rotvec(tilt).as_matrix()@base;pred0=project(p,R,1,[0,0]);ss=np.sqrt(np.sum((q-q.mean(axis=0))**2)/max(np.sum((pred0-pred0.mean(axis=0))**2),1e-10));off=q.mean(axis=0)-pred0.mean(axis=0)*ss;z=np.r_[Rotation.from_matrix(R).as_rotvec(),np.log(ss),off];candidates.append((np.linalg.norm(objective(z,q)),z))
  # One best geometric initialization per cyclic correspondence, then refine only the best three.
  z=min(candidates,key=lambda a:a[0])[1];fit=least_squares(objective,z,args=(q,),bounds=bounds,max_nfev=45,loss=loss,f_scale=fscale);calls+=fit.nfev;coarse.append((np.linalg.norm(objective(fit.x,q)),fit.x,q,shift))
 refined=[]
 for _,z,q,shift in sorted(coarse,key=lambda a:a[0])[:3]:
  opt=least_squares(objective,z,args=(q,),bounds=bounds,max_nfev=150,loss=loss,f_scale=fscale);calls+=opt.nfev;refined.append((np.linalg.norm(objective(opt.x,q)),opt.x,q,shift))
 refined.sort(key=lambda a:a[0]);score,z,q,shift=refined[0];R=Rotation.from_rotvec(z[:3]).as_matrix();scale=float(np.exp(z[3]));pred=project(p,R,scale,z[4:6]);rmse=float(np.sqrt(np.mean(np.sum((pred-q)**2,axis=1))))
 c=R@np.asarray(f['center']);front=float((R@normal)@[-c[0],-c[1],D-c[2]])>0
 if not front:raise ValueError('最优解将所标晶面置于背面；核对面ID、轴向或镜像，不自动翻转实物')
 for face,pt in centers:
  cc=R@np.asarray(face['center']);nn=R@np.asarray(face['n'])
  if float(nn@[-cc[0],-cc[1],D-cc[2]])<=0:raise ValueError('另一个已知编号面落在背面；当前对应有冲突，需核对面号、镜像或构形')
 holdouts=annotation.get('holdout',[]);held=[]
 for h in holdouts:
  vi=h['vertex_id']
  if not isinstance(vi,int) or not 0<=vi<len(V):raise ValueError('留出顶点索引无效')
  fitted=annotation.get('vertex_ids',f['ids'])
  if vi in fitted:raise ValueError('留出顶点不能同时用于拟合；请选另一面的独立角点')
  pt=xy([h['xy']],1)[0];held.append(float(np.linalg.norm(project([V[vi]],R,scale,z[4:6])[0]-pt)))
 alternatives=[{'cyclic_shift':s,'objective':float(cost),'rmse':float(np.sqrt(np.mean(np.sum((project(p,Rotation.from_rotvec(zz[:3]).as_matrix(),np.exp(zz[3]),zz[4:6])-qq)**2,axis=1))))} for cost,zz,qq,s in refined]
 ambiguous=any(s!=shift and cost<=score*1.05+diag*.001 for cost,zz,qq,s in refined[1:]);warnings=[]
 if ambiguous:warnings.append('存在误差接近的不同角点对应；须用另一视角或明确面编号消歧')
 if not held:warnings.append('未提供留出角点；当前误差是拟合误差，不是独立精度验收')
 if rmse/diag>.02:warnings.append('角点偏差超过图像对角线2%，应检查构形、编号、镜像或角点')
 if not outline.size:warnings.append('缺少外轮廓约束，单面配准不保证整块模型吻合')
 view={'face':fi,'R':R.tolist(),'scale':scale,'offset':z[4:6].tolist(),'D':D,'observed':q.tolist(),'predicted':pred.tolist(),'rmse':rmse,'imageSize':[W,H],'sourceSize':[W,H],'silhouette':outline.tolist() if len(outline) else None,'fitMetric':'corners','fit':'确定性粗到细、多起点、稳健损失；不自动尝试镜像','fitVertexIds':annotation.get('vertex_ids',f['ids']),'status':'candidate_ambiguous' if ambiguous else 'candidate_fit','warnings':warnings}
 return {'view':view,'quality':{'rmse_pixels':rmse,'normalized_rmse':rmse/diag,'holdout_errors_pixels':held,'holdout_rmse_pixels':float(np.sqrt(np.mean(np.square(held)))) if held else None,'ambiguity':ambiguous,'alternatives':alternatives,'warnings':warnings},'performance':{'elapsed_seconds':time.perf_counter()-start,'nfev_reported':calls,'starts':len(targets),'refinements':len(refined)},'annotation':annotation,'engine':'scipy-least_squares-coarse-to-fine-v1'}
