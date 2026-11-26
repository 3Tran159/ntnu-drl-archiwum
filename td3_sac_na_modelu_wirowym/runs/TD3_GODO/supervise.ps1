$env:TORCH_THREADS='2'
while (-not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\TD3_GODO\DONE') -and -not (Test-Path 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\TD3_GODO\STOP')) {
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\TD3_GODO\supervisor.log' ("{0} start" -f (Get-Date -f s))
  $p = Start-Process -FilePath 'T:\NTNU_GODO_CONTROL_20261109\.venv\Scripts\python.exe' -ArgumentList '-X','utf8','T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\train_rl.py','td3','TD3_GODO' -WorkingDirectory 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env' -NoNewWindow -PassThru -RedirectStandardOutput 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\TD3_GODO\stdout.log' -RedirectStandardError 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\TD3_GODO\stderr.log'
  $p.ProcessorAffinity = [IntPtr]([int64]0x3 -shl 18)
  $p.PriorityClass = 'BelowNormal'
  $p.WaitForExit()
  Add-Content 'T:\NTNU_GODO_CONTROL_20261109\50_learning\vortex_env\runs\TD3_GODO\supervisor.log' ("{0} exit {1}" -f (Get-Date -f s), $p.ExitCode)
  Start-Sleep 20
}
