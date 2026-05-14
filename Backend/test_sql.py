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

print("Connecting to", host, "as", username, "...")
conn = pyodbc.connect(cs)
row  = conn.cursor().execute("SELECT @@VERSION").fetchone()
print("CONNECTED. Server version:", row[0].splitlines()[0])
conn.close()