"""Image-only picking suggestions: pixel coordinates and conservative fallbacks."""
import base64
import hashlib
import importlib.util
import io
import math
import unittest
from unittest import mock

OPTIONAL = all(importlib.util.find_spec(name) for name in ('cv2', 'numpy', 'scipy', 'PIL'))


def guides(image):
    assert importlib.util.find_spec('atlas.photo_guides') is not None, 'Image-only automatic picking guides are not implemented'
    from atlas.photo_guides import photo_guides
    return photo_guides(image)


def encode(image, fmt='PNG', **options):
    stream = io.BytesIO()
    image.save(stream, format=fmt, **options)
    raw = stream.getvalue()
    mime = 'jpeg' if fmt == 'JPEG' else 'png'
    return 'data:image/' + mime + ';base64,' + base64.b64encode(raw).decode(), raw


class GuideInput(unittest.TestCase):
    def test_malformed_input_is_rejected(self):
        for value in (None, '', 'not base64!', 'data:image/gif;base64,aGVsbG8=', base64.b64encode(b'not an image').decode()):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guides(value)

    def test_missing_optional_dependency_is_actionable_and_never_downloaded(self):
        # A valid PNG signature lets this test run even on a stdlib-only interpreter.
        image = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
        with mock.patch.dict('sys.modules', {'cv2': None}):
            with self.assertRaisesRegex(ValueError, 'OpenCV.*端点|端点.*OpenCV'):
                guides(image)


@unittest.skipUnless(OPTIONAL, 'optional photo dependencies not installed')
class PhotoGuides(unittest.TestCase):
    def synthetic(self, size=(400, 500)):
        from PIL import Image, ImageDraw
        im = Image.new('RGB', size, (205, 215, 225))
        base = [(130, 145), (220, 125), (258, 190), (230, 320), (150, 335), (105, 240)]
        polygon = [(x*size[0]/400, y*size[1]/500) for x, y in base]
        ImageDraw.Draw(im).polygon(polygon, fill=(95, 95, 85))
        return im, polygon

    def assert_bounded(self, result):
        width, height = result['image_size']
        self.assertLessEqual(len(result['corners']), 64)
        self.assertLessEqual(len(result['segments']), 96)
        points = [c['point'] for c in result['corners']] + [p for line in result['segments'] for p in line['points']]
        self.assertTrue(all(len(p) == 2 and all(math.isfinite(x) for x in p) and 0 <= p[0] <= width and 0 <= p[1] <= height for p in points))

    def test_synthetic_outline_produces_only_pixel_suggestions_without_model_fitting(self):
        image, polygon = self.synthetic()
        value, raw = encode(image)
        with mock.patch('atlas.photo_candidates.from_photos', side_effect=AssertionError('No template search')), \
             mock.patch('atlas.photo_candidates.match_outline', side_effect=AssertionError('No fitting')):
            result = guides(value)
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['image_size'], [400, 500])
        self.assertEqual(result['status'], 'suggestions_only')
        self.assertGreaterEqual(len(result['corners']), 4)
        self.assertTrue(all(c['kind'] == 'image_corner' and c['source'] == 'outline' for c in result['corners']))
        for truth in polygon:
            self.assertLess(min(math.dist(truth, c['point']) for c in result['corners']), 6)
        self.assertNotIn('preview', result)
        self.assertNotIn('model', result)
        self.assertNotIn('candidates', result)
        self.assertIn('不是', result['claim_boundary'])
        self.assert_bounded(result)

    def test_refinement_is_exposed_as_unconfirmed_help_not_committed_annotation(self):
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (1200, 1000), (205, 215, 225))
        truth = [(391, 233), (796, 279), (873, 702), (359, 738)]
        ImageDraw.Draw(image).polygon(truth, fill=(95, 95, 85))
        result = guides(encode(image)[0])
        self.assertTrue(any(c.get('refined') for c in result['corners']))
        self.assertTrue(all(c['priority'] == 'primary' for c in result['corners']))
        self.assertLess(sum(min(math.dist(p, c['point']) for c in result['corners']) for p in truth)/len(truth), 2)
        self.assertNotIn('annotation', result)

    def test_failed_segmentation_falls_back_to_explicit_background_or_text_candidates(self):
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (200, 200), 'white')
        ImageDraw.Draw(image).rectangle((5, 5, 25, 25), fill='black')
        result = guides(encode(image)[0])
        self.assertEqual(result['status'], 'suggestions_only')
        self.assertGreater(len(result['corners']), 0)
        self.assertTrue(all(c['source'] == 'detected' and c['priority'] == 'secondary' for c in result['corners']))
        self.assertTrue(any('文字' in warning and '背景' in warning for warning in result['warnings']))
        self.assertEqual(result['segments'], [])
        self.assert_bounded(result)

    def test_blank_image_returns_empty_unavailable_instead_of_fabricated_points(self):
        from PIL import Image
        result = guides(encode(Image.new('RGB', (200, 200), 'white'))[0])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['corners'], [])
        self.assertEqual(result['segments'], [])
        self.assertTrue(result['warnings'])

    def test_exif_orientation_uses_display_pixels_and_original_byte_hash(self):
        image, _ = self.synthetic()
        exif = image.getexif()
        exif[274] = 6
        value, raw = encode(image, 'JPEG', exif=exif)
        result = guides(value)
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['image_size'], [500, 400])
        self.assertEqual(result['display_orientation'], 'exif-transposed')
        self.assert_bounded(result)

    def test_downsampled_working_image_returns_original_image_coordinates(self):
        image, truth = self.synthetic((2000, 2500))
        result = guides(encode(image)[0])
        self.assertEqual(result['image_size'], [2000, 2500])
        self.assertLessEqual(max(result['working_image_size']), 1200)
        for point in truth:
            self.assertLess(min(math.dist(point, c['point']) for c in result['corners']), 15)
        self.assert_bounded(result)

    def test_decode_size_and_pixel_limits_are_enforced_before_extraction(self):
        from PIL import Image
        with self.assertRaisesRegex(ValueError, '尺寸'):
            guides(encode(Image.new('RGB', (31, 100), 'white'))[0])
        with self.assertRaisesRegex(ValueError, '解码|图像'):
            guides(base64.b64encode(b'\x89PNG\r\n\x1a\ninvalid').decode())
        from atlas import photo_guides
        with mock.patch.object(photo_guides, 'MAX_IMAGE_PIXELS', 10000):
            with self.assertRaisesRegex(ValueError, '像素'):
                guides(encode(Image.new('RGB', (200, 200), 'white'))[0])


if __name__ == '__main__':
    unittest.main()
