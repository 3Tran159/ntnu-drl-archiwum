$ErrorActionPreference='Stop'
$base='C:\Users\ThinkPad\Documents\ChatGPT\ntnu science'
$destinationRoot='F:\ntnu\flap_control'
$names=@('flap_poc_2606_20261102','flap_drl_20261102')
$manifestPath=Join-Path $destinationRoot '_migration\copy_manifest.json'
if(Test-Path -LiteralPath $manifestPath){throw 'Copy manifest already exists; inspect before resuming'}
function Assert-ExactDirectory([string]$p,[string]$expected) {
 $resolved=(Resolve-Path -LiteralPath $p).ProviderPath
 if(-not [string]::Equals($resolved,$expected,[StringComparison]::OrdinalIgnoreCase)){throw "Unexpected resolved path: $resolved"}
 if((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Reparse root: $p"}
 $links=@(Get-ChildItem -LiteralPath $p -Recurse -Force | Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint})
 if($links.Count){throw "Reparse child in $p"}
}
function Assert-Inactive {
 $processes=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(starccm\+|star-ccm\+|starccmw|starserver|python|pythonw|java|javaw)\.exe$'}
 foreach($proc in $processes) {
  $command=$proc.CommandLine
  $session=''
  if($command -match '-(?:xencoded-session|encoded-session)\s+([A-Za-z0-9+/=]+)'){
   try{$session=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Matches[1]))}catch{}
  }
  foreach($name in $names){
   $source=Join-Path $base $name
   if(($command -and $command.IndexOf($source,[StringComparison]::OrdinalIgnoreCase) -ge 0) -or ($session -and $session.StartsWith($source,[StringComparison]::OrdinalIgnoreCase))){throw "Source is active in process $($proc.ProcessId)"}
  }
 }
}
Assert-ExactDirectory $destinationRoot 'F:\ntnu\flap_control'
Assert-Inactive
$groups=@()
$totalBytes=[long]0
foreach($name in $names) {
 $source=[IO.Path]::GetFullPath((Join-Path $base $name))
 if($source -ne (Join-Path $base $name)){throw 'Source normalization mismatch'}
 Assert-ExactDirectory $source (Join-Path $base $name)
 $target=[IO.Path]::GetFullPath((Join-Path $destinationRoot $name))
 if(-not $target.StartsWith($destinationRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Destination escaped the selected root'}
 if(Test-Path -LiteralPath $target){throw "Destination already exists: $target"}
 $sourceFiles=@(Get-ChildItem -LiteralPath $source -Recurse -File -Force)
 $sourceDirs=@(Get-ChildItem -LiteralPath $source -Recurse -Directory -Force | ForEach-Object {$_.FullName.Substring($source.Length+1)} | Sort-Object)
 $bytes=[long](($sourceFiles|Measure-Object Length -Sum).Sum)
 $totalBytes+=$bytes
 if((Get-PSDrive F).Free -lt ($bytes+1GB)){throw 'Insufficient destination space'}
 Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
 Assert-ExactDirectory $target $target
 $targetFiles=@(Get-ChildItem -LiteralPath $target -Recurse -File -Force)
 $targetDirs=@(Get-ChildItem -LiteralPath $target -Recurse -Directory -Force | ForEach-Object {$_.FullName.Substring($target.Length+1)} | Sort-Object)
 if($targetFiles.Count -ne $sourceFiles.Count){throw "File count mismatch: $name"}
 if(@(Compare-Object $sourceDirs $targetDirs).Count){throw "Directory mismatch: $name"}
 $files=@()
 foreach($file in $sourceFiles) {
  $relative=$file.FullName.Substring($source.Length+1)
  $new=Join-Path $target $relative
  $copied=Get-Item -LiteralPath $new
  if($copied.Length -ne $file.Length){throw "Size mismatch: $relative"}
  $before=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
  $after=(Get-FileHash -LiteralPath $new -Algorithm SHA256).Hash
  if($before -ne $after){throw "Hash mismatch: $relative"}
  $files+=[pscustomobject]@{Relative=$relative;Bytes=$file.Length;SourceWriteTicks=$file.LastWriteTimeUtc.Ticks;SHA256=$before}
 }
 $groups+=[pscustomobject]@{Name=$name;Source=$source;Destination=$target;FileCount=$files.Count;DirectoryCount=$sourceDirs.Count;Bytes=$bytes;Files=$files}
 Write-Output ("VERIFIED "+$name+" files="+$files.Count+" bytes="+$bytes)
}
Assert-Inactive
$manifest=[pscustomobject]@{At=[DateTimeOffset]::Now.ToString('o');State='copied_and_hash_verified';OriginalsDeleted=$false;TotalBytes=$totalBytes;Groups=$groups}
$manifest|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output ("COPY_COMPLETE total_bytes="+$totalBytes+" manifest="+$manifestPath)
