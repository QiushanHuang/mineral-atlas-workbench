import json
import pathlib
import tempfile
import unittest
import zipfile

from atlas.service import execute, TOOLS


class EditorIntegration(unittest.TestCase):
    def test_explicit_save_persists_document_without_browser_blob_downloads(self):
        with tempfile.TemporaryDirectory() as output:
            document={'schema_version':1,'annotations':[]}
            saved=execute('atlas_save_document',{'kind':'annotations','document':document},output)
            path=pathlib.Path(saved['path'])
            self.assertTrue(path.is_relative_to(pathlib.Path(output).resolve()))
            self.assertEqual(json.loads(path.read_text()),document)
            self.assertEqual(execute('atlas_save_document',{'kind':'annotations','document':document},output)['path'],saved['path'])
            with self.assertRaises(ValueError):
                execute('atlas_save_document',{'kind':'../../escape','document':document},output)

    def test_common_service_edits_exports_and_reviews_without_optional_dependencies(self):
        self.assertIn('atlas_editor', {t['name'] for t in TOOLS}, 'editor is accessible through the shared service')
        with tempfile.TemporaryDirectory() as output:
            r = execute('atlas_editor', {'action': 'create', 'preset': 'box'}, output)
            self.assertTrue(r['analysis']['quality']['ok'])
            self.assertTrue(execute('atlas_validate', {'model': r['model']}, output)['ok'], 'exported v2 geometry remains valid without a declared point group')
            edit = execute('atlas_editor', {'action': 'apply', 'draft': r['draft'],
                'command': {'type': 'move_faces', 'face_ids': [r['model']['faces'][0]['id']], 'delta': .1}}, output)
            self.assertNotEqual(edit['fingerprint'], r['fingerprint'])
            packet = execute('atlas_review_export', {'draft': edit['draft']}, output)
            checked = execute('atlas_review_check', {'packet': packet, 'response': packet['response_template'],
                'current_fingerprint': edit['fingerprint']}, output)
            self.assertEqual(checked['selected_commands'], [])
            exported = execute('atlas_editor_export', {'draft': edit['draft']}, output)
            target = pathlib.Path(exported['path'])
            self.assertTrue((target/'index.html').is_file())
            self.assertEqual(json.loads((target/'draft.json').read_text()), edit['draft'])
            with zipfile.ZipFile(target/'result.zip') as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn('editor-canvas.js', archive.namelist())
                self.assertIn('analysis.json', archive.namelist())
            self.assertTrue(execute('atlas_editor_export', {'draft': edit['draft']}, output)['cached'])

    def test_draft_title_cannot_inject_exported_html_or_javascript(self):
        with tempfile.TemporaryDirectory() as output:
            r = execute('atlas_editor', {'action': 'create', 'preset': 'box', 'title': '</script><img src=x onerror=alert(1)>'}, output)
            exported = execute('atlas_editor_export', {'draft': r['draft']}, output)
            target = pathlib.Path(exported['path'])
            self.assertNotIn('</script><img', (target/'data.js').read_text())
            self.assertNotIn('<img src=x', (target/'report.html').read_text())

if __name__ == '__main__':
    unittest.main()
