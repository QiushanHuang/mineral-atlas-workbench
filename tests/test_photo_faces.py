"""Seeded 2-D face-region proposals stay bounded and respect manual barriers."""
import base64
import copy
import hashlib
import importlib.util
import io
import math
import unittest
from unittest import mock

OPTIONAL = all(importlib.util.find_spec(name) for name in ('PIL', 'numpy', 'cv2'))


def propose(image, **kwargs):
    assert importlib.util.find_spec('atlas.photo_faces') is not None, 'Seeded face-region proposals are not implemented'
    from atlas.photo_faces import propose_face
    return propose_face(image, **kwargs)


def encode(image, fmt='PNG', **kwargs):
    stream = io.BytesIO()
    image.save(stream, format=fmt, **kwargs)
    raw = stream.getvalue()
    return base64.b64encode(raw).decode(), raw


def annotation(raw, size, features):
    return {'schema_version': 1, 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'image_size': list(size), 'features': features}


class FaceProposalInputs(unittest.TestCase):
    def test_bad_payload_is_rejected(self):
        for image in (None, 'not-base64', base64.b64encode(b'bad image').decode()):
            with self.subTest(image=image), self.assertRaises(ValueError):
                propose(image, seed=[10, 10])

    def test_missing_optional_dependencies_are_actionable(self):
        with mock.patch.dict('sys.modules', {'cv2': None}):
            with self.assertRaisesRegex(ValueError, 'OpenCV.*手工|手工.*OpenCV'):
                propose(base64.b64encode(b'\x89PNG\r\n\x1a\n').decode(), seed=[10, 10])


@unittest.skipUnless(OPTIONAL, 'optional image dependencies not installed')
class PhotoFaces(unittest.TestCase):
    def picture(self, size=(320, 240)):
        from PIL import Image, ImageDraw
        im = Image.new('RGB', size, (225, 230, 235))
        sx, sy = size[0]/320, size[1]/240
        ImageDraw.Draw(im).rectangle((60*sx, 60*sy, 260*sx, 180*sy), fill=(110, 110, 100))
        return im

    def rect_lines(self, points):
        return [{'id': f'E{i}', 'kind': 'edge', 'points': [a, b]}
                for i, (a, b) in enumerate(zip(points, points[1:] + points[:1]))]

    def assert_valid_polygon(self, result, raw):
        from atlas.photo_annotations import validate_annotation
        self.assertEqual(result['status'], 'needs_review', result['warnings'])
        self.assertTrue(3 <= len(result['polygon']) <= 64)
        self.assertTrue(all(math.isfinite(x) for p in result['polygon'] for x in p))
        validate_annotation(annotation(raw, result['image_size'], [{'id': 'candidate', 'kind': 'face', 'points': result['polygon']}]), raw)

    def iou(self, result, truth):
        import cv2
        import numpy as np
        width, height = result['image_size']
        a = np.zeros((height, width), 'uint8')
        b = a.copy()
        cv2.fillPoly(a, [np.round(truth).astype('int32')], 1)
        cv2.fillPoly(b, [np.round(result['polygon']).astype('int32')], 1)
        return float(np.logical_and(a, b).sum()/np.logical_or(a, b).sum())

    def test_uniform_rectangular_region_is_only_a_reviewable_image_proposal(self):
        value, raw = encode(self.picture())
        result = propose(value, seed=[110, 120])
        self.assert_valid_polygon(result, raw)
        self.assertEqual(result['method'], 'lab_gradient_region')
        self.assertGreater(self.iou(result, [[60, 60], [260, 60], [260, 180], [60, 180]]), .9)
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertIn('未确认', result['evidence'])
        self.assertNotIn('face_id', result)
        self.assertNotIn('model', result)

    def test_manual_edge_separates_adjacent_faces_with_identical_colors(self):
        value, raw = encode(self.picture())
        ann = annotation(raw, (320, 240), [
            {'id': 'outline', 'kind': 'silhouette', 'points': [[60, 60], [260, 60], [260, 180], [60, 180]]},
            {'id': 'ridge', 'kind': 'edge', 'points': [[160, 60], [160, 180]]}])
        result = propose(value, annotation=ann, seed=[110, 120])
        self.assert_valid_polygon(result, raw)
        self.assertEqual(result['method'], 'manual_enclosure')
        self.assertLessEqual(max(p[0] for p in result['polygon']), 160)
        self.assertGreater(self.iou(result, [[60, 60], [160, 60], [160, 180], [60, 180]]), .94)

    def test_closed_manual_edge_loop_ignores_internal_print_and_shadow(self):
        from PIL import ImageDraw
        image = self.picture()
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 60, 160, 180), fill=(55, 55, 50))
        draw.rectangle((120, 110, 145, 130), fill='black')
        value, raw = encode(image)
        truth = [[65, 65], [155, 65], [155, 175], [65, 175]]
        result = propose(value, annotation=annotation(raw, image.size, self.rect_lines(truth)), seed=[130, 120])
        self.assert_valid_polygon(result, raw)
        self.assertEqual(result['method'], 'manual_enclosure')
        self.assertGreater(self.iou(result, truth), .94)

    def test_broken_manual_separator_does_not_pretend_to_be_a_closed_face(self):
        value, raw = encode(self.picture())
        ann = annotation(raw, (320, 240), [
            {'id': 'outline', 'kind': 'silhouette', 'points': [[60, 60], [260, 60], [260, 180], [60, 180]]},
            {'id': 'broken', 'kind': 'edge', 'points': [[160, 80], [160, 160]]}])
        result = propose(value, annotation=ann, seed=[110, 120])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['polygon'], [])
        self.assertIn('闭合', ''.join(result['warnings']))

    def test_blank_background_and_tiny_print_are_not_fabricated_faces(self):
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (320, 240), 'white')
        result = propose(encode(image)[0], seed=[160, 120])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['polygon'], [])
        ImageDraw.Draw(image).rectangle((140, 100, 144, 119), fill='black')
        result = propose(encode(image)[0], seed=[142, 110])
        self.assertEqual(result['status'], 'unavailable')

    def test_automatic_shadow_regions_retain_explicit_ambiguity(self):
        from PIL import ImageDraw
        image = self.picture()
        ImageDraw.Draw(image).rectangle((160, 60, 260, 180), fill=(70, 70, 65))
        result = propose(encode(image)[0], seed=[110, 120])
        self.assertEqual(result['status'], 'needs_review')
        self.assertTrue(any('阴影' in w and '文字' in w for w in result['warnings']))

    def test_bad_seed_tolerance_and_annotation_hash_rejected_without_mutation(self):
        value, raw = encode(self.picture())
        for seed in (None, [0], [-1, 10], [320, 0], [float('nan'), 0], [True, 0]):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                propose(value, seed=seed)
        for tolerance in (-1, 0, 1000, float('inf'), True):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                propose(value, seed=[100, 100], tolerance=tolerance)
        wrong = annotation(raw, (320, 240), [])
        wrong['source_sha256'] = '0'*64
        before = copy.deepcopy(wrong)
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            propose(value, annotation=wrong, seed=[100, 100])
        self.assertEqual(wrong, before)

    def test_proposal_binding_is_deterministic_and_input_remains_unchanged(self):
        value, raw = encode(self.picture())
        ann = annotation(raw, (320, 240), [])
        before = copy.deepcopy(ann)
        first = propose(value, annotation=ann, seed=[110, 120])
        second = propose(value, annotation=ann, seed=[110., 120.])
        self.assertEqual(first['proposal_id'], second['proposal_id'])
        self.assertEqual(first['annotation_sha256'], second['annotation_sha256'])
        self.assertEqual(ann, before)
        self.assertNotEqual(first['proposal_id'], propose(value, annotation=ann, seed=[111, 120])['proposal_id'])

    def test_exif_size_downsampling_and_returned_original_pixel_polygon(self):
        image = self.picture((1600, 1200))
        value, raw = encode(image)
        result = propose(value, seed=[550, 600])
        self.assert_valid_polygon(result, raw)
        self.assertEqual(result['image_size'], [1600, 1200])
        self.assertLessEqual(max(result['working_image_size']), 1000)
        self.assertGreater(self.iou(result, [[300, 300], [1300, 300], [1300, 900], [300, 900]]), .9)
        small = self.picture()
        exif = small.getexif()
        exif[274] = 6
        value, raw = encode(small, 'JPEG', exif=exif)
        rotated = propose(value, seed=[120, 110])
        self.assert_valid_polygon(rotated, raw)
        self.assertEqual(rotated['image_size'], [240, 320])
        self.assertEqual(rotated['source_sha256'], hashlib.sha256(raw).hexdigest())

    def test_seed_on_manual_boundary_is_not_silently_relocated(self):
        value, raw = encode(self.picture())
        ann = annotation(raw, (320, 240), [{'id': 'ridge', 'kind': 'edge', 'points': [[160, 60], [160, 180]]}])
        result = propose(value, annotation=ann, seed=[160, 120])
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('内部', ''.join(result['warnings']))


if __name__ == '__main__':
    unittest.main()
