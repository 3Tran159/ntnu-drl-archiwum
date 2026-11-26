$ErrorActionPreference='Stop'
$h='F:\ntnu\flap_control\hydro_validation_2606_20261102'
$pause=Get-Content -LiteralPath "$h\audit\RELOCATION_CURRENT.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$all=@(Get-CimInstance Win32_Process)
$ids=@{}
foreach($p in $all){
 $cmd=[string]$p.CommandLine
 if($p.Name -match '^(starccm\+|mpiexec|smpd|hydra|mpirun)' -or $cmd.Contains($h)){$ids[[int]$p.ProcessId]=$true}
}
$changed=$true
while($changed){
 $changed=$false
 foreach($p in $all){if($ids.ContainsKey([int]$p.ParentProcessId) -and -not $ids.ContainsKey([int]$p.ProcessId)){$ids[[int]$p.ProcessId]=$true;$changed=$true}}
}
$rows=@()
foreach($p in $all){
 if(-not $ids.ContainsKey([int]$p.ProcessId)){continue}
 $cmd=[string]$p.CommandLine
 $sim=$null
 $m=[regex]::Match($cmd,'-xencoded-session\s+([A-Za-z0-9+/=]+)')
 if($m.Success){try{$sim=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($m.Groups[1].Value))}catch{}}
 if(-not $sim){$m=[regex]::Match($cmd,'(?:^|\s)(?:"(?<s>[A-Za-z]:[\\/][^"]+\.sim)"|(?<s>[A-Za-z]:[\\/]\S+\.sim))');if($m.Success){$sim=$m.Groups['s'].Value}}
 $version=$null
 if($p.ExecutablePath -and (Test-Path -LiteralPath $p.ExecutablePath)){try{$version=(Get-Item -LiteralPath $p.ExecutablePath).VersionInfo.ProductVersion}catch{}}
 $owner=$null
 try{$o=Invoke-CimMethod -InputObject $p -MethodName GetOwner -ErrorAction Stop;$owner=$o.Domain+'\'+$o.User}catch{}
 $isAudit=$cmd -match 'audit_relocation_processes\.ps1'
 $task=if($isAudit){'this read-only audit helper'}elseif($cmd.Contains($h) -or ($sim -and $sim.StartsWith($h))){'owned flap campaign'}else{'OTHER or unassigned; protected'}
 $rows+=[pscustomobject]@{pid=$p.ProcessId;ppid=$p.ParentProcessId;name=$p.Name;created=[string]$p.CreationDate;executable=$p.ExecutablePath;version=$version;windows_owner=$owner;task=$task;sim=$sim;is_current_audit_helper=$isAudit}
}
$record=[pscustomobject]@{at=(Get-Date -Format o);audit_pid=$PID;processes=$rows}
$dest=Join-Path $pause.archive ('process_audit_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'.json')
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $dest -Encoding UTF8
$record | ConvertTo-Json -Depth 5
