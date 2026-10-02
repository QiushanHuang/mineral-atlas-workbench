"""Immutable local editor exports, viewable without Python or an internet connection."""
import html
import json
import os
import pathlib
import shutil
import tempfile
import time
import zipfile

from .editor import execute_editor
from .project import ROOT, LOCK, canonical, sha, write_json, source_hash, require_current_source, cache_valid


def export_editor(draft, output):
    require_current_source()
    start = time.perf_counter()
    result = execute_editor({'action': 'analyze', 'draft': draft})
    source = source_hash()
    digest = 'editor-' + sha(canonical({'draft': result['draft'], 'source': source}))[:20]
    output = pathlib.Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with LOCK:
        target = output / digest
        if cache_valid(target):
            return {'run_id': target.name, 'path': str(target), 'cached': True, 'quality': result['analysis']['quality']}
        suffix = 2
        while target.exists():
            target = output / (digest + '-r' + str(suffix))
            suffix += 1
        tmp = pathlib.Path(tempfile.mkdtemp(prefix='.editor-building-', dir=output))
        try:
            for name, data in [('draft.json', result['draft']), ('model.json', result['model']),
                               ('analysis.json', result['analysis']), ('quality.json', result['analysis']['quality'])]:
                write_json(tmp / name, data)
            title = html.escape(result['draft']['title'])
            analysis = html.escape(json.dumps(result['analysis'], ensure_ascii=False, indent=2))
            report = f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{title} · 参数报告</title><style>body{{font:15px/1.7 system-ui;max-width:1100px;margin:30px auto;padding:20px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style><h1>{title}</h1><p>参考几何，模型相对单位。指数是用户参考轴下的候选，不是实物测定。原始草稿、编辑来源和算法指纹随包保存。</p><a href="index.html">模型预览</a><pre>{analysis}</pre></html>'
            (tmp / 'report.html').write_text(report, encoding='utf-8')
            (tmp / 'data.js').write_text('const EDITOR_RESULT = ' + json.dumps(result, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c') + ';\n', encoding='utf-8')
            shutil.copyfile(ROOT / 'ui/editor-canvas.js', tmp / 'editor-canvas.js')
            shutil.copyfile(ROOT / 'LICENSE', tmp / 'LICENSE')
            page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>body{{font:15px/1.6 system-ui;background:#f3f5ef;color:#214536;max-width:1250px;margin:auto;padding:22px}}.views{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}figure{{margin:0}}canvas{{width:100%;height:320px;display:block}}button,select{{font:inherit;padding:8px}}@media(max-width:650px){{canvas{{height:220px}}}}</style></head><body><h1>{title}</h1><p>离线参考模型 · 固定正交视图 · 不代表真实晶体学测定</p><label>定位面 <select id="face"></select></label> <button id="reset">标准方向</button><p><a href="report.html">参数报告</a> · <a href="draft.json" download>编辑项目</a> · <a href="analysis.json" download>解析数据</a> · <a href="receipt.json">复现记录</a></p><div class="views"><figure>正面<canvas id="front"></canvas></figure><figure>侧面<canvas id="side"></canvas></figure><figure>顶面<canvas id="top"></canvas></figure><figure>三维预览<canvas id="three"></canvas></figure></div><p>继续编辑：在晶面工作台的“轻松建模”中打开 draft.json。此预览无需服务或联网。</p><script src="data.js"></script><script src="editor-canvas.js"></script><script>
const r=EDITOR_RESULT,s=document.getElementById('face');r.model.faces.forEach(f=>{{const o=document.createElement('option');o.value=f.id;o.textContent=f.id+' · '+f.label;s.append(o);}});function draw(){{['front','side','top','three'].forEach(view=>AtlasEditorCanvas.draw(document.getElementById(view),r.model,{{view,selected:[s.value],axes:r.draft.axes}}));}}s.onchange=draw;document.getElementById('reset').onclick=draw;window.onresize=draw;draw();</script></body></html>'''
            (tmp / 'index.html').write_text(page, encoding='utf-8')
            files = {p.name: sha(p.read_bytes()) for p in sorted(tmp.iterdir())}
            write_json(tmp / 'receipt.json', {'schema_version': 1, 'source_sha256': source,
                       'input_sha256': result['fingerprint'], 'files': files, 'claim_level': 'reference_geometry',
                       'units': 'relative_model_units', 'network_required': False})
            with zipfile.ZipFile(tmp / 'result.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                for p in sorted(tmp.iterdir()):
                    if p.name == 'result.zip':
                        continue
                    info = zipfile.ZipInfo(p.name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, p.read_bytes())
            write_json(tmp / '.integrity.json', {p.name: sha(p.read_bytes()) for p in tmp.iterdir()})
            os.rename(tmp, target)
        except Exception:
            shutil.rmtree(tmp)
            raise
    return {'run_id': target.name, 'path': str(target), 'cached': False,
            'quality': result['analysis']['quality'], 'elapsed_seconds': time.perf_counter() - start}
