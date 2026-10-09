param([ValidateSet('en','sk')][string]$Locale='en')
$g='F:\Remaster Framework\source\Godot\Godot_v4.7.2-stable_win64_console.exe'
$stdout=Join-Path $env:TEMP ("oa211_"+$Locale+"_"+$PID+".out")
$stderr=$stdout+".err"
$env:OPENAZRAEL_TEST_LOCALE=$Locale
$argsLine='--headless --path "F:\Remaster Framework\work\OpenAzrael" --script res://scripts/kg001_localized_full_demo_runner_v210.gd'
$p=Start-Process -FilePath $g -ArgumentList $argsLine -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Remove-Item Env:OPENAZRAEL_TEST_LOCALE -ErrorAction SilentlyContinue
$out=(Get-Content $stdout -Raw -ErrorAction SilentlyContinue)+"`n"+(Get-Content $stderr -Raw -ErrorAction SilentlyContinue)
Remove-Item $stdout,$stderr -ErrorAction SilentlyContinue
$functional=$p.ExitCode -eq 0 -and $out -match '"status":"PASS"' -and $out -match '"checks":34'
$m=[regex]::Match($out,'WARNING: (\d+) ObjectDB instances were leaked at exit')
$leaks=if($m.Success){[int]$m.Groups[1].Value}else{0}
$unexpected=@($out -split "`r?`n"|Where-Object {$_ -match 'ERROR:|SCRIPT ERROR:|WARNING:' -and $_ -notmatch 'ObjectDB instances were leaked at exit'})
$knownShutdown=($leaks -eq 0 -or $leaks -eq 4)
if($functional -and $knownShutdown -and $unexpected.Count -eq 0){
  $status=if($leaks -eq 0){'PASS_CLEAN'}else{'PASS_WITH_KNOWN_GODOT_SHUTDOWN_WARNING'}
}else{$status='FAIL'}
[ordered]@{schema='openazrael.localization.harness_gate';version=211;locale=$Locale;status=$status;functional_pass=$functional;allowed_objectdb_leaks=@(0,4);observed_objectdb_leaks=$leaks;unexpected_diagnostics=$unexpected}|ConvertTo-Json -Compress
if($status -eq 'FAIL'){exit 1}else{exit 0}
