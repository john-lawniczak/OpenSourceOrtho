"""Small cross-process lock for local registry read/modify/write transactions."""
from contextlib import contextmanager
import os
from pathlib import Path
from threading import RLock

_THREAD_LOCK = RLock()


@contextmanager
def exclusive_file_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _THREAD_LOCK, path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
