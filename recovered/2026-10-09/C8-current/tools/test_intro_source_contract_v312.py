import json, os, tempfile, unittest
from pathlib import Path
from intro_source_contract_v312 import extract
from le_bound_image_v312 import LEError
class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=os.environ.get('OPENAZRAEL_CORPUS')
        if not root: raise unittest.SkipTest('set OPENAZRAEL_CORPUS')
        cls.root=Path(root);cls.result=extract(cls.root)
    def test_frozen_contract(self):
        expected=json.loads((Path(__file__).resolve().parents[1]/'data/tests/intro_source_contract_v312.json').read_text(encoding='utf8'))
        self.assertEqual(self.result,expected)
    def test_order(self):
        self.assertEqual(self.result['startup_order'],['MINDLOGO','INTRO','TITLE','MOV_INTRO'])
        self.assertFalse(self.result['demo_outro']['startup'])
    def test_periods(self):
        self.assertEqual(self.result['clips']['MINDLOGO']['frame_period_us'],66666)
        for name in ['INTRO','MOV_INTRO','MOV_DEMO']:
            self.assertEqual(self.result['clips'][name]['frame_period_us'],100000)
    def test_title_clock_and_position(self):
        self.assertEqual(self.result['title']['origin'],[0,0])
        self.assertEqual(self.result['title']['nominal_hold_seconds'],2.6)
    def test_wrong_executable(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'R.EXE').write_bytes(b'not authoritative')
            with self.assertRaises(LEError):extract(Path(d))
    def test_wrong_title(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'R.EXE').write_bytes((self.root/'R.EXE').read_bytes())
            (Path(d)/'TITLE.PCX').write_bytes(b'not authoritative')
            with self.assertRaises(LEError):extract(Path(d))
    def test_original_resource_directory(self):
        self.assertEqual(self.result['movie_directory'], 'mov\\')
        self.assertEqual(self.result['movie_directory_assignment'], 0xba89)
    def test_wrong_resource_config(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('R.EXE','TITLE.PCX'):
                (Path(d)/name).write_bytes((self.root/name).read_bytes())
            (Path(d)/'RESOURCE.CFG').write_bytes(b'textures\\\r\nsounds\\\r\nwrong\\\r\n')
            with self.assertRaises(LEError):extract(Path(d))
if __name__=='__main__':unittest.main(verbosity=2)
