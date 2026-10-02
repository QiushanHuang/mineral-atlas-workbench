"""Shared service for CLI, local HTTP UI, and MCP. No account or remote dependencies."""
import pathlib,json,base64
from .core import build,validate
from .project import build_project,write_json,require_current_source
from .images import doctor,inspect_image,ocr,vision,from_photos
from .fit import fit_view
from .photo_policy import MAX_PHOTOS

def execute(name,args,output):
 if not isinstance(args,dict):raise ValueError('工具参数必须是对象')
 if name=='atlas_photo_guides':
  require_current_source()
  from .photo_guides import photo_guides
  return photo_guides(args['image'])
 if name=='atlas_photo_face':
  require_current_source()
  from .photo_faces import propose_face
  return propose_face(args['image'],args.get('annotation'),args.get('seed'),args.get('tolerance',24))
 if name=='atlas_photo_align':
  require_current_source()
  from .photo_alignment import align_photo
  from .editor import fingerprint
  if args.get('expected_fingerprint') and args['expected_fingerprint']!=fingerprint(args['draft']):raise ValueError('模型已改变，请重新对齐当前版本')
  r=align_photo(args['draft'],args['image'],args.get('annotation'))
  saved=execute('atlas_save_document',{'kind':'alignment','document':r},output)
  return {**r,'record_path':saved['path'],'record_url':saved['url']}
 if name=='atlas_save_document':
  from .project import canonical,sha,LOCK
  kind=args.get('kind')
  if kind not in ('draft','annotations','review','prompt','alignment'):raise ValueError('不支持的本地文档类型')
  document=args.get('document')
  if kind=='prompt':
   if not isinstance(document,str):raise ValueError('提示词必须是文本')
   data=document.encode('utf-8');extension='.txt'
  else:
   if not isinstance(document,dict):raise ValueError('项目和纠错文档必须是JSON对象')
   data=canonical(document);extension='.json'
  if len(data)>4*1024*1024:raise ValueError('本地文档超过4MiB')
  root=pathlib.Path(output).resolve();root.mkdir(parents=True,exist_ok=True);stem=kind+'-'+sha(data)[:20]
  with LOCK:
   target=root/(stem+extension);suffix=2
   while target.exists():
    if not target.is_symlink() and target.read_bytes()==data:break
    target=root/(stem+'-r'+str(suffix)+extension);suffix+=1
   else:target.write_bytes(data)
  return {'path':str(target),'url':'/runs/'+target.name,'sha256':sha(data),'bytes':len(data)}
 if name in ('atlas_editor','atlas_editor_export','atlas_review_export','atlas_review_check','atlas_photo_annotations'):
  require_current_source()
  from .editor import execute_editor
  if name=='atlas_editor':return execute_editor(args)
  if name=='atlas_editor_export':
   from .editor_export import export_editor
   return export_editor(args['draft'],output)
  if name=='atlas_review_export':
   from .review import make_review_packet
   r=execute_editor({'action':'analyze','draft':args['draft']})
   return make_review_packet(r['draft'],r['model'],r['analysis'],args.get('annotations'))
  if name=='atlas_review_check':
   from .review import review_response
   return review_response(args['packet'],args['response'],args['current_fingerprint'],args.get('selected_ids'))
  from .photo_annotations import validate_annotation
  from .images import decode_image
  return {'annotation':validate_annotation(args['annotation'],decode_image(args['image'])[0])}
 if name in ('atlas_build','atlas_validate','atlas_fit','atlas_from_photos'):require_current_source()
 if name=='atlas_doctor':return doctor()
 if name=='atlas_build':return build_project(args['spec'],output)
 if name=='atlas_validate':
  model=args['model'];is_geometry=model.get('claimLevel')=='reference_geometry'
  result=validate(model,check_symmetry=not is_geometry)
  if is_geometry:result['claim_level']='reference_geometry'
  return result
 if name=='atlas_inspect_image':return inspect_image(args['image'])
 if name=='atlas_ocr':return ocr(args['image'],args.get('language','eng'))
 if name=='atlas_vision':return vision(args['image'],args['model_name'])
 if name=='atlas_from_photos':
  result=from_photos(args['images'],boxes=args.get('boxes'),constraints=args.get('constraints'),evidence=args.get('evidence'))
  for candidate in result['candidates']:
   items=[{'image':image,'view':view,'annotation':{'mode':observation['mode'],'source_sha256':observation['source_sha256'],'box':result['inputs']['boxes'][number],'constraints':result['inputs']['constraints'],'user_evidence':result['inputs']['evidence'],'coverage':observation.get('coverage'),'quality_weight':observation['quality_weight'],'status':observation['status'],'warnings':observation['warnings'],'fusion':result['fusion'],'analysis':result['analysis'],'reproducibility':result['reproducibility']},'fit_quality':metrics} for number,(image,view,observation,metrics) in enumerate(zip(args['images'],candidate['views'],result['observations'],candidate['per_photo']))]
   candidate['artifact']=build_project(candidate['spec'],output,{'items':items})
  from .project import sha,canonical,source_hash
  result['source_sha256']=source_hash()
  record=pathlib.Path(output)/('photo-candidates-'+sha(canonical({'images':[o['source_sha256'] for o in result['observations']],'ranking':result['ranking'],'engine':result['engine'],'source':result['source_sha256'],'boxes':args.get('boxes'),'constraints':args.get('constraints'),'evidence':args.get('evidence'),'reproducibility':result['reproducibility']}))[:20]+'.json')
  if not record.exists():write_json(record,result)
  result['record_path']=str(record.resolve())
  return result
 if name=='atlas_fit':
  model,quality=build(args['spec']);result=fit_view(model,args['annotation'])
  if args.get('image'):
   result['artifact']=build_project(args['spec'],output,{'image':args['image'],'view':result['view'],'annotation':args['annotation'],'fit_quality':result['quality']})
   # Save the complete fit/annotation record separately; it is not mislabeled independent validation.
   # These records use their own content hash and never replace the build's quality.json.
   from .project import sha,canonical
   p=pathlib.Path(output)/('fit-'+sha(canonical({'spec':args['spec'],'annotation':args['annotation']}))[:20]+'.json')
   if not p.exists():write_json(p,result)
   result['record_path']=str(p.resolve())
  return result
 raise ValueError('未知工具：'+name)

TOOLS=[
 {'name':'atlas_photo_align','description':'将当前可编辑v2参考模型与原图棱线/面区域标注对齐，返回线框、待确认面对应及拟合内误差；不改三维外形。','inputSchema':{'type':'object','properties':{'draft':{'type':'object'},'image':{'type':'string'},'annotation':{'type':'object'},'expected_fingerprint':{'type':'string'}},'required':['draft','image']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}},
 {'name':'atlas_editor','description':'本地创建预设、导入旧模型、面推拉/截切、手动参考轴与几何参数解析；所有修改返回新草稿，未知指数保留候选。','inputSchema':{'type':'object','properties':{'action':{'enum':['create','import','apply','analyze']},'preset':{'type':'string'},'draft':{'type':'object'},'spec':{'type':'object'},'command':{'type':'object'},'expected_fingerprint':{'type':'string'}},'required':['action']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_editor_export','description':'把几何编辑草稿另存为可离线浏览的模型/参数/修订包，不覆盖已有输出。','inputSchema':{'type':'object','properties':{'draft':{'type':'object'}},'required':['draft']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}},
 {'name':'atlas_review_export','description':'为当前草稿与手工标注生成本地复核包和共享提示词；不含原图，不联网。','inputSchema':{'type':'object','properties':{'draft':{'type':'object'},'annotations':{'type':'array'}},'required':['draft']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_review_check','description':'核对复核回复的模型/策略指纹、面ID和命令，只返回待采纳建议，不自动执行。','inputSchema':{'type':'object','properties':{'packet':{'type':'object'},'response':{'type':'object'},'current_fingerprint':{'type':'string'},'selected_ids':{'type':'array','items':{'type':'string'}}},'required':['packet','response','current_fingerprint']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_photo_annotations','description':'核验手绘棱线/轮廓/面区/遮挡与原图指纹和显示像素尺寸，返回可用于候选评分的标注。','inputSchema':{'type':'object','properties':{'annotation':{'type':'object'},'image':{'type':'string'}},'required':['annotation','image']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_from_photos','description':'从1–24张同一物体的照片自动提取轮廓，并生成最多3个初始3D形态候选。无需先选模型或标角点；结果来自显式模板先验，需确认，不自动判定真实晶系、面号或指数。','inputSchema':{'type':'object','properties':{'images':{'type':'array','items':{'type':'string'},'minItems':1,'maxItems':MAX_PHOTOS},'boxes':{'type':'array','description':'可选，每张照片的原像素[x,y,width,height]框，未知用null'},'constraints':{'type':'object','description':'仅填写已确认的晶系和总面数','properties':{'crystal_system':{'type':'string'},'expected_faces':{'type':'integer'}}},'evidence':{'type':'object','properties':{'morphology':{'type':'string','description':'外形或教材晶形；可写多个可能答案与缺失信息'},'strength':{'type':'string','enum':['tentative','likely']},'annotations':{'type':'array','description':'逐图手工棱、轮廓、面区域与遮挡，使用photo-annotation.schema.json，未知用null'},'coverage':{'type':'array','items':{'type':'string','enum':['unknown','complete','partial']}}}}},'required':['images']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}},
 {'name':'atlas_build','description':'离线按参考基底、点群和面距构形，校验并导出交互HTML和五项报告；不自动识别真实指数。','inputSchema':{'type':'object','properties':{'spec':{'type':'object'}},'required':['spec']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}},
 {'name':'atlas_validate','description':'检查模型凸性、平面、面指数、闭合共棱、Euler与声明点群。','inputSchema':{'type':'object','properties':{'model':{'type':'object'}},'required':['model']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_fit','description':'可选NumPy/SciPy确定性相机配准。需原始像素角点及face_id；返回歧义和留出误差，不自动镜像照片。','inputSchema':{'type':'object','properties':{'spec':{'type':'object'},'annotation':{'type':'object'},'image':{'type':'string','description':'可选PNG/JPEG data URL，用于创建原图叠加HTML'}},'required':['spec','annotation']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':False}},
 {'name':'atlas_doctor','description':'检查Python核心、NumPy、SciPy、Pillow、Tesseract；不自动联网或下载。','inputSchema':{'type':'object','properties':{}},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_inspect_image','description':'读取本地图像的文件头、尺寸和EXIF方向（Pillow可选）。','inputSchema':{'type':'object','properties':{'image':{'type':'string'}},'required':['image']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_ocr','description':'可选本机Tesseract文字框与置信度，结果须核对，不作为晶面指数。','inputSchema':{'type':'object','properties':{'image':{'type':'string'},'language':{'type':'string','enum':['eng','chi_sim','eng+chi_sim']}},'required':['image']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_vision','description':'用户选择后仅调用127.0.0.1上的已有Ollama视觉模型；输出未确认观察建议，不能自动标定指数。','inputSchema':{'type':'object','properties':{'image':{'type':'string'},'model_name':{'type':'string'}},'required':['image','model_name']},'annotations':{'readOnlyHint':True,'openWorldHint':False}}
]
