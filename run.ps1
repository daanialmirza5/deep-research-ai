<#
.SYNOPSIS
    Starts the entire DeepResearch AI stack locally, no Docker required.

.DESCRIPTION
    Brings up Postgres+pgvector (via pgserver), Redis, MinIO, the FastAPI
    backend, a Celery worker, and the Next.js frontend - each in its own
    visible PowerShell window so you can watch its logs - then opens your
    browser to the app. Safe to re-run: Postgres data persists in ./pgdata,
    migrations/seeding are idempotent.

    One-time setup (venv + deps + portable Redis/MinIO binaries) must already
    be done - see docs/installation.md - before this script's shortcuts work.

.NOTES
    Requires Ollama running separately (ollama serve, with a model pulled)
    for AI_PROVIDER=ollama, the default this script sets. Use your own
    OPENAI_API_KEY/ANTHROPIC_API_KEY instead by editing the $env:AI_PROVIDER
    block below.
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$pidFile = Join-Path $root ".tools\run-pids.txt"

function Test-Prereqs {
    if (-not (Test-Path $venvPython)) {
        Write-Host "Missing backend/.venv - run this first:" -ForegroundColor Red
        Write-Host "  cd backend; uv venv; uv pip install -e `".[dev,local]`"; uv pip install pgserver"
        exit 1
    }
    if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
        Write-Host "Missing frontend/node_modules - run this first:" -ForegroundColor Red
        Write-Host "  cd frontend; npm install"
        exit 1
    }
    if (-not (Test-Path (Join-Path $root ".tools\minio.exe"))) {
        Write-Host "Missing .tools/minio.exe - see docs/installation.md section 4 Option B." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path (Join-Path $root ".tools\redis\redis-server.exe"))) {
        Write-Host "Missing .tools/redis/redis-server.exe - see docs/installation.md section 4 Option B." -ForegroundColor Red
        exit 1
    }
}

Test-Prereqs
New-Item -ItemType Directory -Force -Path (Join-Path $root ".tools") | Out-Null
"" | Out-File -FilePath $pidFile -Encoding utf8   # reset PID log for this run

Write-Host "`n[1/6] Starting Postgres+pgvector..." -ForegroundColor Cyan
# psql's own harmless NOTICEs (e.g. "extension already exists, skipping") go
# to stderr; with $ErrorActionPreference = "Stop" in effect, capturing
# stderr via 2>&1 turns that single benign line into a terminating error,
# aborting the script even though start_postgres.py itself exits 0. Relaxed
# to Continue for just this one call.
$previousErrorPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$pgOutput = & $venvPython (Join-Path $root "scripts\start_postgres.py") 2>&1
$ErrorActionPreference = $previousErrorPreference
$pgOutput | ForEach-Object { Write-Host "  $_" }
$databaseUrl = ($pgOutput | Select-String "^DATABASE_URL=(.+)$").Matches.Groups[1].Value
if (-not $databaseUrl) {
    Write-Host "Failed to start Postgres - see output above." -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/6] Starting Redis..." -ForegroundColor Cyan
$redisProc = Start-Process -FilePath (Join-Path $root ".tools\redis\redis-server.exe") -ArgumentList "--port", "6379" -WindowStyle Normal -PassThru
"redis=$($redisProc.Id)" | Out-File -Append -FilePath $pidFile -Encoding utf8

Write-Host "[3/6] Starting MinIO..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path (Join-Path $root ".tools\miniodata") | Out-Null
# Built as a plain variable, not inline inside -ArgumentList @(...): PowerShell's
# array-literal parser does not honor a trailing + as line-continuation the way
# a normal statement does - it silently splits a multi-line concatenation into
# extra array elements instead of one string, which then desyncs the parser for
# everything after (caught only by actually running this script, not by reading
# it - every subsequent line looked like an unrelated syntax error until traced
# back here).
$minioCommand = "`$env:MINIO_ROOT_USER='dra_minio'; `$env:MINIO_ROOT_PASSWORD='change-me-8chars-min'; " + "& '$root\.tools\minio.exe' server '$root\.tools\miniodata'"
$minioProc = Start-Process powershell -ArgumentList @("-NoExit", "-Command", $minioCommand) -PassThru
"minio=$($minioProc.Id)" | Out-File -Append -FilePath $pidFile -Encoding utf8

Start-Sleep -Seconds 3

Write-Host "`n[4/6] Applying migrations + seeding agents..." -ForegroundColor Cyan
$env:DATABASE_URL = $databaseUrl
$env:PYTHONPATH = $root
Push-Location (Join-Path $root "backend")
& ".venv\Scripts\alembic.exe" upgrade head
& ".venv\Scripts\python.exe" -m app.scripts.seed
Pop-Location

$commonEnv = "`$env:DATABASE_URL='$databaseUrl'; `$env:PYTHONPATH='$root'; `$env:AI_PROVIDER='ollama'; `$env:OLLAMA_BASE_URL='http://localhost:11434'; `$env:OLLAMA_MODEL='llama3.2:1b'; `$env:EMBEDDING_PROVIDER='bge'; `$env:BGE_MODEL_NAME='BAAI/bge-large-en-v1.5'; `$env:EMBEDDING_DIMENSION='1024'; `$env:MAX_REVISION_LOOPS='2'; `$env:SECRET_KEY='local-dev-secret-change-me'; "

Write-Host "[5/6] Starting backend + Celery worker..." -ForegroundColor Cyan
$backendCommand = "$commonEnv Set-Location '$root\backend'; .venv\Scripts\uvicorn.exe app.main:app --reload"
$backendProc = Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCommand) -PassThru
"backend=$($backendProc.Id)" | Out-File -Append -FilePath $pidFile -Encoding utf8

$workerCommand = "$commonEnv Set-Location '$root\backend'; .venv\Scripts\celery.exe -A app.workers.celery_app worker --pool=solo --loglevel=info"
$workerProc = Start-Process powershell -ArgumentList @("-NoExit", "-Command", $workerCommand) -PassThru
"worker=$($workerProc.Id)" | Out-File -Append -FilePath $pidFile -Encoding utf8

Write-Host "[6/6] Starting frontend..." -ForegroundColor Cyan
$frontendCommand = "Set-Location '$root\frontend'; npm run dev"
$frontendProc = Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCommand) -PassThru
"frontend=$($frontendProc.Id)" | Out-File -Append -FilePath $pidFile -Encoding utf8

try {
    # 127.0.0.1, not "localhost": observed Invoke-WebRequest intermittently
    # fail against "localhost" (likely trying an IPv6 ::1 route first against
    # a server only listening on IPv4) even though the exact same service
    # answers curl/a fresh PowerShell session immediately - not reproducible
    # on demand, but reliably worked around by removing the DNS/IPv6 step
    # entirely and using the literal loopback address everywhere below.
    Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2 -UseBasicParsing | Out-Null
} catch {
    Write-Host "`nWARNING: Ollama doesn't seem to be running at 127.0.0.1:11434." -ForegroundColor Yellow
    Write-Host "Research sessions need it (or edit this script to use OPENAI_API_KEY/ANTHROPIC_API_KEY instead)." -ForegroundColor Yellow
}

Write-Host "`nWaiting for the backend to come up before opening the browser..." -ForegroundColor Cyan
# A totally fresh venv's first `uvicorn --reload` start takes noticeably longer
# than a warm one (Python importing torch/sentence-transformers for the first
# time, the --reload supervisor spawning its own worker process) - observed
# taking over 60s once, well past what a "just wait a few seconds" timeout
# would assume. 90 retries * 2s = up to 3 minutes before giving up.
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -UseBasicParsing | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($ready) {
    Start-Sleep -Seconds 3   # give the frontend dev server a moment too
    Start-Process "http://localhost:3000"
    Write-Host "`nEverything is up! http://localhost:3000" -ForegroundColor Green
} else {
    Write-Host "`nBackend didn't come up within 3 minutes - check its window for errors." -ForegroundColor Red
}

Write-Host "Run .\stop.ps1 to shut everything down cleanly.`n" -ForegroundColor Cyan
