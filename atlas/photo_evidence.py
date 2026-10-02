"""Soft morphology hypotheses and duplicate-aware robust evidence fusion (standard library)."""
import hashlib
import json
import math
import pathlib
import re
import statistics

CATALOGUE_PATH=pathlib.Path(__file__).with_name('morphology-priors.json')

def catalogue():
    return json.loads(CATALOGUE_PATH.read_text(encoding='utf-8'))

# Longer textbook names are consumed first; alternatives are OR, combinations within one clause are AND.
ALIASES=[
 ('五角十二面体','forms','pyritohedron'),('菱面体','forms','rhombohedron'),('十二面体','forms','dodecahedron'),
 ('八面体','forms','octahedron'),('立方体','forms','cube'),('长方体','forms','box'),
 ('双锥状','forms','dipyramid'),('双锥','forms','dipyramid'),('棱柱','forms','prism'),('柱状','forms','prism'),('锥状','forms','pyramid'),
 ('长柱','habits','elongated'),('针状','habits','elongated'),('扁平','habits','platy'),('板状','habits','platy'),('等轴状','habits','equant'),
 ('截尖','ends','truncated'),('截平','ends','truncated'),('尖端','ends','pointed'),('削边','ends','beveled'),
 ('rhombohedron','forms','rhombohedron'),('dipyramid','forms','dipyramid'),('pyramid','forms','pyramid'),('prism','forms','prism'),('octahedron','forms','octahedron'),('cube','forms','cube')]
NUMBERS={'三':3,'四':4,'六':6,'八':8,'九':9,'3':3,'4':4,'6':6,'8':8,'9':9}

def parse_morphology(text):
    if text is None:text=''
    if not isinstance(text,str) or len(text)>1000:raise ValueError('形态描述须为不超过1000字的文本')
    raw=text;hypotheses=[];unparsed=[];matched=[];negated=[]
    def preserve_negative(match):
        negated.append(match.group(0));return ' '
    text=re.sub(r'(?:不是|并非|没有|无|不属于|排除)[^，,；;。]*?(?=而是|但是|但|，|,|；|;|。|$)',preserve_negative,text)
    unparsed.extend('未应用否定描述：'+clause for clause in negated)
    uncertain=bool(re.search(r'可能|也许|不确定|疑似|或|maybe|unknown',text,re.I))
    incomplete=bool(re.search(r'残缺|缺失|不完整|看不全|看不清|遮挡|缺角|破损|missing|partial',text,re.I))
    for clause in re.split(r'或者|也可能|或|\bor\b|/|｜|\|',text.lower()):
        h={'forms':[],'orders':[],'habits':[],'ends':[]};rest=clause
        def named_form(m):
            h['orders'].append(NUMBERS[m.group(1)]);h['forms'].append({'柱':'prism','锥':'pyramid','双锥':'dipyramid'}[m.group(2)]);matched.append(m.group(0));return ' '
        rest=re.sub(r'([三四六八九34689])(?:方|角)(双锥|柱|锥)',named_form,rest)
        def section(m):
            h['section_sides']=NUMBERS[m.group(1)];matched.append(m.group(0));return ' '
        rest=re.sub(r'([三四六八九34689])边形(?:截面)?',section,rest)
        for word,field,value in ALIASES:
            if word in rest:h[field].append(value);matched.append(word);rest=rest.replace(word,' ')
        for field in ['forms','orders','habits','ends']:h[field]=sorted(set(h[field]))
        if any(h.values()):hypotheses.append(h)
        rest=re.sub(r'可能|也许|不确定|疑似|残缺|缺失|不完整|看不全|看不清|遮挡|缺角|破损|局部|端部|两端|信息|还有|有|是|呈|形态|组合|和|及|与|但|大概|的|maybe|unknown|partial|missing',' ',rest)
        rest=re.sub(r'[\s，,；;。.?？!！、+()（）]+',' ',rest).strip()
        if rest:unparsed.append(rest)
    return {'raw':raw,'negated_clauses':negated,'hypotheses':hypotheses,'uncertain':uncertain,'incomplete':incomplete,'matched':matched,'unparsed':'；'.join(unparsed),'interpretation':'soft hypotheses; never physical crystal identification'}


def morphology_penalties(specs,parsed,strength='tentative'):
    if strength not in ('tentative','likely'):raise ValueError('形态提示强度须为tentative或likely')
    cat=catalogue();weight=.005 if strength=='tentative' else .009
    if parsed['uncertain']:weight=min(weight,.005)
    details={};penalties={}
    for spec in specs:
        tags=cat['models'].get(spec['id']);losses=[]
        if tags:
            for hypothesis in parsed['hypotheses']:
                tests=[]
                for field in ('forms','orders','habits','ends'):
                    tests.extend(float(value not in tags.get(field,[])) for value in hypothesis.get(field,[]))
                if 'section_sides' in hypothesis:tests.append(float(tags.get('section_sides')!=hypothesis['section_sides']))
                if tests:losses.append(sum(tests)/len(tests))
        mismatch=min(losses) if losses else 0.
        penalties[spec['id']]=weight*mismatch
        details[spec['id']]={'mismatch':mismatch,'known_prior_tags':bool(tags),'matched_alternative':losses.index(mismatch) if losses else None}
    digest=hashlib.sha256(CATALOGUE_PATH.read_bytes()).hexdigest()
    return penalties,{'parsed':parsed,'strength':strength,'weight':weight,'catalogue_sha256':digest,'per_template':details,'policy':'OR between alternatives; soft AND within combinations; unknown text has no penalty'}


def group_views(observations):
    valid=[i for i,o in enumerate(observations) if o.get('status','usable')!='unusable']
    parent={i:i for i in valid}
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for offset,i in enumerate(valid):
        for j in valid[offset+1:]:
            a,b=observations[i],observations[j];same=a['source_sha256']==b['source_sha256']
            if not same and a.get('perceptual_hash') and b.get('perceptual_hash'):
                same=(int(a['perceptual_hash'],16)^int(b['perceptual_hash'],16)).bit_count()<=4
            if same:parent[root(j)]=root(i)
    groups={}
    for i in valid:groups.setdefault(root(i),[]).append(i)
    ordered=sorted(groups.values(),key=lambda ix:min(observations[i]['source_sha256'] for i in ix))
    def representative_key(i):
        observation=observations[i]
        # One source can have different object boxes or coverage hints. Break quality
        # ties with the actual fitting evidence, never input order or photo labels.
        evidence={key:observation.get(key) for key in ('image_size','silhouette','segments','coverage','manual_segments','occlusion_regions')}
        if evidence['occlusion_regions'] is not None:evidence['occlusion_regions']=[region['points'] for region in evidence['occlusion_regions']]
        if observation.get('face_regions'):
            evidence['face_regions']=sorted(({key:region.get(key) for key in ('points','face_id','model_fingerprint')} for region in observation['face_regions']),key=lambda region:json.dumps(region,sort_keys=True))
        content=json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False)
        return (-observation.get('quality_weight',1),observation['source_sha256'],content)
    return [{'members':sorted(ids),'representative':min(ids,key=representative_key),'weight':max(observations[i].get('quality_weight',1) for i in ids)} for ids in ordered]


def _weighted_median(values,weights):
    total=sum(weights);acc=0
    for value,weight in sorted(zip(values,weights)):
        acc+=weight
        if acc>=total/2:return value
    return max(values)


def _aggregate(values,weights):
    median=_weighted_median(values,weights)
    spread=_weighted_median([abs(x-median) for x in values],weights)
    ceiling=median+max(.012,3*spread)
    adjusted=[min(x,ceiling) for x in values] if len(values)>=4 else values
    return math.fsum(x*w for x,w in sorted(zip(adjusted,weights)))/math.fsum(weights),ceiling


def fuse_scores(matrix,observations,penalties=None):
    groups=group_views(observations)
    if not groups:raise ValueError('没有可用照片证据')
    penalties=penalties or {}
    def weights_for(use):
        result=[]
        for i in use:
            w=max(.05,groups[i]['weight'])
            # With very few views, speculative segmentation quality should not suppress a whole viewpoint.
            if len(use)<4 and observations[groups[i]['representative']].get('coverage') not in ('partial','suspected_partial'):w=.75+.25*w
            result.append(w)
        return result
    weights=weights_for(list(range(len(groups))))
    for g,w in zip(groups,weights):g['effective_weight']=w
    vectors={key:[.25 if row[g['representative']] is None else float(row[g['representative']]) for g in groups] for key,row in matrix.items()}
    def rank(use):
        result=[]
        for key,values in vectors.items():
            score,ceiling=_aggregate([values[i] for i in use],weights_for(use))
            result.append({'template_id':key,'score':round(score+penalties.get(key,0),12),'image_score':round(score,12),'morphology_penalty':penalties.get(key,0)})
        return sorted(result,key=lambda r:(r['score'],r['template_id']))
    ranking=rank(list(range(len(groups))));winner=ranking[0]['template_id'];values=vectors[winner];_,ceiling=_aggregate(values,weights)
    conflicts=[groups[i]['representative'] for i,x in enumerate(values) if x>ceiling or x>min(v[i] for v in vectors.values())+.02]
    loo=[]
    if len(groups)>=3:
        for i in range(len(groups)):
            alternative=rank([j for j in range(len(groups)) if j!=i]);loo.append({'removed_group':i,'winner':alternative[0]['template_id']})
    return {'ranking':ranking,'groups':groups,'independent_views':len(groups),'redundant_photos':sum(len(g['members'])-1 for g in groups),'conflicting_photos':conflicts,'leave_one_group_out':loo,'winner_stable_count':sum(r['winner']==winner for r in loo),'method':'sparse-view conservative quality weights; grouped mean; cap large losses at median + max(0.012, 3*MAD) for 4+ groups','not_a_confidence_probability':True}


def analysis_summary(observations,fusion,morphology,ranking_without_prior):
    usable=[i for i,o in enumerate(observations) if o.get('status')!='unusable']
    incomplete=[i for i in usable if observations[i].get('coverage') in ('partial','suspected_partial')]
    excluded=[i for i,o in enumerate(observations) if o.get('status')=='unusable']
    winner=fusion['ranking'][0]['template_id'];recommendations=[]
    if fusion['independent_views']<3:recommendations.append('补拍明显不同方向的完整视角；重复照片不增加独立证据。')
    if incomplete:recommendations.append('补拍未遮挡的另一侧及两端；残缺视角仅提供局部约束，不能证明不可见面。')
    if fusion['conflicting_photos']:recommendations.append('优先核对标记为冲突的照片轮廓、物体框，以及是否混入不同物体。')
    if morphology['parsed']['unparsed']:recommendations.append('存在未理解的形态片段，已保留原文；可补充标准名称或可见面/端部特征。')
    if len(fusion['ranking'])>1:recommendations.append('若候选仍接近，补拍端面确认截面边数，并拍包含两端的正侧面。')
    return {'usable_photos':usable,'excluded_photos':excluded,'partial_photos':incomplete,'image_only_winner':ranking_without_prior[0]['template_id'],'prior_changed_winner':winner!=ranking_without_prior[0]['template_id'],'morphology_hypotheses':morphology['parsed'],'next_observations':recommendations,'claim_boundary':{'user_information':'retained with uncertainty','image_evidence':'segmentation and outline consistency only','template_assumptions':'depth, hidden faces, crystal class and indices are unmeasured'},'status':'needs_review'}
