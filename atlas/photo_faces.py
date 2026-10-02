"""Conservative, seeded 2-D region proposals with source-bound manual barriers.

These proposals do not establish planarity in 3-D, crystal-face identity or indices.
No template search, model fitting, network calls or annotation writes occur here.
"""
import hashlib
import io
import json
import math

from .images import decode_image
from .photo_annotations import validate_annotation, _intersects

VERSION = 'seeded-face-region-v1'
MAX_IMAGE_PIXELS = 40_000_000
MAX_WORKING_EDGE = 1000
MAX_POLYGON_POINTS = 64
CLAIM = '二维面区候选，须人工检查和改点；用户采纳仍未确认真实三维晶面、平面性、晶轴或米勒指数。'


def _canonical(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def annotation_fingerprint(annotation):
    """Stable across JSON.stringify's conversion of integral floats to integers."""
    try:
        data = json.dumps(_canonical(annotation), ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError) as error:
        raise ValueError('标注必须为有限数值的 JSON 数据') from error
    return hashlib.sha256(data).hexdigest()


def _dependencies():
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageOps
    except ImportError as error:
        raise ValueError('面区建议需要本机已有 Pillow、NumPy 和 OpenCV；可继续手工圈面，不会自动安装组件。') from error
    return cv2, np, Image, ImageOps


def _finite(number):
    return isinstance(number, (int, float)) and not isinstance(number, bool) and math.isfinite(number)


def _simple_polygon(points):
    if len(points) < 3 or len({tuple(p) for p in points}) != len(points):
        return False
    edges = list(zip(points, points[1:] + points[:1]))
    for i, (a, b) in enumerate(edges):
        for j, (c, d) in enumerate(edges[i+1:], i+1):
            if j == i+1 or (i == 0 and j == len(edges)-1):
                continue
            if _intersects(a, b, c, d):
                return False
    return True


def propose_face(image, annotation=None, seed=None, tolerance=24):
    """Suggest one bounded image region, never automatically confirm a face.

    ``seed`` is in EXIF-displayed original pixels. ``tolerance`` (8..64) is an
    image color threshold on OpenCV's encoded Lab channels, not a physical metric.
    Closed manual subdivisions take priority; otherwise color and gradient limits
    apply while edge/outline/occlusion barriers remain impassable.
    """
    raw, _ = decode_image(image)
    cv2, np, Image, ImageOps = _dependencies()
    if not isinstance(seed, (list, tuple)) or len(seed) != 2 or not all(_finite(x) for x in seed):
        raise ValueError('请提供图中面内种子点 seed=[x,y]，坐标须为有限数值')
    if not _finite(tolerance) or not 8 <= tolerance <= 64:
        raise ValueError('面区容差须为 8–64 的有限数值，例如 12、24 或 40')
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.width*source.height > MAX_IMAGE_PIXELS:
                raise ValueError('面区建议最多处理 4000 万像素的图像')
            displayed = ImageOps.exif_transpose(source)
            width, height = displayed.size
            if min(width, height) < 32:
                raise ValueError('照片尺寸至少需要 32×32 像素')
            if not 0 <= seed[0] < width or not 0 <= seed[1] < height:
                raise ValueError('种子点须位于 EXIF 转正后的原图像素范围内')
            displayed.thumbnail((MAX_WORKING_EDGE, MAX_WORKING_EDGE), Image.Resampling.BICUBIC)
            working = displayed.convert('RGB')
    except ValueError:
        raise
    except Exception as error:
        raise ValueError('图像解码失败，不能生成面区候选') from error
    checked = validate_annotation(annotation, raw)
    work_width, work_height = working.size
    scale = [work_width/width, work_height/height]
    sx, sy = [min(limit-1, max(0, round(value*factor)))
              for value, factor, limit in zip(seed, scale, (work_width, work_height))]
    source_hash = hashlib.sha256(raw).hexdigest()
    annotation_hash = annotation_fingerprint(checked)
    warnings = []
    if working.size != (width, height):
        warnings.append('候选区域在最长边不超过 1000 像素的图上计算后映回原图，细小缺口须放大检查。')
    method = 'none'
    metrics = {'area_fraction': 0., 'working_image_size': [work_width, work_height],
               'seed': list(seed), 'tolerance': tolerance, 'manual_edge_segments': 0}

    def finish(polygon, reason=None):
        evidence = (f'本机二维面区候选 {VERSION}；方法={method}；种子={list(seed)}；容差={tolerance}；'
                    f'原图SHA256={source_hash}；标注SHA256={annotation_hash}；{CLAIM}')
        identity = annotation_fingerprint({'algorithm': VERSION, 'source_sha256': source_hash,
                                          'annotation_sha256': annotation_hash, 'seed': list(seed),
                                          'tolerance': tolerance, 'method': method, 'polygon': polygon})
        return {'source_sha256': source_hash, 'image_size': [width, height],
                'display_orientation': 'exif-transposed', 'working_image_size': [work_width, work_height],
                'annotation_sha256': annotation_hash, 'proposal_id': 'face-'+identity[:24],
                'polygon': polygon, 'status': 'needs_review' if polygon else 'unavailable',
                'reason_code': reason, 'method': method, 'warnings': list(dict.fromkeys(warnings)),
                'evidence': evidence, 'metrics': metrics, 'claim_boundary': CLAIM}

    domain = np.ones((work_height, work_width), 'uint8')
    barrier = np.zeros_like(domain)
    manual_edges = np.zeros_like(domain)
    silhouette = None
    edge_count = 0
    for feature in (checked or {}).get('features', []):
        pts = np.round(np.asarray(feature['points'], dtype='float64')*scale).astype('int32')
        kind = feature['kind']
        if kind == 'silhouette':
            silhouette = np.zeros_like(domain)
            cv2.fillPoly(silhouette, [pts], 1)
            cv2.polylines(barrier, [pts], True, 1, 1, cv2.LINE_8)
        elif kind == 'edge':
            cv2.polylines(barrier, [pts], False, 1, 1, cv2.LINE_8)
            cv2.polylines(manual_edges, [pts], False, 1, 1, cv2.LINE_8)
            edge_count += len(pts)-1
        elif kind == 'occlusion':
            cv2.fillPoly(domain, [pts], 0)
    if silhouette is not None:
        domain &= silhouette
    metrics['manual_edge_segments'] = edge_count
    if not domain[sy, sx] or barrier[sy, sx]:
        warnings.append('种子点落在手工边界、遮挡区或轮廓外；请在目标面的可见内部重新点击。')
        return finish([], 'seed_on_manual_boundary')
    free = ((domain > 0) & (barrier == 0)).astype('uint8')
    minimum = max(64, work_width*work_height*.001)
    manual_region = None
    manual_closed = False
    if edge_count:
        count, labels, stats, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
        seed_label = int(labels[sy, sx])
        manual_region = (labels == seed_label).astype('uint8')
        meaningful = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= minimum]
        touches = any(bool(side.any()) for side in (manual_region[0], manual_region[-1], manual_region[:, 0], manual_region[:, -1]))
        adjacent_edge = bool((cv2.dilate(manual_edges, np.ones((3, 3), 'uint8')) & manual_region).any())
        manual_closed = adjacent_edge and not touches and (silhouette is None or len(meaningful) >= 2)
        metrics.update(manual_regions=len(meaningful), manual_closed=bool(manual_closed))
    if manual_closed:
        method = 'manual_enclosure'
        region = manual_region
        warnings.append('此区域主要由用户手线围成；文字和阴影未用来改变该边界，仍需检查线是否画在真实面界上。')
    else:
        method = 'lab_gradient_region'
        warnings.append('颜色或梯度边界可能来自文字、阴影或背景；候选区域不自动确认真实晶面，请检查并改点。')
        if edge_count:
            warnings.append('已有手线未围成可用闭合面，算法不会自动补齐断线；可先补线再重新点选。')
        rgb = np.asarray(working)
        smooth = cv2.GaussianBlur(rgb, (5, 5), 0)
        lab = cv2.cvtColor(smooth, cv2.COLOR_RGB2LAB).astype('float32')
        seed_color = np.median(lab[max(0, sy-1):sy+2, max(0, sx-1):sx+2], axis=(0, 1))
        difference = np.linalg.norm(lab-seed_color, axis=2)
        light = lab[:, :, 0]
        gradient = cv2.magnitude(cv2.Sobel(light, cv2.CV_32F, 1, 0, ksize=3),
                                 cv2.Sobel(light, cv2.CV_32F, 0, 1, ksize=3))/4
        allowed = ((difference <= tolerance) & (gradient <= max(8., tolerance*.6)) & (free > 0)).astype('uint8')
        if not allowed[sy, sx]:
            warnings.append('种子点靠近强边界或细小文字，请在目标面较均匀的内部重选。')
            return finish([], 'seed_on_image_boundary')
        _, labels, _, _ = cv2.connectedComponentsWithStats(allowed, connectivity=4)
        region = (labels == labels[sy, sx]).astype('uint8')
        if edge_count and silhouette is not None and region.sum() >= .85*free.sum():
            warnings.append('候选绕过了未闭合手线并覆盖几乎整个物体轮廓，未按一个面接受；请补齐分界线。')
            return finish([], 'repair_manual_boundary')
    area = int(region.sum())
    metrics['area_fraction'] = float(area/(work_width*work_height))
    metrics['touches_image_border'] = any(bool(side.any()) for side in (region[0], region[-1], region[:, 0], region[:, -1]))
    if metrics['touches_image_border']:
        warnings.append('候选区域触及图像边界，可能泄漏到背景或未完整拍下；请补轮廓/棱线后重试。')
        return finish([], 'leaks_to_image_boundary')
    if area < minimum:
        warnings.append('候选区域过小，可能是文字、纹理或局部阴影；请更换面内点或手工圈面。')
        return finish([], 'region_too_small')
    if metrics['area_fraction'] > .65:
        warnings.append('候选覆盖图像过大，无法可靠区分目标面与背景；请先补充边界。')
        return finish([], 'region_too_large')
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        warnings.append('没有形成闭合外边界，请手工补线或圈面。')
        return finish([], 'no_closed_contour')
    contour = max(contours, key=cv2.contourArea)
    filled = np.zeros_like(region)
    cv2.drawContours(filled, [contour], -1, 1, cv2.FILLED)
    holes = float((filled.sum()-region.sum())/max(int(filled.sum()), 1))
    metrics['hole_fraction'] = holes
    if holes > .15:
        warnings.append('候选内存在较大缺口或纹理分裂，单一面区域不能可靠表达；请补边界或改点。')
        return finish([], 'fragmented_region')
    if holes > .01:
        warnings.append('候选仅表示外边界，内部小色差缺口未单独圈出；请核对文字或遮挡。')
    perimeter = cv2.arcLength(contour, True)
    polygon = None
    for relative in (.001, .002, .004, .008, .012):
        approx = cv2.approxPolyDP(contour, max(.5, perimeter*relative), True)[:, 0, :]
        points = [[float(p[0])/scale[0], float(p[1])/scale[1]] for p in approx]
        if not 3 <= len(points) <= MAX_POLYGON_POINTS or not _simple_polygon(points):
            continue
        candidate_mask = np.zeros_like(region)
        cv2.fillPoly(candidate_mask, [approx], 1)
        spill = float(((candidate_mask > 0) & (filled == 0)).sum()/max(int(candidate_mask.sum()), 1))
        # Do not bridge meaningful gaps merely to reduce the polygon point count.
        if spill > .025 or cv2.pointPolygonTest(approx, (float(sx), float(sy)), False) < 0:
            continue
        polygon = points
        metrics.update(polygon_vertices=len(points), simplification_spill_fraction=spill,
                       polygon_area_fraction=float(cv2.contourArea(approx)/(work_width*work_height)))
        break
    if polygon is None:
        warnings.append('边界过于复杂或简化会跨越缺口，不能生成可靠简单多边形；请手工分面或补线。')
        return finish([], 'complex_boundary')
    return finish(polygon)
