param([switch]$OpenBrowser)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logs = Join-Path $projectRoot '.local'
$url = 'http://127.0.0.1:8080'

if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8080 jest zajety. Zamknij poprzedni podglad przed uruchomieniem nowego.'
}
if (-not (Test-Path -LiteralPath $python)) { throw 'Najpierw utworz .venv i zainstaluj zaleznosci z README.' }

Push-Location (Join-Path $projectRoot 'frontend')
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie zbudowac frontendu.' }
} finally { Pop-Location }

New-Item -ItemType Directory -Path $logs -Force | Out-Null
$process = Start-Process -FilePath $python -WindowStyle Hidden -PassThru `
    -WorkingDirectory $projectRoot `
    -ArgumentList @('-m', 'uvicorn', 'staylens.api:create_app', '--factory', '--host', '127.0.0.1', '--port', '8080', '--no-access-log') `
    -RedirectStandardOutput (Join-Path $logs 'preview.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'preview.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $logs 'preview.pid')

for ($attempt = 0; $attempt -lt 40; $attempt++) {
    $process.Refresh()
    if ($process.HasExited) { break }
    try {
        $health = Invoke-RestMethod "$url/health" -TimeoutSec 2
        if ($health.status -eq 'ok' -and $health.model_version -eq 's02-v1') {
            Write-Output "StayLens: $url (PID $($process.Id)). Zatrzymanie: Stop-Process -Id $($process.Id)"
            if ($OpenBrowser) { Start-Process $url }
            exit 0
        }
    } catch { Start-Sleep -Milliseconds 300 }
}
throw "Aplikacja nie wystartowala. Sprawdz $logs\preview.stderr.log"
