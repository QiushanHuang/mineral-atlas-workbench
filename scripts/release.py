"""Produce portable software/plugin and standalone-skill ZIPs from an explicit allowlist."""
import pathlib,shutil,sys,tempfile,zipfile,json,hashlib,os,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));from install_skill import payload
DIRS=['atlas','templates','ui','examples','schema','tests','scripts','skills','docs','assets','.github','.codex-plugin']
FILES=['atlas_cli.py','mcp_launcher.py','plugin.json','mcp.json','.mcp.json','README.md','requirements-fit.lock','start.sh','启动工作台.command','启动工作台.bat','查看预置图谱.html','README.zh-CN.md','LICENSE','AUTHORS.md','CONTRIBUTING.md','SECURITY.md','CITATION.cff','CHANGELOG.md','.gitignore','.gitattributes']
def copy_release(dest):
 dest.mkdir(parents=True,exist_ok=True)
 for name in DIRS:shutil.copytree(ROOT/name,dest/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','WORK.md'))
 for name in FILES:shutil.copy2(ROOT/name,dest/name)
 (dest/'verification').mkdir(exist_ok=True)
 evidence=ROOT/'verification' if (ROOT/'verification').exists() else ROOT/'evaluation'
 for name in ['benchmark.json','fit-benchmark.json','skill-scenarios.json']:shutil.copy2(evidence/name,dest/'verification'/name)
 manifests={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='SHA256.json'}
 (dest/'SHA256.json').write_text(json.dumps(manifests,indent=2), encoding="utf-8")
 return dest

def zip_tree(root,path):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(root.rglob('*')):
   if not p.is_file():continue
   entry=zipfile.ZipInfo(str(pathlib.Path(root.name)/p.relative_to(root)),(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.create_system=3;entry.external_attr=(p.stat().st_mode&0o777)<<16;z.writestr(entry,p.read_bytes())
 with zipfile.ZipFile(path) as z:
  if z.testzip():raise ValueError('ZIP校验失败')
 return {'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,default=ROOT.parent/'dist');p.add_argument('--copy-plugin',type=pathlib.Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='atlas-release-') as d:
  stage=copy_release(pathlib.Path(d)/'mineral-atlas-workbench');standalone=pathlib.Path(d)/'mineral-face-atlas';payload(standalone)
  # The installed skill must be independent of the developer's machine and private source-photo storage.
  for tree in [stage,standalone]:
   for f in tree.rglob('*'):
    if f.is_file() and f.suffix in ('.py','.js','.json','.md','.html','.yaml','.toml'):
     data=f.read_bytes()
     for pattern in [(str(pathlib.Path.home())+'/').encode(),b'com.tencent.'+b'xinWeChat',b'evaluation/'+b'ui-runs']:
      if pattern in data:raise ValueError('分享包出现私人路径：'+str(f.relative_to(tree)))
  receipts=[zip_tree(stage,a.out/'mineral-atlas-workbench-1.0.0.zip'),zip_tree(standalone,a.out/'mineral-face-atlas-skill-2.0.0.zip')]
  if a.copy_plugin:copy_release(a.copy_plugin.expanduser().resolve())
 (a.out/'release-checksums.json').write_text(json.dumps(receipts,indent=2), encoding="utf-8");print(json.dumps(receipts,indent=2))
