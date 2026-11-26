$ErrorActionPreference='Stop'
$base='C:\Users\ThinkPad\Documents\ChatGPT\ntnu science'
$root='F:\ntnu\flap_control'
$allowed=@('flap_poc_2606_20261102','flap_drl_20261102')
$manifest=Get-Content -LiteralPath ($root+'\_migration\copy_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$ready=Get-Content -LiteralPath ($root+'\_migration\relocation_ready.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($manifest.State -ne 'copied_and_hash_verified' -or $ready.state -ne 'destination_ready_for_source_deletion' -or -not $ready.all_sim_hashes_match -or -not $ready.artifact_checks_passed){throw 'Destination readiness not verified'}
if((Resolve-Path -LiteralPath $root).ProviderPath -ne 'F:\ntnu\flap_control'){throw 'Unexpected destination root'}
function Assert-Inactive {
 foreach($proc in (Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(starccm\+|star-ccm\+|starccmw|starserver|python|pythonw|java|javaw)\.exe$'})){
  $command=$proc.CommandLine;$session=''
  if($command -match '-(?:xencoded-session|encoded-session)\s+([A-Za-z0-9+/=]+)'){try{$session=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Matches[1]))}catch{}}
  foreach($name in $allowed){
   $source=Join-Path $base $name
   if(($command -and $command.IndexOf($source,[StringComparison]::OrdinalIgnoreCase) -ge 0) -or ($session -and $session.StartsWith($source,[StringComparison]::OrdinalIgnoreCase))){throw "Source became active in PID $($proc.ProcessId)"}
  }
 }
}
Assert-Inactive
# Verify all sources again before deleting either directory.
foreach($group in $manifest.Groups){
 if($allowed -notcontains $group.Name){throw 'Unexpected directory in manifest'}
 $expectedSource=Join-Path $base $group.Name
 $expectedTarget=Join-Path $root $group.Name
 if($group.Source -ne $expectedSource -or $group.Destination -ne $expectedTarget){throw 'Manifest path mismatch'}
 $resolved=(Resolve-Path -LiteralPath $expectedSource).ProviderPath
 if($resolved -ne $expectedSource -or [IO.Path]::GetFullPath($expectedSource) -ne $expectedSource){throw 'Source resolution mismatch'}
 if((Get-Item -LiteralPath $expectedSource -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Source is a reparse point'}
 if(@(Get-ChildItem -LiteralPath $expectedSource -Recurse -Force|Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Source contains reparse points'}
 $current=@(Get-ChildItem -LiteralPath $expectedSource -Recurse -File -Force)
 if($current.Count -ne $group.FileCount){throw 'Source file count changed'}
 foreach($item in $group.Files){
  $sourceFile=Join-Path $expectedSource $item.Relative
  $targetFile=Join-Path $expectedTarget $item.Relative
  if(-not(Test-Path -LiteralPath $targetFile -PathType Leaf)){throw "Missing destination file $targetFile"}
  if((Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash -ne $item.SHA256){throw "Source changed: $sourceFile"}
  if($item.Relative.EndsWith('.sim') -or $item.Relative.EndsWith('.sim~')){
   if((Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash -ne $item.SHA256){throw "Destination simulation changed: $targetFile"}
  }
 }
}
Assert-Inactive
$deleted=@()
foreach($name in $allowed){
 $source=Join-Path $base $name
 # Exact, resolved targets only. Never delete the parent workspace.
 $resolved=(Resolve-Path -LiteralPath $source).ProviderPath
 if($resolved -ne (Join-Path 'C:\Users\ThinkPad\Documents\ChatGPT\ntnu science' $name) -or $allowed -notcontains (Split-Path -Leaf $resolved)){throw 'Deletion target failed final check'}
 Remove-Item -LiteralPath $resolved -Recurse -Force
 if(Test-Path -LiteralPath $source){throw "Source remains: $source"}
 $deleted+=$source
}
$receipt=[pscustomobject]@{At=[DateTimeOffset]::Now.ToString('o');State='move_complete';DeletedSourceDirectories=$deleted;DataBytesRemovedFromC=$manifest.TotalBytes;NewWorkRoot=$root;WorkingSimulation=($root+'\flap_poc_2606_20261102\FlapPOC_2606_working.sim');OriginalC01AndOtherCampaignsTouched=$false}
$receipt|ConvertTo-Json -Depth 5|Set-Content -LiteralPath ($root+'\_migration\move_complete.json') -Encoding UTF8
$receipt|ConvertTo-Json -Depth 5
