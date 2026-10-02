"""Offline review interchange. Validate proposals; never execute or send them."""
from copy import deepcopy
import json
import math
from pathlib import Path
import re
from .core import matrix, validate_basis
from .editor import fingerprint

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError('复核数据必须为有限数值组成的 JSON') from exc


def _sha(value):
    # Packet data takes the same numeric canonicalization as draft identity.
    # Browser JSON.stringify turns integral floats into integers.
    return fingerprint({'review_payload': value})


def _fingerprint(draft):
    # Reuse the editor's public identity, including browser 1.0 -> 1 roundtrips.
    return fingerprint(draft)


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError('复核对象缺少必要字段或包含未知字段')


def _text(value, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('复核理由和证据必须为非空文本且长度有限')
    return value


def _token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('复核 ID 格式不合法')
    return value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('复核参数必须是有限数值')
    return value


def _vector(value, size=3):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError('复核向量维数不合法')
    return [_number(v) for v in value]


def _policy():
    prompt = (Path(__file__).with_name('review-prompt.txt')).read_text(encoding='utf-8')
    schema = json.loads((ROOT / 'schema/review.schema.json').read_text(encoding='utf-8'))
    return prompt, _sha({'prompt': prompt, 'schema': schema})


def _annotations(value):
    """Export only the documented geometric annotation fields, never paths/images."""
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    if len(items) > 24:
        raise ValueError('复核标注最多对应 24 张图')
    result = []
    for item in items:
        if item is None:
            continue
        if not isinstance(item, dict) or type(item.get('schema_version')) is not int or item.get('schema_version') != 1:
            raise ValueError('复核标注版本不受支持')
        dims = _vector(item.get('image_size'), 2)
        if min(dims) <= 0 or any(int(v) != v for v in dims):
            raise ValueError('标注图像尺寸不合法')
        digest = item.get('source_sha256')
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError('标注缺少原图指纹')
        features = item.get('features')
        if not isinstance(features, list) or len(features) > 200:
            raise ValueError('标注特征列表不合法')
        safe, seen = [], set()
        for feature in features:
            if not isinstance(feature, dict):
                raise ValueError('标注特征不合法')
            fid = _token(feature.get('id'))
            if fid in seen:
                raise ValueError('同图标注 ID 重复')
            seen.add(fid)
            kind = feature.get('kind')
            if kind not in ('edge', 'silhouette', 'face', 'occlusion', 'uncertain'):
                raise ValueError('未知用户标注类型')
            points = feature.get('points')
            if not isinstance(points, list) or not 2 <= len(points) <= 500:
                raise ValueError('标注点数量不合法')
            for point in points:
                x, y = _vector(point, 2)
                if not 0 <= x <= dims[0] or not 0 <= y <= dims[1]:
                    raise ValueError('标注点超出原图')
            clean = {'id': fid, 'kind': kind, 'points': deepcopy(points)}
            if 'face_id' in feature:
                clean['face_id'] = _token(feature['face_id'])
            if 'model_fingerprint' in feature:
                binding = feature['model_fingerprint']
                if not isinstance(binding, str) or not SHA256.fullmatch(binding):
                    raise ValueError('用户标注特征的模型关联指纹不合法，请重新确认关联')
                clean['model_fingerprint'] = binding
            safe.append(clean)
        clean_item = {'schema_version': 1, 'image_size': dims, 'source_sha256': digest,
                      'features': safe, 'provenance': 'unverified_user_drawn'}
        result.append(clean_item)
    return result


def make_review_packet(draft, model, analysis, annotations=None):
    """Make a deterministic, path-free local interchange packet with no image bytes."""
    input_sha = _fingerprint(draft)
    if not isinstance(model, dict) or not isinstance(analysis, dict):
        raise ValueError('复核需要几何模型和解析对象')
    if analysis.get('input_fingerprint', analysis.get('fingerprint', input_sha)) != input_sha or model.get('draftFingerprint', input_sha) != input_sha:
        raise ValueError('解析已过期，请先重新解析当前草稿')
    faces, ids = [], []
    for f in model.get('faces', []):
        fid = _token(f.get('id'))
        if fid in ids:
            raise ValueError('模型面 ID 重复')
        ids.append(fid)
        face = {'id': fid, 'normal': _vector(f.get('n')), 'distance': _number(f.get('d'))}
        if 'ids' in f:
            face['vertex_ids'] = deepcopy(f['ids'])
        if 'modelMiller' in f:
            face['reference_indices'] = deepcopy(f['modelMiller'])
        faces.append(face)
    if not ids:
        raise ValueError('复核需要至少一张有效模型面')
    vertices = [_vector(v) for v in model.get('vertices', [])]
    safe_annotations = _annotations(annotations)
    for item in safe_annotations:
        if any('face_id' in f and f.get('model_fingerprint') != input_sha for f in item['features']):
            raise ValueError('用户标注特征的面关联未绑定当前模型，请逐项重新确认关联或清除旧关联')
        if any(f.get('face_id') and f['face_id'] not in ids for f in item['features']):
            raise ValueError('用户标注关联未知模型面')
    prompt, policy_sha = _policy()
    summary = {'face_ids': ids, 'faces': faces, 'vertices': vertices,
               'face_count': len(ids), 'vertex_count': len(vertices),
               'units': 'relative_model_units', 'physical_indices_verified': False}
    # The geometry is sufficient to independently inspect angles/areas. Do not copy
    # arbitrary analysis metadata, provenance strings, filesystem paths, or images.
    for key in ('volume', 'surface_area'):
        if key in analysis:
            summary[key] = _number(analysis[key])
    if 'area' in analysis:
        summary['surface_area'] = _number(analysis['area'])
    if isinstance(model.get('indexing'), dict) and 'basis' in model['indexing']:
        basis = model['indexing']['basis']
        if isinstance(basis, list) and len(basis) == 3:
            summary['reference_basis'] = [_vector(row) for row in basis]
    if isinstance(draft.get('axes'), dict):
        axes = draft['axes']
        summary['reference_basis'] = [_vector(row) for row in axes['basis']]
        summary['reference_origin'] = _vector(axes['origin'])
        summary['index_count'] = axes['index_count']
    body = {'schema_version': 1, 'input_sha256': input_sha, 'policy_sha256': policy_sha,
            'brief': '复核参考几何及用户标注，提出有证据的待采纳建议；未附原图。',
            'model_summary': summary, 'annotations': safe_annotations, 'prompt': prompt}
    body['id'] = 'review-' + _sha(body)[:24]
    body['response_template'] = {'schema_version': 1, 'packet_id': body['id'],
                                 'input_sha256': input_sha, 'policy_sha256': policy_sha,
                                 'suggestions': [], 'uncertain': []}
    body['packet_sha256'] = _sha(body)
    return body


def _command(command, target, face_ids):
    if not isinstance(command, dict):
        raise ValueError('建议命令必须是对象')
    kind = command.get('type')
    if kind == 'move_faces':
        _fields(command, ('type', 'face_ids', 'delta'), ('scope',))
        ids = command['face_ids']
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids) or not set(ids) <= face_ids:
            raise ValueError('推拉建议包含未知或重复面 ID')
        _number(command['delta'])
        if command.get('scope', 'selected') not in ('selected', 'module', 'opposite'):
            raise ValueError('未知推拉联动范围')
        expected_target = 'geometry'
    elif kind == 'set_axes':
        _fields(command, ('type', 'basis', 'index_count'), ('origin',))
        basis = command['basis']
        if not isinstance(basis, list) or len(basis) != 3:
            raise ValueError('参考轴必须为 3×3 基底')
        [_vector(row) for row in basis]
        if isinstance(command['index_count'], bool) or command['index_count'] not in (3, 4):
            raise ValueError('指数维数只能是 3 或 4')
        try:
            matrix(basis)
            if command['index_count'] == 4:
                validate_basis(basis, '六方', 4)
        except (OverflowError, ZeroDivisionError) as exc:
            raise ValueError('参考轴数值范围不合法') from exc
        if 'origin' in command:
            _vector(command['origin'])
        expected_target = 'axes'
    elif kind == 'truncate':
        _fields(command, ('type', 'normal', 'distance'), ('id', 'label', 'evidence'))
        normal = _vector(command['normal'])
        if math.hypot(*normal) < 1e-12 or not math.isfinite(math.hypot(*normal)) or _number(command['distance']) <= 0:
            raise ValueError('截切需要有效法线和正支持距离')
        if 'id' in command and (not re.fullmatch(r'F\d{2,3}', _token(command['id'])) or command['id'] in face_ids):
            raise ValueError('新截面 ID 不合法或已存在')
        for key in ('label', 'evidence'):
            if key in command:
                _text(command[key])
        expected_target = 'geometry'
    else:
        raise ValueError('未允许的复核命令')
    if target != expected_target:
        raise ValueError('建议领域与命令不匹配')


def review_response(packet, response, current_fingerprint, selected_ids=None):
    """Validate an entire reply, returning selected commands without executing them."""
    _fields(packet, ('schema_version', 'id', 'input_sha256', 'policy_sha256', 'brief',
                     'model_summary', 'annotations', 'prompt', 'response_template', 'packet_sha256'))
    prompt, policy_sha = _policy()
    if type(packet['schema_version']) is not int or packet['schema_version'] != 1 or packet['policy_sha256'] != policy_sha or packet['prompt'] != prompt:
        raise ValueError('复核策略已改变，请重新导出复核包')
    if _sha({k: v for k, v in packet.items() if k != 'packet_sha256'}) != packet['packet_sha256']:
        raise ValueError('复核包内容或输入指纹已改变')
    if not isinstance(current_fingerprint, str) or not SHA256.fullmatch(current_fingerprint) or packet['input_sha256'] != current_fingerprint:
        raise ValueError('草稿已改变，拒绝过期复核回复')
    _fields(response, ('schema_version', 'packet_id', 'input_sha256', 'policy_sha256', 'suggestions', 'uncertain'))
    _canonical(response)
    if type(response['schema_version']) is not int or response['schema_version'] != 1 or response['packet_id'] != packet['id'] or response['input_sha256'] != current_fingerprint or response['policy_sha256'] != policy_sha:
        raise ValueError('回复不属于当前模型或策略')
    suggestions = response['suggestions']
    if not isinstance(suggestions, list) or len(suggestions) > 100:
        raise ValueError('建议数量不合法')
    uncertain = response['uncertain']
    if not isinstance(uncertain, list) or len(uncertain) > 100:
        raise ValueError('不确定项必须为文本列表')
    for item in uncertain:
        _text(item)
    face_ids = set(packet['model_summary']['face_ids'])
    # Annotation references include the image hash to disambiguate repeated edge IDs.
    annotation_ids = {item['source_sha256'] + ':' + f['id'] for item in packet['annotations'] for f in item['features']}
    seen = set()
    for suggestion in suggestions:
        _fields(suggestion, ('id', 'target', 'reason', 'evidence', 'command'))
        sid = _token(suggestion['id'])
        if sid in seen:
            raise ValueError('建议 ID 重复')
        seen.add(sid)
        if suggestion['target'] not in ('geometry', 'axes'):
            raise ValueError('未知建议领域')
        _text(suggestion['reason'])
        evidence = suggestion['evidence']
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 50:
            raise ValueError('每项建议必须附有可追溯证据')
        for item in evidence:
            _fields(item, ('kind', 'reference', 'detail'))
            _text(item['detail']); ref = _text(item['reference'], 200)
            kind = item['kind']
            if kind == 'model_face' and ref in face_ids:
                pass
            elif kind == 'model_summary' and ref in packet['model_summary']:
                pass
            elif kind == 'user_annotation' and ref in annotation_ids:
                pass
            elif kind == 'visual_observation':
                raise ValueError('本复核包未附原图，不能把用户标注或模型冒充像素观察')
            else:
                raise ValueError('证据类型或引用未知')
        _command(suggestion['command'], suggestion['target'], face_ids)
    selected = [] if selected_ids is None else selected_ids
    if not isinstance(selected, list) or any(not isinstance(s, str) for s in selected) or len(set(selected)) != len(selected) or not set(selected) <= seen:
        raise ValueError('选择了未知或重复的建议')
    # Preserve response order so dependent operations remain reviewable.
    commands = [deepcopy(s['command']) for s in suggestions if s['id'] in selected]
    return {'schema_version': 1, 'packet_id': packet['id'], 'input_sha256': current_fingerprint,
            'policy_sha256': policy_sha, 'suggestions': deepcopy(suggestions),
            'uncertain': deepcopy(uncertain), 'selected_ids': deepcopy(selected),
            'selected_commands': commands, 'status': 'reviewed_not_applied'}
