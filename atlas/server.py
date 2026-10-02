"""Loopback-only UI server; token/origin checks prevent cross-site local write requests."""
import http.server,json,pathlib,secrets,urllib.parse,webbrowser,threading,sys
from .project import ROOT
from .service import execute
from .photo_policy import MAX_REQUEST_BYTES,MAX_PHOTOS,MAX_TOTAL_IMAGE_BYTES
MAX_REQUEST=MAX_REQUEST_BYTES

def make_server(output,port=0):
 output=pathlib.Path(output).resolve();output.mkdir(parents=True,exist_ok=True);token=secrets.token_urlsafe(32)
 class Handler(http.server.BaseHTTPRequestHandler):
  def log_message(self,fmt,*args):pass
  def reply(self,code,data,mime='application/json; charset=utf-8'):
   if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
   self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(data)
  def local_host(self):
   return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
  def do_GET(self):
   if not self.local_host():return self.reply(403,{'error':'只接受本机127.0.0.1访问'})
   path=urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
   if path=='/api/config':return self.reply(200,{'token':token,'doctor':execute('atlas_doctor',{},output),'photo_policy':{'max_photos':MAX_PHOTOS,'max_total_bytes':MAX_TOTAL_IMAGE_BYTES}})
   if path=='/api/demo':
    import base64
    return self.reply(200,{'spec':json.loads((ROOT/'examples/cube.json').read_text(encoding="utf-8")),'annotation':json.loads((ROOT/'examples/synthetic-annotation.json').read_text(encoding="utf-8")),'image':'data:image/png;base64,'+base64.b64encode((ROOT/'examples/synthetic.png').read_bytes()).decode()})
   if path=='/api/real-demo':
    import base64,hashlib
    folder=ROOT/'examples/451-photo-study';raw=(folder/'photos/01.jpg').read_bytes();old=json.loads((folder/'annotations/01.json').read_text(encoding='utf-8'))
    evidence='公开451教学实物示例的既有人工参考边界；不是本轮自动识别结果，也不是独立测量真值。'
    features=[{'id':'A1','kind':'silhouette','points':old['silhouette'],'evidence':evidence}]
    for i,(a,b) in enumerate(zip(old['points'],old['points'][1:]+old['points'][:1]),2):features.append({'id':'A'+str(i),'kind':'edge','points':[a,b],'evidence':evidence})
    return self.reply(200,{'spec':json.loads((folder/'project.json').read_text(encoding='utf-8')),'image':'data:image/jpeg;base64,'+base64.b64encode(raw).decode(),'annotation':{'schema_version':1,'image_size':old['image_size'],'source_sha256':hashlib.sha256(raw).hexdigest(),'features':features},'notice':evidence})
   if path=='/api/examples':
    specs=json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding="utf-8"));specs.insert(0,json.loads((ROOT/'examples/cube.json').read_text(encoding="utf-8")));return self.reply(200,specs)
   if path.startswith('/runs/'):
    target=(output/path[len('/runs/'):]).resolve();base=output
   else:
    target=(ROOT/'ui'/('index.html' if path=='/' else path.lstrip('/'))).resolve();base=(ROOT/'ui').resolve()
   if not target.is_relative_to(base) or not target.is_file():return self.reply(404,{'error':'未找到文件'})
   import mimetypes
   mime=mimetypes.guess_type(str(target))[0] or 'application/octet-stream';self.reply(200,target.read_bytes(),mime)
  def do_POST(self):
   if not self.local_host():return self.reply(403,{'error':'Host不匹配'})
   origin=self.headers.get('Origin');expected=f'http://127.0.0.1:{self.server.server_port}'
   if (origin and origin!=expected) or self.headers.get('X-Atlas-Token')!=token:return self.reply(403,{'error':'请求不是当前工作台会话'})
   try:size=int(self.headers.get('Content-Length','0'))
   except ValueError:return self.reply(400,{'error':'Content-Length无效'})
   if not 0<size<=MAX_REQUEST:return self.reply(413,{'error':'请求过大或为空'})
   name={'/api/from-photos':'atlas_from_photos','/api/build':'atlas_build','/api/fit':'atlas_fit','/api/inspect':'atlas_inspect_image','/api/ocr':'atlas_ocr','/api/vision':'atlas_vision','/api/editor':'atlas_editor','/api/editor-export':'atlas_editor_export','/api/review-export':'atlas_review_export','/api/review-check':'atlas_review_check','/api/photo-annotations':'atlas_photo_annotations'}.get(self.path)
   if self.path=='/api/save-document':name='atlas_save_document'
   if self.path=='/api/photo-guides':name='atlas_photo_guides'
   if self.path=='/api/photo-face':name='atlas_photo_face'
   if self.path=='/api/photo-align':name='atlas_photo_align'
   if not name:return self.reply(404,{'error':'未知接口'})
   try:
    args=json.loads(self.rfile.read(size));result=execute(name,args,output);self.reply(200,result)
   except (ValueError,KeyError,TypeError,IndexError,OverflowError) as e:self.reply(400,{'error':str(e),'code':getattr(e,'code','invalid_input'),'details':getattr(e,'details',None)})
   except Exception as e:self.reply(500,{'error':f'本机处理失败：{type(e).__name__}: {str(e)[:300]}'})
 server=http.server.ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True
 return server

def serve(output,port=0,open_browser=False):
 server=make_server(output,port);url=f'http://127.0.0.1:{server.server_port}/';print(url,flush=True)
 if open_browser:webbrowser.open(url)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
