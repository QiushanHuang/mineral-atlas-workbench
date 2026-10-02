"""Align the user's current reference draft to source-bound photo corrections."""
import hashlib
import math
from .core import dot, mv, sub
from .editor import execute_editor
from .images import decode_image
from .photo_annotations import validate_annotation, apply_annotation
from .photo_candidates import extract_outline, match_outline
from .photo_faces import annotation_fingerprint


def align_photo(draft, image, annotation=None):
    current=execute_editor({'action':'analyze','draft':draft})
    raw,_=decode_image(image)
    checked=validate_annotation(annotation,raw)
    try:
        observation=extract_outline(image)
    except ValueError:
        if not checked or not any(f['kind']=='silhouette' for f in checked['features']):
            raise ValueError('没有可靠整体轮廓；请先采用并修正照片轮廓，或手动画一条闭合外轮廓，再对齐当前模型。')
        observation=None
    observation=apply_annotation(observation,checked,raw)
    observation['coverage']='suspected_partial' if observation.get('solidity',1)<.84 else 'unknown'
    if observation['coverage']=='suspected_partial':observation['warnings'].append('自动轮廓存在凹陷或疑似遮挡，按部分轮廓约束对齐，不视作完整外形。')
    fit=match_outline(current['model'],observation)
    view=fit['view'];R=view['R'];D=view['D'];scale=view['scale'];offset=view['offset']
    vertices=current['model']['vertices']
    projected=[]
    for v in vertices:
        q=mv(R,v);den=1-q[2]/D
        if den<=1e-8:raise ValueError('相机投影退化，无法叠加；请检查标注后重试。')
        projected.append([q[0]*scale/den+offset[0],-q[1]*scale/den+offset[1]])
    faces=current['model']['faces']
    visible=[dot(mv(R,f['n']),sub([0,0,D],mv(R,f['center'])))>1e-8 for f in faces]
    edges=[{'vertex_ids':e['ids'],'face_ids':[faces[i]['id'] for i in e['faces']],
            'points':[projected[i] for i in e['ids']]} for e in current['model']['edges'] if any(visible[i] for i in e['faces'])]
    regions=[{'face_id':f['id'],'polygon':[projected[i] for i in f['ids']]} for i,f in enumerate(faces) if visible[i]]
    return {'schema_version':1,'model_fingerprint':current['fingerprint'],
            'source_sha256':hashlib.sha256(raw).hexdigest(),'image_size':observation['image_size'],
            'annotation_sha256':annotation_fingerprint(checked),'view':view,
            'projected_edges':edges,'projected_faces':regions,
            'metrics':{k:v for k,v in fit.items() if k!='view'},
            'warnings':list(dict.fromkeys(observation.get('warnings',[])+view.get('warnings',[]))),
            'independent_validation':None,'status':'needs_review',
            'claim_boundary':'这是当前参考模型与手工照片约束的相机拟合；没有修改三维外形，面对应仍待确认，拟合残差不是独立实物精度。'}
