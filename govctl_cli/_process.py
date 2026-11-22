"""Process helpers that behave the same on POSIX and Windows.

``os.kill(pid, 0)`` is *not* a liveness probe on Windows — any signal other
than CTRL_C_EVENT/CTRL_BREAK_EVENT terminates the process, so checking a PID
would kill it. The helpers here use the Win32 API instead.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def pid_is_running(pid: int) -> bool:
    """Return True when *pid* exists and has not exited."""

    if os.name == "nt":  # pragma: no cover - exercised on Windows
        import ctypes

        synchronize = 0x00100000
        wait_timeout = 0x00000102
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(synchronize, False, int(pid))
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def spawn_detached(code: str, *, cwd: str | Path) -> int:
    """Run *code* in a detached Python process and return its PID.

    Windows has no ``fork``; a detached child started with
    ``DETACHED_PROCESS`` gives the same "survives the parent" behaviour that
    the double-fork daemonisation provides on POSIX.
    """

    kwargs: dict[str, object] = {}
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **kwargs,
    )
    return proc.pid
