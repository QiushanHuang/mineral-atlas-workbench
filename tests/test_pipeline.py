import unittest,pathlib,tempfile,json,sys,io,copy,threading,urllib.request,urllib.error
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.project import build_project,ROOT
from atlas.server import make_server
from atlas.mcp import run
CUBE=json.loads((ROOT/'examples/cube.json').read_text(encoding="utf-8"))
class Pipeline(unittest.TestCase):
 def test_cache_integrity_and_portability(self):
  with tempfile.TemporaryDirectory(prefix='atlas portable space ') as d:
   r=build_project(CUBE,d);p=pathlib.Path(r['path']);self.assertFalse(r['cached']);self.assertTrue((p/'result.zip').exists());self.assertTrue(build_project(CUBE,d)['cached'])
   original=(p/'model.json').read_bytes();(p/'model.json').write_text('{}', encoding="utf-8");next=build_project(CUBE,d);self.assertNotEqual(next['path'],r['path']);self.assertEqual((pathlib.Path(next['path'])/'model.json').read_bytes(),original)
 def test_mcp_roundtrip(self):
  reqs=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'atlas_build','arguments':{'spec':CUBE}}},{'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'atlas_build','arguments':{'spec':{}}}}]
  with tempfile.TemporaryDirectory() as d:
   out=io.StringIO();run(d,io.StringIO('\n'.join(json.dumps(r) for r in reqs)),out);res=[json.loads(x) for x in out.getvalue().splitlines()];self.assertEqual(len(res),4);self.assertEqual(len(res[1]['result']['tools']),7);self.assertFalse(res[2]['result']['isError']);self.assertTrue(res[3]['result']['isError'])
 def test_http_tokens_paths_and_build(self):
  with tempfile.TemporaryDirectory() as d:
   server=make_server(d);t=threading.Thread(target=server.serve_forever,daemon=True);t.start();base=f'http://127.0.0.1:{server.server_port}'
   try:
    config=json.load(urllib.request.urlopen(base+'/api/config'));data=json.dumps({'spec':CUBE}).encode()
    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(base+'/api/build',data=data))
    req=urllib.request.Request(base+'/api/build',data=data,headers={'Content-Type':'application/json','X-Atlas-Token':config['token'],'Origin':base});r=json.load(urllib.request.urlopen(req));self.assertTrue(r['quality']['ok'])
    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/runs/%2e%2e/atlas_cli.py')
    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(base+'/api/build',data=data,headers={'X-Atlas-Token':config['token'],'Origin':'https://example.com'}))
   finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
