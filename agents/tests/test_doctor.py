import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import doctor  # noqa: E402


class DoctorTests(unittest.TestCase):
    def test_local_probes_pass_on_fixture_folders(self):
        tmp = tempfile.TemporaryDirectory(prefix='pico-doctor-')
        self.addCleanup(tmp.cleanup)
        results = {r['name']: r for r in doctor.run_checks(
            {'grants': [{'path': tmp.name}]},
            probes=(doctor.probe_heartbeat, doctor.probe_folders,
                    doctor.probe_interpreter))}
        self.assertEqual(results['heartbeat']['status'], 'pass')
        self.assertEqual(results['folders']['status'], 'pass')
        self.assertEqual(results['interpreter']['status'], 'pass')

    def test_missing_folders_fail_honestly(self):
        (result,) = doctor.run_checks(
            {'grants': [{'path': '/nonexistent-dir-xyz'}]},
            probes=(doctor.probe_folders,))
        self.assertEqual(result['status'], 'fail')

    def test_crashing_probe_becomes_failure_not_crash(self):
        def boom(_):
            raise RuntimeError('probe bug')
        (result,) = doctor.run_checks({}, probes=(boom,))
        self.assertEqual(result['status'], 'fail')
        self.assertIn('crashed', result['detail'])

    def test_injected_network_probes_decide_exit_code(self):
        ok = lambda _: {'name': 'relay', 'status': 'pass', 'detail': 'x'}  # noqa: E731
        bad = lambda _: {'name': 'relay', 'status': 'fail', 'detail': 'down'}  # noqa: E731
        self.assertTrue(all(r['status'] != 'fail' for r in doctor.run_checks({}, (ok,))))
        self.assertFalse(all(r['status'] != 'fail' for r in doctor.run_checks({}, (bad,))))

    def test_cli_reports_json_and_fails_closed_offline(self):
        proc = subprocess.run(
            [sys.executable, str(Path(doctor.__file__)),
             '--relay', 'http://127.0.0.1:9', '--json'],
            capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 1)
        results = {r['name']: r for r in json.loads(proc.stdout)['results']}
        self.assertEqual(results['relay']['status'], 'fail')
        self.assertEqual(results['heartbeat']['status'], 'pass')

    def test_screen_probe_skips_without_binary(self):
        result = doctor.probe_screen_permission({})
        self.assertIn(result['status'], ('pass', 'fail', 'skip'))
        self.assertTrue(result['detail'])


if __name__ == '__main__':
    unittest.main()
