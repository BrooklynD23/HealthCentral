"""Quick check: is sqlcipher3 installed and working?"""
import sys

try:
    import sqlcipher3
except ImportError as e:
    print("FAIL: sqlcipher3 not installed:", e, file=sys.stderr)
    print("Install (Linux/WSL): pip install sqlcipher3-binary", file=sys.stderr)
    sys.exit(1)

conn = sqlcipher3.connect(":memory:")
cur = conn.cursor()
cur.execute("PRAGMA cipher_version")
row = cur.fetchone()
conn.close()
print("OK: SQLCipher version:", row[0] if row else row)
