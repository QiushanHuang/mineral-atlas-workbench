"""611 photo-2 proportion regression; thresholds bound the approved reference shape."""
import json
import pathlib
import unittest
from atlas.core import build, validate

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOWER = {'F03', 'F04', 'F05', 'F13', 'F14', 'F18'}

class Model611(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = next(s for s in json.loads((ROOT / 'examples/reference-atlas.json').read_text(encoding='utf-8')) if s['id'] == '611')
        cls.model, cls.quality = build(spec)

    def test_lower_end_is_long_and_has_a_broad_terminal_edge(self):
        vertices = self.model['vertices']
        upper = max(p[1] for p in vertices)
        lower = -min(p[1] for p in vertices)
        self.assertGreaterEqual(lower / upper, 1.6, 'Photo 2 requires an elongated lower end')
        radius = lambda p: (p[0] ** 2 + p[2] ** 2) ** .5
        terminal = [p for p in vertices if abs(p[1] + lower) < 1e-7]
        self.assertEqual(len(terminal), 6)
        self.assertGreaterEqual(max(map(radius, terminal)) / max(map(radius, vertices)), .45,
                                'The lower end must retain a broad six-sided rim')

    def test_numbering_shared_edges_and_geometric_symmetry(self):
        m = self.model
        self.assertTrue(self.quality['ok'])
        self.assertTrue(validate(m)['ok'])
        self.assertEqual(len(m['faces']), 20)
        self.assertEqual({f['id'] for f in m['faces'] if -.99 < f['n'][1] < -.01}, LOWER)
        for f in m['faces']:
            self.assertEqual(int(f['photoLabel']), int(f['id'][1:]))
        neighbors = {m['faces'][i]['id'] for e in m['edges'] if 18 in e['faces'] for i in e['faces'] if i != 18}
        self.assertEqual(neighbors, LOWER)
        self.assertEqual(m['indexing']['pointGroup'], '6mm')
        self.assertEqual(len(m['indexing']['operations']), 12)
        self.assertFalse(m['indexing']['symmetryElements']['inversion'])

if __name__ == '__main__':
    unittest.main()
