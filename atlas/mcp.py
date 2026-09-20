"""MCP stdio protocol 2025-06-18; one JSON-RPC message per line, no stdout diagnostics."""
import sys,json,pathlib
from . import __version__
from .service import execute,TOOLS

def run(output,instream=None,outstream=None):
 if instream is None and hasattr(sys.stdin,'reconfigure'):sys.stdin.reconfigure(encoding='utf-8')
 if outstream is None and hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
 inp=instream or sys.stdin;out=outstream or sys.stdout;initialized=False;version='2025-06-18'
 def send(obj):out.write(json.dumps(obj,ensure_ascii=False,allow_nan=False)+'\n');out.flush()
 while True:
  line=inp.readline(24*1024*1024+1)
  if not line:break
  if len(line)>24*1024*1024:
   send({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'消息超过24MiB'}});break
  try:
   req=json.loads(line)
   if not isinstance(req,dict) or req.get('jsonrpc')!='2.0' or not isinstance(req.get('method'),str):raise ValueError()
  except (ValueError,TypeError):send({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'JSON-RPC消息无效'}});continue
  if 'id' not in req:continue
  rid=req['id'];method=req['method'];params=req.get('params',{})
  try:
   if method=='initialize':
    requested=params.get('protocolVersion');version=requested if requested in ('2024-11-05','2025-03-26','2025-06-18') else '2025-06-18';initialized=True;result={'protocolVersion':version,'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'mineral-atlas-workbench','version':__version__},'instructions':'所有指数为参考模型标记。未标定照片不能唯一确定真实晶面指数。工具不访问远程服务。'}
   elif method=='ping':result={}
   elif not initialized:raise ValueError('请先initialize')
   elif method=='tools/list':result={'tools':TOOLS}
   elif method=='tools/call':
    try:
     data=execute(params['name'],params.get('arguments',{}),output);result={'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False,allow_nan=False)}],'isError':False}
     if version=='2025-06-18':result['structuredContent']=data
    except Exception as e:result={'content':[{'type':'text','text':str(e)[:1000]}],'isError':True}
   else:
    send({'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'不支持的方法'}});continue
   send({'jsonrpc':'2.0','id':rid,'result':result})
  except (ValueError,KeyError,TypeError) as e:send({'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':str(e)}})
