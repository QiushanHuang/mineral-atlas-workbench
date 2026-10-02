"""Optional local image adapters. Outputs are suggestions, never confirmed crystal indices."""
import base64,io,json,hashlib,shutil,subprocess,tempfile,pathlib,urllib.request,importlib.util,importlib.metadata
MAX_IMAGE=16*1024*1024

def _image_payload(value):
 if not isinstance(value,str):raise ValueError('图像须为PNG/JPEG data URL或base64字符串')
 if value.startswith('data:'):
  head,value=value.split(',',1)
  if head not in ('data:image/png;base64','data:image/jpeg;base64'):raise ValueError('仅支持PNG/JPEG')
 if len(value)>MAX_IMAGE*1.4:raise ValueError('单张图像超过16MiB')
 try:raw=base64.b64decode(value,validate=True)
 except Exception as e:raise ValueError('图像base64无效') from e
 if len(raw)>MAX_IMAGE:raise ValueError('图像超过16MiB')
 return raw

def decode_photo_input(value):
 raw=_image_payload(value)
 ext='.png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if raw.startswith(b'\xff\xd8\xff') else '.bin'
 return raw,ext,('图像文件头损坏或不是PNG/JPEG；保留原始字节但不参与识别' if ext=='.bin' else None)

def decode_image(value):
 raw,ext,error=decode_photo_input(value)
 if error:raise ValueError('图像文件头不是PNG/JPEG')
 return raw,ext

def doctor():
 packages={}
 for name in ['numpy','scipy','PIL','cv2']:
  found=importlib.util.find_spec(name) is not None
  try:version=importlib.metadata.version({'PIL':'Pillow','cv2':'opencv-python-headless'}.get(name,name)) if found else None
  except importlib.metadata.PackageNotFoundError:version='unknown'
  packages[name]={'available':found,'version':version}
 return {'core':'ready (Python standard library)','fit':all(packages[n]['available'] for n in ('numpy','scipy')),'photo_candidates':all(packages[n]['available'] for n in ('numpy','scipy','PIL','cv2')),'packages':packages,'tesseract':shutil.which('tesseract'),'local_vision':'optional: user-installed Ollama at 127.0.0.1:11434; not contacted automatically','network_policy':'No remote services. Optional vision uses loopback only.'}

def inspect_image(value):
 raw,ext=decode_image(value);result={'format':ext[1:],'bytes':len(raw),'claim_level':'image_metadata_only'}
 try:
  from PIL import Image
  im=Image.open(io.BytesIO(raw));result.update(size=list(im.size),exif_orientation=im.getexif().get(274,1));im.verify()
 except ImportError:result['note']='Pillow未安装，未读取尺寸/EXIF；浏览器可直接显示并标注'
 except Exception as e:raise ValueError('图像解码失败') from e
 return result

def ocr(value,language='eng'):
 binary=shutil.which('tesseract')
 if not binary:raise ValueError('未安装Tesseract；可继续手工标注。不会自动下载程序或语言包。')
 if language not in ('eng','chi_sim','eng+chi_sim'):raise ValueError('OCR语言仅支持eng、chi_sim、eng+chi_sim')
 raw,ext=decode_image(value)
 with tempfile.TemporaryDirectory(prefix='mineral-ocr-') as tmp:
  p=pathlib.Path(tmp)/('image'+ext);p.write_bytes(raw)
  r=subprocess.run([binary,str(p),'stdout','-l',language,'tsv'],capture_output=True,text=True,timeout=45)
 if r.returncode:raise ValueError('Tesseract识别失败；请核对本机语言包。'+r.stderr[-300:])
 import csv
 boxes=[]
 for row in csv.DictReader(io.StringIO(r.stdout),delimiter='\t'):
  if row.get('text','').strip():boxes.append({'text':row['text'],'confidence':float(row['conf']),'box':[int(row[k]) for k in ['left','top','width','height']]})
 return {'candidates':boxes,'claim_level':'unverified_transcription','warnings':['负号、上划线、小字号与红色手写编号必须人工核对；OCR数字不是米勒指数。']}

VISION_PROMPT=pathlib.Path(__file__).with_name('visual-analysis-prompt.txt').read_text(encoding='utf-8')
VISUAL_POLICY_SHA256=hashlib.sha256(VISION_PROMPT.encode('utf-8')).hexdigest()
def vision(value,model_name):
 raw,_=decode_image(value)
 if not isinstance(model_name,str) or not 1<=len(model_name)<=120:raise ValueError('请指定本机已安装的视觉模型名称')
 body=json.dumps({'model':model_name,'messages':[{'role':'user','content':VISION_PROMPT,'images':[base64.b64encode(raw).decode()]}],'stream':False,'format':'json','options':{'temperature':0,'seed':439}}).encode()
 req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=body,headers={'Content-Type':'application/json'})
 try:
  # Ignore shell proxy settings for local-only image processing. No redirects to external hosts.
  class NoRedirect(urllib.request.HTTPRedirectHandler):
   def redirect_request(self,*args,**kwargs):return None
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
  with opener.open(req,timeout=120) as response:result=json.loads(response.read(4*1024*1024))
 except Exception as e:raise ValueError('无法调用本机Ollama视觉模型；请确认服务和模型已由你安装。图像未发送到远程服务。') from e
 return {'model':model_name,'policy_sha256':VISUAL_POLICY_SHA256,'suggestion':result.get('message',{}).get('content',''),'claim_level':'unverified_visual_suggestion','warnings':['模型输出需人工复核；不会自动写入晶系、点群、轴比或晶面指数。'],'reproducibility':'seed=439, temperature=0；不同模型/硬件仍可能产生不同文字结果。'}


def from_photos(images,boxes=None,constraints=None,bank=None,evidence=None):
 """Optional local photo-to-template proposals; lazy imports keep core dependency-free."""
 from .photo_candidates import from_photos as generate
 return generate(images,boxes=boxes,constraints=constraints,bank=bank,evidence=evidence)
