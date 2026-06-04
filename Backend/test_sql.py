import os, urllib.parse, pyodbc
from dotenv import load_dotenv

load_dotenv("unified.env")
host     = os.getenv("SQL_HOST").strip("'\"")
database = os.getenv("SQL_DATABASE").strip("'\"")
username = os.getenv("SQL_USERNAME").strip("'\"")
password = os.getenv("SQL_PASSWORD").strip("'\"")
driver   = os.getenv("SQL_DRIVER").strip("'\"")

cs = (
    f"DRIVER={{{driver}}};"
    f"SERVER={host};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=10;"
)

print("Connecting to", host, "database", database, "as", username, "...")
try:
    conn = pyodbc.connect(cs)
except pyodbc.Error as e:
    msg = str(e)
    if "actively refused" in msg and "1433" in host:
        print("\nHint: Port 1433 is not open. Use SQL_HOST=localhost\\SQLEXPRESS if you use Express.")
    elif "Login failed for user" in msg:
        print("\nHint: Server reached but password/login is wrong. In SSMS: enable 'sa', set password to match SQL_PASSWORD in unified.env.")
    raise

row = conn.cursor().execute("SELECT @@SERVERNAME, @@VERSION").fetchone()
print("CONNECTED. Server:", row[0])
print("Version:", row[1].splitlines()[0])
conn.close()