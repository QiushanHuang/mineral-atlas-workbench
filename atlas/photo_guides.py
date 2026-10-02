"""Bounded, image-only picking suggestions; no template search or model writes."""
import base64
import hashlib
import io
import math

from .images import decode_image
from .photo_candidates import extract_outline

MAX_IMAGE_PIXELS = 40_000_000
MAX_WORKING_EDGE = 1200
MAX_CORNERS = 64
MAX_SEGMENTS = 96
CLAIM_BOUNDARY = '这些点线仅为图像中的吸附建议，不是真实晶棱、晶面、晶轴或指数的识别结论；点击确认前不会成为手工标注。'


def _dependencies():
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageOps
    except ImportError as error:
        raise ValueError('自动找点需要本机已有 Pillow、NumPy 和 OpenCV；可继续使用已有端点吸附，不会自动下载组件。') from error
    return cv2, np, Image, ImageOps


def photo_guides(image):
    """Return suggestions in EXIF-displayed original pixels, bound to raw bytes.

    Segmentation reuses the existing outline extractor, with its optional bounded
    corner refinement exposed only as a guide. Oversized images are reduced for
    this interactive path; original byte identity and coordinate extent remain
    unchanged. Failure to find an outline permits explicitly weaker image corners.
    """
    raw, _ = decode_image(image)
    cv2, np, Image, ImageOps = _dependencies()
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise ValueError('图像超过自动找点的像素限制（最多 4000 万像素）')
            orientation = source.getexif().get(274, 1)
            displayed = ImageOps.exif_transpose(source)
            width, height = displayed.size
            if min(width, height) < 32:
                raise ValueError('照片尺寸过小，自动找点至少需要 32×32 像素')
            displayed.thumbnail((MAX_WORKING_EDGE, MAX_WORKING_EDGE), Image.Resampling.BICUBIC)
            working = displayed.convert('RGB')
    except ValueError:
        raise
    except Exception as error:
        raise ValueError('图像解码失败，不能生成自动找点建议') from error
    work_width, work_height = working.size
    scale = [width/work_width, height/work_height]
    warnings = []
    if working.size != (width, height):
        warnings.append('为保持交互速度，自动找点使用缩小图计算并映回原图坐标；可继续手动微调。')
    corners, segments = [], []

    def point(value):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return None
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in value):
            return None
        mapped = [float(value[i])*scale[i] for i in range(2)]
        if not 0 <= mapped[0] <= width or not 0 <= mapped[1] <= height:
            return None
        return mapped

    def add_corner(value, source, refined=False):
        mapped = point(value)
        if mapped is None or len(corners) >= MAX_CORNERS:
            return
        if any(math.dist(mapped, c['point']) < 1.5*max(scale) for c in corners):
            return
        corners.append({'id': f'G{len(corners)+1:02d}', 'point': mapped,
                        'kind': 'image_corner', 'source': source,
                        'priority': 'primary' if source == 'outline' else 'secondary',
                        'refined': bool(refined)})

    def add_segment(a, b, source):
        first, second = point(a), point(b)
        if first is None or second is None or len(segments) >= MAX_SEGMENTS or math.dist(first, second) < 2*max(scale):
            return
        segments.append({'id': f'L{len(segments)+1:02d}', 'points': [first, second],
                         'kind': 'image_segment', 'source': source,
                         'priority': 'primary' if source == 'outline' else 'secondary'})

    stream = io.BytesIO()
    working.save(stream, format='PNG')
    encoded = base64.b64encode(stream.getvalue()).decode('ascii')
    try:
        observation = extract_outline(encoded)
        refined = bool(observation.get('corner_refinement', {}).get('candidate_valid') and observation.get('refined_silhouette'))
        polygon = (observation.get('refined_silhouette') if refined else observation.get('coarse_silhouette')) or observation.get('silhouette', [])
        for p in polygon:
            add_corner(p, 'outline', refined)
        if len(polygon) >= 3:
            for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                add_segment(a, b, 'outline')
        for line in observation.get('segments', []):
            if len(line) == 2:
                add_segment(line[0], line[1], 'detected')
        warnings.extend(observation.get('warnings', []))
        if any(s['source'] == 'detected' for s in segments):
            warnings.append('内部线段可能来自文字、纹理或阴影，吸附后请核对是否为真实棱。')
    except (ValueError, cv2.error) as error:
        warnings.append('未取得可靠自动轮廓：' + str(error))

    if not corners:
        # These are image intensity corners, deliberately not called crystal vertices.
        gray = cv2.cvtColor(np.asarray(working), cv2.COLOR_RGB2GRAY)
        try:
            detected = cv2.goodFeaturesToTrack(gray, maxCorners=MAX_CORNERS, qualityLevel=.04,
                                             minDistance=max(8., max(working.size)/70.),
                                             blockSize=5, useHarrisDetector=False)
        except cv2.error:
            detected = None
        if detected is not None:
            for p in detected.reshape(-1, 2).tolist():
                add_corner(p, 'detected')
        if corners:
            warnings.append('低优先级角点可能是文字或背景，不代表晶体角点；仅在靠近所需位置时确认。')
        else:
            warnings.append('未找到足够清晰的候选点；仍可手动点选或吸附到已有标注端点。')
    return {'source_sha256': hashlib.sha256(raw).hexdigest(), 'image_size': [width, height],
            'display_orientation': 'exif-transposed', 'exif_orientation': orientation,
            'working_image_size': [work_width, work_height], 'corners': corners, 'segments': segments,
            'status': 'suggestions_only' if corners or segments else 'unavailable',
            'warnings': list(dict.fromkeys(warnings)), 'claim_boundary': CLAIM_BOUNDARY}
