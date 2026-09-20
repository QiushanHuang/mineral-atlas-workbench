import unittest,json,pathlib,sys,copy,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import *
ROOT=pathlib.Path(__file__).resolve().parents[1]
CUBE={'schema_version':1,'id':'cube','crystal_system':'等轴','point_group':'m-3m','index_count':3,'basis':[[0,1,0],[0,0,1],[1,0,0]],'expected_faces':6,'forms':[{'hkl':[1,0,0],'distance':1}]}
class Core(unittest.TestCase):
 def test_cube_oracle(self):
  m,q=build(CUBE);self.assertEqual((q['vertices'],q['edges'],q['faces']),(8,12,6));self.assertAlmostEqual(q['volume'],8)
  self.assertEqual({tuple(round(x) for x in v) for v in m['vertices']},set(itertools.product([-1,1],repeat=3)))
 def test_invalid_indices(self):
  self.assertEqual(indices('1̅ 0 1 0',4),[-1,0,1,0]);self.assertEqual(indices('(2 0 -2 0)',4),[1,0,-1,0])
  for x in ['(1 1 1 0)','(0 0 0 0)','[1000]','1.5 0 -1.5 0']:
   with self.assertRaises(ValueError):indices(x,4)
 def test_group_orders(self):
  orders=[1,2,2,2,4,4,4,8,4,4,8,8,8,8,16,3,6,6,6,12,6,6,12,12,12,12,24,12,24,24,24,48]
  self.assertEqual([len(canonical_ops(p)) for p in GENERATORS],orders)
 def test_all32_groups_closed_geometry(self):
  specs=json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding="utf-8"));by_system={s['crystal_system']:s for s in specs}
  for pg,system in GROUP_SYSTEM.items():
   base=by_system[system];A=base['basis'];count=base['index_count'];ops=operations(pg,A);rows={}
   for seed in [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1],[1,2,3]]:
    h=[seed[0],seed[1],-seed[0]-seed[1],seed[2]] if count==4 else seed
    for index in orbit(h,A,ops,count):rows[index]={'hkl':list(index),'distance':1,'expand':False}
   model,q=build({'schema_version':1,'id':'group-test','crystal_system':system,'point_group':pg,'index_count':count,'basis':A,'faces':list(rows.values())});self.assertTrue(q['ok'],pg)
 def test_reject_unbounded_and_inactive(self):
  s=copy.deepcopy(CUBE);s['point_group']='23';s['forms']=[{'hkl':[1,1,1],'distance':1}];m,q=build({k:v for k,v in s.items() if k!='expected_faces'});self.assertEqual(q['faces'],4)
  s=copy.deepcopy(CUBE);s.pop('forms');s['faces']=[{'hkl':h,'distance':1} for h in [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0]]]
  with self.assertRaisesRegex(ValueError,'有界'):build(s)
  s=copy.deepcopy(CUBE);s['forms'].append({'hkl':[1,1,1],'distance':10})
  with self.assertRaisesRegex(ValueError,'截去'):build(s)
 def test_basis_metric_and_corruption(self):
  s=copy.deepcopy(CUBE);s['basis'][2][0]=2
  with self.assertRaises(ValueError):build(s)
  m,q=build(CUBE);m['vertices'][0][0]+=.1;self.assertFalse(validate(m)['ok'])
 def test_legacy_migration(self):
  bundle=ROOT/'examples'/'reference-atlas.json'
  self.assertTrue(bundle.exists())
  specs=json.loads(bundle.read_text(encoding="utf-8"));self.assertEqual(len(specs),15)
  for s in specs:
   m,q=build(s);self.assertEqual(q['faces'],s['expected_faces'],s['id']);self.assertTrue(q['ok'])
   if s['id']=='7518':self.assertEqual(len(m['splitRidges']),12)
if __name__=='__main__':unittest.main()
