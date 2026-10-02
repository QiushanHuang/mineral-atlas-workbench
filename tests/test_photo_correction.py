import base64
import hashlib
import json
import unittest
from pathlib import Path
from atlas.photo_annotations import validate_annotation

ROOT=Path(__file__).resolve().parents[1]

class Alignment(unittest.TestCase):
    def test_suspected_partial_outline_is_not_fitted_as_complete(self):
        import importlib.util
        if not all(importlib.util.find_spec(n) for n in ('numpy','scipy','PIL','cv2')):self.skipTest('optional dependencies')
        from unittest.mock import patch
        from atlas.editor import execute_editor
        from atlas.photo_candidates import extract_outline
        from atlas.photo_alignment import align_photo
        image=base64.b64encode((ROOT/'examples/synthetic.png').read_bytes()).decode()
        observation=extract_outline(image);observation['solidity']=.7
        draft=execute_editor({'action':'import','spec':json.loads((ROOT/'examples/cube.json').read_text())})['draft']
        with patch('atlas.photo_alignment.extract_outline',return_value=observation):
            self.assertEqual(align_photo(draft,image)['view']['fitMetric'],'partial_silhouette')

    def test_current_v2_model_is_aligned_without_changing_draft(self):
        import importlib.util
        if not all(importlib.util.find_spec(n) for n in ('numpy','scipy','PIL','cv2')):
            self.skipTest('optional photo dependencies not installed')
        self.assertTrue((ROOT/'atlas/photo_alignment.py').exists(),'current editable model can be aligned from the same photo corrections')
        from atlas.photo_alignment import align_photo
        from atlas.editor import execute_editor, fingerprint
        raw=(ROOT/'examples/synthetic.png').read_bytes()
        old=json.loads((ROOT/'examples/synthetic-annotation.json').read_text())
        model=execute_editor({'action':'import','spec':json.loads((ROOT/'examples/cube.json').read_text())})
        a={'schema_version':1,'source_sha256':hashlib.sha256(raw).hexdigest(),'image_size':old['image_size'],
           'features':[{'id':'A1','kind':'silhouette','points':old['silhouette']},
                       {'id':'A2','kind':'face','points':old['points']}]}
        result=align_photo(model['draft'],base64.b64encode(raw).decode(),a)
        self.assertEqual(result['model_fingerprint'],fingerprint(model['draft']))
        self.assertEqual(result['source_sha256'],a['source_sha256'])
        self.assertTrue(result['projected_edges'])
        self.assertGreaterEqual(result['metrics']['manual_faces_used'],1)
        self.assertIsNone(result['independent_validation'])
        self.assertEqual(fingerprint(model['draft']),model['fingerprint'])

class Provenance(unittest.TestCase):
    def test_accepted_region_evidence_survives_validation(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow not installed')
        raw=(ROOT/'examples/synthetic.png').read_bytes()
        annotation={'schema_version':1,'image_size':[800,600],'source_sha256':hashlib.sha256(raw).hexdigest(),
            'features':[{'id':'A1','kind':'face','points':[[100,100],[300,100],[200,250]],'evidence':'本地图像建议，经用户采纳；不是实物测定'}]}
        self.assertEqual(validate_annotation(annotation,raw)['features'][0]['evidence'],annotation['features'][0]['evidence'])
        annotation['features'][0]['evidence']='x'*2001
        with self.assertRaises(ValueError):validate_annotation(annotation,raw)

if __name__=='__main__':unittest.main()
