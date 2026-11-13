"""Quick check: is sqlcipher3 installed and working?

    python scripts/check_sqlcipher.py              # module imports and reports a cipher version
    python scripts/check_sqlcipher.py --file-probe # also writes a keyed file and proves it is ciphertext

The file probe is what dev.ps1 runs before it lets a launch keep encryption on:
a module can import and still not encrypt, so it writes a real file, reads the
raw bytes, and checks that stdlib sqlite3 cannot open it. The probe file holds
only a fixed synthetic string and a random key, and is deleted afterwards.
"""
import os
import shutil
import sqlite3
import sys
import tempfile

PLAIN_HEADER = b"SQLite format 3\x00"
CANARY = "HC-PROBE-CANARY-not-patient-data"


def _fail(message):
    print("FAIL:", message, file=sys.stderr)
    sys.exit(1)


try:
    import sqlcipher3
except ImportError as e:
    print("FAIL: sqlcipher3 not installed:", e, file=sys.stderr)
    print(
        "Install (Windows): pip install --only-binary=:all: --no-deps --require-hashes "
        "-r src\\backend\\requirements-sqlcipher-win.txt",
        file=sys.stderr,
    )
    print("Install (Linux/WSL): pip install sqlcipher3-binary", file=sys.stderr)
    sys.exit(1)


def file_probe():
    folder = tempfile.mkdtemp(prefix="hc-sqlcipher-probe-")
    try:
        path = os.path.join(folder, "probe.db")
        key = os.urandom(32).hex()
        conn = sqlcipher3.connect(path)
        conn.execute("PRAGMA key = \"x'%s'\"" % key)
        conn.execute("CREATE TABLE probe (v TEXT)")
        conn.execute("INSERT INTO probe VALUES (?)", (CANARY,))
        conn.commit()
        conn.close()

        with open(path, "rb") as handle:
            raw = handle.read()
        if raw[:16] == PLAIN_HEADER:
            _fail("the keyed probe file is plaintext SQLite; this build does not encrypt")
        if CANARY.encode() in raw:
            _fail("the keyed probe file holds its data in plaintext; this build does not encrypt")
        plain = sqlite3.connect(path)
        try:
            try:
                plain.execute("SELECT count(*) FROM sqlite_master").fetchone()
            except sqlite3.DatabaseError:
                pass
            else:
                _fail("stdlib sqlite3 read the keyed probe file; it is plaintext")
        finally:
            plain.close()
        conn = sqlcipher3.connect(path)
        conn.execute("PRAGMA key = \"x'%s'\"" % key)
        row = conn.execute("SELECT v FROM probe").fetchone()
        conn.close()
        if not row or row[0] != CANARY:
            _fail("the keyed probe file did not reopen with its key")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("OK: file probe: the keyed file is ciphertext on disk and reopens with its key")


conn = sqlcipher3.connect(":memory:")
row = conn.execute("PRAGMA cipher_version").fetchone()
conn.close()
if not row or not row[0]:
    _fail("sqlcipher3 imports but reports no cipher version; it is not SQLCipher")
print("OK: SQLCipher version:", row[0])
if "--file-probe" in sys.argv[1:]:
    file_probe()
