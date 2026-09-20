import unittest,pathlib,json,hashlib,math,tempfile,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from atlas.core import build,mv
D=ROOT/'examples/451-photo-study'
class PhotoExample(unittest.TestCase):
 def test_authorized_set_and_saved_projection(self):
  manifest=json.loads((D/'manifest.json').read_text(encoding='utf-8'));self.assertEqual(len(manifest['photos']),3);self.assertEqual(manifest['shared_by'],'QiushanHuang');self.assertFalse(manifest['physical_indices_verified']);model,_=build(json.loads((D/'project.json').read_text(encoding='utf-8')))
  for photo in manifest['photos']:
   self.assertEqual(hashlib.sha256((D/photo['path']).read_bytes()).hexdigest(),photo['sha256'])
   if not photo['annotation']:self.assertEqual(photo['role'],'additional_observation_only');continue
   fit=json.loads((D/f'fits/{photo["id"]}.json').read_text(encoding='utf-8'));v=fit['view'];f=model['faces'][v['face']];pred=[]
   for i in f['ids']:
    p=mv(v['R'],model['vertices'][i]);pred.append([p[0]*v['scale']/(1-p[2]/v['D'])+v['offset'][0],-p[1]*v['scale']/(1-p[2]/v['D'])+v['offset'][1]])
   self.assertLess(max(abs(a-b) for p,q in zip(pred,v['predicted']) for a,b in zip(p,q)),1e-6)
   rms=math.sqrt(sum(sum((a-b)**2 for a,b in zip(p,q)) for p,q in zip(pred,v['observed']))/len(pred));self.assertAlmostEqual(rms,fit['quality']['rmse_pixels']);self.assertIsNone(fit['quality']['holdout_rmse_pixels'])
 def test_standard_library_export(self):
  with tempfile.TemporaryDirectory() as tmp:
   subprocess.run([sys.executable,str(ROOT/'scripts/build_photo_example.py'),'--out',tmp],check=True,stdout=subprocess.DEVNULL)
   out=pathlib.Path(tmp);data=json.loads((out/'data.js').read_text(encoding='utf-8').removeprefix('const DATA = ').rstrip(';\n'))
   self.assertEqual(len(data['photos']['451']),3);self.assertEqual([v['photo'] for v in data['views']['451']],[1,2]);self.assertTrue((out/'DATA_NOTICE.md').is_file());self.assertTrue((out/'index.html').is_file())
if __name__=='__main__':unittest.main()
