import sys,pathlib,unittest,base64,unittest.mock as mock,json,io
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.images import decode_image,ocr,vision,doctor
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Images(unittest.TestCase):
 def image(self):return base64.b64encode((ROOT/'examples/synthetic.png').read_bytes()).decode()
 def test_local_adapters_contract(self):
  raw,ext=decode_image(self.image());self.assertEqual(ext,'.png')
  with mock.patch('atlas.images.shutil.which',return_value=None):
   with self.assertRaisesRegex(ValueError,'Tesseract'):ocr(self.image())
  response=mock.MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'message':{'content':'{"observations":["synthetic"]}'}}).encode();opener=mock.Mock();opener.open.return_value=response
  with mock.patch('atlas.images.urllib.request.build_opener',return_value=opener):
   result=vision(self.image(),'local-test-fixture');self.assertEqual(result['claim_level'],'unverified_visual_suggestion');req=opener.open.call_args.args[0];self.assertEqual(req.full_url,'http://127.0.0.1:11434/api/chat')
 def test_invalid_image(self):
  for x in ['data:image/svg+xml;base64,PHN2Zz4=','notbase64!',base64.b64encode(b'<html>').decode()]:
   with self.assertRaises(ValueError):decode_image(x)
 def test_core_without_network(self):
  from atlas.core import build
  with mock.patch('socket.socket',side_effect=AssertionError('Network not allowed')):
   m,q=build(json.loads((ROOT/'examples/cube.json').read_text(encoding="utf-8")));self.assertTrue(q['ok']);self.assertEqual(doctor()['core'],'ready (Python standard library)')
if __name__=='__main__':unittest.main()
