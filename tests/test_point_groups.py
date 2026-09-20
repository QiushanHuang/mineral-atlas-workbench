import unittest,copy,json,pathlib,tempfile,zipfile
from atlas.core import build,validate,canonical_ops,GENERATORS
from atlas.point_groups import GROUPS,elements
from atlas.project import build_project,ROOT
class Standards(unittest.TestCase):
 def test_complete_catalogue(self):
  self.assertEqual(set(GROUPS),set(GENERATORS));self.assertEqual(len(GROUPS),32)
  for pg,g in GROUPS.items():
   e=elements(canonical_ops(pg));self.assertEqual(e['order'],g['order'],pg);self.assertEqual(e['mirrors'],g['mirrorCount'],pg)
 def test_correct_shorthand_and_preserve_original(self):
  spec=next(s for s in json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding='utf-8')) if s['id']=='671')
  spec=copy.deepcopy(spec);spec.setdefault('metadata',{})['symmetry']='Lᵢ⁶ 3L² 4P'
  m,q=build(spec);self.assertEqual(m['indexing']['symmetry'],'Lᵢ⁶ 3L² 3P');self.assertEqual(m['indexing']['originalSymmetry'],'Lᵢ⁶ 3L² 4P');self.assertEqual(m['indexing']['symmetryElements']['mirrors'],4);self.assertTrue(q['warnings'])
  bad=copy.deepcopy(m);bad['indexing']['operations']=[];self.assertFalse(validate(bad)['ok'])
  bad=copy.deepcopy(m);bad['indexing']['symmetry']='incorrect';self.assertFalse(validate(bad)['ok'])
  bad=copy.deepcopy(m);bad['indexing']['pointGroup']='7';self.assertFalse(validate(bad)['ok'])
 def test_export_contains_standard(self):
  spec=json.loads((ROOT/'examples/cube.json').read_text(encoding='utf-8'))
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(build_project(spec,d)['path'])
   with zipfile.ZipFile(p/'result.zip') as z:self.assertIn('point-groups-32.json',z.namelist());self.assertIn('point-groups.html',z.namelist())
   text=(p/'report.html').read_text(encoding='utf-8')
   for pg in GROUPS:self.assertIn('id="pg-'+pg+'"',text)
