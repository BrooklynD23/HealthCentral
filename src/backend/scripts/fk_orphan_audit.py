"""Report-only FK orphan audit (SQL-FK-001). Never deletes, never opens a live vault.

  python scripts/fk_orphan_audit.py --master
  python scripts/fk_orphan_audit.py --profile <id> --source <data dir containing vaults/<id>> [--password PW]

--source is a COPY SOURCE: it is copied to a tempdir and the copy is audited.
Exit 0 clean, 1 on any enforced orphan, 2 on refused/invalid usage.
"""
import argparse
import asyncio
import getpass
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _report(findings, checks) -> int:
    by_id = {f.check_id: f for f in findings}
    enforced = [c for c in checks if c.enforced]
    logical = [c for c in checks if not c.enforced]
    bad = 0
    for title, group in (("", enforced), ("INFORMATIONAL (no constraint)", logical)):
        if not group:
            continue
        if title:
            print(f"\n{title}")
        for c in group:
            f = by_id.get(c.check_id)
            head = f"{c.check_id} {c.child_table}.{c.child_column}→{c.parent_table}.{c.parent_column}"
            if f:
                print(f"{head}: {f.count} orphans ({', '.join(f.sample_ids)}{', ...' if f.count > len(f.sample_ids) else ''})")
                bad += c.enforced
            else:
                print(f"{head}: 0 orphans")
    return 1 if bad else 0


def _master() -> int:
    from core.config import settings
    from core.fk_audit import MASTER_CHECKS, find_orphans_dbapi

    path = Path(settings.database_url.split("///", 1)[1])
    if not path.exists():
        print(f"master DB not found at {path}; nothing to audit")
        return 0
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return _report(find_orphans_dbapi(conn, MASTER_CHECKS), MASTER_CHECKS)
    finally:
        conn.close()


async def _profile(profile_id: str, password: str) -> int:
    from core.fk_audit import LOGICAL_CHECKS, PROFILE_CHECKS, find_orphans
    from core.profile_database import get_profile_db_manager

    manager = get_profile_db_manager()
    checks = PROFILE_CHECKS + LOGICAL_CHECKS
    try:
        connection = await manager.open_profile_database(profile_id, password)
        async with connection.get_session() as session:
            return _report(await find_orphans(session, checks), checks)
    finally:
        await manager.close_all()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", action="store_true")
    ap.add_argument("--profile")
    ap.add_argument("--source")
    ap.add_argument("--password")
    a = ap.parse_args()
    if a.master == bool(a.profile):
        ap.error("pick exactly one of --master / --profile")
    if a.master:
        return _master()
    if not a.source:
        ap.error("--profile needs --source (a copy of the data dir)")

    src = Path(a.source).resolve()
    from core.config import settings  # real settings, before any override

    if src == settings.app_data_path.resolve():
        print(f"refusing: --source is the live data dir ({src}); copy it elsewhere first")
        return 2
    if not (src / "vaults" / a.profile).is_dir():
        print(f"no vault at {src / 'vaults' / a.profile}")
        return 2
    password = a.password if a.password is not None else getpass.getpass("vault password: ")

    with tempfile.TemporaryDirectory(prefix="fk-audit-") as tmp:
        shutil.copytree(src, tmp, dirs_exist_ok=True)
        # app_data_path is a read-only property of the already-built settings;
        # server mode derives it from sqlite_database_path, so patch that field.
        settings.app_mode = "server"
        settings.sqlite_database_path = str(Path(tmp) / "asclexis.db")
        assert Path(settings.app_data_path).resolve() == Path(tmp).resolve()
        return asyncio.run(_profile(a.profile, password))


if __name__ == "__main__":
    sys.exit(main())
