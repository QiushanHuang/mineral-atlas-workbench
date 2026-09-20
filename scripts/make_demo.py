import pathlib,json,sys,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw
from atlas.core import build
from atlas.project import ROOT,write_json
spec=json.loads((ROOT/'examples/cube.json').read_text(encoding="utf-8"));m,q=build(spec);V=np.array(m['vertices']);R=Rotation.from_rotvec([.28,-.4,.12]).as_matrix();D=8*max(np.linalg.norm(V,axis=1));scale=190;offset=np.array([400,300]);P=V@R.T;screen=P[:,:2]*[1,-1]*scale/(1-P[:,2,None]/D)+offset
im=Image.new('RGB',(800,600),'#eaf0e7');draw=ImageDraw.Draw(im);draw.text((20,15),'SYNTHETIC CAMERA FIXTURE - NOT A MINERAL PHOTO',fill='#244737')
for f in sorted(m['faces'],key=lambda f:(R@np.array(f['center']))[2]):
 n=R@f['n'];c=R@f['center']
 if n@[-c[0],-c[1],D-c[2]]<=0:continue
 shade=int(150+70*n[2]);pts=[tuple(screen[i]) for i in f['ids']];draw.polygon(pts,fill=(shade-10,shade+5,shade-15),outline='#305542',width=3);ctr=screen[f['ids']].mean(axis=0);draw.text(tuple(ctr),f['id'],fill='#203d30')
for i,p in enumerate(screen):draw.text(tuple(p+[3,-15]),str(i),fill='#8d3d31')
im.save(ROOT/'examples/synthetic.png');fi=next(i for i,f in enumerate(m['faces']) if (R@f['n'])[2]>.8);f=m['faces'][fi]
from scipy.spatial import ConvexHull
annotation={'schema_version':1,'face_id':f['id'],'image_size':[800,600],'points':screen[f['ids']].tolist(),'mode':'cyclic','silhouette':screen[ConvexHull(screen).vertices].tolist(),'loss':'linear','holdout':[{'vertex_id':i,'xy':screen[i].tolist()} for i in range(len(V)) if i not in f['ids']],'evidence':'合成相机样例，有已知几何和留出点，仅用于验证流程'}
write_json(ROOT/'examples/synthetic-annotation.json',annotation)
