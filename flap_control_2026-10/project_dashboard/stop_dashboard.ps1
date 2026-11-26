# Stop this dashboard only, never any STAR-CCM+ or CFD process.
$ErrorActionPreference='Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$file = Join-Path $dir 'dashboard.pid'
if (-not (Test-Path $file)) { Write-Output "Dashboard PID file absent."; exit 0 }
$idText = (Get-Content $file -Raw).Trim()
if ($idText -notmatch '^\d+$') { throw "Invalid dashboard PID file" }
$pidNumber = [int]$idText
$record = Get-CimInstance Win32_Process -Filter "ProcessId=$pidNumber"
if (-not $record) { Remove-Item -LiteralPath $file; Write-Output "Dashboard was not running."; exit 0 }
if (-not ($record.Name -like 'python*' -and $record.CommandLine -like '*flap_control\project_dashboard\server.py*')) {
  throw "PID not owned by this dashboard. Refusing to stop it."
}
Stop-Process -Id $pidNumber -ErrorAction Stop
Remove-Item -LiteralPath $file
Write-Output "Stopped dashboard process $pidNumber (not CFD)."
