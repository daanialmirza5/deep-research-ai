"""Starts (or reconnects to) a real, persistent Postgres+pgvector instance for
local dev — no Docker, no system install. Safe to run repeatedly: `pgserver`
reuses the existing data directory instead of recreating it, and
`CREATE EXTENSION IF NOT EXISTS` is idempotent.

`cleanup_mode=None` is what makes the server outlive this script: pgserver's
default cleanup mode stops the server when the Python object is garbage
collected (i.e. when this process exits), which is wrong for a background
service other processes (uvicorn, the Celery worker, `alembic`) need to keep
reaching after this script has already finished running.

Prints DATABASE_URL=<uri> on its own line so run.ps1 can capture it.
"""

import pathlib

import psutil

import pgserver

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PGDATA = PROJECT_ROOT / "pgdata"
PGDATA.mkdir(parents=True, exist_ok=True)


def _clear_stale_pidfile() -> None:
    """A postmaster.pid left behind by an unclean shutdown (a crashed
    terminal, a forced reboot, or — caught live — stop.ps1 once only killing
    Postgres's main process and not its Windows worker sub-processes) makes
    the next start attempt hang until pgserver's own timeout, with no
    indication why. If the PID it records isn't actually a running postgres
    process anymore, it's safe to remove before trying to start."""
    pidfile = PGDATA / "postmaster.pid"
    if not pidfile.exists():
        return
    try:
        pid = int(pidfile.read_text().splitlines()[0])
    except (ValueError, IndexError):
        pidfile.unlink()
        return
    if not (psutil.pid_exists(pid) and "postgres" in psutil.Process(pid).name().lower()):
        pidfile.unlink()


_clear_stale_pidfile()
srv = pgserver.get_server(PGDATA, cleanup_mode=None)
srv.psql("CREATE EXTENSION IF NOT EXISTS vector;")

uri = srv.get_uri().replace("postgresql://", "postgresql+asyncpg://")
print(f"DATABASE_URL={uri}")
print(f"PID={srv.get_pid()}")
