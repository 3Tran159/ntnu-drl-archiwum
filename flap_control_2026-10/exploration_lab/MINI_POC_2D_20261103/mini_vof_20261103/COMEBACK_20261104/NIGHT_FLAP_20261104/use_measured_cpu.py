from pathlib import Path
p=Path(__file__).with_name("night_flap.py")
s=p.read_text().replace("class NightGuard(GuardResume):\n","class NightGuard(GuardResume):\n    headroom_checked_at=0.0\n",1)
a=s.index("        if host_mask in values:")
b=s.index("\n    def preflight",a)
s=s[:a]+'''        if host_mask in values and time.monotonic()-NightGuard.headroom_checked_at>45:
            measurement=query(r"""
$old=@{}
Get-Process | ForEach-Object { $old[$_.Id]=$_.CPU }
$timer=[Diagnostics.Stopwatch]::StartNew()
Start-Sleep -Seconds 5
$sum=0.
Get-Process | ForEach-Object {
  if ($old.ContainsKey($_.Id) -and $null -ne $_.CPU -and $_.ProcessName -notin @('Idle','System')) {
    $sum += [Math]::Max(0,$_.CPU-$old[$_.Id])
  }
}
[pscustomobject]@{used_cores=$sum/$timer.Elapsed.TotalSeconds; cores=[Environment]::ProcessorCount} | ConvertTo-Json -Compress
""")
            if not measurement or measurement[0]["cores"]-measurement[0]["used_cores"]<4:
                raise RuntimeError("Unpinned independent STAR ranks and fewer than four spare CPU equivalents")
            NightGuard.headroom_checked_at=time.monotonic()
'''+s[b:]
s=s.replace('or "CPU above 85 percent" in last_error', 'or "spare CPU equivalents" in last_error')
p.write_text(s)

