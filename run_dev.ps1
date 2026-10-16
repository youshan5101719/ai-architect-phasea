# FastAPI dev server with reliable Agent console logs (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Stop-UvicornOrphans {
    Write-Host "==> Stopping uvicorn / orphaned reload workers..." -ForegroundColor Yellow
    $pythonProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue
    foreach ($proc in $pythonProcs) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        $isUvicorn = $cmd -match "uvicorn" -or $cmd -match "main:app"
        $isOrphanWorker = $cmd -match "multiprocessing\.spawn" -and $cmd -match "spawn_main"
        if ($isUvicorn -or $isOrphanWorker) {
            Write-Host "    taskkill /PID $($proc.ProcessId) /F /T  ($cmd)"
            cmd /c "taskkill /PID $($proc.ProcessId) /F /T" 2>$null | Out-Null
        }
    }
}

function Stop-PortListeners {
    param([int]$Port = 8000)

    Write-Host "==> Stopping listeners on port $Port..." -ForegroundColor Yellow
    for ($i = 1; $i -le 3; $i++) {
        $pids = @()
        netstat -ano | Select-String "127.0.0.1:$Port\s+.*LISTENING" | ForEach-Object {
            $parts = ($_.Line -split '\s+') | Where-Object { $_ -ne '' }
            $procId = [int]$parts[-1]
            if ($procId -gt 0) { $pids += $procId }
        }
        foreach ($procId in ($pids | Select-Object -Unique)) {
            Write-Host "    taskkill /PID $procId /F /T"
            cmd /c "taskkill /PID $procId /F /T" 2>$null | Out-Null
        }
        Start-Sleep -Seconds 1
    }
}

Stop-UvicornOrphans
Stop-PortListeners -Port 8000
Start-Sleep -Seconds 1

$left = netstat -ano | Select-String "127.0.0.1:8000\s+.*LISTENING"
if ($left) {
    Write-Host "WARNING: Port 8000 still shows LISTENING (may be stale netstat PIDs)." -ForegroundColor Yellow
    Write-Host "         Trying orphan cleanup again..." -ForegroundColor Yellow
    Stop-UvicornOrphans
    Start-Sleep -Seconds 2
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "==> Starting uvicorn (single process, no --reload)" -ForegroundColor Green
Write-Host "    Agent trace file: $PSScriptRoot\agent.trace.log"
Write-Host "    Docs: http://127.0.0.1:8000/docs"
Write-Host ""

python -m uvicorn main:app `
    --host 127.0.0.1 `
    --port 8000 `
    --log-level info `
    --access-log
