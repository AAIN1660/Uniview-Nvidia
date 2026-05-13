"""
Load Backend/unified.env into the process, then run the NAT CLI (same argv as `nat`).

Usage (from Backend):
  .\\.venv_nat\\Scripts\\python.exe run_nat_serve.py serve --config_file src/unified_nat_autogen/configs/config.yml --port 8090

Or use run_nat_serve.ps1 on Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _backend_root() -> Path:
    return Path(__file__).resolve().parent


def _nat_executable(backend: Path) -> Path:
    if sys.platform == "win32":
        return backend / ".venv_nat" / "Scripts" / "nat.exe"
    return backend / ".venv_nat" / "bin" / "nat"


def main() -> int:
    backend = _backend_root()
    os.chdir(backend)

    try:
        from dotenv import load_dotenv
    except ImportError:
        print("run_nat_serve: install python-dotenv in .venv_nat", file=sys.stderr)
        return 1

    unified = backend / "unified.env"
    if unified.is_file():
        load_dotenv(unified, override=False)
    else:
        print(f"run_nat_serve: warning: {unified} not found", file=sys.stderr)

    nat = _nat_executable(backend)
    if not nat.is_file():
        print(f"run_nat_serve: nat not found at {nat}", file=sys.stderr)
        return 1

    argv_rest = sys.argv[1:]
    if not argv_rest:
        print(
            "run_nat_serve: pass NAT args, e.g. "
            "serve --config_file src/unified_nat_autogen/configs/config.yml --port 8090",
            file=sys.stderr,
        )
        return 1

    return subprocess.call([str(nat), *argv_rest])


if __name__ == "__main__":
    raise SystemExit(main())
