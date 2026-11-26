# Safe independent dashboard-only rollout. No CFD process or campaign mutation.
$ErrorActionPreference = 'Stop'
$homeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$listen = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $listen) { throw 'Port 8787 is not currently listening. Refusing blind restart.' }
$record = Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)"
if (-not $record -or $record.Name -notlike 'python*' -or $record.CommandLine -notlike '*flap_control\project_dashboard\server.py*') {
    throw 'Unrecognized port owner; dashboard not modified.'
}
$stage = Invoke-RestMethod 'http://127.0.0.1:8788/api/ramp' -TimeoutSec 8
if ($stage.read_only -ne $true -or $stage.experiment_id -ne 'RAMP_C0_PLUS2_S5_20261103') {
    throw 'Staging validation failed; deployment cancelled.'
}
Write-Output "Preflight OK: dashboard PID $($listen.OwningProcess); staging has $($stage.rows) native samples."
& "$homeDir\stop_dashboard.ps1"
& "$homeDir\start_dashboard.ps1"
$h = Invoke-RestMethod 'http://127.0.0.1:8787/api/health' -TimeoutSec 8
$r = Invoke-RestMethod 'http://127.0.0.1:8787/api/ramp' -TimeoutSec 12
if ($h.service -ne 'ok' -or $h.read_only -ne $true -or $r.experiment_id -ne 'RAMP_C0_PLUS2_S5_20261103' -or $r.rows -lt 5) {
    throw 'New application health/data check failed. Staging on 8788 remains available.'
}
Write-Output "DEPLOYED: local= http://127.0.0.1:8787 | native rows=$($r.rows) | status=$($r.state)"
