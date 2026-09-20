"""Check published archives in a fresh Unicode/spaced path, with no optional packages required."""
import pathlib,sys,json,zipfile,tempfile,hashlib,subprocess
folder=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'dist').resolve();receipts=json.loads((folder/'release-checksums.json').read_text(encoding='utf-8'))
for r in receipts:
 p=folder/r['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],p.name
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
with tempfile.TemporaryDirectory(prefix='mineral atlas 迁移 ') as td:
 temp=pathlib.Path(td)
 for r in receipts:
  with zipfile.ZipFile(folder/r['file']) as z:
   for name in z.namelist():assert (temp/name).resolve().is_relative_to(temp.resolve()),name
   z.extractall(temp)
 root=temp/'mineral-atlas-workbench';skill=temp/'mineral-face-atlas'
 def call(args):return json.loads(subprocess.check_output([sys.executable,*map(str,args)],cwd=temp,text=True,encoding='utf-8'))
 first=call([root/'atlas_cli.py','build',root/'examples/439.json','--out',temp/'results']);repeat=call([root/'atlas_cli.py','build',root/'examples/439.json','--out',temp/'results']);assert repeat['cached'] and first['quality']['faces']==16
 other=call([skill/'scripts/atlas.py','build',root/'examples/439.json','--out',temp/'skill-results']);assert (pathlib.Path(first['path'])/'model.json').read_bytes()==(pathlib.Path(other['path'])/'model.json').read_bytes()
 for relative,digest in json.loads((root/'SHA256.json').read_text(encoding='utf-8')).items():assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==digest,relative
 for relative in ['assets/logo.png','README.md','README.zh-CN.md','LICENSE','AUTHORS.md','CONTRIBUTING.md','CITATION.cff','docs/RELEASING.md']:assert (root/relative).is_file(),relative
 assert (pathlib.Path(first['path'])/'logo.png').is_file();assert (pathlib.Path(first['path'])/'LICENSE').is_file()
 # Rebuild from the released tree: no development-only evaluation directory is allowed as a dependency.
 subprocess.run([sys.executable,str(root/'scripts/release.py'),'--out',str(temp/'rebuilt')],cwd=temp,check=True,stdout=subprocess.DEVNULL)
 requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},{'jsonrpc':'2.0','id':2,'method':'tools/list'}]
 result=subprocess.run([sys.executable,str(root/'mcp_launcher.py')],cwd=root,input='\n'.join(json.dumps(x) for x in requests)+'\n',text=True,encoding='utf-8',capture_output=True,check=True);messages=[json.loads(line) for line in result.stdout.splitlines()];assert len(messages[1]['result']['tools'])==7
print('PASS: archive checksums, Unicode/spaced relocation, software/skill parity, clean-package rebuild, logo/license assets, and real stdio MCP startup')
