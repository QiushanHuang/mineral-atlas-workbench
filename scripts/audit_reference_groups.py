"""Re-enumerate geometric symmetries independently of declared operations, without NumPy."""
import sys,pathlib,itertools,json,collections
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build,det,tr,inv,mm,mv,dot,norm,sub,canonical_ops,keymat
from atlas.point_groups import GROUPS,elements
ROOT=pathlib.Path(__file__).resolve().parents[1]
def signature(ops):return tuple(sorted(collections.Counter((round(det(T)),round(sum(T[i][i] for i in range(3)),6)) for T in ops).items()))
def enumerate_geometry(V):
 ids=max(itertools.combinations(range(min(len(V),12)),3),key=lambda ix:abs(det([V[i] for i in ix])))
 B=tr([V[i] for i in ids]);G=mm(tr(B),B);candidates=[[i for i,v in enumerate(V) if abs(dot(v,v)-G[j][j])<1e-7] for j in range(3)];out={};Bi=inv(B)
 for ix in itertools.product(*candidates):
  if len(set(ix))<3:continue
  C=tr([V[i] for i in ix]);gram=mm(tr(C),C)
  if any(abs(gram[i][j]-G[i][j])>1e-7 for i in range(3) for j in range(3)):continue
  T=mm(C,Bi)
  if all(min(norm(sub(mv(T,v),q)) for q in V)<1e-7 for v in V):out[keymat(T)]=T
 return list(out.values())
def audit(specs):
 signatures={signature(canonical_ops(pg)):pg for pg in GROUPS};assert len(signatures)==32
 rows=[]
 for spec in specs:
  m,q=build(spec);actual=enumerate_geometry(m['vertices']);observed=signatures.get(signature(actual));declared=spec['point_group']
  rows.append({'id':spec['id'],'faces':len(m['faces']),'crystal_system':spec['crystal_system'],'declared':declared,'geometry_group':observed,'textbook':GROUPS[declared]['textbook'],'elements':elements(actual),'matches_reference_claim':observed==declared,'claim_level':'reference_model','limits':'Geometry symmetry is not specimen identification; photo-label ambiguities remain as supplied.'})
 return rows
if __name__=='__main__':
 rows=audit(json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding='utf-8')))
 (ROOT/'docs/reference-point-group-audit.json').write_text(json.dumps({'scope':'15 reference models, independently enumerated geometric operations','results':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for r in rows:print(r['id'],r['geometry_group'],r['textbook'],r['matches_reference_claim'])
 if not all(r['matches_reference_claim'] for r in rows):raise SystemExit('Reference point-group discrepancy')
