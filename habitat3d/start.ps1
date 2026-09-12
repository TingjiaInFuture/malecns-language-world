param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$HabitatRoot = $PSScriptRoot
$HabitatPython = Join-Path (Split-Path $HabitatRoot -Parent) '.venv\Scripts\python.exe'
$HabitatState = Join-Path $HabitatRoot 'state'
$HabitatUrl = 'http://127.0.0.1:8765'
New-Item -ItemType Directory -Force -Path $HabitatState | Out-Null
$HabitatReady = $false
try {
    $HabitatHealth = Invoke-RestMethod "$HabitatUrl/api/health" -TimeoutSec 2
    if ($HabitatHealth.app -ne 'malecns-habitat') { throw 'Port 8765 belongs to another application.' }
    if (-not $HabitatHealth.ok) { throw 'Existing habitat has an error. Inspect state/server.log.' }
    if ($HabitatHealth.schema -ne 'habitat3d/2') { throw 'Existing server uses an obsolete controller.' }
    if ($HabitatHealth.mode -ne 'full') { throw 'Existing service is not the required full graph mode.' }
    $HabitatReady = $true
} catch {
    if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { throw }
}
if (-not $HabitatReady) {
    if (-not (Test-Path -LiteralPath $HabitatPython)) { throw "Missing Python environment: $HabitatPython" }
    $HabitatProcess = Start-Process -FilePath $HabitatPython -ArgumentList @('-u', ('"' + (Join-Path $HabitatRoot 'server.py') + '"'), '--port', '8765') -WorkingDirectory $HabitatRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $HabitatState 'server.log') -RedirectStandardError (Join-Path $HabitatState 'server.err.log') -PassThru
    $HabitatProcess.Id | Set-Content -LiteralPath (Join-Path $HabitatState 'launcher.pid')
    for ($HabitatAttempt = 0; $HabitatAttempt -lt 1200; $HabitatAttempt++) {
        Start-Sleep -Milliseconds 250
        try {
            $HabitatHealth = Invoke-RestMethod "$HabitatUrl/api/health" -TimeoutSec 1
            if ($HabitatHealth.app -eq 'malecns-habitat' -and $HabitatHealth.ok -and $HabitatHealth.mode -eq 'full') { $HabitatReady = $true; break }
        } catch { }
        if ($HabitatProcess.HasExited) { break }
    }
    if (-not $HabitatReady) { throw 'Habitat did not start. Inspect habitat3d/state/server.err.log.' }
}
if (-not $NoBrowser) {
    $HabitatChrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
    if (Test-Path -LiteralPath $HabitatChrome) { Start-Process -FilePath $HabitatChrome -ArgumentList "--app=$HabitatUrl" }
    else { Start-Process $HabitatUrl }
}
Write-Output "Micro Habitat: $HabitatUrl"
