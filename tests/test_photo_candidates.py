"""Photo-first behavior: actual pixels, no supplied face IDs or corner annotations."""
import base64
import importlib.util
import io
import unittest

OPTIONAL = all(importlib.util.find_spec(n) for n in ('cv2','numpy','scipy','PIL'))

@unittest.skipUnless(OPTIONAL, 'optional photo dependencies not installed')
class PhotoCandidates(unittest.TestCase):
    def photo(self, color=(115,115,105), hand=True):
        from PIL import Image, ImageDraw
        im=Image.new('RGB',(400,500),(193,209,214));d=ImageDraw.Draw(im)
        if hand:d.ellipse((180,255,350,480),fill=(186,128,95))
        polygon=[(130,145),(220,125),(258,190),(230,320),(150,335),(105,240)]
        d.polygon(polygon,fill=color);b=io.BytesIO();im.save(b,format='PNG')
        return base64.b64encode(b.getvalue()).decode(),polygon

    def test_entry_point_exists(self):
        from atlas import images
        self.assertTrue(callable(getattr(images,'from_photos',None)), 'Photos must generate candidates without a model or face annotation')

    def test_segmentation_excludes_hand_and_covers_object(self):
        from atlas.photo_candidates import extract_outline
        import numpy as np,cv2
        for color in [(115,115,105),(130,108,58),(85,50,29)]:
            raw,truth=self.photo(color);r=extract_outline(raw)
            self.assertEqual(r['image_size'],[400,500]);a=np.zeros((500,400),'uint8');b=a.copy()
            cv2.fillPoly(a,[np.array(truth,dtype='int32')],1);cv2.fillPoly(b,[np.round(r['silhouette']).astype('int32')],1)
            iou=np.logical_and(a,b).sum()/np.logical_or(a,b).sum()
            self.assertGreater(iou,.85,(color,iou))

    def test_blank_image_does_not_invent_a_model(self):
        from PIL import Image
        from atlas.images import from_photos
        b=io.BytesIO();Image.new('RGB',(200,200),'white').save(b,format='PNG')
        with self.assertRaisesRegex(ValueError,'轮廓|物体'):
            from_photos([base64.b64encode(b.getvalue()).decode()])

    def test_large_image_refines_corners_in_native_pixels(self):
        from PIL import Image,ImageDraw
        from atlas.photo_candidates import extract_outline
        import numpy as np
        im=Image.new('RGB',(1200,1000),(205,215,225));truth=np.array([[391,233],[796,279],[873,702],[359,738]])
        ImageDraw.Draw(im).polygon([tuple(point) for point in truth],fill=(95,95,85))
        stream=io.BytesIO();im.save(stream,format='PNG')
        result=extract_outline(base64.b64encode(stream.getvalue()).decode())
        self.assertTrue('corner_refinement' in result,'coarse 480px corners should be checked at source resolution')
        self.assertTrue(result['corner_refinement']['candidate_valid'])
        self.assertFalse(result['corner_refinement']['applied'])
        self.assertEqual(result['silhouette'],result['coarse_silhouette'])
        def error(points):return np.min(np.linalg.norm(np.asarray(points)[:,None]-truth,axis=2),axis=0).mean()
        self.assertLess(error(result['refined_silhouette']),error(result['coarse_silhouette']))
        self.assertLess(error(result['refined_silhouette']),1.5)

    def test_candidates_are_explicit_priors_without_photo_number_claims(self):
        from atlas.images import from_photos
        from atlas.core import build
        from atlas.project import ROOT
        import json
        raw,_=self.photo(hand=False)
        bank=[json.loads((ROOT/'examples/cube.json').read_text(encoding='utf-8'))]
        r=from_photos([raw],bank=bank)
        self.assertEqual(r['claim_level'],'template_candidates')
        c=r['candidates'][0];m,q=build(c['spec']);self.assertTrue(q['ok'])
        self.assertTrue(c['requires_review']);self.assertTrue(r['warnings'])
        self.assertFalse(any('photo_label' in f for f in c['spec'].get('faces',[])))
        self.assertEqual(len(c['views']),1);self.assertEqual(c['views'][0]['fitMetric'],'silhouette')
        self.assertGreaterEqual(c['score'],0)
        self.assertEqual(r['inputs']['boxes'],[None]);self.assertEqual(r['inputs']['constraints'],{})
        self.assertEqual(len(r['reproducibility']['template_bank_sha256']),64)
        self.assertIn('opencv',r['reproducibility']['dependencies'])

if __name__=='__main__':unittest.main()

class PhotoRegistration(unittest.TestCase):
    def test_photo_generation_tool_is_exposed(self):
        from atlas.service import TOOLS
        self.assertIn('atlas_from_photos',{t['name'] for t in TOOLS})

@unittest.skipUnless(OPTIONAL, 'optional photo dependencies not installed')
class PhotoEvidence(unittest.TestCase):
    def test_exif_orientation_and_input_limits(self):
        from PIL import Image
        from atlas.photo_candidates import extract_outline
        from atlas.images import from_photos
        encoded,_=PhotoCandidates().photo(hand=False)
        im=Image.open(io.BytesIO(base64.b64decode(encoded)));exif=im.getexif();exif[274]=6;b=io.BytesIO();im.save(b,format='JPEG',exif=exif)
        r=extract_outline(base64.b64encode(b.getvalue()).decode());self.assertEqual(r['image_size'],[500,400]);self.assertEqual(r['exif_orientation'],6)
        with self.assertRaisesRegex(ValueError,'1–24'):from_photos([])
        with self.assertRaisesRegex(ValueError,'1–24'):from_photos([encoded]*25)
        with self.assertRaisesRegex(ValueError,'物体框'):extract_outline(encoded,[-1,0,100,100])

    def test_single_photo_export_retains_observation_evidence(self):
        import tempfile,pathlib,json
        from atlas.project import ROOT,build_project
        encoded,_=PhotoCandidates().photo(hand=False);spec=json.loads((ROOT/'examples/cube.json').read_text())
        item={'image':encoded,'annotation':{'mode':'box-assisted','source_sha256':'test-source-hash'},'fit_quality':{'normalized_silhouette_rmse':.02}}
        with tempfile.TemporaryDirectory() as d:
            r=build_project(spec,d,{'items':[item]});p=pathlib.Path(r['path'])/'photo-evidence.json'
            self.assertTrue(p.exists(),'Single-photo candidates must keep the same evidence as multi-photo candidates')
            saved=json.loads(p.read_text());self.assertEqual(saved[0]['annotation'],item['annotation']);self.assertEqual(saved[0]['fit_quality'],item['fit_quality'])

    def test_multiple_photos_are_retained_in_artifact(self):
        import tempfile,pathlib,json,zipfile
        from atlas.project import ROOT,build_project
        encoded,_=PhotoCandidates().photo(hand=False);spec=json.loads((ROOT/'examples/cube.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            r=build_project(spec,d,{'items':[{'image':encoded},{'image':encoded}]});p=pathlib.Path(r['path'])
            with zipfile.ZipFile(p/'result.zip') as z:
                self.assertIn('photo-1.png',z.namelist());self.assertIn('photo-2.png',z.namelist());self.assertIn('photo-evidence.json',z.namelist())
            data=json.loads((p/'data.js').read_text().removeprefix('const DATA = ').strip().removesuffix(';'))
            self.assertEqual(len(data['photos'][spec['id']]),2)
