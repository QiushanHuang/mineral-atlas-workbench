"""Content-addressed builds with immutable outputs and an offline viewer/report."""
import json,hashlib,pathlib,tempfile,os,shutil,platform,time,html,zipfile,threading
from . import __version__
from .core import build,validate
ROOT=pathlib.Path(__file__).resolve().parents[1]
LOCK=threading.Lock()
def canonical(data):return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def write_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def source_hash():
 files=sorted((ROOT/'atlas').glob('*.py'))+sorted((ROOT/'templates').glob('*'))+[ROOT/'assets/logo.png',ROOT/'LICENSE']
 return sha(b''.join(p.name.encode()+p.read_bytes() for p in files))
LOADED_SOURCE_HASH=source_hash()
def require_current_source():
 if source_hash()!=LOADED_SOURCE_HASH:raise ValueError('程序文件已改变，请重启工作台后再生成，避免混用代码版本')

def cache_valid(path):
 try:
  receipt=json.loads((path/'.integrity.json').read_text(encoding="utf-8"));return bool(receipt) and all((path/k).is_file() and sha((path/k).read_bytes())==v for k,v in receipt.items())
 except (ValueError,OSError,KeyError):return False

def report(model,quality,spec):
 x=model['indexing'];e=lambda s:html.escape(str(s));symbol=lambda h:'('+' '.join(map(str,h))+')'
 rows=[('对称型',x['symmetry']+' / '+x['pointGroup']),('晶系',model['crystalSystem']),('结晶轴的选择',x['axisChoice']+' '+x['axisConvention']),('晶体几何常数特征',x['geometricFeatures']),('晶面符号','；'.join('{'+ ' '.join(map(str,g['representative']))+'} × '+str(len(g['faces'])) for g in x['forms']))]
 body='<h1>'+e(spec.get('title',spec['id']))+'</h1><nav><a href="index.html">交互模型</a> · <a href="input.json">参数</a></nav><p>指数属于明确参考基底下的外形模型。计算自洽不证明实物标定或矿物鉴定。</p><table>'+''.join('<tr><th>'+e(a)+'</th><td>'+e(b)+'</td></tr>' for a,b in rows)+'</table><p>'+e(x['basisNote'])+'</p><h2>逐面映射</h2><table><tr><th>面ID</th><th>指数</th><th>位置/标签</th><th>共棱邻面</th><th>证据</th></tr>'
 for i,f in enumerate(model['faces']):
  ns=sorted(set(j for ed in model['edges'] if i in ed['faces'] for j in ed['faces'] if j!=i));cols=[f['id'],symbol(f['modelMiller']),f['label'],', '.join(model['faces'][j]['id'] for j in ns),f.get('photoEvidence','')];body+='<tr>'+''.join('<td>'+e(c)+'</td>' for c in cols)+'</tr>'
 body+='</table><h2>校验与来源</h2><pre>'+e(json.dumps(quality,ensure_ascii=False,indent=2))+'</pre><pre>'+e(json.dumps(spec.get('evidence',[]),ensure_ascii=False,indent=2))+'</pre>'
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>晶面五项报告</title><style>body{max-width:1200px;margin:28px auto;padding:0 24px;font:14px/1.7 system-ui;color:#243e35;background:#f8faf6}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #c4d0c7;padding:8px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#28654e}@media print{tr{break-inside:avoid}}</style>'+body+'</html>'

def build_project(spec,output,attachment=None):
 """Same canonical inputs + source revision share cached artifacts. Never overwrite a completed build."""
 require_current_source();start=time.perf_counter();output=pathlib.Path(output).resolve();source=source_hash();digest=sha(canonical({'spec':spec,'source':source,'attachment':attachment}))[:20];output.mkdir(parents=True,exist_ok=True)
 with LOCK:
  target=output/digest
  if cache_valid(target):return {'run_id':target.name,'path':str(target),'cached':True,'elapsed_seconds':time.perf_counter()-start,'quality':json.loads((target/'quality.json').read_text(encoding="utf-8"))}
  if target.exists():
   n=2
   while (output/f'{digest}-r{n}').exists():n+=1
   target=output/f'{digest}-r{n}'
  model,quality=build(spec);tmp=pathlib.Path(tempfile.mkdtemp(prefix='.building-',dir=output))
  try:
   photos=[];views=[]
   if attachment:
    from .images import decode_image
    raw,ext=decode_image(attachment['image']);(tmp/('photo'+ext)).write_bytes(raw);photos=[{'number':1,'path':'photo'+ext}]
    if attachment.get('view'):
     view=attachment['view'];views=[dict(view,photo=1)]
   data={'models':{spec['id']:model},'views':{spec['id']:views},'photos':{spec['id']:photos}}
   write_json(tmp/'input.json',spec);write_json(tmp/'model.json',model);write_json(tmp/'quality.json',quality)
   if attachment and attachment.get('view'):
    write_json(tmp/'view.json',attachment['view'])
    if attachment.get('annotation'):write_json(tmp/'annotation.json',attachment['annotation'])
    if attachment.get('fit_quality'):write_json(tmp/'fit-quality.json',attachment['fit_quality'])
   shutil.copyfile(ROOT/'assets/logo.png',tmp/'logo.png')
   shutil.copyfile(ROOT/'LICENSE',tmp/'LICENSE')
   for src,dst in [('viewer.html','index.html'),('viewer.js','viewer.js'),('style.css','style.css')]:shutil.copyfile(ROOT/'templates'/src,tmp/dst)
   (tmp/'data.js').write_text('const DATA = '+json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')+';\n',encoding='utf-8')
   (tmp/'report.html').write_text(report(model,quality,spec),encoding='utf-8')
   files={p.name:sha(p.read_bytes()) for p in sorted(tmp.iterdir()) if p.is_file()};receipt={'schema_version':1,'engine_version':__version__,'source_sha256':source,'input_sha256':sha(canonical(spec)),'artifact_key':digest,'claim_level':'reference_model','python':platform.python_version(),'platform':platform.system(),'files':files,'deterministic_geometry':True,'notes':['环境版本记录用于追溯；照片判读和物理指数仍需外部证据。']}
   write_json(tmp/'receipt.json',receipt)
   with zipfile.ZipFile(tmp/'result.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(tmp.iterdir()):
     if p.is_file() and p.name!='result.zip':
      entry=zipfile.ZipInfo(p.name,date_time=(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,p.read_bytes())
   write_json(tmp/'.integrity.json',{p.name:sha(p.read_bytes()) for p in sorted(tmp.iterdir()) if p.is_file()})
   os.rename(tmp,target)
  except Exception:
   shutil.rmtree(tmp);raise
 return {'run_id':target.name,'path':str(target),'cached':False,'elapsed_seconds':time.perf_counter()-start,'quality':quality}
