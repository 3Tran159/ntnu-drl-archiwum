param([string]$Only="")
# start_td3k.ps1 - TD3 (hiperparametry Godo) na Faltinsenie B z kosztem MPC komfortowego. 17.11.
# Rdzenie 18-21 (URANS 2-17, POL32 0-1 nietkniete), priorytet BelowNormal. Zatrzymanie: runs\<TAG>\STOP. Wznowienie: uruchom ponownie.
$here = "T:\NTNU_GODO_CONTROL_20261109\95_WARSZTAT_KOORDYNATOR\warsztat\20261117_td3_komfort"
$py = "T:\NTNU_GODO_CONTROL_20261109\.venv\Scripts\python.exe"
$jobs = @(@{tag="TD3K_WA1.5"; wa="1.5"; shift=18}, @{tag="TD3K_WA0"; wa="0"; shift=20}) | ? { -not $Only -or $_.tag -eq $Only }
foreach ($j in $jobs) {
    $tag = $j.tag; $run = Join-Path $here "runs\$tag"; New-Item -ItemType Directory -Force $run | Out-Null
    $sup = @"
`$env:TORCH_THREADS='1'; `$env:TD3K_W_A='$($j.wa)'
while (-not (Test-Path '$run\DONE') -and -not (Test-Path '$run\STOP')) {
  Add-Content '$run\supervisor.log' ("{0} start" -f (Get-Date -f s))
  `$p = Start-Process -FilePath '$py' -ArgumentList '-X','utf8','$here\train_rl.py','td3','$tag' -WorkingDirectory '$here' -NoNewWindow -PassThru -RedirectStandardOutput '$run\stdout.log' -RedirectStandardError '$run\stderr.log'
  `$p.ProcessorAffinity = [IntPtr]([int64]3 -shl $($j.shift)); `$p.PriorityClass = 'BelowNormal'
  Start-Sleep 3; Get-CimInstance Win32_Process | ? { `$_.ParentProcessId -eq `$p.Id } | % { try { `$c = Get-Process -Id `$_.ProcessId; `$c.ProcessorAffinity = `$p.ProcessorAffinity; `$c.PriorityClass = 'BelowNormal' } catch {} }
  `$p.WaitForExit()
  Add-Content '$run\supervisor.log' ("{0} exit {1}" -f (Get-Date -f s), `$p.ExitCode)
  Start-Sleep 20
}
"@
    $f = Join-Path $run "supervise.ps1"; Set-Content -Path $f -Value $sup -Encoding UTF8
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $f -WindowStyle Hidden
    Write-Output "uruchomiono $tag (W_A $($j.wa)) na rdzeniach $($j.shift)-$($j.shift+1)"
}

