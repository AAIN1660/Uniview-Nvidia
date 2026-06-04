"""Try common SQL Server host strings; run: python test_sql_hosts.py"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv("unified.env")

def _clean(v, default=""):
    v = (v or default).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v

user = _clean(os.getenv("SQL_USERNAME"), "sa")
password = _clean(os.getenv("SQL_PASSWORD"))
driver = _clean(os.getenv("SQL_DRIVER"), "ODBC Driver 18 for SQL Server")
database = _clean(os.getenv("SQL_DATABASE"), "master")

servers = [
    "localhost,1433",
    r"localhost\SQLEXPRESS",
    r"localhost\MSSQLSERVER",
    r"(local)\SQLEXPRESS",
    r".\SQLEXPRESS",
    r".\MSSQLSERVER",
    r"127.0.0.1\SQLEXPRESS",
]

print(f"User={user!r}  DB(test)={database!r}  Driver={driver!r}\n")
for host in servers:
    cs = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE=master;"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=5;"
    )
    try:
        conn = pyodbc.connect(cs)
        row = conn.cursor().execute("SELECT @@SERVERNAME, @@VERSION").fetchone()
        conn.close()
        print(f"OK  SERVER={host}")
        print(f"    @@SERVERNAME={row[0]}")
        print(f"    version={row[1].splitlines()[0][:80]}")
    except Exception as e:
        print(f"FAIL SERVER={host}")
        print(f"    {str(e)[:120]}")
