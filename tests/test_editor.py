"""Independent geometric and provenance oracles for the offline draft editor."""
import copy
import importlib.util
import itertools
import json
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
ROOT = pathlib.Path(__file__).resolve().parents[1]
IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
CUBE = {'schema_version': 1, 'id': 'cube', 'crystal_system': '等轴',
        'point_group': 'm-3m', 'index_count': 3, 'basis': IDENTITY,
        'forms': [{'hkl': [1, 0, 0], 'distance': 1}]}


def run(**kwargs):
    assert importlib.util.find_spec('atlas.editor') is not None, 'Offline draft editor is not implemented'
    from atlas.editor import execute_editor
    return execute_editor(kwargs)


class Editor(unittest.TestCase):
    def box(self):
        return run(action='create', preset='box')

    def apply(self, result, **command):
        return run(action='apply', draft=result['draft'], command=command)

    def test_box_independent_volume_area_and_topology(self):
        result = self.box()
        self.assertEqual((len(result['model']['vertices']), len(result['model']['edges']), len(result['model']['faces'])), (8, 12, 6))
        self.assertAlmostEqual(result['analysis']['volume'], 8)
        self.assertAlmostEqual(result['analysis']['area'], 24)
        self.assertTrue(all(abs(f['area'] - 4) < 1e-9 for f in result['analysis']['faces']))
        self.assertTrue(all(abs(e['length'] - 2) < 1e-9 and abs(e['interior_angle_deg'] - 90) < 1e-9 for e in result['analysis']['edges']))
        self.assertEqual({tuple(v) for v in result['model']['vertices']}, set(itertools.product([-1., 1.], repeat=3)))
        self.assertTrue(result['analysis']['quality']['ok'])

    def test_new_geometry_does_not_invent_crystallographic_facts(self):
        result = self.box()
        self.assertIsNone(result['draft'].get('point_group'))
        self.assertIsNone(result['draft'].get('crystal_system'))
        self.assertTrue(all(f['modelMiller'] is None for f in result['model']['faces']))
        self.assertEqual(result['analysis']['units'], 'model_relative_units')
        self.assertIn('参考', result['analysis']['claim_boundary'])

    def test_all_presets_are_closed_and_module_membership_is_explicit(self):
        counts = {'box': 6, 'triangular_prism': 5, 'hexagonal_prism': 8, 'pyramid': 5,
                  'dipyramid': 8, 'rhombohedron': 6, 'truncated_box': 14}
        for preset, count in counts.items():
            with self.subTest(preset=preset):
                result = run(action='create', preset=preset)
                self.assertEqual(len(result['model']['faces']), count)
                self.assertTrue(result['analysis']['quality']['ok'])
                self.assertTrue(all(p['module'] in {'body', 'top', 'bottom', 'bevel'} for p in result['draft']['planes']))

    def test_prism_volume_uses_apothem_one(self):
        self.assertAlmostEqual(run(action='create', preset='triangular_prism')['analysis']['volume'], 6 * math.sqrt(3))
        self.assertAlmostEqual(run(action='create', preset='hexagonal_prism')['analysis']['volume'], 4 * math.sqrt(3))

    def test_dimensions_scale_geometric_extent(self):
        result = run(action='create', preset='box', parameters={'width': 4, 'depth': 3, 'height': 5})
        self.assertAlmostEqual(result['analysis']['volume'], 60)
        self.assertAlmostEqual(result['analysis']['area'], 94)

    def test_move_selected_and_opposite_are_reversible_without_mutating_input(self):
        original = self.box()
        frozen = copy.deepcopy(original)
        fid = original['draft']['planes'][0]['id']
        moved = self.apply(original, type='move_faces', face_ids=[fid], delta=.25, scope='selected')
        self.assertAlmostEqual(moved['analysis']['volume'], 9)
        self.assertEqual(original, frozen)
        restored = self.apply(moved, type='move_faces', face_ids=[fid], delta=-.25, scope='selected')
        self.assertEqual(restored['model']['vertices'], original['model']['vertices'])
        linked = self.apply(original, type='move_faces', face_ids=[fid], delta=.25, scope='opposite')
        self.assertAlmostEqual(linked['analysis']['volume'], 10)

    def test_module_only_moves_explicit_members(self):
        original = self.box()
        fid = next(p['id'] for p in original['draft']['planes'] if p['module'] == 'top')
        result = self.apply(original, type='move_faces', face_ids=[fid], delta=.5, scope='module')
        changed = [p['id'] for p, q in zip(result['draft']['planes'], original['draft']['planes']) if p['distance'] != q['distance']]
        self.assertEqual(changed, [fid])

    def test_edit_history_uses_parent_fingerprint_and_invalidates_registration(self):
        original = self.box()
        result = self.apply(original, type='scale', factors=[2, 1, 1])
        self.assertEqual(result['draft']['history'][-1]['parent_fingerprint'], original['fingerprint'])
        self.assertEqual(result['draft']['history'][-1]['result_fingerprint'], result['fingerprint'])
        self.assertEqual(result['draft']['registration_status'], 'needs_refit')
        self.assertEqual({p['id'] for p in original['draft']['planes']}, {p['id'] for p in result['draft']['planes']})
        self.assertAlmostEqual(result['analysis']['volume'], 16)

    def test_truncate_keeps_old_face_ids_and_allocates_new_one(self):
        original = self.box()
        result = self.apply(original, type='truncate', normal=[1, 1, 1], distance=2.5 / math.sqrt(3))
        self.assertEqual(len(result['model']['faces']), 7)
        self.assertTrue({p['id'] for p in original['draft']['planes']} < {p['id'] for p in result['draft']['planes']})
        self.assertAlmostEqual(result['analysis']['volume'], 8 - .5 ** 3 / 6)

    def test_invalid_previews_report_codes_and_preserve_source(self):
        original = self.box()
        frozen = copy.deepcopy(original)
        commands = [
            ({'type': 'move_faces', 'face_ids': ['F01'], 'delta': -2}, 'invalid_distance'),
            ({'type': 'move_faces', 'face_ids': ['MISSING'], 'delta': .2}, 'unknown_face'),
            ({'type': 'scale', 'factors': [1, 0, 1]}, 'invalid_scale'),
            ({'type': 'truncate', 'normal': [1, 1, 1], 'distance': 10}, 'inactive_faces'),
            ({'type': 'truncate', 'normal': [1, 0, 0], 'distance': .5}, 'duplicate_normal'),
        ]
        for command, code in commands:
            with self.subTest(command=command):
                with self.assertRaises(ValueError) as caught:
                    run(action='apply', draft=original['draft'], command=command)
                self.assertEqual(getattr(caught.exception, 'code', None), code)
                self.assertEqual(original, frozen)

    def test_opposite_link_rejects_non_symmetric_plane_pair(self):
        original = self.box()
        asymmetric = self.apply(original, type='move_faces', face_ids=['F01'], delta=.2)
        with self.assertRaisesRegex(ValueError, '对面|对称'):
            self.apply(asymmetric, type='move_faces', face_ids=['F01'], delta=.1, scope='opposite')

    def test_reference_axes_and_origin_never_change_geometry(self):
        original = self.box()
        basis = [[1, .3, 0], [0, 1, 0], [0, 0, 2]]
        changed = self.apply(original, type='set_axes', basis=basis, index_count=3, origin=[5, 2, -3])
        self.assertEqual(changed['model']['vertices'], original['model']['vertices'])
        self.assertEqual(changed['draft']['planes'], original['draft']['planes'])
        self.assertEqual(changed['analysis']['axes']['origin'], [5, 2, -3])
        self.assertAlmostEqual(changed['analysis']['axes']['lengths'][1], math.sqrt(1.09))
        self.assertNotEqual(changed['draft']['registration_status'], 'needs_refit')

    def test_axes_reject_degenerate_left_handed_and_invalid_four_axis_basis(self):
        original = self.box()
        for basis, count in [([[1, 1, 0], [0, 0, 0], [0, 0, 1]], 3),
                             ([[-1, 0, 0], [0, 1, 0], [0, 0, 1]], 3), (IDENTITY, 4)]:
            with self.subTest(basis=basis, count=count), self.assertRaises(ValueError):
                self.apply(original, type='set_axes', basis=basis, index_count=count)

    def test_four_axis_relation_and_exact_candidate_indices(self):
        basis = [[1, -.5, 0], [0, math.sqrt(3) / 2, 0], [0, 0, 2]]
        changed = self.apply(self.box(), type='set_axes', basis=basis, index_count=4)
        axes = changed['analysis']['axes']['display_axes']
        self.assertEqual(axes[2], [-axes[0][i] - axes[1][i] for i in range(3)])
        for face in changed['analysis']['faces']:
            for candidate in face['index_candidates']['candidates']:
                self.assertEqual(sum(candidate['hkl'][:3]), 0)

    def test_index_candidates_known_and_explicitly_unsolved(self):
        result = self.box()
        plus_x = next(f for f in result['analysis']['faces'] if f['normal'] == [1, 0, 0])
        self.assertEqual(plus_x['index_candidates']['candidates'][0]['hkl'], [1, 0, 0])
        changed = self.apply(result, type='set_axes', basis=[[1, .314159265, 0], [0, 1, 0], [0, 0, 1]], index_count=3)
        analyzed = run(action='analyze', draft=changed['draft'], max_index=2, tolerance_deg=.000001)
        plus_x = next(f for f in analyzed['analysis']['faces'] if f['normal'] == [1, 0, 0])
        self.assertEqual(plus_x['index_candidates']['status'], 'no_solution_within_tolerance')
        self.assertEqual(plus_x['index_candidates']['candidates'], [])
        self.assertEqual(plus_x['index_candidates']['max_index'], 2)

    def test_rebuild_needs_recorded_indices_and_changes_geometry_explicitly(self):
        with self.assertRaisesRegex(ValueError, '指数'):
            self.apply(self.box(), type='rebuild_axes', basis=IDENTITY, index_count=3)
        imported = run(action='import', spec=CUBE)
        basis = [[1, .5, 0], [0, 1, 0], [0, 0, 1]]
        rebuilt = self.apply(imported, type='rebuild_axes', basis=basis, index_count=3)
        self.assertNotEqual(rebuilt['model']['vertices'], imported['model']['vertices'])
        self.assertEqual(rebuilt['draft']['registration_status'], 'needs_refit')

    def test_imported_indices_remain_provenance_after_reference_axes_change(self):
        imported = run(action='import', spec=CUBE)
        old_indices = [p['source_hkl'] for p in imported['draft']['planes']]
        changed = self.apply(imported, type='set_axes', basis=[[1, .5, 0], [0, 1, 0], [0, 0, 1]], index_count=3)
        self.assertEqual([p['source_hkl'] for p in changed['draft']['planes']], old_indices)
        self.assertTrue(all(f['modelMiller'] is None for f in changed['model']['faces']))

    def test_import_all_reference_models_without_geometric_or_face_id_drift(self):
        from atlas.core import build
        for spec in json.loads((ROOT / 'examples/reference-atlas.json').read_text()):
            with self.subTest(model=spec['id']):
                original, quality = build(spec)
                result = run(action='import', spec=spec, max_index=3)
                self.assertEqual(result['model']['vertices'], original['vertices'])
                self.assertEqual([f['id'] for f in result['model']['faces']], [f['id'] for f in original['faces']])
                self.assertAlmostEqual(result['analysis']['volume'], quality['volume'])
                self.assertTrue(all(p['module'] == 'single' for p in result['draft']['planes']))

    def test_save_reopen_fingerprint_stable_and_metadata_edits_keep_geometry(self):
        original = self.box()
        changed = self.apply(original, type='metadata', face_ids=['F01'], label='手动确认面', evidence='用户重画边界')
        self.assertEqual(changed['model']['vertices'], original['model']['vertices'])
        reopened = run(action='analyze', draft=json.loads(json.dumps(changed['draft'])))
        self.assertEqual(reopened['fingerprint'], changed['fingerprint'])
        self.assertEqual(reopened['model']['faces'][0]['label'], '手动确认面')
        self.assertNotEqual(original['fingerprint'], changed['fingerprint'])

    def test_nan_unbounded_and_duplicate_ids_rejected(self):
        draft = self.box()['draft']
        malformed = copy.deepcopy(draft)
        malformed['planes'][0]['normal'][0] = float('nan')
        with self.assertRaises(ValueError): run(action='analyze', draft=malformed)
        malformed = copy.deepcopy(draft)
        malformed['planes'][1]['id'] = malformed['planes'][0]['id']
        with self.assertRaisesRegex(ValueError, '唯一|重复'): run(action='analyze', draft=malformed)
        malformed = copy.deepcopy(draft)
        malformed['planes'] = malformed['planes'][1:]
        with self.assertRaisesRegex(ValueError, '开放|有界|闭合'): run(action='analyze', draft=malformed)

    def test_browser_roundtrip_preserves_fingerprint_with_integral_floats(self):
        result = self.box()
        # JSON.stringify in the browser serializes 1.0 as 1, unlike Python.
        browser_draft = json.loads(json.dumps(result['draft']), parse_float=lambda s: int(float(s)) if float(s).is_integer() else float(s))
        from atlas.editor import fingerprint
        self.assertEqual(result['fingerprint'], fingerprint(browser_draft))
        reopened = run(action='analyze', draft=browser_draft, expected_fingerprint=result['fingerprint'])
        self.assertEqual(result['fingerprint'], reopened['fingerprint'])

    def test_stale_and_overflowing_inputs_fail_with_useful_codes(self):
        result = self.box()
        with self.assertRaises(ValueError) as caught:
            run(action='apply', draft=result['draft'], expected_fingerprint='0'*64,
                command={'type': 'scale', 'factors': [2, 1, 1]})
        self.assertEqual(caught.exception.code, 'stale_draft')
        with self.assertRaises(ValueError) as caught:
            self.apply(result, type='set_axes', basis=[[1e308, 0, 0], [0, 1e308, 0], [0, 0, 1e308]], index_count=3)
        self.assertEqual(caught.exception.code, 'invalid_axes')

    def test_metadata_project_title_creates_revision_without_face_selection(self):
        original = self.box()
        result = self.apply(original, type='metadata', title='重新命名的模型')
        self.assertEqual(result['draft']['title'], '重新命名的模型')
        self.assertEqual(result['model']['info']['title'], '重新命名的模型')
        self.assertEqual(result['model']['vertices'], original['model']['vertices'])
        self.assertEqual(result['draft']['history'][-1]['parent_fingerprint'], original['fingerprint'])
        self.assertFalse(result['draft']['history'][-1]['geometry_changed'])

    def test_cube_geometry_symmetry_and_three_axis_zones_are_conditional(self):
        result = self.box()
        self.assertIn('geometry_symmetry_candidates', result['analysis'])
        symmetry = result['analysis']['geometry_symmetry_candidates']
        self.assertIn({'point_group': 'm-3m', 'order': 48}, symmetry['highest_candidates'])
        self.assertEqual(symmetry['status'], 'basis_relative_compatible')
        self.assertIsNone(result['draft'].get('point_group'))
        zones = result['analysis']['zone_candidates']
        self.assertEqual(len(zones), 3)
        self.assertEqual({tuple(round(abs(x)) for x in z['direction']) for z in zones}, {(1, 0, 0), (0, 1, 0), (0, 0, 1)})
        self.assertTrue(all(len(z['face_ids']) == 4 for z in zones))

    def test_hexagonal_geometry_candidates_and_six_side_face_zone(self):
        result = run(action='create', preset='hexagonal_prism')
        self.assertIn('geometry_symmetry_candidates', result['analysis'])
        symmetry = result['analysis']['geometry_symmetry_candidates']
        self.assertIn({'point_group': '6/mmm', 'order': 24}, symmetry['highest_candidates'])
        axial = [z for z in result['analysis']['zone_candidates'] if abs(z['direction'][2]) > 1 - 1e-8]
        self.assertEqual(len(axial), 1)
        self.assertEqual(set(axial[0]['face_ids']), {p['id'] for p in result['draft']['planes'] if p['module'] == 'body'})

    def test_nonorthogonal_reference_reports_only_tested_orientation_and_axes_do_not_move_solid(self):
        original = self.box()
        changed = self.apply(original, type='set_axes', basis=[[1, .2, .17], [0, 1, .26], [0, 0, 1]], index_count=3)
        self.assertIn('geometry_symmetry_candidates', changed['analysis'])
        symmetry = changed['analysis']['geometry_symmetry_candidates']
        self.assertNotIn('m-3m', [c['point_group'] for c in symmetry['candidates']])
        self.assertEqual(symmetry['orientation_search'], 'reference_frame_only')
        self.assertEqual(changed['model']['vertices'], original['model']['vertices'])
        self.assertEqual(changed['analysis']['zone_candidates'], original['analysis']['zone_candidates'])

    def test_translated_box_symmetry_uses_geometric_center_not_reference_marker(self):
        result = self.apply(self.box(), type='move_faces', face_ids=['F01'], delta=.25)
        self.assertIn('geometry_symmetry_candidates', result['analysis'])
        symmetry = result['analysis']['geometry_symmetry_candidates']
        self.assertAlmostEqual(symmetry['center'][0], .125)
        self.assertIn('mmm', [c['point_group'] for c in symmetry['candidates']])


if __name__ == '__main__':
    unittest.main()
