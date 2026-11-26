$env:TORCH_THREADS='1'; $env:TD3K_W_A='1.5'
while (-not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\runs\TD3K_WA1.5\DONE') -and -not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\runs\TD3K_WA1.5\STOP')) {
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\runs\TD3K_WA1.5\supervisor.log' ("{0} start" -f (Get-Date -f s))
  $p = Start-Process -FilePath 'T:\NTNU_GODO_CONTROL_20261109\.venv\Scripts\python.exe' -ArgumentList '-X','utf8','T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\train_rl.py','td3','TD3K_WA1.5' -WorkingDirectory 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort' -NoNewWindow -PassThru -RedirectStandardOutput 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\runs\TD3K_WA1.5\stdout.log' -RedirectStandardError 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\runs\TD3K_WA1.5\stderr.log'
  $p.ProcessorAffinity = [IntPtr]([int64]3 -shl 18); $p.PriorityClass = 'BelowNormal'
  Start-Sleep 3; Get-CimInstance Win32_Process | ? { $_.ParentProcessId -eq $p.Id } | % { try { $c = Get-Process -Id $_.ProcessId; $c.ProcessorAffinity = $p.ProcessorAffinity; $c.PriorityClass = 'BelowNormal' } catch {} }
  $p.WaitForExit()
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort\runs\TD3K_WA1.5\supervisor.log' ("{0} exit {1}" -f (Get-Date -f s), $p.ExitCode)
  Start-Sleep 20
}
