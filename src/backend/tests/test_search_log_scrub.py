"""SEARCH-LOG-SCRUB: the search term in GET /api/v1/search/?q=... must never reach a log.

uvicorn's access record is `'%s - "%s %s HTTP/%s" %d'` with the path *and* query string
as args[2]. These tests boot the real app under real uvicorn logging config and look
at two views of every record, because either alone can miss a leak:
  - the record itself (getMessage(), msg, repr(args), __dict__) on every logger, and
  - the formatted line the stream handler actually wrote.
The method, path and status must still be in the access line (the log is kept).
"""

from __future__ import annotations

import io
import logging
import logging.config
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import httpx
import pytest
import uvicorn
from uvicorn.config import LOGGING_CONFIG

BACKEND_DIR = Path(__file__).resolve().parents[1]
SEARCH_PATH = "/api/v1/search/"
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _term(label: str) -> str:
    return f"SLS{label}{uuid.uuid4().hex[:12]}"


def _access_lines(text: str, method: str, status: int) -> list[str]:
    return [
        ln for ln in text.splitlines()
        if f"{method} {SEARCH_PATH}" in ln and str(status) in ln
    ]


class _Capture(logging.Handler):
    """Keeps every view of every record that reaches it."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.views: list[str] = []
        self.args_seen: list[tuple] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
        except Exception as exc:  # a broken format must not hide a leak
            msg = f"<getMessage failed: {exc!r}>"
        self.views.append(f"{msg}\n{record.msg!r}\n{record.args!r}\n{record.__dict__!r}")
        if isinstance(record.args, tuple):
            self.args_seen.append(record.args)


class _LoggingSandbox:
    """Snapshot and restore the logging state uvicorn's dictConfig / fileConfig rewrite.

    Filters on the uvicorn loggers are cleared on entry, so a scrub filter present at
    the end of a test was installed by code the test ran, not left over from an earlier test.
    """

    def __enter__(self) -> "_LoggingSandbox":
        self._saved = {}
        for name in ("", *UVICORN_LOGGERS):
            lg = logging.getLogger(name)
            self._saved[name] = (list(lg.handlers), lg.level, lg.propagate, list(lg.filters), lg.disabled)
        for name in UVICORN_LOGGERS:
            logging.getLogger(name).filters[:] = []
        self._saved_disabled = {
            n: lg.disabled
            for n, lg in logging.root.manager.loggerDict.items()
            if isinstance(lg, logging.Logger)
        }
        self.capture = _Capture()
        self.stream = io.StringIO()
        self._added: list[logging.Logger] = []
        return self

    def attach(self) -> None:
        """Capture every logger and redirect stream handlers into a buffer.

        Call after uvicorn.Config(...): its dictConfig drops handlers on its own loggers.
        """
        loggers = [logging.getLogger()] + [
            lg for lg in logging.root.manager.loggerDict.values() if isinstance(lg, logging.Logger)
        ]
        for lg in loggers:
            if self.capture not in lg.handlers:
                lg.addHandler(self.capture)
                self._added.append(lg)
        for name in ("", *UVICORN_LOGGERS):
            for h in logging.getLogger(name).handlers:
                if isinstance(h, logging.StreamHandler) and h is not self.capture:
                    h.setStream(self.stream)

    def __exit__(self, *exc) -> None:
        for lg in self._added:
            lg.removeHandler(self.capture)
        for name, (handlers, level, propagate, filters, disabled) in self._saved.items():
            lg = logging.getLogger(name)
            lg.handlers[:] = handlers
            lg.setLevel(level)
            lg.propagate = propagate
            lg.filters[:] = filters
            lg.disabled = disabled
        for n, lg in logging.root.manager.loggerDict.items():
            if isinstance(lg, logging.Logger) and n in self._saved_disabled:
                lg.disabled = self._saved_disabled[n]


def _serve_and_probe(
    term: str, post_term: str, sandbox: _LoggingSandbox, after_create_app=None
) -> tuple[int, int]:
    """Run the real app under real uvicorn in-process; return (GET status, POST status).

    Order matches production: uvicorn configures logging first, then the app module
    is imported and create_app() runs. lifespan is off: it would open the real master
    DB (GATE-12). The access line is written by the protocol layer before any route
    runs, so the scrub is still exercised.
    """
    import main

    async def placeholder(scope, receive, send):  # replaced below, after create_app()
        raise RuntimeError("placeholder app must not serve")

    port = _free_port()
    config = uvicorn.Config(
        placeholder, host="127.0.0.1", port=port, lifespan="off", log_config=LOGGING_CONFIG
    )
    config.app = main.create_app()
    if after_create_app is not None:
        after_create_app()
    sandbox.attach()
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            assert thread.is_alive(), "uvicorn server thread died before starting"
            assert time.monotonic() < deadline, "uvicorn did not start within 30 s"
            time.sleep(0.05)
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(timeout=15) as client:
            got = client.get(f"{base}{SEARCH_PATH}", params={"q": term})
            posted = client.post(f"{base}{SEARCH_PATH}?q={post_term}&x=1")
        return got.status_code, posted.status_code
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        assert not thread.is_alive(), "uvicorn server thread did not stop"


def _assert_scrubbed(
    text: str, capture: _Capture | None, terms: list[str], statuses: tuple[int, int]
) -> None:
    for t in terms:
        assert t not in text, f"search term {t} reached the formatted log output:\n{text}"
        if capture is not None:
            for view in capture.views:
                assert t not in view, f"search term {t} reached a log record: {view[:300]}"
    get_lines = _access_lines(text, "GET", statuses[0])
    post_lines = _access_lines(text, "POST", statuses[1])
    assert get_lines, f"no 'GET {SEARCH_PATH} ... {statuses[0]}' access line (the log must be kept):\n{text}"
    assert post_lines, f"no 'POST {SEARCH_PATH} ... {statuses[1]}' access line (the log must be kept):\n{text}"
    for ln in get_lines + post_lines:
        assert "?" not in ln, f"query delimiter left in access line: {ln}"


def _access_args(capture: _Capture) -> list[tuple]:
    return [
        a for a in capture.args_seen
        if len(a) == 5 and isinstance(a[2], str) and a[2].startswith(SEARCH_PATH)
    ]


@pytest.fixture
def sandbox():
    with _LoggingSandbox() as sb:
        yield sb


def test_hc_sls_001_in_process_uvicorn_logs_no_search_term(sandbox):
    term, post_term = _term("get"), _term("post")
    statuses = _serve_and_probe(term, post_term, sandbox)
    _assert_scrubbed(sandbox.stream.getvalue(), sandbox.capture, [term, post_term], statuses)
    # Record side: the access args themselves carry only the bare path.
    recs = _access_args(sandbox.capture)
    assert len(recs) >= 2, f"expected the GET and POST access records, saw {recs}"
    assert all(a[2] == SEARCH_PATH for a in recs), recs


def _subprocess_env(tmp_path: Path, port: int, debug: bool) -> dict[str, str]:
    env = dict(os.environ)
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "logs").mkdir(exist_ok=True)
    env.update(
        {
            # Server mode keeps the master DB and logs out of the real src/backend/data.
            "APP_MODE": "server",
            "APP_ENV": "development",
            "SQLITE_DATABASE_PATH": str(tmp_path / "data" / "asclexis.db"),
            "LOG_FILE_PATH": str(tmp_path / "logs" / "asclexis.log"),
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "DEBUG": "true" if debug else "false",
            "HF_HUB_OFFLINE": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return env


def _stop_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)


def _run_server_subprocess(
    cmd: list[str], env: dict[str, str], port: int, out_file: Path
) -> tuple[str, tuple[int, int], str, str]:
    term, post_term = _term("sub"), _term("subpost")
    with out_file.open("wb") as out:
        proc = subprocess.Popen(
            cmd, cwd=BACKEND_DIR, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True
        )
    try:
        deadline = time.monotonic() + 120
        while "Application startup complete" not in out_file.read_text(errors="replace"):
            assert proc.poll() is None, f"server exited early:\n{out_file.read_text(errors='replace')}"
            assert time.monotonic() < deadline, f"no startup line in 120 s:\n{out_file.read_text(errors='replace')}"
            time.sleep(0.25)
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(timeout=30) as client:
            got = client.get(f"{base}{SEARCH_PATH}", params={"q": term})
            posted = client.post(f"{base}{SEARCH_PATH}?q={post_term}&x=1")
        time.sleep(0.5)  # let the access lines flush
    finally:
        _stop_group(proc)
    return out_file.read_text(errors="replace"), (got.status_code, posted.status_code), term, post_term


def test_hc_sls_002_python_m_uvicorn_logs_no_search_term(tmp_path):
    port = _free_port()
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)]
    text, statuses, term, post_term = _run_server_subprocess(
        cmd, _subprocess_env(tmp_path, port, debug=False), port, tmp_path / "uvicorn.out"
    )
    _assert_scrubbed(text, None, [term, post_term], statuses)


def test_hc_sls_003_python_main_py_reloader_logs_no_search_term(tmp_path):
    port = _free_port()
    cmd = [sys.executable, "main.py"]
    text, statuses, term, post_term = _run_server_subprocess(
        cmd, _subprocess_env(tmp_path, port, debug=True), port, tmp_path / "main.out"
    )
    assert "reloader" in text.lower(), (
        f"python main.py did not start the reloader (debug=true), so this case proves nothing:\n{text}"
    )
    _assert_scrubbed(text, None, [term, post_term], statuses)


def test_hc_sls_004_survives_alembic_fileconfig(sandbox):
    """alembic's env.py calls fileConfig(alembic.ini, disable_existing_loggers=False)
    on every vault open. The scrub must still hold after it."""
    ini = BACKEND_DIR / "alembic.ini"
    assert ini.is_file(), ini

    def alembic_runs():
        logging.config.fileConfig(str(ini), disable_existing_loggers=False)

    term, post_term = _term("fc"), _term("fcpost")
    statuses = _serve_and_probe(term, post_term, sandbox, after_create_app=alembic_runs)
    _assert_scrubbed(sandbox.stream.getvalue(), sandbox.capture, [term, post_term], statuses)
