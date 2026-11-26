$ErrorActionPreference='Stop'
$root='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029'
$uri='http://127.0.0.1:8771/'
$connected=$false
try { $null=Invoke-RestMethod -Uri ($uri+'api/status') -TimeoutSec 2; $connected=$true } catch {}
if(-not $connected) {
 Start-Process -FilePath 'C:/Python315/python.exe' -ArgumentList ($root+'/manual_control_server.py') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput ($root+'/manual_control_server.stdout.log') -RedirectStandardError ($root+'/manual_control_server.stderr.log')
 for($i=0;$i -lt 20;$i++) { Start-Sleep -Milliseconds 500; try { $null=Invoke-RestMethod -Uri ($uri+'api/status') -TimeoutSec 1; $connected=$true; break } catch {} }
}
if(-not $connected){throw 'Local panel did not start. No calculation was launched. See manual_control_server.stderr.log.'}
Start-Process ($uri+'#manual-control-panel')
