"""Bounded local process runner for the desktop helper (A06).

Structured subprocess execution only: explicit argv (never a shell
string), a workspace-contained cwd, timeout, per-stream output caps, PID
reporting and cancellation. Timeouts terminate the whole process tree on
POSIX (each child runs in its own process group); on Windows the child
itself is terminated. Children inherit the helper's environment (same
local user); callers may overlay extra variables.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 120
DEFAULT_OUTPUT_CAP = 64 * 1024


class ProcHandle:
    """A started child process with cancellation support (A13 primitive)."""

    def __init__(self, proc, cap):
        self._proc = proc
        self._cap = cap
        self.pid = proc.pid
        self.cancelled = False
        self.started = time.monotonic()

    def cancel(self):
        self.cancelled = True
        _kill_tree(self._proc)

    def wait(self, timeout=None):
        try:
            stdout, stderr = self._proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(self._proc)
            stdout, stderr = self._proc.communicate()
            return _result(self._proc, stdout, stderr, self._cap,
                           self.started, timed_out=True, cancelled=self.cancelled)
        return _result(self._proc, stdout, stderr, self._cap,
                       self.started, timed_out=False, cancelled=self.cancelled)


def _kill_tree(proc):
    try:
        if os.name == 'posix':
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (OSError, ProcessLookupError):
        pass


def _capped(raw, cap):
    return raw[:cap], len(raw) > cap


def _result(proc, stdout, stderr, cap, started, timed_out, cancelled):
    out, out_cut = _capped(stdout or b'', cap)
    err, err_cut = _capped(stderr or b'', cap)
    return {'exit_code': proc.returncode, 'pid': proc.pid,
            'stdout': out.decode('utf-8', errors='replace'),
            'stderr': err.decode('utf-8', errors='replace'),
            'truncated': out_cut or err_cut, 'timed_out': timed_out,
            'cancelled': cancelled, 'elapsed_ms': int((time.monotonic() - started) * 1000)}


def _check_args(argv, cwd, timeout, cap):
    if not isinstance(argv, (list, tuple)) or not argv:
        raise ValueError('argv must be a non-empty list.')
    if any(not isinstance(a, str) for a in argv):
        raise ValueError('argv entries must be strings.')
    if not argv[0]:
        raise ValueError('argv[0] must not be empty.')
    root = Path(cwd).expanduser().resolve() if cwd else Path.cwd()
    if not root.is_dir():
        raise ValueError('cwd is not a directory.')
    timeout = DEFAULT_TIMEOUT if timeout is None else int(timeout)
    if not 1 <= timeout <= MAX_TIMEOUT:
        raise ValueError(f'timeout must be 1-{MAX_TIMEOUT} seconds.')
    return list(argv), root, timeout, int(cap)


def start(argv, cwd=None, timeout=None, cap=DEFAULT_OUTPUT_CAP, env_add=None):
    """Start a child process; no shell involved. Returns a ProcHandle."""
    argv, root, timeout, cap = _check_args(argv, cwd, timeout, cap)
    env = dict(os.environ)
    for key, value in (env_add or {}).items():
        env[str(key)] = str(value)
    kwargs = {'cwd': str(root), 'env': env, 'stdout': subprocess.PIPE,
              'stderr': subprocess.PIPE}
    if os.name == 'posix':
        kwargs['start_new_session'] = True
    else:
        kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    try:
        proc = subprocess.Popen(argv, **kwargs)
    except OSError as error:
        raise ValueError(f'Could not start process: {error.strerror or error}.') from None
    handle = ProcHandle(proc, cap)
    handle.timeout = timeout
    return handle


def run(argv, cwd=None, timeout=None, cap=DEFAULT_OUTPUT_CAP, env_add=None):
    """Run to completion. Returns stdout/stderr/exit_code/timed_out/..."""
    handle = start(argv, cwd=cwd, timeout=timeout, cap=cap, env_add=env_add)
    return handle.wait(timeout=handle.timeout)


def python():
    """The current interpreter, for running fixture scripts portably."""
    return sys.executable
