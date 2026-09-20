"""Reference-basis indices and bounded half-space geometry; Python standard library only."""
import math, itertools, re
from fractions import Fraction
from functools import lru_cache
I=[[1.,0,0],[0,1.,0],[0,0,1.]]
SYSTEMS=('三斜','单斜','正交','四方','三方','六方','等轴')
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): return math.sqrt(dot(a,a))
def unit(a):
 n=norm(a)
 if n<1e-14: raise ValueError('零向量不能定义方向')
 return [x/n for x in a]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def tr(A): return [list(x) for x in zip(*A)]
def mv(A,v): return [dot(r,v) for r in A]
def mm(A,B): return [[dot(r,c) for c in tr(B)] for r in A]
def det(A): return dot(A[0],cross(A[1],A[2]))
def inv(A):
 d=det(A)
 if abs(d)<1e-12: raise ValueError('基底奇异或病态：三个独立轴必须张成三维空间')
 return [[x/d for x in row] for row in tr([cross(A[1],A[2]),cross(A[2],A[0]),cross(A[0],A[1])])]
def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def matrix(A):
 if not isinstance(A,list) or len(A)!=3 or any(not isinstance(r,list) or len(r)!=3 or not all(finite(x) for x in r) for r in A):raise ValueError('basis 必须是有限数值的3×3矩阵，列为独立晶轴')
 if det(A)<=1e-10:raise ValueError('basis 必须为非退化右手基底，det(A)>0')
 if max(norm(c) for c in tr(A))/min(norm(c) for c in tr(A))>1000:raise ValueError('轴比超过1000，需重新选取数值尺度')
 if norm([v for r in A for v in r])*norm([v for r in inv(A) for v in r])>1e6:raise ValueError('基底病态，不能稳定反算法线')
 return A

def indices(value,count=3):
 if isinstance(value,str):
  s=value.strip().replace('−','-').replace('–','-');s=re.sub(r'(\d)[\u0304\u0305]',r'-\1',s)
  if s[:1] in ('(','{'):
   if s[-1:]!=(')' if s[0]=='(' else '}'):raise ValueError('指数括号不匹配')
   s=s[1:-1].strip()
  tokens=re.split(r'[\s,]+',s) if re.search(r'[\s,]',s) else re.findall(r'-?\d',s)
  if ''.join(tokens)!=re.sub(r'[\s,]','',s) or any(not re.fullmatch(r'-?\d+',t) for t in tokens):raise ValueError('指数须为整数；多位数用空格分隔')
  h=[int(t) for t in tokens]
 else:h=value
 if not isinstance(h,(tuple,list)) or len(h)!=count or any(not isinstance(x,int) or isinstance(x,bool) or abs(x)>9999 for x in h):raise ValueError(f'本模型需要{count}个整数，绝对值不超过9999')
 if not any(h):raise ValueError('全零指数没有晶面方向')
 if count==4 and sum(h[:3])!=0:raise ValueError('四轴指数必须满足 h+k+i=0')
 g=math.gcd(*h);return [x//g for x in h]
def independent(h):return [h[0],h[1],h[3]] if len(h)==4 else h

def rational(v,count=3):
 scale=max(abs(x) for x in v);fs=[Fraction(x/scale).limit_denominator(10000) if abs(x)>1e-10 else Fraction(0) for x in v];L=math.lcm(*(f.denominator for f in fs));h=[int(f*L) for f in fs];g=math.gcd(*h);h=[x//g for x in h]
 if count==4:h=[h[0],h[1],-h[0]-h[1],h[2]]
 if any(abs(x)>9999 for x in h):raise ValueError('点群与基底不相容，不能生成稳定的低误差整数轨道')
 return h

def frame(A):
 a,b,c=tr(A);y=unit(c);x=unit(sub(b,[dot(b,y)*v for v in y]));return [x,y,cross(x,y)]
def rotY(deg):
 t=math.radians(deg);c=math.cos(t);s=math.sin(t);return [[c,0,s],[0,1,0],[-s,0,c]]
def diag(a,b,c):return [[a,0,0],[0,b,0],[0,0,c]]
INVERSION=diag(-1,-1,-1);MX=diag(-1,1,1);MY=diag(1,-1,1);RX=diag(1,-1,-1);CYCLIC=[[0,1,0],[0,0,1],[1,0,0]]
GENERATORS={
 '1':[],'-1':[INVERSION],'2':[rotY(180)],'m':[MX],'2/m':[RX,MX],
 '222':[RX,rotY(180)],'mm2':[MX,diag(1,1,-1)],'mmm':[MX,MY,diag(1,1,-1)],
 '4':[rotY(90)],'-4':[mm(INVERSION,rotY(90))],'4/m':[rotY(90),INVERSION],
 '422':[rotY(90),RX],'4mm':[rotY(90),MX],'-42m':[mm(INVERSION,rotY(90)),RX],'4/mmm':[rotY(90),MX,MY],
 '3':[rotY(120)],'-3':[rotY(120),INVERSION],'32':[rotY(120),RX],'3m':[rotY(120),MX],'-3m':[rotY(120),MX,INVERSION],
 '6':[rotY(60)],'-6':[mm(INVERSION,rotY(60))],'6/m':[rotY(60),INVERSION],
 '622':[rotY(60),RX],'6mm':[rotY(60),MX],'-6m2':[rotY(120),MX,MY],'6/mmm':[rotY(60),MX,MY],
 '23':[CYCLIC,RX],'m-3':[CYCLIC,RX,INVERSION],'432':[CYCLIC,rotY(90)],'-43m':[CYCLIC,RX,mm(INVERSION,rotY(90))],'m-3m':[CYCLIC,rotY(90),INVERSION]}
# Monoclinic unique axis b (canonical +X), unlike higher-system principal c (+Y).
GROUP_SYSTEM={'1':'三斜','-1':'三斜',**{k:'单斜' for k in ['2','m','2/m']},**{k:'正交' for k in ['222','mm2','mmm']},**{k:'四方' for k in ['4','-4','4/m','422','4mm','-42m','4/mmm']},**{k:'三方' for k in ['3','-3','32','3m','-3m']},**{k:'六方' for k in ['6','-6','6/m','622','6mm','-6m2','6/mmm']},**{k:'等轴' for k in ['23','m-3','432','-43m','m-3m']}}
GENERATORS['2']=[RX]
def keymat(A):return tuple(round(x,9) for r in A for x in r)
@lru_cache(maxsize=64)
def canonical_ops(pg):
 if pg not in GENERATORS:raise ValueError('不支持的点群：'+str(pg))
 out=[I];seen={keymat(I)}
 for t in out:
  for g in GENERATORS[pg]:
   n=mm(g,t);k=keymat(n)
   if k not in seen:
    if len(out)>=48:raise ValueError('点群闭包异常')
    seen.add(k);out.append(n)
 return out

def operations(pg,A):
 R=frame(A);return [mm(mm(tr(R),g),R) for g in canonical_ops(pg)]
def orbit(h,A,ops,count):
 n=unit(mv(inv(tr(A)),independent(h)));out={}
 for T in ops:
  q=mv(T,n);index=rational(mv(tr(A),q),count);back=unit(mv(inv(tr(A)),independent(index)))
  if norm(sub(back,q))>1e-7:raise ValueError('当前点群方向与晶轴基底不相容；请核对晶轴设置')
  out[tuple(index)]=back
 return out

def validate_basis(A,system,count):
 matrix(A);cols=tr(A);lens=list(map(norm,cols));angles=[math.degrees(math.acos(max(-1,min(1,dot(cols[i],cols[j])/lens[i]/lens[j])))) for i,j in [(1,2),(0,2),(0,1)]]
 eq=lambda x,y:abs(x-y)<1e-6*max(1,abs(x),abs(y))
 if count==4:
  if system not in ('三方','六方') or not eq(lens[0],lens[1]) or not all(eq(x,y) for x,y in zip(angles,[90,90,120])):raise ValueError('四轴要求三方/六方、等长基轴、α=β=90°、γ=120°')
 elif system in ('三方','六方'):raise ValueError('此版本三方/六方统一使用四轴六方设置；菱方原胞三指数需先转换')
 if system in ('正交','四方','等轴') and not all(eq(x,90) for x in angles):raise ValueError('所选晶系要求三轴正交')
 if system in ('四方','等轴') and not eq(lens[0],lens[1]):raise ValueError('所选晶系要求 a=b')
 if system=='等轴' and not eq(lens[0],lens[2]):raise ValueError('等轴晶系要求 a=b=c')
 if system=='单斜' and not (eq(angles[0],90) and eq(angles[2],90)):raise ValueError('本程序单斜采用唯一轴b：α=γ=90°')
 return lens,angles

def mesh(planes):
 if not 4<=len(planes)<=96:raise ValueError('展开后的晶面数须在4至96之间')
 ns=[p['n'] for p in planes];scale=max(p['d'] for p in planes);tol=scale*1e-8
 # Recession cone must be trivial: otherwise finite triple intersections can hide unbounded rays.
 for a,b in itertools.combinations(ns,2):
  d=cross(a,b)
  if norm(d)<1e-10:continue
  d=unit(d)
  for sign in (-1,1):
   if all(sign*dot(n,d)<=1e-10 for n in ns):raise ValueError('面集合不能围成有界晶体；存在开放方向，请补充封闭面')
 vs=[];bins={};candidate_count=0
 for i,j,k in itertools.combinations(range(len(planes)),3):
  a,b,c=[planes[t] for t in (i,j,k)];bc=cross(b['n'],c['n']);D=dot(a['n'],bc)
  if abs(D)<1e-10:continue
  ca=cross(c['n'],a['n']);ab=cross(a['n'],b['n']);v=[(a['d']*bc[t]+b['d']*ca[t]+c['d']*ab[t])/D for t in range(3)];candidate_count+=1
  if any(dot(p['n'],v)>p['d']+tol for p in planes):continue
  q=tuple(round(x/(tol*10)) for x in v)
  if any(norm(sub(v,vs[idx]))<tol*10 for near in itertools.product(*(range(x-1,x+2) for x in q)) for idx in bins.get(near,[])):continue
  bins.setdefault(q,[]).append(len(vs));vs.append(v)
 if len(vs)<4:raise ValueError('未得到三维闭合晶体：面集合退化或互相矛盾')
 faces=[];inactive=[]
 for p in planes:
  ids=[i for i,v in enumerate(vs) if abs(dot(p['n'],v)-p['d'])<tol*5]
  if len(ids)<3:inactive.append(p['id']);continue
  c=[sum(vs[i][j] for i in ids)/len(ids) for j in range(3)];n=p['n'];u=unit(cross(n,[0,1,0] if abs(n[1])<.9 else [1,0,0]));v=cross(n,u)
  ids.sort(key=lambda i:math.atan2(dot(sub(vs[i],c),v),dot(sub(vs[i],c),u)))
  faces.append({**p,'ids':ids,'center':c,'miller':None})
 if inactive:raise ValueError('以下指定面被其他面完全截去，不能冒充可见外表面：'+', '.join(inactive))
 edges={}
 for i,f in enumerate(faces):
  for a,b in zip(f['ids'],f['ids'][1:]+f['ids'][:1]):edges.setdefault(tuple(sorted((a,b))),[]).append(i)
 model={'vertices':vs,'faces':faces,'edges':[{'ids':list(k),'faces':v} for k,v in sorted(edges.items())]}
 return model,{'triple_candidates':candidate_count,'plane_count':len(planes)}

def validate(model,check_symmetry=True):
 V=model.get('vertices',[]);F=model.get('faces',[]);errors=[]
 if len(V)<4 or len(F)<4:return {'ok':False,'errors':['至少需要四个顶点与四个面']}
 if any(len(v)!=3 or not all(finite(x) for x in v) for v in V):return {'ok':False,'errors':['顶点存在非有限数值']}
 tol=max(1,max(norm(v) for v in V))*1e-7;edges={};used=set();volume=0;max_residual=0
 A=model.get('indexing',{}).get('basis');count=model.get('indexing',{}).get('indexCount',3)
 for fi,f in enumerate(F):
  ids=f.get('ids',[]);n=f.get('n',[]);d=f.get('d')
  if len(ids)<3 or len(set(ids))!=len(ids) or any(not isinstance(i,int) or i<0 or i>=len(V) for i in ids):errors.append(f'面{fi}顶点索引错误');continue
  if len(n)!=3 or not all(finite(x) for x in n) or not finite(d) or abs(norm(n)-1)>1e-6:errors.append(f'面{fi}法线或面距无效');continue
  residual=max(abs(dot(V[i],n)-d) for i in ids);max_residual=max(max_residual,residual)
  if residual>tol or max(dot(v,n)-d for v in V)>tol:errors.append(f'面{fi}不满足平面/凸半空间约束')
  used.update(ids)
  for a,b in zip(ids,ids[1:]+ids[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((fi,a,b))
  for a,b in zip(ids[1:-1],ids[2:]):
   area=cross(sub(V[a],V[ids[0]]),sub(V[b],V[ids[0]]))
   if dot(area,n)<-tol:errors.append(f'面{fi}绕序与外法线相反')
   volume+=dot(V[ids[0]],cross(V[a],V[b]))/6
  if A:
   try:
    h=indices(f['modelMiller'],count);q=unit(mv(inv(tr(A)),independent(h)))
    if norm(sub(q,n))>1e-7:errors.append(f'面{fi}指数与外法线不一致')
   except (ValueError,KeyError):errors.append(f'面{fi}指数无效')
 for e,items in edges.items():
  if len(items)!=2 or items[0][1:]==items[-1][1:]:errors.append(f'棱{e}不是两个反向绕序面共用')
 declared={tuple(sorted(e['ids'])):sorted(e['faces']) for e in model.get('edges',[])}
 actual={e:sorted(x[0] for x in items) for e,items in edges.items()}
 if declared!=actual:errors.append('存储邻接棱与面边界不一致')
 if len(used)!=len(V):errors.append('存在未被面引用的顶点')
 if len(V)-len(edges)+len(F)!=2:errors.append('Euler关系不满足V−E+F=2')
 if volume<=tol**3:errors.append('体积非正或模型退化')
 if check_symmetry:
  for T in model.get('indexing',{}).get('operations',[]):
   if any(min(norm(sub(mv(T,v),q)) for q in V)>tol for v in V):errors.append('声明的点群并不保持当前模型；需调整面距或对称型');break
 return {'ok':not errors,'errors':errors,'vertices':len(V),'edges':len(edges),'faces':len(F),'euler':len(V)-len(edges)+len(F),'volume':volume,'max_plane_residual':max_residual}

FEATURES={'三斜':'a、b、c一般不等；三轴斜交，轴角由参考基底给出。','单斜':'a、b、c一般不等；唯一轴b，α=γ=90°，β由参考基底给出。','正交':'a≠b≠c；α=β=γ=90°。','四方':'a=b≠c；α=β=γ=90°。','等轴':'a=b=c；α=β=γ=90°。','三方':'六方四轴设置：a₁=a₂=a₃≠c；α=β=90°，γ=120°。','六方':'a₁=a₂=a₃≠c；α=β=90°，γ=120°。'}
def build(spec):
 if not isinstance(spec,dict) or spec.get('schema_version')!=1:raise ValueError('输入必须是schema_version=1的项目对象')
 name=spec.get('id','')
 if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',name):raise ValueError('id需为1–64位字母、数字、横线或下划线')
 system=spec.get('crystal_system');count=spec.get('index_count',3);A=spec.get('basis');pg=spec.get('point_group')
 if system not in SYSTEMS or count not in (3,4):raise ValueError('晶系或指数数量无效')
 lens,angles=validate_basis(A,system,count)
 if pg not in GENERATORS:raise ValueError('需要明确支持的点群；未知时先完成证据判读，不从晶系猜定')
 if GROUP_SYSTEM[pg]!=system:raise ValueError('点群与晶系不一致')
 ops=operations(pg,A);planes=[];seen=set();face_ids=set();warnings=[]
 if ('faces' in spec)==('forms' in spec):raise ValueError('faces与forms必须且只能提供一种')
 rows=spec.get('faces') or spec.get('forms')
 if not isinstance(rows,list) or not 1<=len(rows)<=96:raise ValueError('需要1–96组面或晶形参数')
 for row in rows:
  if not isinstance(row,dict):raise ValueError('面参数须为对象')
  h=indices(row.get('hkl'),count);d=row.get('distance')
  if not finite(d) or not 1e-5<=d<=10000:raise ValueError('distance为单位法线到原点的正支持距离，范围1e-5至10000')
  orb=orbit(h,A,ops,count);expand=row.get('expand', 'forms' in spec and not spec.get('faces'))
  items=sorted(orb.items()) if expand else [(tuple(h),unit(mv(inv(tr(A)),independent(h))))]
  for ix,n in items:
   if ix in seen:raise ValueError('面方向重复；请合并重复晶形或去掉重叠面')
   seen.add(ix);fid=row.get('id') if not expand else None;fid=fid or f'F{len(planes)+1:02d}'
   if not re.fullmatch(r'F\d{2,3}',str(fid)) or fid in face_ids:raise ValueError('面id须唯一且形如F01')
   face_ids.add(fid);f={'id':fid,'n':n,'d':d,'label':str(row.get('label','参考晶形面')),'modelMiller':list(ix),'formOrbit':[list(x) for x in sorted(orb)],'indexStatus':'参考基底下的模型指数；非照片自动测定','photoEvidence':str(row.get('evidence','面型与距离为模型参数；未提供实测依据'))}
   if 'photo_label' in row:f['photoLabel']=str(row['photo_label'])
   if max(abs(x) for x in ix)>32:warnings.append(f'{fid}含高指数，应核对拟合斜率有理化与轴比假设')
   planes.append(f)
 if len(planes)>96:raise ValueError('晶形展开超过96面；请拆分项目')
 model,stats=mesh(planes);R=frame(A);forms=[];done=set()
 for i,f in enumerate(model['faces']):
  if i in done:continue
  orb={tuple(h) for h in f['formOrbit']};members=[j for j,g in enumerate(model['faces']) if tuple(g['modelMiller']) in orb];done.update(members);forms.append({'representative':list(max(orb)),'faces':members,'faceIds':[model['faces'][j]['id'] for j in members]})
 meta=spec.get('metadata',{});choice=str(meta.get('axis_choice','c沿主轴；其余独立轴及正向由所列基矩阵明确。单斜唯一轴为b。'))
 info={'indexCount':count,'basis':A,'basisInverseTranspose':inv(tr(A)),'lengths':lens,'angles':angles,'symmetry':str(meta.get('symmetry',pg)),'pointGroup':pg,'status':'参考模型参数；实物证据另行核对','axisChoice':choice,'geometricFeatures':FEATURES[system],'basisNote':str(meta.get('basis_note','轴比与面距是参考模型参数，未自动解释为实物标定。')),'axisConvention':'A的列为'+('a₁、a₂、c；a₃=−a₁−a₂。' if count==4 else 'a、b、c。')+'使用右手基底。','standardRotation':R,'standardPlacement':'c直立，第二独立基轴向右；晶轴随模型旋转，箭头长度只表示方向。','projectionNote':'沿用固定缩放的斜投影/自由正交投影，照片采用明确相机模型。','operations':ops,'forms':forms,'formula':'n ∝ A⁻ᵀ(h,k,l)；四轴另补i=−h−k。'}
 if count==4:
  a,b,c=tr(A);info.update(displayAxes=[a,b,[-x-y for x,y in zip(a,b)],c],axisLabels=['a₁','a₂','a₃','c'])
 model.update(indexing=info,crystalSystem=system,mineralName=str(meta.get('mineral_name','')),geometryStatus='参考参数构形；非原子结构',info={'system':system,'title':str(spec.get('title',name)),'desc':str(meta.get('description','由参考基底、晶面方向与支持距离生成凸多面体。')),'notes':[str(x) for x in meta.get('notes',[])]+['原始输入、算法版本与质量校验随输出保存。'],'limits':'照片可辅助定向，不能独立唯一确定晶胞参数、晶面指数或矿物种属。'},claimLevel='reference_model')
 if meta.get('highlight_face_pairs'):
  pairs={frozenset(pair) for pair in meta['highlight_face_pairs']};model['splitRidges']=[ed for ed in model['edges'] if frozenset(model['faces'][i]['id'] for i in ed['faces']) in pairs]
  if len(model['splitRidges'])!=len(pairs):raise ValueError('标记棱对应的两张面不共棱，需核对修复关系')
 quality=validate(model)
 if spec.get('expected_faces') is not None and len(model['faces'])!=spec['expected_faces']:quality['errors'].append('实际面数与用户给定面数不同');quality['ok']=False
 if not quality['ok']:raise ValueError('；'.join(quality['errors']))
 quality['warnings']=list(dict.fromkeys(warnings));quality['claim_level']='reference_model';quality['stats']=stats
 return model,quality
