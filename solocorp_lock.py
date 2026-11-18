"""Cross-platform advisory file locking.

POSIX uses ``fcntl.flock``. Windows has no ``flock``; ``msvcrt.locking``
provides byte-range locks on a file handle instead, which is close enough for
the lock files this repo uses (single byte at offset 0, held for the duration
of a read-modify-write section).

Usage is the same shape as ``fcntl``::

    from solocorp_lock import LOCK_EX, LOCK_NB, LOCK_UN, flock

    with path.open("a+b") as handle:
        flock(handle, LOCK_EX)
        try:
            ...
        finally:
            flock(handle, LOCK_UN)

``flock`` accepts either a file object or a raw file descriptor. On Windows a
``LOCK_SH`` request is treated as exclusive because ``msvcrt`` only offers
exclusive locks; every current caller either takes an exclusive lock or uses
the lock only to serialise access, so the stronger lock is safe.
"""

from __future__ import annotations

import errno
import os
import sys
import time
from typing import IO, Union

FileOrFd = Union[int, IO[bytes], IO[str]]

if sys.platform == "win32":  # pragma: no cover - exercised on Windows
    import msvcrt

    LOCK_SH = 1
    LOCK_EX = 2
    LOCK_NB = 4
    LOCK_UN = 8

    _LOCK_BYTES = 1
    _RETRY_SECONDS = 0.05
    _LOCK_BUSY_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}

    def _fileno(file_or_fd: FileOrFd) -> int:
        if isinstance(file_or_fd, int):
            return file_or_fd
        return file_or_fd.fileno()

    def flock(file_or_fd: FileOrFd, operation: int) -> None:
        fd = _fileno(file_or_fd)
        os.lseek(fd, 0, os.SEEK_SET)
        if operation & LOCK_UN:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, _LOCK_BYTES)
            return

        blocking = not (operation & LOCK_NB)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, _LOCK_BYTES)
                return
            except OSError as exc:
                if not blocking or exc.errno not in _LOCK_BUSY_ERRNOS:
                    raise
                time.sleep(_RETRY_SECONDS)

else:  # POSIX
    from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN, flock  # noqa: F401


__all__ = ["LOCK_EX", "LOCK_NB", "LOCK_SH", "LOCK_UN", "flock"]
