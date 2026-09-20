"""A no-runtime, no-network reference atlas for recipients who only need to inspect existing cases."""
import sys,pathlib,json,html,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build
from atlas.point_groups import reference_page
from atlas.project import ROOT,write_json,report,source_hash
(ROOT/'ui/point-groups.html').write_text(reference_page().replace('href="index.html"','href="reference-atlas.html"'),encoding='utf-8')
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
# Keep the full standard readable directly on GitHub as well as in offline HTML.
from atlas.point_groups import CATALOGUE
headers=['晶系','国际符号','Schoenflies','教材简式','操作数','实际镜面数','其他设置']
md='# 32种晶体学点群对照标准\n\n由 `atlas/point-groups-32.json` 生成；教材简式和实际镜面数分别列出。−6m2简式为Lᵢ⁶ 3L² 3P，水平镜面隐含于六次反轴，实际共4个镜面。面数不等于操作数。其他设置不增加新点群类型，变换设置时须同步变换晶轴和晶面指数。\n\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'
for g in CATALOGUE['groups']:
 md+='|'+'|'.join(str(v) for v in [g['crystalSystem'],g['display'],g['schoenflies'],g['textbook'],g['order'],g['mirrorCount'],', '.join(g['aliases']) or '—'])+'|\n'
md+='\n来源：[IUCr Table 2](https://www.iucr.org/what-we-do/education/pamphlets/introduction-crystal-physics)、[International Tables](https://onlinelibrary.wiley.com/iucr/itc/Ac/ch3o2v0001/)。[本次修正与核对环节](point-group-audit.md)。\n'
(ROOT/'docs/point-groups-32.md').write_text(md,encoding='utf-8')
