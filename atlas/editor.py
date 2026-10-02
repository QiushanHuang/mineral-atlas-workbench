"""Versioned convex geometry editing and conditional parameter analysis, offline.

The reference basis is metadata unless ``rebuild_axes`` is explicitly requested.
No draft is promoted to a measured mineral, crystal class, or lattice. Commands
are pure: errors leave the caller's draft intact. All axes use basis *columns*.
"""
import copy
import hashlib
import itertools
import json
import math
import re
from functools import lru_cache

from .core import (I, GENERATORS, build, cross, det, dot, finite, independent, indices, inv,
                   keymat, matrix, mesh, mv, norm, operations, sub, tr, unit, validate,
                   validate_basis)

VERSION = 'editor-2.0.0'
PRESETS = ('box', 'triangular_prism', 'hexagonal_prism', 'pyramid', 'dipyramid',
           'rhombohedron', 'truncated_box')
CLAIM = '几何及轴均为参考模型参数；指数是指定参考轴下的条件候选，不确定真实晶系、点群、晶胞或矿物种属。'


class EditorError(ValueError):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def fingerprint(draft):
    """Content identity; command history is provenance rather than geometry state."""
    if not isinstance(draft, dict):
        raise EditorError('invalid_draft', '草稿必须是对象')
    def canonical_numbers(value):
        # A browser serializes 1.0 as 1. Content identity must survive that roundtrip.
        if isinstance(value, float) and math.isfinite(value) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {key: canonical_numbers(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [canonical_numbers(item) for item in value]
        return value
    content = canonical_numbers({k: v for k, v in draft.items() if k not in ('history', 'fingerprint')})
    try:
        data = json.dumps(content, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError) as error:
        raise EditorError('invalid_draft', '草稿必须包含可保存的有限 JSON 数值') from error
    return hashlib.sha256(data).hexdigest()


def _vector(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(finite(x) for x in value):
        raise EditorError('invalid_vector', name + ' 必须是三个有限数值')
    return list(value)


def _distance(value, face_id=''):
    if not finite(value) or not 1e-5 <= value <= 10000:
        raise EditorError('invalid_distance', f'{face_id} 面距必须为 1e-5 至 10000 的正数；内部原点须处于实体内', {'face_id': face_id})
    return value


def _axes(value):
    if not isinstance(value, dict):
        raise EditorError('invalid_axes', '轴设置必须是对象')
    result = copy.deepcopy(value)
    count = result.get('index_count', 3)
    if isinstance(count, bool) or count not in (3, 4):
        raise EditorError('invalid_axes', '指数数量只能为 3 或 4')
    try:
        basis = matrix(result.get('basis'))
        if not finite(det(basis)) or not all(finite(norm(column)) for column in tr(basis)):
            raise ValueError('轴数值超过稳定计算范围，请缩小参考轴单位')
        if count == 4:
            validate_basis(basis, '六方', 4)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as error:
        raise EditorError('invalid_axes', str(error)) from error
    result.update(index_count=count, basis=copy.deepcopy(basis),
                  origin=_vector(result.get('origin', [0, 0, 0]), '参考原点'), status='user_reference')
    return result


def _validate_draft(value):
    if not isinstance(value, dict) or value.get('schema_version') != 2:
        raise EditorError('invalid_draft', '手动草稿必须是 schema_version=2；旧项目请先导入')
    draft = copy.deepcopy(value)
    if not isinstance(draft.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', draft['id']):
        raise EditorError('invalid_id', '草稿 id 须为 1–64 位字母、数字、横线或下划线')
    if not isinstance(draft.get('title'), str):
        raise EditorError('invalid_draft', '草稿 title 必须是文字')
    planes = draft.get('planes')
    if not isinstance(planes, list) or not 4 <= len(planes) <= 96:
        raise EditorError('invalid_planes', '草稿需要 4–96 张面')
    seen = set()
    for plane in planes:
        if not isinstance(plane, dict):
            raise EditorError('invalid_planes', '面记录必须是对象')
        fid = plane.get('id')
        if not isinstance(fid, str) or not re.fullmatch(r'F\d{2,3}', fid) or fid in seen:
            raise EditorError('duplicate_face_id', '面 ID 必须唯一且形如 F01，不能重复')
        seen.add(fid)
        n = _vector(plane.get('normal'), fid + ' 法向')
        if abs(norm(n) - 1) > 1e-7:
            raise EditorError('invalid_normal', fid + ' 法向必须是单位向量')
        _distance(plane.get('distance'), fid)
        for key in ('label', 'module', 'evidence'):
            if not isinstance(plane.get(key), str):
                raise EditorError('invalid_planes', fid + ' 的 ' + key + ' 必须是文字')
    for a, b in itertools.combinations(planes, 2):
        if norm(sub(a['normal'], b['normal'])) < 1e-9:
            raise EditorError('duplicate_normal', f"{a['id']} 与 {b['id']} 法向重复；请推拉已有面", {'face_ids': [a['id'], b['id']]})
    draft['axes'] = _axes(draft.get('axes'))
    if not isinstance(draft.get('history', []), list):
        raise EditorError('invalid_history', '编辑历史必须为数组')
    draft.setdefault('history', [])
    draft.setdefault('geometry_origin', [0, 0, 0])
    _vector(draft['geometry_origin'], '内部原点')
    draft.setdefault('registration_status', 'not_registered')
    fingerprint(draft)
    return draft


def _plane(number, normal, distance, module, label=None, evidence=None):
    return {'id': f'F{number:02d}', 'normal': unit(normal), 'distance': distance,
            'module': module, 'label': label or {'body': '主体面', 'top': '上端面', 'bottom': '下端面', 'bevel': '截角面'}.get(module, '单面'),
            'evidence': evidence or '用户选用的几何预设；未经实物测量'}


def _create(args):
    preset = args.get('preset', 'box')
    if preset not in PRESETS:
        raise EditorError('unknown_preset', '未知几何预设：' + str(preset))
    rows = []
    def add(normal, distance=1., module='body'):
        rows.append(_plane(len(rows) + 1, normal, distance, module))
    if preset in ('box', 'truncated_box', 'rhombohedron'):
        for i in range(3):
            for sign in (1, -1):
                normal = [0, 0, 0]
                normal[i] = sign
                add(normal, module=('top' if sign > 0 else 'bottom') if i == 2 else 'body')
        if preset == 'truncated_box':
            for normal in itertools.product((-1, 1), repeat=3):
                add(normal, 2.5 / math.sqrt(3), 'bevel')
        if preset == 'rhombohedron':
            # Equal-length generators at 75 degrees define a geometric rhombohedron.
            c = math.cos(math.radians(75))
            s = math.sin(math.radians(75))
            z = math.sqrt(1 - c*c - (c-c*c)**2/(s*s))
            transform = [[1, c, c], [0, s, (c-c*c)/s], [0, 0, z]]
            reciprocal = inv(tr(transform))
            for p in rows:
                q = mv(reciprocal, p['normal'])
                p.update(normal=unit(q), distance=p['distance']/norm(q))
    elif preset in ('triangular_prism', 'hexagonal_prism'):
        count = 3 if preset == 'triangular_prism' else 6
        for i in range(count):
            angle = 2*math.pi*i/count
            add([math.cos(angle), math.sin(angle), 0])
        add([0, 0, 1], module='top')
        add([0, 0, -1], module='bottom')
    else:
        for z in ((1, -1) if preset == 'dipyramid' else (1,)):
            for x, y in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                add([x, y, z], 1/math.sqrt(2), 'top' if z > 0 else 'bottom')
        if preset == 'pyramid':
            add([0, 0, -1], module='bottom')
    draft = {'schema_version': 2, 'id': args.get('id', 'draft-' + preset.replace('_', '-')),
             'title': args.get('title', preset), 'geometry_source': 'cartesian_planes',
             'planes': rows, 'axes': {'basis': copy.deepcopy(I), 'index_count': 3,
                                    'origin': [0, 0, 0], 'status': 'user_reference'},
             'geometry_origin': [0, 0, 0], 'history': [], 'preset': preset,
             'registration_status': 'not_registered', 'units': 'model_relative_units',
             'algorithm_version': VERSION, 'claim_boundary': CLAIM}
    parameters = args.get('parameters', {})
    if not isinstance(parameters, dict):
        raise EditorError('invalid_parameters', '预设参数必须是对象')
    if parameters:
        model, _ = _geometry(draft)
        extents = [max(v[i] for v in model['vertices']) - min(v[i] for v in model['vertices']) for i in range(3)]
        factors = [parameters.get(key, size)/size if finite(parameters.get(key, size)) else None
                   for key, size in zip(('width', 'depth', 'height'), extents)]
        _scale(draft, factors)
    return draft


def _import(spec):
    try:
        model, _ = build(spec)
    except (ValueError, TypeError, KeyError) as error:
        raise EditorError('invalid_legacy_project', '旧项目不能导入：' + str(error)) from error
    return {'schema_version': 2, 'id': spec['id'], 'title': spec.get('title', spec['id']),
            'geometry_source': 'cartesian_planes',
            'planes': [{'id': f['id'], 'normal': f['n'], 'distance': f['d'], 'label': f['label'],
                        'module': 'single', 'evidence': f['photoEvidence'], 'source_hkl': f['modelMiller'],
                        **({'photo_label': f['photoLabel']} if 'photoLabel' in f else {})} for f in model['faces']],
            'axes': {'basis': copy.deepcopy(spec['basis']), 'index_count': spec.get('index_count', 3),
                     'origin': [0, 0, 0], 'status': 'user_reference'},
            'source_indexing': {'basis': copy.deepcopy(spec['basis']), 'index_count': spec.get('index_count', 3),
                                'status': 'imported_reference'},
            'reference_symmetry': {'basis': copy.deepcopy(spec['basis']), 'point_group': spec['point_group'],
                                   'crystal_system': spec['crystal_system'], 'status': 'imported_reference'},
            'source_fingerprint': fingerprint(spec), 'geometry_origin': [0, 0, 0],
            'registration_status': 'not_registered', 'history': [],
            'units': 'model_relative_units', 'algorithm_version': VERSION, 'claim_boundary': CLAIM}


def _geometry(draft):
    rows = [{'id': p['id'], 'n': p['normal'], 'd': p['distance'],
             'label': p['label'], 'module': p['module'], 'photoEvidence': p['evidence'],
             'modelMiller': None} for p in draft['planes']]
    try:
        model, stats = mesh(rows)
    except ValueError as error:
        message = str(error)
        code = 'inactive_faces' if '截去' in message else ('unbounded_geometry' if '开放' in message else 'degenerate_geometry')
        raise EditorError(code, message) from error
    quality = validate(model, check_symmetry=False)
    if not quality['ok']:
        raise EditorError('invalid_geometry', '；'.join(quality['errors']), quality)
    quality.update(stats=stats, claim_level='reference_geometry')
    return model, quality


def _scale(draft, factors):
    if not isinstance(factors, (list, tuple)) or len(factors) != 3 or not all(finite(x) and 1e-4 <= x <= 10000 for x in factors):
        raise EditorError('invalid_scale', '宽、厚、高缩放系数须为 1e-4 至 10000 的正数')
    for p in draft['planes']:
        q = [n/s for n, s in zip(p['normal'], factors)]
        p.update(normal=unit(q), distance=p['distance']/norm(q))


def _selected(draft, command):
    ids = command.get('face_ids')
    available = {p['id']: p for p in draft['planes']}
    if not isinstance(ids, list) or not ids or any(not isinstance(fid, str) or fid not in available for fid in ids):
        raise EditorError('unknown_face', '请选取当前草稿中存在的面 ID', {'face_ids': ids})
    return [available[fid] for fid in dict.fromkeys(ids)]


def _apply(draft, command):
    if not isinstance(command, dict):
        raise EditorError('invalid_command', '编辑命令必须是对象')
    kind = command.get('type')
    geometry_changed = kind in ('move_faces', 'scale', 'truncate', 'rebuild_axes', 'set_plane')
    if kind == 'move_faces':
        selected = _selected(draft, command)
        delta = command.get('delta')
        if not finite(delta):
            raise EditorError('invalid_distance', '推拉距离必须是有限数值')
        scope = command.get('scope', 'selected')
        if scope == 'module':
            modules = {p['module'] for p in selected}
            if 'single' in modules:
                raise EditorError('unknown_module', '导入面没有已确认的模块归属；请使用只改选中面')
            selected = [p for p in draft['planes'] if p['module'] in modules]
        elif scope == 'opposite':
            linked = {p['id']: p for p in selected}
            for p in selected:
                opposite = [q for q in draft['planes'] if norm([a+b for a, b in zip(p['normal'], q['normal'])]) < 1e-7
                            and abs(p['distance']-q['distance']) < 1e-7*max(1, p['distance'])]
                if len(opposite) != 1:
                    raise EditorError('invalid_opposite', p['id'] + ' 没有等距对称的对面；请单独编辑')
                linked[opposite[0]['id']] = opposite[0]
            selected = list(linked.values())
        elif scope != 'selected':
            raise EditorError('invalid_scope', '联动范围只能为选中面、明确模块或等距对面')
        for p in selected:
            p['distance'] = _distance(p['distance'] + delta, p['id'])
    elif kind == 'scale':
        _scale(draft, command.get('factors'))
    elif kind == 'truncate':
        normal = _vector(command.get('normal'), '截切法向')
        try:
            normal = unit(normal)
        except ValueError as error:
            raise EditorError('invalid_normal', str(error)) from error
        distance = _distance(command.get('distance'))
        used = {p['id'] for p in draft['planes']}
        fid = command.get('id') or next((f'F{i:02d}' for i in range(1, 1000) if f'F{i:02d}' not in used), None)
        draft['planes'].append({'id': fid, 'normal': normal, 'distance': distance, 'module': 'bevel',
                                'label': str(command.get('label', '新增截切面')),
                                'evidence': str(command.get('evidence', '用户手动截切，参数为参考值'))})
    elif kind in ('set_axes', 'rebuild_axes'):
        old_axes = copy.deepcopy(draft['axes'])
        new_axes = _axes({**old_axes, **{key: command[key] for key in ('basis', 'index_count', 'origin') if key in command}})
        if kind == 'rebuild_axes':
            source = draft.get('source_indexing')
            if not source or source.get('index_count') != new_axes['index_count'] or any('source_hkl' not in p for p in draft['planes']):
                raise EditorError('indices_required', '按轴重建需要每张面的已记录参考指数且指数数量相同；不能用未确认候选自动补齐')
            reciprocal = inv(tr(new_axes['basis']))
            for p in draft['planes']:
                try:
                    h = indices(p['source_hkl'], new_axes['index_count'])
                except ValueError as error:
                    raise EditorError('invalid_indices', p['id'] + ' 的记录指数无效') from error
                p['normal'] = unit(mv(reciprocal, independent(h)))
            draft['source_indexing'] = {**source, 'basis': copy.deepcopy(new_axes['basis']), 'status': 'user_rebuilt_reference'}
        draft['axes'] = new_axes
    elif kind == 'metadata':
        if 'title' in command:
            if not isinstance(command['title'], str):
                raise EditorError('invalid_metadata', '标题必须是文字')
            draft['title'] = command['title']
        if 'face_ids' not in command and any(key in command for key in ('label', 'evidence')):
            raise EditorError('unknown_face', '修改面标签或依据前须选取面')
        for p in _selected(draft, command) if 'face_ids' in command else []:
            for key in ('label', 'evidence'):
                if key in command:
                    if not isinstance(command[key], str):
                        raise EditorError('invalid_metadata', key + ' 必须是文字')
                    p[key] = command[key]
    elif kind == 'set_plane':
        selected = _selected(draft, command)
        if len(selected) != 1:
            raise EditorError('invalid_selection', '高级平面编辑一次只修改一张面')
        if 'normal' in command:
            selected[0]['normal'] = unit(_vector(command['normal'], '平面法向'))
        if 'distance' in command:
            selected[0]['distance'] = _distance(command['distance'], selected[0]['id'])
    else:
        raise EditorError('unknown_command', '未知编辑命令：' + str(kind))
    if geometry_changed:
        draft['registration_status'] = 'needs_refit'
    return geometry_changed


def _angle(a, b):
    return math.degrees(math.acos(max(-1., min(1., dot(a, b)/norm(a)/norm(b)))))


@lru_cache(maxsize=24)
def _integer_directions(basis_key, count, maximum):
    basis = [list(basis_key[i:i+3]) for i in (0, 3, 6)]
    reciprocal = inv(tr(basis))
    output = []
    for hkl in itertools.product(range(-maximum, maximum+1), repeat=3):
        if not any(hkl) or math.gcd(*hkl) != 1:
            continue
        displayed = (hkl[0], hkl[1], -hkl[0]-hkl[1], hkl[2]) if count == 4 else hkl
        if max(map(abs, displayed)) <= maximum:
            output.append((displayed, unit(mv(reciprocal, hkl))))
    return output


def _index_candidates(normal, axes, maximum, tolerance):
    basis_key = tuple(x for row in axes['basis'] for x in row)
    nearest = 180.
    candidates = []
    for hkl, direction in _integer_directions(basis_key, axes['index_count'], maximum):
        error = _angle(normal, direction)
        nearest = min(nearest, error)
        if error <= tolerance:
            candidates.append({'hkl': list(hkl), 'error_deg': error})
    candidates.sort(key=lambda row: (row['error_deg'], max(map(abs, row['hkl'])), sum(map(abs, row['hkl']))))
    return {'status': 'conditional_candidates' if candidates else 'no_solution_within_tolerance',
            'candidates': candidates[:8], 'total_candidates': len(candidates),
            'max_index': maximum, 'tolerance_deg': tolerance, 'nearest_error_deg': nearest,
            'reason': '仅指定参考轴下的低阶整数方向；多个候选不能视作唯一识别' if candidates else '搜索范围内无满足角度容差的低阶整数方向；保留未知'}


@lru_cache(maxsize=24)
def _oriented_groups(basis_key):
    basis = [list(basis_key[i:i+3]) for i in (0, 3, 6)]
    return tuple((pg, tuple(tuple(tuple(row) for row in transform) for transform in operations(pg, basis)))
                 for pg in GENERATORS)


@lru_cache(maxsize=48)
def _geometry_symmetry(vertices_key, basis_key):
    """Match convex vertex sets; do not infer lattice metrics or physical classes."""
    center = [sum(v[i] for v in vertices_key)/len(vertices_key) for i in range(3)]
    centered = [sub(v, center) for v in vertices_key]
    tolerance = max(1., max(norm(v) for v in centered))*1e-7
    bins = {}
    for v in centered:
        key = tuple(math.floor(x/tolerance) for x in v)
        bins.setdefault(key, []).append(v)
    tested = {}
    def preserves(transform):
        key = keymat(transform)
        if key in tested:
            return tested[key]
        for v in centered:
            q = mv(transform, v)
            at = [math.floor(x/tolerance) for x in q]
            if not any(norm(sub(p, q)) <= tolerance
                       for near in itertools.product(*(range(x-1, x+2) for x in at))
                       for p in bins.get(near, [])):
                tested[key] = False
                return False
        tested[key] = True
        return True
    candidates = []
    for pg, transforms in _oriented_groups(basis_key):
        if all(preserves(t) for t in transforms):
            candidates.append({'point_group': pg, 'order': len(transforms)})
    candidates.sort(key=lambda row: (-row['order'], row['point_group']))
    highest = candidates[0]['order'] if candidates else 0
    return {'status': 'basis_relative_compatible', 'candidates': candidates,
            'highest_candidates': [row for row in candidates if row['order'] == highest],
            'center': center, 'spatial_tolerance': tolerance, 'tested_groups': len(GENERATORS),
            'tested_distinct_operations': len(tested), 'orientation_search': 'reference_frame_only',
            'claim_boundary': '仅检查 32 群操作在当前参考方向下是否保持凸体顶点集合；未遍历任意方向，也未验证晶格度量或测定实物晶系、点群。'}


@lru_cache(maxsize=64)
def _zones(planes_key):
    """At least three distinct faces whose normals share one perpendicular axis."""
    tolerance_deg = .01
    sine = math.sin(math.radians(tolerance_deg))
    cosine = math.cos(math.radians(tolerance_deg))
    directions = []
    for (_, a), (_, b) in itertools.combinations(planes_key, 2):
        direction = cross(a, b)
        if norm(direction) < 1e-7:
            continue
        direction = unit(direction)
        # A zone is an unoriented line: choose a stable representative sign.
        first = next((x for x in direction if abs(x) > 1e-9), 1.)
        direction = [(-x if first < 0 else x) for x in direction]
        if any(abs(dot(direction, old)) >= cosine for old in directions):
            continue
        directions.append(direction)
    zones = []
    for direction in directions:
        members = [(fid, math.degrees(math.asin(min(1., abs(dot(n, direction))))))
                   for fid, n in planes_key if abs(dot(n, direction)) <= sine]
        if len(members) >= 3:
            zones.append({'face_ids': sorted(fid for fid, _ in members),
                          'direction': [0. if abs(x) < 1e-12 else x for x in direction],
                          'max_deviation_deg': max(error for _, error in members),
                          'tolerance_deg': tolerance_deg, 'status': 'geometric_zone_candidate',
                          'direction_indices': None,
                          'claim_boundary': '三张以上不同面的法向与此几何方向近似垂直；方向指数未经独立确认，不认定真实晶带。'})
    zones.sort(key=lambda row: (-len(row['face_ids']), row['face_ids']))
    return zones


def _analysis(draft, model, quality, args):
    maximum = args.get('max_index', 8)
    tolerance = args.get('tolerance_deg', 1.)
    if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 16:
        raise EditorError('invalid_analysis_options', '指数搜索上限须为 1–16 的整数')
    if not finite(tolerance) or not 0 <= tolerance <= 15:
        raise EditorError('invalid_analysis_options', '指数角度容差须在 0–15 度之间')
    vs = model['vertices']
    faces = []
    for f in model['faces']:
        ids = f['ids']
        area = sum(norm(cross(sub(vs[a], vs[ids[0]]), sub(vs[b], vs[ids[0]])))/2 for a, b in zip(ids[1:-1], ids[2:]))
        faces.append({'id': f['id'], 'area': area, 'normal': f['n'], 'distance': f['d'],
                      'vertex_ids': ids, 'center': f['center'],
                      'index_candidates': _index_candidates(f['n'], draft['axes'], maximum, tolerance)})
    edges = []
    for e in model['edges']:
        a, b = e['ids']
        adjacent = [model['faces'][i] for i in e['faces']]
        exterior = _angle(adjacent[0]['n'], adjacent[1]['n'])
        face_ids = sorted(f['id'] for f in adjacent)
        edges.append({'id': ':'.join(face_ids), 'vertex_ids': [a, b], 'face_ids': face_ids,
                      'length': norm(sub(vs[a], vs[b])), 'direction': unit(sub(vs[b], vs[a])),
                      'exterior_angle_deg': exterior, 'interior_angle_deg': 180-exterior})
    groups, visited = [], set()
    for i, f in enumerate(faces):
        if i in visited:
            continue
        members = [j for j, g in enumerate(faces) if abs(dot(f['normal'], g['normal'])) >= math.cos(math.radians(.01))]
        visited.update(members)
        if len(members) > 1:
            groups.append({'face_ids': [faces[j]['id'] for j in members], 'tolerance_deg': .01})
    axes = copy.deepcopy(draft['axes'])
    a, b, c = tr(axes['basis'])
    axes.update(lengths=list(map(norm, (a, b, c))), angles=[_angle(b, c), _angle(a, c), _angle(a, b)],
                angle_order=['alpha_b_c', 'beta_a_c', 'gamma_a_b'],
                display_axes=[a, b, [-x-y for x, y in zip(a, b)], c] if axes['index_count'] == 4 else [a, b, c],
                labels=['a1', 'a2', 'a3', 'c'] if axes['index_count'] == 4 else ['a', 'b', 'c'])
    center = [sum(v[i] for v in vs)/len(vs) for i in range(3)]
    scale = max(norm(sub(v, center)) for v in vs)
    inversion_error = max(min(norm(sub([2*center[i]-v[i] for i in range(3)], q)) for q in vs) for v in vs)
    return {'volume': quality['volume'], 'area': sum(f['area'] for f in faces), 'faces': faces,
            'edges': edges, 'axes': axes, 'parallel_groups': groups, 'quality': quality,
            'geometry_symmetry_candidates': copy.deepcopy(_geometry_symmetry(
                tuple(tuple(v) for v in vs), tuple(x for row in axes['basis'] for x in row))),
            'zone_candidates': copy.deepcopy(_zones(tuple((p['id'], tuple(p['normal'])) for p in draft['planes']))),
            'symmetry_observations': {'inversion_center_candidate': center if inversion_error <= scale*1e-7 else None,
                                      'inversion_residual': inversion_error, 'status': 'geometric_check_only_not_crystal_class'},
            'dihedral_convention': '外二面角为相邻外法线夹角 [0,180]°；凸体内二面角=180°−外二面角。',
            'units': 'model_relative_units', 'claim_boundary': CLAIM}


def execute_editor(args):
    """Create/import/analyze/apply; return a JSON-safe draft, mesh and analysis."""
    if not isinstance(args, dict):
        raise EditorError('invalid_arguments', '编辑器参数必须是对象')
    action = args.get('action', 'analyze')
    parent = None
    geometry_changed = False
    if action == 'create':
        draft = _create(args)
    elif action == 'import':
        draft = _import(args.get('spec'))
    elif action in ('analyze', 'apply'):
        draft = _validate_draft(args.get('draft'))
        parent = fingerprint(draft)
        if args.get('expected_fingerprint') is not None and args['expected_fingerprint'] != parent:
            raise EditorError('stale_draft', '草稿已改变，请重新解析后再应用建议')
        if action == 'apply':
            geometry_changed = _apply(draft, args.get('command'))
    else:
        raise EditorError('unknown_action', '未知编辑器操作：' + str(action))
    draft = _validate_draft(draft)
    model, quality = _geometry(draft)
    analysis = _analysis(draft, model, quality, args)
    content_id = fingerprint(draft)
    warnings = []
    if geometry_changed:
        warnings.append('几何已改变，旧照片的顶点/棱对应与相机拟合须重新检查，旧配准不得直接复用。')
    source = draft.get('source_indexing', {})
    same_basis = source.get('basis') == draft['axes']['basis'] and source.get('index_count') == draft['axes']['index_count']
    for p, face in zip(draft['planes'], model['faces']):
        hkl = p.get('source_hkl')
        if same_basis and hkl:
            try:
                parsed = indices(hkl, draft['axes']['index_count'])
                expected = unit(mv(inv(tr(draft['axes']['basis'])), independent(parsed)))
                if norm(sub(expected, face['n'])) < 1e-7:
                    face['modelMiller'] = parsed
            except ValueError:
                warnings.append(p['id'] + ' 原记录指数无法验证，当前指数保留未知')
    reference = draft.get('reference_symmetry')
    if reference:
        try:
            transformations = operations(reference['point_group'], reference['basis'])
            scale = max(1, max(norm(v) for v in model['vertices']))
            preserved = all(min(norm(sub(mv(t, v), q)) for q in model['vertices']) <= 1e-7*scale for t in transformations for v in model['vertices'])
            analysis['reference_symmetry_preserved'] = preserved
            if not preserved:
                warnings.append('当前几何不再保持导入时声明的参考点群；原声明仅留作来源记录。')
        except (ValueError, KeyError, TypeError):
            warnings.append('原参考点群记录无效，未用来认定当前几何对称性。')
    model.update(reference_axes=analysis['axes'], indexing={'indexCount': draft['axes']['index_count'],
                 'referenceBasis': draft['axes']['basis'], 'status': 'user_reference', 'pointGroup': None},
                 crystalSystem=None, claimLevel='reference_geometry', geometryStatus=CLAIM,
                 info={'title': draft['title'], 'desc': CLAIM}, draftFingerprint=content_id)
    analysis['input_fingerprint'] = content_id
    if action == 'apply':
        draft['history'].append({'command': copy.deepcopy(args['command']), 'parent_fingerprint': parent,
                                 'result_fingerprint': content_id, 'geometry_changed': geometry_changed,
                                 'algorithm_version': VERSION})
    return {'draft': draft, 'model': model, 'analysis': analysis, 'fingerprint': content_id,
            'warnings': list(dict.fromkeys(warnings))}
