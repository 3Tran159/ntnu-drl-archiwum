# Only prints an authorized Tailscale phone URL. No public networking or solver interaction.
$ErrorActionPreference = 'Stop'
$raw = & tailscale.exe ip -4 2>$null
$ip = ($raw | Select-Object -First 1).ToString().Trim()
if ($LASTEXITCODE -ne 0 -or $ip -notmatch '^100\.(\d{1,3}\.){2}\d{1,3}$') {
  Write-Output 'No connected Tailscale address on ThinkPad. Sign in to Tailscale on ThinkPad and phone, then run this script again.'
  exit 1
}
Write-Output 'Restarting only the independent NTNU dashboard to bind the private Tailscale address.'
& "$PSScriptRoot\stop_dashboard.ps1"
& "$PSScriptRoot\start_dashboard.ps1"
$target = 'http://' + $ip + ':8787'
Write-Output "PRIVATE PHONE URL: $target"
Write-Output 'Open this URL on your phone on the same Tailscale tailnet. Do not port-forward.'
