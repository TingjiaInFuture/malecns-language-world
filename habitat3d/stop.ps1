$ErrorActionPreference = 'Stop'
$HabitatUrl = 'http://127.0.0.1:8765'
$HabitatHealth = Invoke-RestMethod "$HabitatUrl/api/health" -TimeoutSec 3
if ($HabitatHealth.app -ne 'malecns-habitat') { throw 'Port 8765 belongs to another application.' }
Invoke-RestMethod "$HabitatUrl/api/control" -Method Post -ContentType 'application/json' -Body '{"action":"shutdown"}' | Out-Null
Write-Output 'World saved. Local habitat service stopped.'
