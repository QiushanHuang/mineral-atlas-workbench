"""Reproducible synthetic photo-first validation; no private images or annotations."""
import argparse,base64,json,pathlib,sys,math
import numpy as np,cv2
from PIL import Image,ImageDraw
from scipy.spatial.transform import Rotation
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,default=root/'evaluation/photo-modeling-v2/synthetic');args=p.parse_args()
from atlas.core import build
from atlas.images import from_photos
from atlas.project import source_hash
bank=json.loads((root/'examples/reference-atlas.json').read_text());out=args.out;out.mkdir(exist_ok=True);rows=[];fingerprint=source_hash();rng=np.random.default_rng(20260922)
for spec in bank:
 m,_=build(spec);V=np.array(m['vertices']);radius=np.linalg.norm(V,axis=1).max();D=8*radius
 for j in range(2):
  R=Rotation.from_rotvec(rng.normal(size=3)*1.5).as_matrix();q=V@R.T;xy=q[:,:2]*[1,-1]/(1-q[:,2,None]/D);scale=min(250/np.ptp(xy[:,0]),290/np.ptp(xy[:,1]));xy=(xy-(xy.max(axis=0)+xy.min(axis=0))/2)*scale+[240,265]
  im=Image.new('RGB',(480,560),(194,210,216));d=ImageDraw.Draw(im);d.ellipse((215,300,410,550),fill=(184,125,93));truth=np.zeros((560,480),'uint8')
  for f in sorted(m['faces'],key=lambda f:(R@f['center'])[2]):
   c=R@f['center'];n=R@f['n']
   if n@[-c[0],-c[1],D-c[2]]<=0:continue
   pts=xy[f['ids']];shade=int(80+70*max(0,n@np.array([.2,.4,.87])));d.polygon([tuple(p) for p in pts],fill=(shade,shade,shade-5),outline=(60,65,59),width=1);cv2.fillPoly(truth,[np.round(pts).astype('int32')],1)
  path=out/f'{spec["id"]}-{j}.png';im.save(path);r=from_photos([base64.b64encode(path.read_bytes()).decode()]);rank=[x['template_id'] for x in r['ranking']].index(spec['id'])+1;found=np.zeros_like(truth);cv2.fillPoly(found,[np.round(r['observations'][0]['silhouette']).astype('int32')],1);iou=float(np.logical_and(found,truth).sum()/np.logical_or(found,truth).sum());row={'id':spec['id'],'view':j,'rank':rank,'iou':iou,'best':r['ranking'][0]};rows.append(row);print(spec['id'],j,rank,round(iou,3),flush=True)
  (out/'progress.json').write_text(json.dumps(rows,indent=2))
(out/'summary.json').write_text(json.dumps({'source_hash':fingerprint,'scope':'synthetic closed-set unseen poses; seed fixed before evaluation; no parameter tuning on these renders','cases':len(rows),'top1':sum(r['rank']==1 for r in rows),'top3':sum(r['rank']<=3 for r in rows),'median_iou':float(np.median([r['iou'] for r in rows])),'rows':rows},indent=2))

if sum(r['rank']<=3 for r in rows)<27:raise SystemExit("Synthetic top-3 regression: fewer than 27/30 known templates recovered")
if np.median([r['iou'] for r in rows])<.9:raise SystemExit("Synthetic silhouette regression")
