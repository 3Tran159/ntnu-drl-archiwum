param([string[]]$Classes)
$r='E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\doc\client\html\star'
foreach($c in $Classes){
 $f=Join-Path $r ($c.Replace('.','\')+'.html')
 if(!(Test-Path -LiteralPath $f)){Write-Output ('MISSING '+$c);continue}
 $s=Get-Content -Raw -LiteralPath $f
 $m=[regex]::Match($s,'(?s)<section class="method-summary".*?</section>')
 $text=[System.Net.WebUtility]::HtmlDecode([regex]::Replace($m.Value,'<[^>]+>',' '))
 $text=[regex]::Replace($text,'\s+',' ')
 Write-Output ($c+': '+($text -split 'Methods inherited')[0])
}
