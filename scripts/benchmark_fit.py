"""Two fixed 451 photo observations: legacy and candidate, alternating runs in the same process."""
import pathlib,sys,json,tempfile,shutil,io,contextlib,time,statistics,importlib.util
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.project import ROOT,write_json,source_hash
from atlas.core import build
from atlas.fit import fit_view
legacy=pathlib.Path(sys.argv[1]).resolve();source=legacy/'scripts/fit_lab4_views.py';results=[]
with tempfile.TemporaryDirectory() as td:
 tmp=pathlib.Path(td);(tmp/'scripts').mkdir();shutil.copy2(source,tmp/'scripts/fit_lab4_views.py');shutil.copy2(legacy/'models.json',tmp/'models.json');(tmp/'views.json').write_text('{}', encoding="utf-8");shutil.copytree(legacy/'photos/451',tmp/'photos/451')
 spec=next(s for s in json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding="utf-8")) if s['id']=='451');model,_=build(spec)
 module_spec=importlib.util.spec_from_file_location('atlas_legacy_fit',tmp/'scripts/fit_lab4_views.py');old=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(old);oldargv=sys.argv;sys.argv=['baseline','451'];ann=[]
 for photo,num,pts,outline,centers in old.OBS['451']:ann.append({'face_id':f'F{num:02d}','image_size':[960,1280],'mode':'cyclic','points':pts,'silhouette':outline,'face_centers':{f'F{k:02d}':v for k,v in centers.items()},'loss':'linear'})
 try:
  for repeat in range(3):
   row={}
   for mode in (['baseline','candidate'] if repeat%2==0 else ['candidate','baseline']):
    start=time.perf_counter()
    if mode=='baseline':
     with contextlib.redirect_stdout(io.StringIO()):old.main()
     row['baseline_seconds']=time.perf_counter()-start;row['baseline_rmse_native']=[v['rmse']/1.425 for v in json.loads((tmp/'views.json').read_text(encoding="utf-8"))['451']]
    else:
     r=[fit_view(model,a) for a in ann];row['candidate_seconds']=time.perf_counter()-start;row['candidate_rmse_native']=[v['quality']['rmse_pixels'] for v in r]
   assert all(x<=y+1 for x,y in zip(row['candidate_rmse_native'],row['baseline_rmse_native'])),row
   results.append(row)
 finally:sys.argv=oldargv
out={'type':'algorithm_benchmark','source_hash':source_hash(),'scope':'two451photoobservations, same geometry, native-pixel corner RMSE, linear loss, 3 alternating repeats','baseline_seconds':statistics.median(r['baseline_seconds'] for r in results),'candidate_seconds':statistics.median(r['candidate_seconds'] for r in results),'trials':results,'limitations':['Center/visibility weighting and initialization differ intentionally; not identical objective functions','No independent photo holdout exists in these two source observations','Synthetic known-camera holdout is tested separately','Not a broad performance or recognition-accuracy benchmark']}
write_json(ROOT/'evaluation/fit-benchmark.json',out);print(json.dumps(out,indent=2))
