$env:TORCH_THREADS='2'
while (-not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_C\DONE') -and -not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_C\STOP')) {
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_C\supervisor.log' ("{0} start" -f (Get-Date -f s))
  $p = Start-Process -FilePath 'T:\NTNU_GODO_CONTROL_20261109\.venv\Scripts\python.exe' -ArgumentList '-X','utf8','T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\train_rl.py','sac','SAC_C' -WorkingDirectory 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env' -NoNewWindow -PassThru -RedirectStandardOutput 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_C\stdout.log' -RedirectStandardError 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_C\stderr.log'
  $p.ProcessorAffinity = [IntPtr]([int64]0x3 -shl 20)
  $p.PriorityClass = 'BelowNormal'
  # .venv\python.exe to tylko launcher: wlasciwy interpreter jest procesem potomnym i NIE dziedziczy przypiecia - przypinamy go osobno
  Start-Sleep 3; Get-CimInstance Win32_Process | ? { $_.ParentProcessId -eq $p.Id } | % { try { $c = Get-Process -Id $_.ProcessId; $c.ProcessorAffinity = $p.ProcessorAffinity; $c.PriorityClass = 'BelowNormal' } catch {} }
  $p.WaitForExit()
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_C\supervisor.log' ("{0} exit {1}" -f (Get-Date -f s), $p.ExitCode)
  Start-Sleep 20
}
