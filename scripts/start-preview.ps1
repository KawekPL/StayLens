param([switch]$OpenBrowser)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot 'frontend'
$viteEntry = Join-Path $frontendRoot 'node_modules\vite\bin\vite.js'
$runtimeDirectory = Join-Path $projectRoot '.local'
$previewUrl = 'http://127.0.0.1:5174/'

function Test-StayLensPreview {
    try {
        $response = Invoke-WebRequest -Uri $previewUrl -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -eq 200 -and $response.Content -match '<title>StayLens')
    } catch {
        return $false
    }
}

if (Test-StayLensPreview) {
    Write-Output "StayLens is already running: $previewUrl"
    if ($OpenBrowser) { Start-Process $previewUrl }
    exit 0
}

$listener = Get-NetTCPConnection -LocalPort 5174 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw 'Port 5174 is occupied by another service. No process was stopped.'
}
if (-not (Test-Path -LiteralPath $viteEntry)) {
    throw "Vite is not installed. Run npm.cmd ci in $frontendRoot first."
}

$nodeExecutable = (Get-Command node.exe -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
$stdoutPath = Join-Path $runtimeDirectory 'preview.stdout.log'
$stderrPath = Join-Path $runtimeDirectory 'preview.stderr.log'

# A separate hidden Windows process keeps the preview independent of the
# temporary command session. Bind to loopback only, not to the local network.
$previewProcess = Start-Process -FilePath $nodeExecutable `
    -ArgumentList @("`"$viteEntry`"", '--host', '127.0.0.1', '--port', '5174', '--strictPort') `
    -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if (Test-StayLensPreview) {
        @{
            processId = $previewProcess.Id
            projectRoot = $projectRoot
            url = $previewUrl
            startedAt = (Get-Date).ToUniversalTime().ToString('o')
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDirectory 'preview-process.json') -Encoding UTF8
        Write-Output "StayLens is running: $previewUrl (PID $($previewProcess.Id))"
        if ($OpenBrowser) { Start-Process $previewUrl }
        exit 0
    }
    $previewProcess.Refresh()
    if ($previewProcess.HasExited) { break }
    Start-Sleep -Milliseconds 300
}

$startupError = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw } else { 'No startup log.' }
throw "StayLens did not become ready. See $stderrPath. $startupError"
