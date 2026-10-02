"""Uncertain/partial multi-photo evidence must not be turned into false certainty."""
import unittest, importlib.util, json
from pathlib import Path
from atlas import photo_candidates
from atlas.project import ROOT
import test_photo_candidates as fixtures
OPTIONAL=fixtures.OPTIONAL

class EvidenceContracts(unittest.TestCase):
    def test_explicit_evidence_interface(self):
        import inspect
        self.assertIn('evidence',inspect.signature(photo_candidates.from_photos).parameters)

    def test_alternatives_and_unparsed_text_are_preserved(self):
        from atlas.photo_evidence import parse_morphology
        p=parse_morphology('可能六方柱或六方双锥；端部残缺，还有螺旋条纹')
        self.assertEqual(len(p['hypotheses']),2)
        self.assertTrue(p['uncertain']);self.assertTrue(p['incomplete'])
        self.assertIn('螺旋条纹',p['unparsed'])
        self.assertEqual(p['raw'],'可能六方柱或六方双锥；端部残缺，还有螺旋条纹')

    def test_soft_priors_never_remove_other_templates(self):
        from atlas.photo_evidence import morphology_penalties, parse_morphology
        specs=json.loads((ROOT/'examples/reference-atlas.json').read_text())
        penalties,info=morphology_penalties(specs,parse_morphology('可能六方柱或六方双锥'))
        self.assertEqual(len(penalties),len(specs));self.assertLess(penalties['611'],penalties['451'])
        neutral,_=morphology_penalties(specs,parse_morphology('未知螺旋体'))
        self.assertTrue(all(v==0 for v in neutral.values()))

    def test_negated_shapes_are_not_positive_evidence(self):
        from atlas.photo_evidence import parse_morphology
        p=parse_morphology('不是六方柱，是六方双锥')
        self.assertEqual(p['hypotheses'][0]['forms'],['dipyramid'])
        self.assertIn('六方柱',''.join(p['negated_clauses']))
        q=parse_morphology('没有尖端')
        self.assertFalse(q['hypotheses']);self.assertIn('没有尖端',q['unparsed'])

    def test_duplicate_order_and_outlier_invariants(self):
        from atlas.photo_evidence import fuse_scores
        observations=[{'source_sha256':str(i),'quality_weight':1} for i in range(4)]
        matrix={'A':[.01,.012,.008,.2],'B':[.04,.04,.04,.01]}
        a=fuse_scores(matrix,observations)
        self.assertEqual(a['ranking'][0]['template_id'],'A')
        b=fuse_scores({k:[*v,v[0]] for k,v in matrix.items()},[*observations,observations[0]])
        self.assertEqual(a['ranking'],b['ranking']);self.assertEqual(b['independent_views'],4)
        c=fuse_scores({k:list(reversed(v)) for k,v in matrix.items()},list(reversed(observations)))
        self.assertEqual(a['ranking'],c['ranking'])

    def test_duplicate_coverage_ties_are_order_independent(self):
        from atlas.photo_evidence import fuse_scores
        common={'source_sha256':'same-photo','status':'usable','quality_weight':.35,
                'image_size':[400,500],'silhouette':[[0,0],[100,0],[0,100]],'segments':[]}
        observations=[dict(common,coverage='complete',source_index=0),
                      dict(common,coverage='partial',source_index=1)]
        matrix={'A':[.01,.04],'B':[.03,.02]}
        a=fuse_scores(matrix,observations)
        reversed_observations=[dict(o,source_index=i) for i,o in enumerate(reversed(observations))]
        b=fuse_scores({key:list(reversed(scores)) for key,scores in matrix.items()},reversed_observations)
        self.assertEqual(a['ranking'],b['ranking'])
        self.assertEqual(a['groups'][0]['effective_weight'],b['groups'][0]['effective_weight'])
        self.assertEqual(observations[a['groups'][0]['representative']]['coverage'],
                         reversed_observations[b['groups'][0]['representative']]['coverage'])

    def test_duplicate_face_region_ties_are_order_independent(self):
        from atlas.photo_evidence import fuse_scores
        common={'source_sha256':'same-photo','status':'usable','quality_weight':1,
                'image_size':[400,500],'silhouette':[[0,0],[100,0],[0,100]],'segments':[]}
        regions=[{'id':'label-z','points':[[0,0],[40,0],[0,40]],'face_id':'F01','model_fingerprint':'a'*64},
                 {'id':'label-a','points':[[0,0],[80,0],[0,80]],'face_id':'F01','model_fingerprint':'b'*64}]
        observations=[dict(common,face_regions=[region]) for region in regions]
        matrix={'A':[.01,.04],'B':[.03,.02]}
        forward=fuse_scores(matrix,observations)
        reverse=fuse_scores({key:list(reversed(values)) for key,values in matrix.items()},list(reversed(observations)))
        self.assertEqual(forward['ranking'],reverse['ranking'])
        renamed=[dict(o,face_regions=[dict(o['face_regions'][0],id='different-label')]) for o in observations]
        self.assertEqual(forward['ranking'],fuse_scores(matrix,renamed)['ranking'])

@unittest.skipUnless(OPTIONAL,'optional photo dependencies not installed')
class MultiPhoto(unittest.TestCase):
    def test_same_photo_different_boxes_have_order_independent_ranking(self):
        from PIL import Image,ImageDraw
        import io,base64
        image=Image.new('RGB',(480,480),(200,210,220));draw=ImageDraw.Draw(image)
        # Equal-quality regions of the same source produce different outlines and fits.
        for rectangle in [(80,110,220,250),(280,80,350,350)]:
            draw.rectangle(rectangle,fill=(75,75,70));x,y,right,bottom=rectangle
            for row in range(y+10,bottom-10,8):
                draw.line((x+10,row,right-10,row),fill=(125,125,115),width=2)
        buffer=io.BytesIO();image.save(buffer,format='PNG')
        encoded=base64.b64encode(buffer.getvalue()).decode()
        boxes=[[60,90,180,180],[260,60,110,320]]
        bank=[s for s in json.loads((ROOT/'examples/reference-atlas.json').read_text()) if s['id'] in ('128','3519')]
        a=photo_candidates.from_photos([encoded,encoded],boxes=boxes,bank=bank)
        b=photo_candidates.from_photos([encoded,encoded],boxes=list(reversed(boxes)),bank=bank)
        self.assertEqual([o['quality_weight'] for o in a['observations']],[1.,1.])
        self.assertNotEqual(a['observations'][0]['silhouette'],a['observations'][1]['silhouette'])
        self.assertEqual(a['ranking'],b['ranking'])
        self.assertEqual(a['fusion']['independent_views'],1)
        self.assertEqual(b['fusion']['redundant_photos'],1)
        c=photo_candidates.from_photos([encoded]*3,boxes=[boxes[0],boxes[1],boxes[0]],bank=bank)
        self.assertEqual(a['ranking'],c['ranking'])
        self.assertEqual(c['fusion']['independent_views'],1)
        self.assertEqual(c['fusion']['redundant_photos'],2)

    def test_more_than_four_and_bad_view_preserved(self):
        from PIL import Image
        import io,base64
        good,_=fixtures.PhotoCandidates().photo(hand=False);b=io.BytesIO();Image.new('RGB',(200,200),'white').save(b,format='PNG')
        blank=base64.b64encode(b.getvalue()).decode();spec=json.loads((ROOT/'examples/cube.json').read_text())
        r=photo_candidates.from_photos([good]*5+[blank],bank=[spec],evidence={'morphology':'可能是柱状，信息不完整'})
        self.assertEqual(len(r['observations']),6);self.assertEqual(r['fusion']['independent_views'],1)
        self.assertEqual(r['observations'][-1]['status'],'unusable');self.assertIsNone(r['candidates'][0]['views'][-1])
        self.assertEqual(r['inputs']['evidence']['morphology'],'可能是柱状，信息不完整')

    def test_suspected_partial_keeps_local_matching_and_low_weight(self):
        from atlas.photo_candidates import extract_outline,match_outline
        from atlas.photo_evidence import fuse_scores
        from atlas.core import build
        good,_=fixtures.PhotoCandidates().photo(hand=False);spec=json.loads((ROOT/'examples/cube.json').read_text());model,_=build(spec)
        o=extract_outline(good);o['coverage']='suspected_partial';o['quality_weight']=.1
        fit=match_outline(model,o);self.assertEqual(fit['view']['fitMetric'],'partial_silhouette')
        other={'source_sha256':'another','quality_weight':1,'status':'usable'}
        fused=fuse_scores({'cube':[.01,.02]},[o,other])
        group=next(g for g in fused['groups'] if 0 in g['members']);self.assertEqual(group['effective_weight'],.1)

    def test_limit_accepts_24_repeats_without_24_votes(self):
        good,_=fixtures.PhotoCandidates().photo(hand=False);spec=json.loads((ROOT/'examples/cube.json').read_text())
        r=photo_candidates.from_photos([good]*24,bank=[spec])
        self.assertEqual(len(r['observations']),24);self.assertEqual(r['fusion']['independent_views'],1)
        self.assertEqual(r['fusion']['redundant_photos'],23)

    def test_partial_evidence_is_explicit(self):
        good,_=fixtures.PhotoCandidates().photo(hand=False);spec=json.loads((ROOT/'examples/cube.json').read_text())
        r=photo_candidates.from_photos([good],bank=[spec],evidence={'coverage':['partial']})
        self.assertEqual(r['observations'][0]['coverage'],'partial')
        self.assertEqual(r['candidates'][0]['views'][0]['fitMetric'],'partial_silhouette')
        self.assertIn('不完整', ''.join(r['warnings']))

    def test_damaged_image_does_not_abort_valid_photo(self):
        import base64
        good,_=fixtures.PhotoCandidates().photo(hand=False);spec=json.loads((ROOT/'examples/cube.json').read_text())
        damaged=base64.b64encode(b'damaged PNG header').decode()
        r=photo_candidates.from_photos([damaged,good],bank=[spec])
        self.assertEqual(r['observations'][0]['status'],'unusable')
        self.assertEqual(r['candidates'][0]['representative_photo'],1)
        self.assertIsNone(r['candidates'][0]['views'][0])

if __name__=='__main__':unittest.main()
