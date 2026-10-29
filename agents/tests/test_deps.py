import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import deps  # noqa: E402


class DepProbeTests(unittest.TestCase):
    def test_kinds_report_honestly(self):
        self.assertEqual(deps.check(
            {'capability': 'X', 'name': 'json', 'kind': 'pip', 'detail': ''})['status'], 'ok')
        self.assertEqual(deps.check(
            {'capability': 'X', 'name': 'pico_nonexistent_pkg_xyz', 'kind': 'pip',
             'detail': ''})['status'], 'missing')
        self.assertEqual(deps.check(
            {'capability': 'X', 'name': 'sh', 'kind': 'binary', 'detail': ''})['status'], 'ok')
        self.assertEqual(deps.check(
            {'capability': 'X', 'name': 'pico_nonexistent_bin_xyz', 'kind': 'binary',
             'detail': ''})['status'], 'missing')
        with mock.patch.dict('os.environ', {'PICO_PROBE_T': '1'}):
            self.assertEqual(deps.check(
                {'capability': 'X', 'name': 'PICO_PROBE_T', 'kind': 'env',
                 'detail': ''})['status'], 'ok')
        with mock.patch.dict('os.environ', {}, clear=True):
            self.assertEqual(deps.check(
                {'capability': 'X', 'name': 'PICO_PROBE_T', 'kind': 'env',
                 'detail': ''})['status'], 'unconfigured')
        self.assertEqual(deps.check(
            {'capability': 'X', 'name': 'd', 'kind': 'decision', 'detail': ''})['status'],
            'unconfigured')
        self.assertEqual(deps.check(
            {'capability': 'X', 'name': 'l', 'kind': 'local', 'detail': ''})['status'], 'ok')

    def test_every_capability_lists_what_unlocks_it(self):
        for result in deps.check_all():
            self.assertTrue(result['detail'], result['name'])
            self.assertIn(result['status'], ('ok', 'missing', 'unconfigured'))
        names = {r['capability'] for r in deps.check_all()}
        for cap in ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08',
                    'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08',
                    'D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08',
                    'D09', 'D10'):
            self.assertIn(cap, names)

    def test_labels_match_backlog_meanings(self):
        by_cap = {}
        for spec in deps.DEPENDENCIES:
            by_cap.setdefault(spec['capability'], []).append(spec['name'])
        # Spot checks against Pico_Real_Work_Backlog.md wording.
        self.assertIn('local-search', by_cap['B01'])
        self.assertIn('tesseract', by_cap['B05'])
        self.assertIn('local-archives', by_cap['B06'])
        self.assertIn('git', by_cap['C05'])
        self.assertIn('playwright', by_cap['C07'])
        self.assertIn('docx', by_cap['D01'])
        self.assertIn('libreoffice', by_cap['D03'])
        self.assertIn('openpyxl', by_cap['D08'])
        self.assertIn('pptx', by_cap['D10'])
        self.assertNotIn('GOOGLE_CALENDAR_OAUTH', by_cap.get('C01', []))

    def test_removed_renderer_reports_setup_requirement(self):
        spec = deps.find_spec('libreoffice')
        with mock.patch('shutil.which', return_value=None):
            missing = deps.check(spec)
        self.assertEqual(missing['status'], 'missing')
        self.assertIn('install LibreOffice', missing['detail'])
        restored = deps.check(spec)
        self.assertIn(restored['status'], ('ok', 'missing'))
        if restored['status'] == 'ok':
            self.assertNotIn('install LibreOffice', restored['detail'])

    def test_install_refuses_without_flag_unknown_and_non_pip(self):
        calls = []
        specs = ({'capability': 'X', 'name': 'json', 'kind': 'pip', 'detail': ''},
                 {'capability': 'X', 'name': 'sh', 'kind': 'binary', 'detail': 'd'})
        result = deps.install('json', specs=specs,
                              runner=lambda *a, **k: calls.append(a))
        self.assertFalse(result['installed'])
        self.assertIn('--allow-install', result['error'])
        result = deps.install('nope', allow=True, specs=specs,
                              runner=lambda *a, **k: calls.append(a))
        self.assertIn('unknown dependency', result['error'])
        result = deps.install('sh', allow=True, specs=specs,
                              runner=lambda *a, **k: calls.append(a))
        self.assertIn('not installable', result['error'])
        self.assertEqual(calls, [])

    def test_install_claims_complete_only_when_probe_passes(self):
        ok_proc = subprocess.CompletedProcess([], 0, b'', b'')
        specs = ({'capability': 'X', 'name': 'json', 'kind': 'pip', 'detail': ''},)
        calls = []
        result = deps.install(
            'json', allow=True, specs=specs,
            runner=lambda *a, **k: (calls.append(a), ok_proc)[1])
        self.assertTrue(result['installed'])
        self.assertEqual(result['status'], 'ok')
        argv = calls[0][0]
        self.assertEqual(argv[1:], ['-m', 'pip', 'install', 'json'])
        bad_proc = subprocess.CompletedProcess([], 1, b'', b'nope')
        result = deps.install(
            'json', allow=True, specs=specs,
            runner=lambda *a, **k: bad_proc)
        self.assertFalse(result['installed'])
        self.assertIn('pip install json failed', result['error'])
        missing_specs = ({'capability': 'X', 'name': 'pico_nonexistent_pkg_xyz',
                           'kind': 'pip', 'detail': ''},)
        result = deps.install('pico_nonexistent_pkg_xyz', allow=True,
                              specs=missing_specs,
                              runner=lambda *a, **k: ok_proc)
        self.assertFalse(result['installed'])
        self.assertIn('probe still missing', result['error'])

    def test_cli_json_parses(self):
        proc = subprocess.run(
            [sys.executable, str(Path(deps.__file__)), '--json'],
            capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        results = json.loads(proc.stdout)['results']
        self.assertGreater(len(results), 10)


if __name__ == '__main__':
    unittest.main()
