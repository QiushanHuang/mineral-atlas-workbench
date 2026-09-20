"""Repeatable CPU geometry benchmark against a supplied legacy mesh() source (read-only)."""
import sys,pathlib,argparse,json,time,statistics,ast,itertools
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import mesh,build,norm,sub
from atlas.project import ROOT,build_project,write_json,source_hash
p=argparse.ArgumentParser();p.add_argument('--legacy',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,default=ROOT/'evaluation/benchmark.json');a=p.parse_args()
specs=json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding="utf-8"));models=[build(s)[0] for s in specs];old=None
if a.legacy:
 import numpy as np
 tree=ast.parse(a.legacy.read_text(encoding="utf-8"));node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='mesh');env={'np':np,'itertools':itertools};exec(compile(ast.Module(body=[node],type_ignores=[]),str(a.legacy),'exec'),env);old=env['mesh']
rows=[]
for spec,m in zip(specs,models):
 planes=[dict(n=f['n'],d=f['d'],id=f['id']) for f in m['faces']];times={'candidate':[],'baseline':[]}
 for repeat in range(3):
  for mode in (['baseline','candidate'] if repeat%2==0 else ['candidate','baseline']):
   if mode=='baseline' and not old:continue
   start=time.perf_counter();got=old([(f['n'],f['d'],'face') for f in planes]) if mode=='baseline' else mesh(planes)[0];times[mode].append(time.perf_counter()-start)
   assert len(got['faces'])==len(m['faces']) and len(got['vertices'])==len(m['vertices'])
   assert max(min(norm(sub(v,q)) for q in m['vertices']) for v in got['vertices'])<1e-7
 row={'id':spec['id'],'faces':len(m['faces']),'candidate_seconds':statistics.median(times['candidate']),'baseline_seconds':statistics.median(times['baseline']) if times['baseline'] else None};rows.append(row)
import tempfile
with tempfile.TemporaryDirectory() as d:
 cold=[build_project(s,d)['elapsed_seconds'] for s in specs];warm=[build_project(s,d)['elapsed_seconds'] for s in specs]
result={'type':'algorithm_benchmark','scope':'15 fixed reference shapes / same normals and support distances / 3 alternating repeats','source_hash':source_hash(),'rows':rows,'total_candidate_seconds':sum(r['candidate_seconds'] for r in rows),'total_baseline_seconds':sum(r['baseline_seconds'] or 0 for r in rows),'cold_pipeline_seconds':sum(cold),'warm_cached_pipeline_seconds':sum(warm),'quality':'same face/vertex counts and vertex sets within1e-7; candidate additionally rejects recession rays','token_metrics':None,'limitations':['CPU smoke benchmark, not a broad performance ranking','No claim of OCR/model accuracy or LLM token savings','Same geometry inputs; entire old human workflow is not timed']}
a.output.parent.mkdir(parents=True,exist_ok=True);write_json(a.output,result);print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2))
