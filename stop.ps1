<#
.SYNOPSIS
    Stops everything run.ps1 started.

.DESCRIPTION
    Kills each service's full process tree (not just the wrapper window -
    Stop-Process on a "powershell -Command npm run dev" window only kills
    that shell, leaving the actual node.exe/uvicorn.exe/celery.exe child
    process running and still holding its port, unless children are found
    and killed too). Postgres (via pgserver) is a detached background
    process with no parent/child relationship to any of run.ps1's windows,
    so it's found separately, by matching this project's own ./pgdata path
    in its command line - deliberately not a blind Stop-Process -Name
    postgres, which would also kill an unrelated system-wide Postgres
    install if one happens to be running.
#>

$root = $PSScriptRoot
$pidFile = Join-Path $root ".tools\run-pids.txt"

function Stop-ProcessTree {
    param([int]$RootId)
    $toKill = [System.Collections.Generic.Queue[int]]::new()
    $toKill.Enqueue($RootId)
    $all = @()
    while ($toKill.Count -gt 0) {
        $current = $toKill.Dequeue()
        $all += $current
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$current" -ErrorAction SilentlyContinue
        foreach ($child in $children) { $toKill.Enqueue($child.ProcessId) }
    }
    foreach ($procId in $all) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

if (Test-Path $pidFile) {
    Get-Content $pidFile | Where-Object { $_ -match "=" } | ForEach-Object {
        $name, $procId = $_ -split "="
        if ($procId -and (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
            Write-Host "Stopping $name (pid $procId and its children)..." -ForegroundColor Cyan
            Stop-ProcessTree -RootId ([int]$procId)
        }
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
} else {
    Write-Host "No .tools/run-pids.txt found - nothing recorded from a run.ps1 session." -ForegroundColor Yellow
}

Write-Host "Stopping this project's Postgres..." -ForegroundColor Cyan
# Graceful shutdown (pg_ctl stop) first, not a force-kill: a force-killed
# Postgres never gets to checkpoint or mark itself as cleanly shut down, so
# the *next* start pays for full crash recovery (WAL replay + an fsync of
# the whole data directory - observed taking 30+ seconds on this machine)
# on top of Windows Defender routinely locking the freshly-touched log file
# for another ~30 seconds - together blowing past pgserver's own hardcoded
# 10-second start timeout, surfacing only as an opaque "Timeout starting
# server." on the next run.ps1, with nothing pointing back to this being the
# cause. See scripts/stop_postgres.py's own docstring for the full story.
$venvPython = Join-Path $root "backend\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython (Join-Path $root "scripts\stop_postgres.py")
}

# Fallback for anything pg_ctl didn't clean up (e.g. postmaster.pid was
# already stale, or pg_ctl itself timed out): Postgres on Windows runs its
# background workers (forkaux/forkbgworker/forkbackend/etc.) as real
# separate processes, children of the main postgres.exe matched below by its
# -D <pgdata> argument - Stop-ProcessTree (not a plain Stop-Process) is
# needed here for the same reason it's needed for the run.ps1-started
# services above, or these children survive as orphans holding the data
# directory's lock.
$pgdataPath = (Join-Path $root "pgdata").Replace("\", "/")
Get-CimInstance Win32_Process -Filter "Name='postgres.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$pgdataPath*" } |
    ForEach-Object {
        Write-Host "  pg_ctl didn't clean up pid $($_.ProcessId) - force-killing it and its workers"
        Stop-ProcessTree -RootId $_.ProcessId
    }

Write-Host "`nDone. Ollama (if running) was left alone - it's not something this project starts." -ForegroundColor Green
