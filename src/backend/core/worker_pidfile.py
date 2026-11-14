"""PID file for the process that serves requests (WIN-ORPHAN-WORKER).

On Windows the venv ``python.exe`` is a stub and ``uvicorn --reload`` spawns the
serving worker as a child. If the launcher chain dies (window closed, a parent
killed) that worker can live on with no parent and no listening socket, still
holding profile vault handles. ``dev.ps1`` cannot see it through port listeners,
so the worker records itself here and the launcher reads the file.

Opt-in: only the launcher sets ``HC_WORKER_PIDFILE``; without it nothing is
written (tests, Linux ``dev.sh``, production). The lifespan runs only in the
serving process, never in uvicorn's reloader parent, so only the server writes.
The file lives outside the data dir (``logs/``) so no vault or backup picks it up.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from core.time import utcnow

logger = logging.getLogger(__name__)

PIDFILE_ENV = "HC_WORKER_PIDFILE"


def _data_dir() -> Path:
    from core.config import settings

    return Path(settings.app_data_path)


def _target() -> Path | None:
    raw = os.environ.get(PIDFILE_ENV, "").strip()
    return Path(raw) if raw else None


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def write_worker_pidfile() -> Path | None:
    """Record this process (pid, parent pid, start time). Returns the path, or None.

    Fail-soft: a failure is logged and never stops the app from booting.
    Written to a temp file in the same folder and renamed into place, so a reader
    sees either the previous complete file or the new complete one.
    """
    path = _target()
    if path is None:
        return None
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        if _inside(path, _data_dir()):
            logger.warning("Worker PID file refused: %s is inside the data directory", path)
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "started_unix": round(time.time(), 3),
            "started_at": utcnow().isoformat(timespec="seconds") + "Z",
        }
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        return path
    except Exception as exc:
        logger.warning("Worker PID file not written: %s", exc)
        return None
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def remove_worker_pidfile() -> None:
    """Remove the file on clean shutdown, but only if it still names this process.

    On a reload or restart the old worker can finish shutting down after the new
    one has written its own file; that file must survive.
    """
    path = _target()
    if path is None:
        return
    try:
        if json.loads(path.read_text(encoding="utf-8")).get("pid") == os.getpid():
            path.unlink()
    except (OSError, ValueError, AttributeError):
        pass
