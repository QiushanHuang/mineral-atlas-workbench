"""Manual photo evidence remains bound to pixels and separate from automatic accuracy."""
import base64
import copy
import hashlib
import importlib.util
import io
import json
import unittest
from atlas.project import ROOT

OPTIONAL=all(importlib.util.find_spec(name) for name in ('cv2','numpy','scipy','PIL'))

@unittest.skipUnless(OPTIONAL,'optional photo dependencies not installed')
class PhotoAnnotations(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        stream=io.BytesIO();Image.new('RGB',(240,200),'white').save(stream,format='PNG')
        self.raw=stream.getvalue();self.image=base64.b64encode(self.raw).decode()
        self.annotation={'schema_version':1,'image_size':[240,200],
                         'source_sha256':hashlib.sha256(self.raw).hexdigest(),
                         'features':[{'id':'outline-1','kind':'silhouette','points':[[60,40],[180,40],[180,160],[60,160]]},
                                     {'id':'edge-1','kind':'edge','points':[[60,40],[120,90],[180,40]]},
                                     {'id':'face-1','kind':'face','face_id':'F01','points':[[60,40],[180,40],[120,90]]},
                                     {'id':'hidden-1','kind':'occlusion','points':[[70,130],[110,130],[110,160],[70,160]]},
                                     {'id':'unknown-1','kind':'uncertain','points':[[70,45],[90,65]]}]}

    def validator(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas.photo_annotations'),'manual annotation validator must exist')
        from atlas.photo_annotations import validate_annotation
        return validate_annotation

    def test_bound_contract_and_bad_inputs(self):
        validate=self.validator()
        result=validate(self.annotation,self.raw)
        self.assertEqual(result,self.annotation)
        variants=[]
        for key,value in [('source_sha256','0'*64),('image_size',[200,240]),('schema_version',True)]:
            bad=copy.deepcopy(self.annotation);bad[key]=value;variants.append(bad)
        for points in ([[0,0],[250,0],[0,10]],[[0,0],[float('nan'),1],[10,10]],[[0,0],[20,20],[0,20],[20,0]],[[0,0],[10,0],[20,0]]):
            bad=copy.deepcopy(self.annotation);bad['features'][0]['points']=points;variants.append(bad)
        bad=copy.deepcopy(self.annotation);bad['features'][1]['id']='outline-1';variants.append(bad)
        bad=copy.deepcopy(self.annotation);bad['features'].append(copy.deepcopy(bad['features'][0]));bad['features'][-1]['id']='outline-2';variants.append(bad)
        bad=copy.deepcopy(self.annotation);bad['features'][2]['face_id']='confirmed-110';variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):validate(bad,self.raw)

    def test_source_binding_uses_exif_display_size(self):
        from PIL import Image
        image=Image.new('RGB',(240,200),'white');exif=Image.Exif();exif[274]=6
        stream=io.BytesIO();image.save(stream,format='JPEG',exif=exif);raw=stream.getvalue()
        annotation=copy.deepcopy(self.annotation);annotation['source_sha256']=hashlib.sha256(raw).hexdigest()
        annotation['image_size']=[200,240]
        self.assertEqual(self.validator()(annotation,raw)['image_size'],[200,240])
        annotation['image_size']=[240,200]
        with self.assertRaisesRegex(ValueError,'EXIF'):self.validator()(annotation,raw)

    def test_face_model_fingerprint_is_validated_but_not_confirmed(self):
        from atlas.photo_annotations import apply_annotation
        annotation=copy.deepcopy(self.annotation);annotation['features'][2]['model_fingerprint']='a'*64
        try:validated=self.validator()(annotation,self.raw)
        except ValueError as error:self.fail(f'model-bound face hints must be accepted as unverified: {error}')
        result=apply_annotation(None,validated,self.raw)
        self.assertEqual(result['face_regions'][0]['model_fingerprint'],'a'*64)
        self.assertEqual(result['face_regions'][0]['model_binding_status'],'requires_model_verification')
        legacy=apply_annotation(None,self.annotation,self.raw)
        self.assertEqual(legacy['face_regions'][0]['model_binding_status'],'unbound')
        annotation['features'][2]['model_fingerprint']='not-a-model-hash'
        with self.assertRaisesRegex(ValueError,'model_fingerprint'):self.validator()(annotation,self.raw)

    def test_manual_outline_rescues_failed_segmentation_and_preserves_provenance(self):
        from atlas.photo_candidates import from_photos
        bank=[json.loads((ROOT/'examples/cube.json').read_text())]
        try:result=from_photos([self.image],bank=bank,evidence={'annotations':[self.annotation]})
        except ValueError as error:self.fail(f'manual outline must rescue automatic segmentation: {error}')
        observation=result['observations'][0]
        self.assertEqual(observation['mode'],'manual')
        self.assertEqual(observation['silhouette'],self.annotation['features'][0]['points'])
        self.assertEqual(observation['manual_annotation'],self.annotation)
        self.assertEqual(len(observation['manual_segments']),2)
        self.assertEqual(observation['face_regions'][0]['face_id'],'F01')
        self.assertEqual(len(observation['occlusion_regions']),1)
        self.assertEqual(len(observation['uncertain_features']),1)
        self.assertEqual(result['claim_level'],'template_candidates')
        self.assertIn('手工',''.join(observation['warnings']))

    def test_annotation_binding_errors_are_input_errors_not_bad_photos(self):
        from atlas.photo_candidates import from_photos
        bad=copy.deepcopy(self.annotation);bad['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SHA|sha|绑定'):
            from_photos([self.image],evidence={'annotations':[bad]})

    def test_manual_rescue_does_not_leak_into_unannotated_duplicate(self):
        from atlas.photo_candidates import from_photos
        bank=[json.loads((ROOT/'examples/cube.json').read_text())]
        try:result=from_photos([self.image,self.image],bank=bank,evidence={'annotations':[self.annotation,None]})
        except Exception as error:self.fail(f'unannotated duplicate should be retained as unusable: {error}')
        self.assertEqual([o['status'] for o in result['observations']],['usable','unusable'])

    def test_segment_metric_rejects_crossing_or_displaced_lines(self):
        from atlas import photo_candidates
        self.assertTrue(hasattr(photo_candidates,'segment_residuals'),'edge matching needs endpoint and direction residuals')
        import numpy as np
        predicted=[[[20,50],[180,50]]]
        aligned=photo_candidates.segment_residuals([[[40,50],[100,50]]],predicted,200)
        reversed_line=photo_candidates.segment_residuals([[[100,50],[40,50]]],predicted,200)
        crossing=photo_candidates.segment_residuals([[[100,20],[100,80]]],predicted,200)
        displaced=photo_candidates.segment_residuals([[[40,70],[100,70]]],predicted,200)
        self.assertLess(float(np.linalg.norm(aligned)),1e-10)
        self.assertLess(float(np.linalg.norm(reversed_line)),1e-10)
        self.assertGreater(float(np.linalg.norm(crossing)),.1)
        self.assertGreater(float(np.linalg.norm(displaced)),.05)

    def test_manual_edges_enter_fit_and_uncertain_features_do_not(self):
        import numpy as np
        from scipy.spatial import ConvexHull
        from scipy.spatial.transform import Rotation
        from atlas.core import build
        from atlas.photo_candidates import match_outline
        model,_=build(json.loads((ROOT/'examples/cube.json').read_text()))
        vertices=np.array(model['vertices']);rotation=Rotation.from_rotvec([.28,-.4,.12]).as_matrix()
        distance=8*np.linalg.norm(vertices,axis=1).max();camera=vertices@rotation.T
        projected=camera[:,:2]*[1,-1]*50/(1-camera[:,2,None]/distance)+[120,100]
        outline=projected[ConvexHull(projected).vertices].copy();outline[0]+=[8,-8]
        segments=[projected[edge['ids']].tolist() for edge in model['edges'] if all((rotation@model['faces'][face]['n'])[2]>.08 for face in edge['faces'])]
        observation={'image_size':[240,200],'silhouette':outline.tolist(),'segments':[]}
        plain=match_outline(model,observation)
        assisted=match_outline(model,dict(observation,manual_segments=segments))
        self.assertIn('manual_edge_error',assisted,'manual edges must constrain fitting, not just be stored')
        self.assertIsNotNone(assisted['manual_edge_error'])
        self.assertNotEqual(plain['view']['R'],assisted['view']['R'])
        uncertain=match_outline(model,dict(observation,uncertain_features=[{'points':[[0,0],[239,199]]}]))
        self.assertEqual(plain['view'],uncertain['view'])

    def face_fixture(self):
        import numpy as np
        from scipy.spatial import ConvexHull
        from scipy.spatial.transform import Rotation
        from atlas.core import build
        model,_=build(json.loads((ROOT/'examples/cube.json').read_text()))
        model['draftFingerprint']='a'*64
        for face in model['faces']:face['modelMiller']=None
        vertices=np.array(model['vertices']);rotation=Rotation.from_rotvec([.28,-.4,.12]).as_matrix()
        distance=8*np.linalg.norm(vertices,axis=1).max();camera=vertices@rotation.T
        projected=camera[:,:2]*[1,-1]*50/(1-camera[:,2,None]/distance)+[120,100]
        regions=[]
        for face in model['faces']:
            center=rotation@face['center'];normal=rotation@face['n']
            if float(normal@(np.array([0,0,distance])-center))>0:
                regions.append({'id':'region-'+face['id'],'kind':'face','points':projected[face['ids']].tolist(),'face_id':face['id'],'model_fingerprint':'a'*64})
        observation={'image_size':[240,200],'silhouette':projected[ConvexHull(projected).vertices].tolist(),'segments':[]}
        return model,observation,regions,projected,rotation,distance

    def test_projected_faces_have_zero_boundary_error_and_unique_assignments(self):
        from atlas import photo_candidates
        self.assertTrue(hasattr(photo_candidates,'match_face_regions'),'face geometry must be comparable independently of camera fitting')
        model,observation,regions,projected,rotation,distance=self.face_fixture()
        result=photo_candidates.match_face_regions(model,regions,projected,rotation,distance,200)
        self.assertEqual(result['manual_faces_used'],3)
        self.assertLess(result['manual_face_error'],1e-10)
        matches=result['face_matches']
        self.assertEqual(len({match['model_face_id'] for match in matches}),3)
        self.assertTrue(all(match['method']=='bound_face' for match in matches))
        self.assertTrue(all(match['visible'] for match in matches))
        self.assertTrue(all(match.get('status')=='candidate_match' for match in matches))
        duplicate=copy.deepcopy(regions[0]);duplicate['id']='duplicate-region'
        doubled=photo_candidates.match_face_regions(model,[regions[0],duplicate],projected,rotation,distance,200)
        self.assertEqual(doubled['manual_faces_used'],1)
        self.assertTrue(any(match.get('reason') for match in doubled['face_matches']))

    def test_stale_face_id_is_not_a_constraint_and_hidden_binding_is_not_matched(self):
        from atlas import photo_candidates
        self.assertTrue(hasattr(photo_candidates,'match_face_regions'),'face binding must be checked against current geometry')
        model,observation,regions,projected,rotation,distance=self.face_fixture()
        region=copy.deepcopy(regions[0]);original=region['face_id'];region['face_id']=regions[1]['face_id'];region['model_fingerprint']='b'*64
        result=photo_candidates.match_face_regions(model,[region],projected,rotation,distance,200)
        match=result['face_matches'][0]
        self.assertEqual(match['model_face_id'],original)
        self.assertEqual(match['binding_status'],'stale_model_binding_ignored')
        self.assertEqual(match['method'],'geometric_one_to_one')
        visible={item['face_id'] for item in regions};hidden=next(face['id'] for face in model['faces'] if face['id'] not in visible)
        region['model_fingerprint']='a'*64;region['face_id']=hidden
        result=photo_candidates.match_face_regions(model,[region],projected,rotation,distance,200)
        self.assertEqual(result['manual_faces_used'],0)
        self.assertIsNone(result['face_matches'][0]['model_face_id'])
        self.assertIn('不可见',result['face_matches'][0]['reason'])

    def test_faces_enter_camera_fit_and_score_without_claiming_holdout(self):
        import numpy as np
        from atlas.photo_candidates import match_outline
        model,observation,regions,projected,rotation,distance=self.face_fixture()
        observation['silhouette'][0][0]+=10
        plain=match_outline(model,observation)
        assisted=match_outline(model,dict(observation,face_regions=regions))
        self.assertIn('manual_face_error',assisted,'manual face regions must enter fitting')
        self.assertEqual(assisted['manual_faces_used'],3)
        self.assertNotEqual(plain['view']['R'],assisted['view']['R'])
        self.assertNotEqual(plain['score'],assisted['score'])
        def error(result):
            view=result['view'];vertices=np.array(model['vertices']);q=vertices@np.array(view['R']).T
            p=q[:,:2]*[1,-1]*view['scale']/(1-q[:,2,None]/view['D'])+view['offset']
            return float(np.mean([np.linalg.norm(p[face['ids']]-projected[face['ids']],axis=1).mean() for face in model['faces'] if face['id'] in {r['face_id'] for r in regions}]))
        self.assertLess(error(assisted),error(plain))
        self.assertTrue(all(match['model_face_id']==region['face_id'] for match,region in zip(assisted['face_matches'],sorted(regions,key=lambda r:r['id']))))
        self.assertIn('不是独立',''.join(assisted['view']['warnings']))

    def test_dense_face_boundaries_occlusion_and_limit_are_explicit(self):
        import numpy as np
        from atlas.photo_candidates import match_face_regions
        model,observation,regions,projected,rotation,distance=self.face_fixture()
        polygon=np.array(regions[0]['points']);dense=[]
        for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
            dense.extend((a+(b-a)*t).tolist() for t in np.arange(16)/16)
        region=dict(regions[0],points=dense)
        result=match_face_regions(model,[region],projected,rotation,distance,200)
        self.assertEqual(len(dense),64);self.assertLess(result['manual_face_error'],1e-10)
        hidden=match_face_regions(model,[region],projected,rotation,distance,200,occlusions=[{'points':[[0,0],[240,0],[240,200],[0,200]]}])
        self.assertEqual(hidden['manual_faces_used'],0)
        self.assertIn('遮挡',hidden['face_matches'][0]['reason'])
        many=[dict(region,id=f'region-{i:02d}') for i in range(17)]
        limited=match_face_regions(model,many,projected,rotation,distance,200)
        self.assertEqual(len(limited['face_matches']),17)
        self.assertTrue(any('16' in (match.get('reason') or '') for match in limited['face_matches']))
        self.assertTrue(any(match['ambiguity'] for match in limited['face_matches'] if match['model_face_id']))

    def test_unbound_faces_separate_cube_from_wrong_octahedron(self):
        from atlas.photo_candidates import match_outline
        from atlas.core import build
        model,observation,regions,*_=self.face_fixture()
        regions=[{'id':r['id'],'points':r['points']} for r in regions]
        observation['silhouette'][0][0]+=10
        spec=json.loads((ROOT/'examples/cube.json').read_text());spec['forms']=[{'hkl':[1,1,1],'distance':1}];spec.pop('expected_faces',None)
        wrong,_=build(spec)
        baseline_gap=match_outline(wrong,observation)['score']-match_outline(model,observation)['score']
        corrected=dict(observation,face_regions=regions)
        correct=match_outline(model,corrected);incorrect=match_outline(wrong,corrected)
        self.assertGreater(incorrect['score']-correct['score'],baseline_gap)
        self.assertTrue(all(match['method']=='geometric_one_to_one' for match in correct['face_matches']))

    def test_current_v2_model_bound_face_enters_camera_initialization(self):
        import numpy as np
        from scipy.spatial import ConvexHull
        from scipy.spatial.transform import Rotation
        from atlas.editor import execute_editor
        from atlas.photo_candidates import match_outline
        result=execute_editor({'action':'create','preset':'box'});model=result['model']
        vertices=np.array(model['vertices']);rotation=Rotation.from_rotvec([2.6,.7,-.9]).as_matrix()
        distance=8*np.linalg.norm(vertices,axis=1).max();camera=vertices@rotation.T
        projected=camera[:,:2]*[1,-1]*80/(1-camera[:,2,None]/distance)+[250,250]
        face=max(model['faces'],key=lambda face:float((rotation@face['n'])@(np.array([0,0,distance])-rotation@face['center'])))
        self.assertIsNone(face['modelMiller'])
        region={'id':'bound-current-model','kind':'face','face_id':face['id'],'model_fingerprint':result['fingerprint'],'points':projected[face['ids']].tolist()}
        observation={'image_size':[500,500],'silhouette':projected[ConvexHull(projected).vertices].tolist(),'segments':[],'face_regions':[region]}
        fit=match_outline(model,observation)
        self.assertEqual(fit['manual_faces_used'],1)
        self.assertEqual(fit['face_matches'][0]['model_face_id'],face['id'])
        self.assertTrue(fit['face_matches'][0]['visible'])
        self.assertLess(fit['face_matches'][0]['boundary_rmse_pixels'],.1)

if __name__=='__main__':unittest.main()
