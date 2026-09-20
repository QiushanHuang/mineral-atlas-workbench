import unittest,json,pathlib,sys,importlib.util,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build
from atlas.fit import fit_view
ROOT=pathlib.Path(__file__).resolve().parents[1]
@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('scipy'),'optional NumPy/SciPy not installed')
class Fit(unittest.TestCase):
 def setUp(self):
  import numpy as np
  from scipy.spatial.transform import Rotation
  s=json.loads((ROOT/'examples/cube.json').read_text(encoding="utf-8"));self.model,_=build(s);V=np.array(self.model['vertices']);self.R=Rotation.from_rotvec([.28,-.4,.12]).as_matrix();self.D=8*max(np.linalg.norm(V,axis=1));self.scale=190;self.offset=np.array([400,300]);q=V@self.R.T;self.xy=q[:,:2]*[1,-1]*self.scale/(1-q[:,2,None]/self.D)+self.offset
  self.fi=next(i for i,f in enumerate(self.model['faces']) if (self.R@f['n'])[2]>.8);f=self.model['faces'][self.fi];self.ann={'face_id':f['id'],'image_size':[800,600],'points':self.xy[f['ids']].tolist(),'mode':'correspondences','vertex_ids':f['ids'],'holdout':[{'vertex_id':i,'xy':self.xy[i].tolist()} for i in range(len(V)) if i not in f['ids']]}
 def test_known_camera_and_independent_holdout(self):
  a=fit_view(self.model,self.ann);self.assertLess(a['quality']['rmse_pixels'],.01);self.assertLess(a['quality']['holdout_rmse_pixels'],.1)
  b=fit_view(self.model,self.ann);self.assertEqual(a['view'],b['view'])
 def test_leakage_and_wrong_count(self):
  self.ann['holdout'][0]['vertex_id']=self.ann['vertex_ids'][0]
  with self.assertRaisesRegex(ValueError,'留出'):fit_view(self.model,self.ann)
  self.ann['mode']='cyclic';self.ann['points'].pop()
  with self.assertRaises(ValueError):fit_view(self.model,self.ann)
if __name__=='__main__':unittest.main()
