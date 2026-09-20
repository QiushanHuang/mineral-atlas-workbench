#!/usr/bin/env python3
"""Portable entry point; core commands require Python 3.10+ only."""
import argparse,pathlib,json,sys,base64,os
from atlas.project import build_project,write_json
from atlas.core import validate
from atlas.images import doctor

def main():
 if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
 if hasattr(sys.stderr,"reconfigure"):sys.stderr.reconfigure(encoding="utf-8")
 p=argparse.ArgumentParser(description='离线矿物晶面工作台');sub=p.add_subparsers(dest='command',required=True)
 b=sub.add_parser('build');b.add_argument('input',type=pathlib.Path);b.add_argument('--out',type=pathlib.Path,default=pathlib.Path('atlas-runs'))
 v=sub.add_parser('validate');v.add_argument('model',type=pathlib.Path)
 f=sub.add_parser('fit');f.add_argument('input',type=pathlib.Path);f.add_argument('annotation',type=pathlib.Path);f.add_argument('--image',type=pathlib.Path);f.add_argument('--out',type=pathlib.Path,default=pathlib.Path('atlas-runs'))
 sub.add_parser('doctor')
 s=sub.add_parser('serve');s.add_argument('--out',type=pathlib.Path,default=pathlib.Path('atlas-runs'));s.add_argument('--port',type=int,default=0);s.add_argument('--open',action='store_true')
 m=sub.add_parser('mcp');m.add_argument('--out',type=pathlib.Path,default=pathlib.Path(os.environ.get('PLUGIN_DATA',str(pathlib.Path.home()/'.mineral-atlas')))/'runs')
 a=p.parse_args()
 try:
  if a.command=='build':r=build_project(json.loads(a.input.read_text(encoding='utf-8')),a.out)
  elif a.command=='validate':
   r=validate(json.loads(a.model.read_text(encoding='utf-8')))
   if not r['ok']:print(json.dumps(r,ensure_ascii=False,indent=2));return 1
  elif a.command=='doctor':r=doctor()
  elif a.command=='fit':
   from atlas.service import execute
   args={'spec':json.loads(a.input.read_text()),'annotation':json.loads(a.annotation.read_text())}
   if a.image:args['image']=base64.b64encode(a.image.read_bytes()).decode()
   r=execute('atlas_fit',args,a.out);a.out.mkdir(parents=True,exist_ok=True)
   from atlas.project import sha,canonical
   result_path=a.out/('fit-'+sha(canonical(r))[:20]+'.json')
   if not result_path.exists():write_json(result_path,r)
   r={'record':str(result_path.resolve()),'quality':r['quality'],'performance':r['performance'],'artifact':r.get('artifact')}
  elif a.command=='serve':
   from atlas.server import serve
   serve(a.out,a.port,a.open);return 0
  elif a.command=='mcp':
   from atlas.mcp import run
   run(a.out);return 0
  print(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False));return 0
 except (ValueError,OSError,KeyError,TypeError,IndexError) as e:print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
