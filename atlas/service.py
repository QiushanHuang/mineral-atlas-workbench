"""Shared service for CLI, local HTTP UI, and MCP. No account or remote dependencies."""
import pathlib,json,base64
from .core import build,validate
from .project import build_project,write_json,require_current_source
from .images import doctor,inspect_image,ocr,vision
from .fit import fit_view

def execute(name,args,output):
 if not isinstance(args,dict):raise ValueError('工具参数必须是对象')
 if name in ('atlas_build','atlas_validate','atlas_fit'):require_current_source()
 if name=='atlas_doctor':return doctor()
 if name=='atlas_build':return build_project(args['spec'],output)
 if name=='atlas_validate':return validate(args['model'])
 if name=='atlas_inspect_image':return inspect_image(args['image'])
 if name=='atlas_ocr':return ocr(args['image'],args.get('language','eng'))
 if name=='atlas_vision':return vision(args['image'],args['model_name'])
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
 {'name':'atlas_build','description':'离线按参考基底、点群和面距构形，校验并导出交互HTML和五项报告；不自动识别真实指数。','inputSchema':{'type':'object','properties':{'spec':{'type':'object'}},'required':['spec']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}},
 {'name':'atlas_validate','description':'检查模型凸性、平面、面指数、闭合共棱、Euler与声明点群。','inputSchema':{'type':'object','properties':{'model':{'type':'object'}},'required':['model']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_fit','description':'可选NumPy/SciPy确定性相机配准。需原始像素角点及face_id；返回歧义和留出误差，不自动镜像照片。','inputSchema':{'type':'object','properties':{'spec':{'type':'object'},'annotation':{'type':'object'},'image':{'type':'string','description':'可选PNG/JPEG data URL，用于创建原图叠加HTML'}},'required':['spec','annotation']},'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':False}},
 {'name':'atlas_doctor','description':'检查Python核心、NumPy、SciPy、Pillow、Tesseract；不自动联网或下载。','inputSchema':{'type':'object','properties':{}},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_inspect_image','description':'读取本地图像的文件头、尺寸和EXIF方向（Pillow可选）。','inputSchema':{'type':'object','properties':{'image':{'type':'string'}},'required':['image']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_ocr','description':'可选本机Tesseract文字框与置信度，结果须核对，不作为晶面指数。','inputSchema':{'type':'object','properties':{'image':{'type':'string'},'language':{'type':'string','enum':['eng','chi_sim','eng+chi_sim']}},'required':['image']},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
 {'name':'atlas_vision','description':'用户选择后仅调用127.0.0.1上的已有Ollama视觉模型；输出未确认观察建议，不能自动标定指数。','inputSchema':{'type':'object','properties':{'image':{'type':'string'},'model_name':{'type':'string'}},'required':['image','model_name']},'annotations':{'readOnlyHint':True,'openWorldHint':False}}
]
