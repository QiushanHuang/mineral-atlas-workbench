"""Explicit dependency preparation on a connected machine matching the offline target platform/Python."""
import argparse,pathlib,subprocess,sys,json,hashlib,platform
p=argparse.ArgumentParser();p.add_argument('--download',action='store_true',help='Explicitly allow pip download from configured package index');p.add_argument('--install',action='store_true',help='Install only from existing wheelhouse, never from network');p.add_argument('--wheelhouse',type=pathlib.Path,default=pathlib.Path('wheelhouse'));a=p.parse_args();root=pathlib.Path(__file__).resolve().parents[1]
if a.download==a.install:p.error('Choose exactly one of --download or --install')
if a.download:
 a.wheelhouse.mkdir(parents=True,exist_ok=True);subprocess.run([sys.executable,'-m','pip','download','--only-binary=:all:','-r',str(root/'requirements-fit.lock'),'-d',str(a.wheelhouse)],check=True)
 files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.wheelhouse.glob('*.whl')};(a.wheelhouse/'SHA256.json').write_text(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'files':files},indent=2), encoding="utf-8");print('Prepared wheels; use the same target OS, architecture and Python ABI.')
else:
 receipt=json.loads((a.wheelhouse/'SHA256.json').read_text(encoding="utf-8"))
 for name,digest in receipt['files'].items():
  if pathlib.Path(name).name!=name:raise SystemExit('Invalid wheel filename')
  if hashlib.sha256((a.wheelhouse/name).read_bytes()).hexdigest()!=digest:raise SystemExit('Wheel checksum mismatch: '+name)
 subprocess.run([sys.executable,'-m','pip','install','--no-index','--find-links',str(a.wheelhouse),'-r',str(root/'requirements-fit.lock')],check=True)
