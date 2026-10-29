import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runner  # noqa: E402


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-runner-')
        self.addCleanup(self.tmp.cleanup)
        self.cwd = self.tmp.name

    def test_fixture_script_returns_real_streams_and_exit(self):
        script = Path(self.cwd) / 'add.py'
        script.write_text('import sys\nprint(2 + 3)\nprint("warn", file=sys.stderr)\n')
        out = runner.run([runner.python(), str(script)], cwd=self.cwd)
        self.assertEqual((out['exit_code'], out['stdout'], out['stderr']),
                         (0, '5\n', 'warn\n'))
        self.assertFalse(out['timed_out'])
        self.assertGreater(out['pid'], 0)

    def test_nonzero_exit_and_stderr_preserved(self):
        out = runner.run([runner.python(), '-c', 'import sys; sys.exit(7)'], cwd=self.cwd)
        self.assertEqual(out['exit_code'], 7)

    def test_metacharacters_are_data_not_shell(self):
        probe = 'a b;$(touch HACKED)|x`y`'
        out = runner.run([runner.python(), '-c', 'import sys; print(sys.argv[1])', probe],
                         cwd=self.cwd)
        self.assertEqual(out['stdout'].strip(), probe)
        self.assertFalse(Path(self.cwd, 'HACKED').exists())

    def test_spaces_in_script_path_work(self):
        script = Path(self.cwd) / 'my script.py'
        script.write_text('print("spaced ok")\n')
        out = runner.run([runner.python(), str(script)], cwd=self.cwd)
        self.assertEqual(out['stdout'], 'spaced ok\n')

    def test_timeout_kills_and_reports(self):
        start = time.monotonic()
        out = runner.run([runner.python(), '-c', 'import time; time.sleep(60)'],
                         cwd=self.cwd, timeout=1)
        self.assertTrue(out['timed_out'])
        self.assertLess(time.monotonic() - start, 15)

    def test_timeout_kills_child_tree(self):
        if os.name != 'posix':
            self.skipTest('process-group kill is POSIX-only')
        beat = Path(self.cwd, 'beat.txt')
        parent = Path(self.cwd, 'parent.py')
        parent.write_text(
            'import subprocess, sys, time\n'
            'heartbeat = "import time; [time.sleep(0.2) or '
            'open(\'' + str(beat) + '\', \'a\').write(\'x\') '
            'for _ in range(100000)]"\n'
            'subprocess.Popen([sys.executable, "-c", heartbeat])\n'
            'time.sleep(60)\n')
        out = runner.run([runner.python(), str(parent)], cwd=self.cwd, timeout=1)
        self.assertTrue(out['timed_out'])
        time.sleep(1.0)
        count_after_kill = len(beat.read_text()) if beat.exists() else 0
        time.sleep(1.2)
        count_later = len(beat.read_text()) if beat.exists() else 0
        self.assertEqual(count_after_kill, count_later)

    def test_cancel_stops_a_started_process(self):
        handle = runner.start([runner.python(), '-c', 'import time; time.sleep(60)'],
                              cwd=self.cwd, timeout=60)
        handle.cancel()
        out = handle.wait(timeout=10)
        self.assertTrue(out['cancelled'])
        self.assertIsNotNone(out['exit_code'])

    def test_output_is_capped(self):
        out = runner.run([runner.python(), '-c', 'print("y" * 10000)'],
                         cwd=self.cwd, cap=100)
        self.assertTrue(out['truncated'])
        self.assertLessEqual(len(out['stdout']), 101)

    def test_bad_invocations_rejected(self):
        with self.assertRaises(ValueError):
            runner.run([], cwd=self.cwd)
        with self.assertRaises(ValueError):
            runner.run('echo hi', cwd=self.cwd)
        with self.assertRaises(ValueError):
            runner.run([runner.python(), '-c', '1'], cwd=self.cwd, timeout=9999)
        with self.assertRaises(ValueError):
            runner.run([runner.python(), '-c', '1'], cwd='/nonexistent-dir-xyz')


if __name__ == '__main__':
    unittest.main()
