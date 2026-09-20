"""A no-runtime, no-network reference atlas for recipients who only need to inspect existing cases."""
import sys,pathlib,json,html,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build
from atlas.project import ROOT,write_json,report,source_hash
shutil.copyfile(ROOT/'assets/logo.png',ROOT/'ui/logo.png')
specs=json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding="utf-8"));models={};qualities={};reports=[]
for s in specs:
 m,q=build(s);models[s['id']]=m;qualities[s['id']]=q;page=report(m,q,s);body=page[page.index('<h1>'):page.rindex('</html>')].replace('href="index.html"','href="reference-atlas.html"').replace('href="input.json"','href="reference-inputs.json"');reports.append(body)
data={'models':models,'photos':{k:[] for k in models},'views':{k:[] for k in models}};css=(ROOT/'templates/style.css').read_text(encoding="utf-8");js=(ROOT/'templates/viewer.js').read_text(encoding="utf-8");page=(ROOT/'templates/viewer.html').read_text(encoding="utf-8");page=page.replace('<link rel="stylesheet" href="style.css">','<style>'+css+'</style>');page=page.replace('<script src="data.js"></script><script src="viewer.js"></script>','<script>const DATA = '+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';</script><script>'+js+'</script>')
for a,b in [('report.html','reference-report.html'),('input.json','reference-inputs.json'),('model.json','reference-models.json'),('quality.json','reference-quality.json'),('receipt.json','reference-receipt.json')]:page=page.replace('href="'+a+'"','href="'+b+'"')
(ROOT/'ui/reference-atlas.html').write_text(page, encoding="utf-8");(ROOT/'ui/reference-report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>十五组参考报告</title><style>body{font:14px/1.6 system-ui;margin:25px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #bbb;padding:8px}pre{white-space:pre-wrap}h1{border-top:2px solid #375a47;padding-top:20px}</style>'+''.join(reports)+'</html>', encoding="utf-8")
for n,x in [('inputs',specs),('models',models),('quality',qualities),('receipt',{'source_sha256':source_hash(),'model_count':15,'face_count':226,'claim_level':'reference_model','photos_included':False})]:write_json(ROOT/f'ui/reference-{n}.json',x)
(ROOT/'查看预置图谱.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=ui/reference-atlas.html"><a href="ui/reference-atlas.html">打开十五组参考图谱（无需Python或网络）</a>', encoding="utf-8")
print('Built offline reference atlas: 15 models / 226 faces; no private photos')
