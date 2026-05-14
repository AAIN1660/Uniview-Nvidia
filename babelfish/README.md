# Babelfish for PostgreSQL — local stack

This folder spins up a T-SQL-compatible database (Babelfish on PostgreSQL)
as a drop-in replacement for our Azure SQL Database. The application code
keeps using `pyodbc` + `ODBC Driver 18 for SQL Server` and keeps emitting
T-SQL (`TOP`, `[brackets]`, `OFFSET … FETCH NEXT`, etc.) — Babelfish
understands all of it.

Nothing in this stack is installed on Windows. Everything runs in Docker.

## What you get

| Service       | Port  | Purpose                                              |
| ------------- | ----- | ---------------------------------------------------- |
| `babelfish`   | 1433  | T-SQL endpoint (TDS). Backend connects here.         |
| `babelfish`   | 5432  | Underlying Postgres admin. Rarely needed.            |
| `adminer`     | 8080  | Browser admin UI — **Azure Portal equivalent**.      |
| `mssql-tools` | n/a   | On-demand container holding `sqlcmd`/`bcp`/`sqlpackage`. |

## Quick start

```powershell
cd "D:\Unified - Nvidia\Working Unified-Nvidia\Uniview-Quin-Eryl"
docker compose -f babelfish/docker-compose.yml up -d
```

Wait ~30 seconds for the healthcheck to go green, then:

* Open `http://localhost:8080` (Adminer).
* Pick **MS SQL (beta)** as the system.
* Server `babelfish`, User `sa`, Password `Strong!Passw0rd`, Database `unified`.

You should land on a Tables view that mirrors what you used to see in the
Azure Portal Query Editor.

## Where you do each Azure Portal task in this stack

| Azure Portal action                | Where to do it here                                  |
| ---------------------------------- | ---------------------------------------------------- |
| Browse table list                  | Adminer ? left sidebar after logging in.             |
| See column definitions             | Adminer ? click a table name.                        |
| Run an ad-hoc query (Query Editor) | Adminer ? **SQL command** in top-left.               |
| View / edit a row                  | Adminer ? **Select data** next to a table.           |
| Export schema or data              | Adminer ? **Export** in the sidebar.                 |
| Import a `.sql` script             | Adminer ? **Import** in the sidebar.                 |
| Look at container resource use     | `docker stats unified-babelfish`                     |
| View server logs                   | `docker logs -f unified-babelfish`                   |

## Migrating data from Azure SQL (no installs on Windows)

The `mssql-tools` profile container holds `sqlcmd`, `bcp` and (in a separate
image we pull on demand) `sqlpackage`. Run the export from inside the
container so nothing lands on your laptop.

```powershell
# 1. Bring the toolbox container up
docker compose -f babelfish/docker-compose.yml --profile tools up -d mssql-tools

# 2. Export the Azure SQL schema to a .dacpac using the official sqlpackage image
docker run --rm `
  -v "${PWD}/babelfish/migration:/work" `
  mcr.microsoft.com/sqlpackage:latest `
  /SqlPackage /Action:Extract `
  /SourceServerName:"uniview-database.database.windows.net" `
  /SourceDatabaseName:"uniview" `
  /SourceUser:"uniview" `
  /SourcePassword:"Affine@2025" `
  /TargetFile:"/work/uniview.dacpac"

# 3. Import the .dacpac into Babelfish
docker run --rm `
  -v "${PWD}/babelfish/migration:/work" `
  --network babelfish_default `
  mcr.microsoft.com/sqlpackage:latest `
  /SqlPackage /Action:Publish `
  /SourceFile:"/work/uniview.dacpac" `
  /TargetServerName:"babelfish,1433" `
  /TargetDatabaseName:"unified" `
  /TargetUser:"sa" `
  /TargetPassword:"Strong!Passw0rd" `
  /TargetTrustServerCertificate:True
```

If `sqlpackage`-based import surfaces incompatibilities, fall back to a plain
`.sql` schema script. Generate it via Adminer (Export) against Azure SQL, then
load it into Babelfish:

```powershell
docker exec -i unified-mssql-tools `
  /opt/mssql-tools/bin/sqlcmd -S babelfish,1433 -U sa -P 'Strong!Passw0rd' `
  -d unified -i /migration/schema.sql
```

## Compatibility check before migrating (recommended)

Before committing to Babelfish, run Babelfish Compass over your Azure SQL
schema dump. It produces an HTML report flagging anything Babelfish doesn't
support. Zero installs — runs in a Java container:

```powershell
# Download the jar once into babelfish/migration/
# https://github.com/babelfish-for-postgresql/babelfish_compass/releases

docker run --rm `
  -v "${PWD}/babelfish/migration:/work" -w /work `
  eclipse-temurin:17-jre `
  java -jar BabelfishCompass.jar -reportoption all uniview_schema.sql
```

Open the resulting `.html` file in your browser. Green/yellow ? safe to
migrate. Red on something the LLM frequently emits ? keep Azure SQL or
tweak that single rule in `Backend/utility/agent_prompts.py`.

## Rollback to Azure SQL

The Azure SQL connection logic is preserved (commented out) in:

* `Backend/unified.env`
* `Backend/utility/inference.py`
* `Backend/src/unified_nat_autogen/unified_tools.py`

To revert: comment out the Babelfish blocks and uncomment the Azure SQL
blocks. No code re-writing needed.

## Shutting down

```powershell
# Stop containers, keep data
docker compose -f babelfish/docker-compose.yml down

# Stop containers AND wipe the database volume
docker compose -f babelfish/docker-compose.yml down -v
```
