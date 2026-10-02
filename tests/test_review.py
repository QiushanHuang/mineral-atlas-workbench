"""Local review protocol: proposals are checked, never applied here."""
import copy
import importlib.util
import json
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


class ReviewProtocol(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas.review'), 'local review protocol is missing')
        from atlas import review
        self.review = review
        self.draft = {'schema_version': 2, 'id': 'fixture', 'private_path': '/Users/private/raw.jpg'}
        self.model = {'vertices': [[-1, -1, -1], [1, 1, 1]],
                      'faces': [{'id': 'F01', 'n': [1, 0, 0], 'd': 1, 'ids': [0, 1]},
                                {'id': 'F02', 'n': [-1, 0, 0], 'd': 1, 'ids': [1, 0]}],
                      'edges': [], 'indexing': {'basis': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}}

    def packet(self):
        return self.review.make_review_packet(self.draft, self.model, {'volume': 8})

    def response(self, packet, command=None):
        r = copy.deepcopy(packet['response_template'])
        r['suggestions'] = [{'id': 's1', 'target': 'geometry', 'reason': 'Check opposite face separation.',
                             'evidence': [{'kind': 'model_face', 'reference': 'F01', 'detail': 'Current support is 1.'}],
                             'command': command or {'type': 'move_faces', 'face_ids': ['F01'], 'delta': 0.1}}]
        r['uncertain'] = ['Depth is not independently calibrated.']
        return r

    def test_export_is_private_path_free_and_deterministic(self):
        p = self.packet()
        self.assertEqual(p, self.packet())
        self.assertNotIn('/Users/private', json.dumps(p))
        self.assertNotIn('private_path', json.dumps(p))
        self.assertEqual(p['model_summary']['face_ids'], ['F01', 'F02'])
        self.assertIn('单张', p['prompt'])
        self.assertIn('遮挡', p['prompt'])

    def test_preview_preserves_uncertainty_and_requires_selection(self):
        p = self.packet(); r = self.response(p); old = copy.deepcopy(self.draft)
        result = self.review.review_response(p, r, p['input_sha256'])
        self.assertEqual(result['selected_commands'], [])
        self.assertEqual(result['uncertain'], r['uncertain'])
        self.assertEqual(result['suggestions'][0]['id'], 's1')
        selected = self.review.review_response(p, r, p['input_sha256'], ['s1'])
        self.assertEqual(selected['selected_commands'], [r['suggestions'][0]['command']])
        self.assertEqual(self.draft, old)

    def test_stale_or_tampered_bindings_are_rejected(self):
        p = self.packet(); r = self.response(p)
        for wrong in [dict(r, input_sha256='0'*64), dict(r, policy_sha256='0'*64), dict(r, packet_id='another')]:
            with self.assertRaises(ValueError): self.review.review_response(p, wrong, p['input_sha256'])
        with self.assertRaises(ValueError): self.review.review_response(p, r, '0'*64)
        for key in ['input_sha256', 'policy_sha256', 'prompt']:
            bad = copy.deepcopy(p); bad[key] = 'tampered'
            with self.assertRaises(ValueError): self.review.review_response(bad, r, p['input_sha256'])

    def test_unknown_fields_commands_domains_and_faces_rejected(self):
        p = self.packet()
        commands = [{'type': 'delete_project'}, {'type': 'move_faces', 'face_ids': ['missing'], 'delta': .1},
                    {'type': 'move_faces', 'face_ids': ['F01'], 'delta': math.nan},
                    {'type': 'move_faces', 'face_ids': ['F01'], 'delta': True},
                    {'type': 'move_faces', 'face_ids': ['F01'], 'delta': .1, 'shell': 'run'}]
        for c in commands:
            with self.subTest(command=c), self.assertRaises(ValueError):
                self.review.review_response(p, self.response(p, c), p['input_sha256'])
        for field, value in [('target', 'physical_crystal_identification'), ('evidence', []), ('reason', '')]:
            r = self.response(p); r['suggestions'][0][field] = value
            with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])
        r = self.response(p); r['unexpected'] = 'ignored?'
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])

    def test_axes_and_truncation_validated_without_execution(self):
        p = self.packet()
        commands = [({'type': 'set_axes', 'basis': [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 'index_count': 3, 'origin': [0, 0, 0]}, 'axes'),
                    ({'type': 'truncate', 'normal': [1, 1, 0], 'distance': 1.2}, 'geometry')]
        for c, target in commands:
            r = self.response(p, c); r['suggestions'][0]['target'] = target
            result = self.review.review_response(p, r, p['input_sha256'], ['s1'])
            self.assertEqual(result['selected_commands'], [c])
        for c in [{'type': 'set_axes', 'basis': [[1, 0, 0], [1, 0, 0], [0, 0, 1]], 'index_count': 3, 'origin': [0, 0, 0]},
                  {'type': 'truncate', 'normal': [0, 0, 0], 'distance': 1},
                  {'type': 'truncate', 'normal': [1, 0, 0], 'distance': math.inf}]:
            r = self.response(p, c); r['suggestions'][0]['target'] = 'axes' if c['type'] == 'set_axes' else 'geometry'
            with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])

    def test_duplicate_selection_and_evidence_references_rejected(self):
        p = self.packet(); r = self.response(p)
        for ids in [['missing'], ['s1', 's1'], 's1']:
            with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'], ids)
        r['suggestions'].append(copy.deepcopy(r['suggestions'][0]))
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])
        r = self.response(p); r['suggestions'][0]['evidence'][0]['reference'] = 'F99'
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])
        r = self.response(p); r['suggestions'][0]['evidence'][0]['kind'] = 'secret_instructions'
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])

    def test_editor_fingerprint_axes_and_current_analysis_are_bound(self):
        from atlas.editor import execute_editor, fingerprint
        result = execute_editor({'action': 'create', 'preset': 'box'})
        p = self.review.make_review_packet(result['draft'], result['model'], result['analysis'])
        self.assertEqual(p['input_sha256'], fingerprint(result['draft']))
        self.assertEqual(p['model_summary'].get('reference_basis'), result['draft']['axes']['basis'])
        self.assertEqual(p['model_summary']['reference_origin'], result['draft']['axes']['origin'])
        self.assertAlmostEqual(p['model_summary']['surface_area'], result['analysis']['area'])
        stale = dict(result['analysis'], input_fingerprint='0'*64)
        with self.assertRaises(ValueError): self.review.make_review_packet(result['draft'], result['model'], stale)
        stale_model = dict(result['model'], draftFingerprint='0'*64)
        with self.assertRaises(ValueError): self.review.make_review_packet(result['draft'], stale_model, result['analysis'])

    def test_manual_annotations_are_unverified_and_not_pixel_observations(self):
        ann = {'schema_version': 1, 'source_sha256': 'a'*64, 'image_size': [100, 80],
               'features': [{'id': 'e1', 'kind': 'edge', 'points': [[5, 5], [20, 30]], 'face_id': 'F01',
                             'model_fingerprint': self.packet()['input_sha256']}],
               'private_path': '/Users/private/raw.jpg', 'image': 'data:private'}
        p = self.review.make_review_packet(self.draft, self.model, {}, [ann])
        self.assertNotIn('/Users/private', json.dumps(p))
        self.assertEqual(p['annotations'][0]['provenance'], 'unverified_user_drawn')
        r = self.response(p)
        r['suggestions'][0]['evidence'] = [{'kind': 'user_annotation', 'reference': 'a'*64+':e1', 'detail': 'User marked an edge.'}]
        self.assertEqual(len(self.review.review_response(p, r, p['input_sha256'])['suggestions']), 1)
        r['suggestions'][0]['evidence'][0]['kind'] = 'visual_observation'
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])

    def test_face_association_requires_current_model_fingerprint(self):
        ann = {'schema_version': 1, 'source_sha256': 'a'*64, 'image_size': [100, 80],
               'features': [{'id': 'face1', 'kind': 'face', 'points': [[1, 1], [20, 1], [1, 20]], 'face_id': 'F01'}]}
        wrong = copy.deepcopy(ann); wrong['features'][0]['model_fingerprint'] = '0'*64
        for bad in [ann, wrong]:
            with self.subTest(annotation=bad), self.assertRaisesRegex(ValueError, '关联'):
                self.review.make_review_packet(self.draft, self.model, {}, [bad])
        ann['features'][0]['model_fingerprint'] = self.packet()['input_sha256']
        packet = self.review.make_review_packet(self.draft, self.model, {}, [ann])
        self.assertEqual(packet['annotations'][0]['features'][0].get('model_fingerprint'), packet['input_sha256'])
        no_binding = copy.deepcopy(ann)
        no_binding['features'][0].pop('model_fingerprint'); no_binding['features'][0].pop('face_id')
        self.assertEqual(len(self.review.make_review_packet(self.draft, self.model, {}, [no_binding])['annotations']), 1)

    def test_same_image_mixed_face_model_bindings_rejected_individually(self):
        current = self.packet()['input_sha256']
        ann = {'schema_version': 1, 'source_sha256': 'a'*64, 'image_size': [100, 80],
               'model_fingerprint': current,
               'features': [
                   {'id': 'a', 'kind': 'face', 'points': [[1, 1], [20, 1], [1, 20]], 'face_id': 'F01', 'model_fingerprint': current},
                   {'id': 'b', 'kind': 'face', 'points': [[30, 1], [50, 1], [30, 20]], 'face_id': 'F02', 'model_fingerprint': '0'*64}]}
        with self.assertRaisesRegex(ValueError, '关联'):
            self.review.make_review_packet(self.draft, self.model, {}, [ann])
        # A new association for one face never refreshes the other face's identity.
        self.assertEqual(ann['features'][1]['model_fingerprint'], '0'*64)
        ann['features'][1]['model_fingerprint'] = current
        packet = self.review.make_review_packet(self.draft, self.model, {}, [ann])
        self.assertNotIn('model_fingerprint', packet['annotations'][0])
        self.assertEqual([f['model_fingerprint'] for f in packet['annotations'][0]['features']], [current, current])

    def test_boolean_versions_and_invalid_four_axis_basis_rejected(self):
        p = self.packet(); r = self.response(p); r['schema_version'] = True
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])
        r = self.response(p, {'type': 'set_axes', 'basis': [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 'index_count': 4})
        r['suggestions'][0]['target'] = 'axes'
        with self.assertRaises(ValueError): self.review.review_response(p, r, p['input_sha256'])

    def test_core_axis_limits_and_truncate_ids(self):
        p = self.packet()
        commands = [
            ({'type': 'set_axes', 'basis': [[1e-8, 0, 0], [0, 1e-8, 0], [0, 0, 1e-8]], 'index_count': 3}, 'axes'),
            ({'type': 'set_axes', 'basis': [[1001, 0, 0], [0, 1, 0], [0, 0, 1]], 'index_count': 3}, 'axes'),
            ({'type': 'truncate', 'normal': [1, 1, 0], 'distance': 1, 'id': 'custom'}, 'geometry')]
        for command, target in commands:
            r = self.response(p, command); r['suggestions'][0]['target'] = target
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.review.review_response(p, r, p['input_sha256'])

    def test_selected_command_matches_direct_local_execution(self):
        from atlas.editor import execute_editor
        state = execute_editor({'action': 'create', 'preset': 'box'})
        p = self.review.make_review_packet(state['draft'], state['model'], state['analysis'])
        response = self.response(p)
        preview = self.review.review_response(p, response, state['fingerprint'], ['s1'])
        direct = execute_editor({'action': 'apply', 'draft': state['draft'], 'command': response['suggestions'][0]['command']})
        accepted = execute_editor({'action': 'apply', 'draft': state['draft'], 'command': preview['selected_commands'][0], 'expected_fingerprint': preview['input_sha256']})
        self.assertEqual(accepted, direct)

    def test_packet_integrity_survives_browser_integer_roundtrip(self):
        from atlas.editor import execute_editor
        state = execute_editor({'action': 'create', 'preset': 'box'})
        packet = self.review.make_review_packet(state['draft'], state['model'], state['analysis'])
        browser = json.loads(json.dumps(packet), parse_float=lambda v: int(float(v)) if float(v).is_integer() else float(v))
        result = self.review.review_response(browser, browser['response_template'], state['fingerprint'])
        self.assertEqual(result['status'], 'reviewed_not_applied')


if __name__ == '__main__':
    unittest.main()
