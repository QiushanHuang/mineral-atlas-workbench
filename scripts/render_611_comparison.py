"""Render old/new 611 geometry in the same orientation and scale, without photos."""
import json
import math
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.core import build, dot, mv
ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    old = json.loads((ROOT / 'docs/611-before.json').read_text(encoding='utf-8'))
    new = next(s for s in json.loads((ROOT / 'examples/reference-atlas.json').read_text(encoding='utf-8')) if s['id'] == '611')
    # c stays upright; looking between F01/F02 exposes F13/F14 below.
    angle = math.radians(30)
    R = [[math.cos(angle), 0, -math.sin(angle)], [0, 1, 0], [math.sin(angle), 0, math.cos(angle)]]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 780" width="1100" height="780">',
             '<rect width="1100" height="780" fill="#f2f4ed"/>',
             '<style>text{font-family:system-ui,sans-serif;fill:#233b32}.label{font-size:17px;font-weight:600}</style>',
             '<text x="50" y="45" font-size="28" font-weight="700">611 · Lower-end proportion correction</text>',
             '<text x="50" y="75" font-size="16">Same orientation and scale · Face IDs and shared edges preserved</text>']
    for spec, cx, caption in [(old, 290, 'Before · equal ends'), (new, 800, 'After · longer, broader lower end')]:
        m, q = build(spec)
        assert q['ok']
        project = lambda v: [cx + 83 * dot(R[0], v), 344 - 83 * dot(R[1], v)]
        parts.append(f'<text x="{cx}" y="115" text-anchor="middle" font-size="20">{caption}</text>')
        for f in sorted(m['faces'], key=lambda f: dot(R[2], f['center'])):
            if dot(R[2], f['n']) <= 1e-8:
                continue
            pts = [project(m['vertices'][i]) for i in f['ids']]
            color = '#91ac98' if f['n'][1] < -.01 else '#c6d2c1'
            parts.append('<polygon points="' + ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts) + f'" fill="{color}" stroke="#31483c" stroke-width="1.8"/>')
            x, y = project(f['center'])
            parts.append(f'<text class="label" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">{f["id"]}</text>')
        parts.append(f'<text x="{cx}" y="710" text-anchor="middle" font-size="16">Reference geometry: {spec["point_group"]} · 20 faces</text>')
    parts.append('<text x="550" y="752" text-anchor="middle" font-size="15">Photo-guided proportions; not calibrated dimensions or a specimen point-group measurement.</text></svg>')
    (ROOT / 'docs/611-comparison.svg').write_text('\n'.join(parts), encoding='utf-8')

if __name__ == '__main__':
    main()
