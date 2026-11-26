# NTNU Science dashboard launcher. Changes only this application's directory.
$ErrorActionPreference = "Stop"
$homeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $homeDir 'server.py'
$pidPath = Join-Path $homeDir 'dashboard.pid'
$localUrl = 'http://127.0.0.1:8787'
if (Test-Path $pidPath) {
  $previousPid = Get-Content $pidPath -Raw -ErrorAction SilentlyContinue
  if ($previousPid -match '^\s*\d+\s*$') {
    $existing = Get-Process -Id ([int]$previousPid.Trim()) -ErrorAction SilentlyContinue
    if ($existing -and ($existing.ProcessName -like 'python*')) {
      try {
        $response = Invoke-RestMethod -Uri ($localUrl + '/api/health') -TimeoutSec 3
        if ($response.service -eq 'ok' -and $response.read_only) {
          Write-Output "Dashboard already running at $localUrl (PID $previousPid)"
          exit 0
        }
      } catch {}
    }
  }
}
try {
  $probe = Invoke-RestMethod -Uri ($localUrl + '/api/health') -TimeoutSec 2
  if ($probe.service -eq 'ok' -and $probe.read_only) {
    Write-Output "Dashboard already running at $localUrl"
    exit 0
  }
  throw "Port 8787 belongs to an unrecognized service"
} catch {
  if ($_.Exception.Message -match 'unrecognized') { throw }
}
$pythonCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command python.exe -ErrorAction Stop }
$arguments = @('"' + $scriptPath + '"', '--port', '8787')
$proc = Start-Process -FilePath $pythonCmd.Source -ArgumentList $arguments -WorkingDirectory $homeDir -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $pidPath -Value $proc.Id -Encoding ascii
Start-Sleep -Milliseconds 950
try {
  $health = Invoke-RestMethod -Uri ($localUrl + '/api/health') -TimeoutSec 4
  if (-not $health.read_only) { throw 'Unexpected server response' }
  Write-Output "NTNU dashboard started: $localUrl (PID $($proc.Id))"
  Write-Output "Autobinds to Tailscale if available. No public listener is created."
} catch {
  Write-Warning "Process spawned, but health check failed. Check $homeDir\server.log"
  exit 1
}
