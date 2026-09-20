import pathlib,sys,json,subprocess,tempfile,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build
from atlas.project import ROOT
node=shutil.which('node')
if not node:raise SystemExit('Node未安装，跳过可选JS回归；软件运行不需要Node。')
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'models.json';p.write_text(json.dumps({s['id']:build(s)[0] for s in json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding="utf-8"))}), encoding="utf-8")
 subprocess.run([node,str(ROOT/'tests/rotation_scale.cjs'),str(ROOT/'templates/viewer.js'),str(p)],check=True)
 subprocess.run([node,'--check',str(ROOT/'ui/workbench.js')],check=True)
