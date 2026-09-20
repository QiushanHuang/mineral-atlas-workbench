"""Offline 32-class catalogue, shared by validation, reports and distributable viewers."""
import json,pathlib,html
CATALOGUE=json.loads(pathlib.Path(__file__).with_name('point-groups-32.json').read_text(encoding='utf-8'))
GROUPS={g['id']:g for g in CATALOGUE['groups']}
def elements(ops):
 from .core import det
 return {'order':len(ops),'mirrors':sum(abs(det(T)+1)<1e-7 and abs(sum(T[i][i] for i in range(3))-1)<1e-7 for T in ops),'inversion':any(all(abs(T[i][j]-(-1 if i==j else 0))<1e-7 for i in range(3) for j in range(3)) for T in ops)}
def appendix():
 e=lambda s:html.escape(str(s));head=['晶系','国际符号','Schoenflies','教材简式','操作数','实际镜面数','其他设置']
 rows=''.join('<tr id="pg-'+e(g['id'])+'">'+''.join('<td>'+e(v)+'</td>' for v in [g['crystalSystem'],g['display'],g['schoenflies'],g['textbook'],g['order'],g['mirrorCount'],', '.join(g['aliases']) or '—'])+'</tr>' for g in GROUPS.values())
 return '<h2>32种晶体学点群对照标准</h2><p>32类为三维非磁晶体学点群。教材简式不重复列出反轴已包含的元素：Lᵢ⁶ 3L² 3P对应6̅m2，实际有4个镜面；水平镜面已隐含于Lᵢ⁶。完整普通元素清单可写L³ 3L² 4P，不能将两种写法混合。操作数不等于外形面数。其他轴向设置不增加新点群类型，但必须同步变换轴系和指数。Schoenflies的S6=C3i对应3̅，不是晶体学六次反轴Lᵢ⁶。</p><table><tr>'+''.join('<th>'+h+'</th>' for h in head)+'</tr>'+rows+'</table><p>Sources: <a href="https://www.iucr.org/what-we-do/education/pamphlets/introduction-crystal-physics">IUCr Table 2</a>; <a href="https://onlinelibrary.wiley.com/iucr/itc/Ac/ch3o2v0001/">International Tables</a>. Geometry compatibility does not establish the physical specimen point group.</p>'
def reference_page():return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>32种晶体学点群对照标准</title><style>body{font:14px/1.7 system-ui;padding:24px;max-width:1250px;margin:auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbcbbf;padding:8px}tr:target{background:#e4eec9}th{background:#edf2e7}</style><a href="index.html">返回模型</a>'+appendix()+'</html>'
