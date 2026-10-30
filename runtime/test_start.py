"""Check portable bootstrap behavior without credentials or a running client."""
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from start import prepare


class BootstrapTest(unittest.TestCase):
    def test_cpu_and_gpu_preferences_preserve_account_identity(self):
        config = Path(__file__).resolve().parents[1] / 'config'
        for gpu in (False, True):
            with self.subTest(gpu=gpu), tempfile.TemporaryDirectory() as folder:
                data = Path(folder)
                identity = data / 'acct_mgr_url.xml'
                identity.write_text('existing account-manager identity')
                prepare(data, config, 2 * 1024**3, 16 * 1024**3, gpu)
                prefs = ET.parse(data / 'global_prefs_override.xml').getroot()
                self.assertEqual(prefs.findtext('leave_apps_in_memory'), '1')
                for name in ('ram_max_used_busy_pct', 'ram_max_used_idle_pct'):
                    self.assertEqual(float(prefs.findtext(name)), 10.9375)
                options = ET.parse(data / 'cc_config.xml').getroot().find('options')
                self.assertEqual(options.findtext('no_gpus'), '0' if gpu else '1')
                self.assertEqual(options.findtext('ncpus'), '1' if gpu else '2')
                self.assertEqual(identity.read_text(), 'existing account-manager identity')

    def test_invalid_memory_budget_does_not_overwrite_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            existing = data / 'cc_config.xml'
            existing.write_text('existing configuration')
            for limit in (0, 256 * 1024**2):
                with self.assertRaises(ValueError):
                    prepare(data, data, limit, 16 * 1024**3, False)
            self.assertEqual(existing.read_text(), 'existing configuration')


if __name__ == '__main__':
    unittest.main()
