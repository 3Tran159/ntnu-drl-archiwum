$env:TORCH_THREADS='2'
while (-not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_B\DONE') -and -not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_B\STOP')) {
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_B\supervisor.log' ("{0} start" -f (Get-Date -f s))
  $p = Start-Process -FilePath 'T:\NTNU_GODO_CONTROL_20261109\.venv\Scripts\python.exe' -ArgumentList '-X','utf8','T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\train_rl.py','sac','SAC_B' -WorkingDirectory 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env' -NoNewWindow -PassThru -RedirectStandardOutput 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_B\stdout.log' -RedirectStandardError 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_B\stderr.log'
  $p.ProcessorAffinity = [IntPtr]([int64]0x3 -shl 20)
  $p.PriorityClass = 'BelowNormal'
  $p.WaitForExit()
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\SAC_B\supervisor.log' ("{0} exit {1}" -f (Get-Date -f s), $p.ExitCode)
  Start-Sleep 20
}
