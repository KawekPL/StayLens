param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logDirectory = Join-Path $projectRoot '.local'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install the Python environment first.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'artifacts\s02-v1\manifest.json'))) { throw 'Run S02 training first.' }
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$url = "http://127.0.0.1:$Port"
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    try {
        $health = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 3
        $openapi = Invoke-RestMethod -Uri "$url/openapi.json" -TimeoutSec 3
        if ($health.status -eq 'ok' -and $openapi.info.title -eq 'StayLens price API') {
            Write-Output "StayLens API already running: $url/docs"
            return
        }
    } catch { }
    throw "Port $Port is occupied. No process was stopped."
}
$apiProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'staylens.api:app', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'api.stdout.log') -RedirectStandardError (Join-Path $logDirectory 'api.stderr.log') -PassThru
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
