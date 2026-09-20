"""Install or update this explicitly requested skill, preserving the previous version outside discovery."""
import pathlib,shutil,argparse,datetime,tempfile,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
def payload(destination):
 shutil.copytree(ROOT/'skills/mineral-face-atlas',destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','WORK.md'))
 runtime=destination/'assets/runtime';runtime.mkdir(parents=True,exist_ok=True)
 for name in ['atlas','templates','ui','examples','schema','tests','docs','assets']:shutil.copytree(ROOT/name,runtime/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','WORK.md'))
 (runtime/'scripts').mkdir(exist_ok=True)
 for name in ['prepare_offline.py','print_mcp_config.py','run_js_checks.py','build_photo_example.py']:shutil.copy2(ROOT/'scripts'/name,runtime/'scripts'/name)
 evidence=ROOT/'verification' if (ROOT/'verification').exists() else ROOT/'evaluation'
 (runtime/'verification').mkdir(exist_ok=True)
 for name in ['benchmark.json','fit-benchmark.json','skill-scenarios.json']:
  if (evidence/name).exists():shutil.copy2(evidence/name,runtime/'verification'/name)
 for name in ['atlas_cli.py','requirements-fit.lock','README.md','README.zh-CN.md','LICENSE','AUTHORS.md']:shutil.copy2(ROOT/name,runtime/name)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dest',type=pathlib.Path,default=pathlib.Path.home()/'.codex/skills/mineral-face-atlas');p.add_argument('--stage-only',action='store_true',help='Build portable standalone-skill payload without replacing an installed skill');a=p.parse_args()
 if a.stage_only:
  if a.dest.exists():raise SystemExit('暂存目标已存在；请指定新目录')
  payload(a.dest);print('Standalone skill staged:',a.dest.resolve())
 else:
  dest=a.dest.expanduser().resolve();dest.parent.mkdir(parents=True,exist_ok=True);tmp=pathlib.Path(tempfile.mkdtemp(prefix='.mineral-atlas-install-',dir=dest.parent))
  try:
   payload(tmp)
   if dest.exists():
    backup=dest.parent.parent/'skill-backups'/('mineral-face-atlas-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(dest),str(backup));print('Previous skill preserved:',backup)
   os.replace(tmp,dest);print('Installed:',dest)
  except Exception:
   if tmp.exists():shutil.rmtree(tmp)
   raise
