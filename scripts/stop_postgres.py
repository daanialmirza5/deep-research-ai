"""Gracefully stops this project's Postgres instance via pg_ctl, rather than
letting stop.ps1 fall back straight to force-killing the process tree.

This matters beyond tidiness: a force-killed Postgres has no chance to
checkpoint or mark itself as cleanly shut down, so the *next* start pays for
full crash recovery — a WAL replay plus an fsync of the whole data directory
(observed taking over 30 seconds on this machine) — on top of Windows
Defender routinely holding a lock on the freshly-touched log file for up to
another 30 seconds ("could not open file './log': sharing violation").
Together those blew straight through pgserver's own hardcoded 10-second
`pg_ctl` start timeout, surfacing only as an opaque "Timeout starting
server." with no indication a graceful stop would have avoided it entirely.
A clean shutdown here skips all of that on the next run.py.

Safe to run when nothing is running: exits quietly if there's no
postmaster.pid (nothing to stop) or pg_ctl reports it's already stopped.
"""

import pathlib
import subprocess
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PGDATA = PROJECT_ROOT / "pgdata"
PG_CTL = (
    PROJECT_ROOT
    / "backend"
    / ".venv"
    / "Lib"
    / "site-packages"
    / "pgserver"
    / "pginstall"
    / "bin"
    / "pg_ctl.exe"
)

if not (PGDATA / "postmaster.pid").exists():
    print("No postmaster.pid — Postgres isn't running, nothing to stop.")
    sys.exit(0)

if not PG_CTL.exists():
    print(f"pg_ctl.exe not found at {PG_CTL} — can't stop gracefully.")
    sys.exit(1)

result = subprocess.run(
    [str(PG_CTL), "-D", str(PGDATA), "-m", "fast", "-w", "-t", "30", "stop"],
    capture_output=True,
    text=True,
)
print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)
