"""Reproduce the authorized 451 photo example. Default exports saved fits; --refit needs NumPy/SciPy."""
import argparse,pathlib,json,sys,shutil,html,hashlib,platform
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build
from atlas.project import ROOT,write_json,report,source_hash
p=argparse.ArgumentParser();p.add_argument('--refit',action='store_true');p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('atlas-runs/451-photo-study'));a=p.parse_args()
d=ROOT/'examples/451-photo-study';spec=json.loads((d/'project.json').read_text(encoding='utf-8'));manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'));m,q=build(spec);views=[];photos=[];fit_qualities={}
for photo in manifest['photos']:
 raw=(d/photo['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==photo['sha256'],photo['id'];number=int(photo['id']);photos.append({'number':number,'path':photo['path']})
 if not photo['annotation']:continue
 ann=json.loads((d/photo['annotation']).read_text(encoding='utf-8'))
 if a.refit:
  import numpy,scipy
  from atlas.fit import fit_view
  result=fit_view(m,ann);result.pop('performance',None);result['environment']={'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__};result['input_photo_sha256']=photo['sha256'];result['source_sha256']=source_hash();write_json(d/f'fits/{photo["id"]}.json',result)
 else:result=json.loads((d/f'fits/{photo["id"]}.json').read_text(encoding='utf-8'))
 assert result['input_photo_sha256']==photo['sha256'];views.append(dict(result['view'],photo=number));fit_qualities[photo['id']]=result['quality']
# Exact vertices and face IDs used by the saved camera records remain reviewable.
if a.refit:write_json(d/'model.json',m);write_json(d/'quality.json',q)
# Deterministic vector figure: no photographic pixels are edited or invented.
v=views[0]
def project(pt):
 c=[sum(x*y for x,y in zip(row,pt)) for row in v['R']];return [c[0]*v['scale']/(1-c[2]/v['D'])+v['offset'][0],-c[1]*v['scale']/(1-c[2]/v['D'])+v['offset'][1]]
projected=[project(pt) for pt in m['vertices']];xs=[p[0] for p in projected];ys=[p[1] for p in projected];s=min(850/(max(xs)-min(xs)),430/(max(ys)-min(ys)));cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
screen=lambda xy:(480+(xy[0]-cx)*s,330+(xy[1]-cy)*s)
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="640" viewBox="0 0 960 640"><rect width="960" height="640" rx="18" fill="#eef3eb"/><g font-family="system-ui,sans-serif" fill="#183b32"><text x="40" y="48" font-size="24" font-weight="700">451 / Indexed reference model</text><text x="40" y="80" font-size="16">Photo 01 pose · selected F01 · four-index labels</text>']
for f in sorted(m['faces'],key=lambda f:sum(x*y for x,y in zip(v['R'][2],f['center']))):
 n=[sum(x*y for x,y in zip(row,f['n'])) for row in v['R']];c=[sum(x*y for x,y in zip(row,f['center'])) for row in v['R']]
 if n[0]*-c[0]+n[1]*-c[1]+n[2]*(v['D']-c[2])<=0:continue
 ps=[screen(projected[i]) for i in f['ids']];col='#d3a557' if f['id']=='F01' else '#a6bca6';svg.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in ps)+'" fill="'+col+'" stroke="#234e3e" stroke-width="3"/>');x,y=screen(project(f['center']));text=f['id']+' ('+' '.join(map(str,f['modelMiller']))+')';svg.append(f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" font-size="18" font-weight="700">{html.escape(text)}</text>')
svg.append('<text x="40" y="586" font-size="16">6 faces · trigonal · reference -3m · provisional opposite-face labels</text><text x="40" y="616" font-size="14">Indices follow an assumed basis; this is not a measured mineral identification.</text></g></svg>');
if a.refit:(d/'model-preview.svg').write_text(''.join(svg),encoding='utf-8')
out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
for name in ['photos','annotations','fits']:shutil.copytree(d/name,out/name,dirs_exist_ok=True)
for name in ['project.json','manifest.json','model.json','quality.json','README.md','DATA_NOTICE.md','model-preview.svg']:shutil.copy2(d/name,out/name)
shutil.copy2(d/'project.json',out/'input.json');shutil.copy2(ROOT/'assets/logo.png',out/'logo.png');shutil.copy2(ROOT/'LICENSE',out/'LICENSE')
for src,dst in [('viewer.html','index.html'),('viewer.js','viewer.js'),('style.css','style.css')]:shutil.copy2(ROOT/'templates'/src,out/dst)
data={'models':{'451':m},'views':{'451':views},'photos':{'451':photos}};(out/'data.js').write_text('const DATA = '+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf-8');(out/'report.html').write_text(report(m,q,spec),encoding='utf-8')
write_json(out/'receipt.json',{'dataset':manifest['dataset_id'],'source_sha256':source_hash(),'photographs':manifest['photos'],'fit_quality':fit_qualities,'claim_level':'reference_model','fit_mode':'freshly_refit' if a.refit else 'saved_fit_replay'})
print(json.dumps({'output':str(out),'faces':len(m['faces']),'photos':len(photos),'fitted_photos':len(views),'rmse_pixels':{k:v['rmse_pixels'] for k,v in fit_qualities.items()}},ensure_ascii=False,indent=2))
