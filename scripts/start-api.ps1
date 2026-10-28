param([int]$Port = 8001, [switch]$Restart)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logDirectory = Join-Path $projectRoot '.local'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install the Python environment first.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'artifacts\s02-v1\manifest.json'))) { throw 'Run S02 training first.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'data\prepared\s03\manifest.json'))) { throw 'Run scripts/build_catalog.py first.' }
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$url = "http://127.0.0.1:$Port"
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    $isStayLens = $false
    try {
        $health = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 3
        $openapi = Invoke-RestMethod -Uri "$url/openapi.json" -TimeoutSec 3
        $isStayLens = ($health.status -eq 'ok' -and $openapi.info.title -eq 'StayLens price API')
        if ($isStayLens -and $openapi.info.version -eq '0.3.0' -and -not $Restart) {
            Write-Output "StayLens API already running: $url/docs"
            return
        }
    } catch { }
    if (-not $isStayLens -or -not $Restart) { throw "Port $Port is occupied or running an older API. Use -Restart only for this StayLens service." }
    $record = Get-Content -LiteralPath (Join-Path $logDirectory 'api-process.json') -Raw | ConvertFrom-Json
    $launcher = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
    $worker = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener[0].OwningProcess)"
    if ($launcher.ExecutablePath -ne $pythonPath -or $launcher.CommandLine -notmatch 'uvicorn staylens\.(api|application):app' -or ($worker.ProcessId -ne $launcher.ProcessId -and $worker.ParentProcessId -ne $launcher.ProcessId)) { throw 'Process ownership check failed; no process stopped.' }
    Stop-Process -Id $worker.ProcessId -ErrorAction Stop
    if ($launcher.ProcessId -ne $worker.ProcessId -and (Get-Process -Id $launcher.ProcessId -ErrorAction SilentlyContinue)) { Stop-Process -Id $launcher.ProcessId -ErrorAction Stop }
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 200
    }
}
$apiProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'staylens.application:app', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'api.stdout.log') -RedirectStandardError (Join-Path $logDirectory 'api.stderr.log') -PassThru
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    $apiProcess.Refresh()
    if ($apiProcess.HasExited) { throw 'API failed to start; inspect .local/api.stderr.log.' }
    try {
        $health = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 2
        if ($health.status -eq 'ok') {
            @{ pid = $apiProcess.Id; url = $url; startedAt = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDirectory 'api-process.json') -Encoding utf8
            Write-Output "StayLens API ready: $url/docs (PID $($apiProcess.Id))"
            return
        }
    } catch { }
}
throw 'API readiness timeout; inspect .local/api.stderr.log.'
