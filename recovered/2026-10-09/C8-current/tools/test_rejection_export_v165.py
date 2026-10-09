"""Export contracts for data read through FileAccess rather than ResourceLoader."""
from pathlib import Path
import configparser, fnmatch, unittest

ROOT = Path(__file__).resolve().parents[1]

class RejectionExportTests(unittest.TestCase):
    def test_production_fileaccess_data_in_every_current_export(self):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(ROOT / 'export_presets.cfg', encoding='utf-8')
        required = ['assets/ui/legacy_menu/legacy_scanner_v164.json',
                    'localization/languages.json', 'localization/en.json']
        for section in ('preset.1', 'preset.2'):
            include = cfg[section]['include_filter'].strip('"').split(',')
            exclude = cfg[section]['exclude_filter'].strip('"').split(',')
            for path in required:
                with self.subTest(preset=section, path=path):
                    self.assertTrue(any(fnmatch.fnmatchcase(path, p) for p in include), path)
                    self.assertFalse(any(fnmatch.fnmatchcase(path, p) for p in exclude), path)

if __name__ == '__main__':
    unittest.main()
