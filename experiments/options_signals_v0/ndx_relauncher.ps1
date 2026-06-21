$py="C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe"
$rp="C:\Users\benbr\BacktestStation\experiments\options_signals_v0\robust_pull.py"
$log="C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards\logs"
$cfgd="C:\Users\benbr\ThetaData\ThetaTerminal"
$ports=@(25510,25511,25512)
for ($iter=0; $iter -lt 200; $iter++) {
  $alldone=$true
  for ($n=0; $n -lt 3; $n++) {
    $f="$log\robust_ndx_s$n.log"
    $done=(Test-Path $f) -and (Select-String -Path $f -Pattern "NDX s$n] DONE" -Quiet)
    if ($done) { continue }
    $alldone=$false
    $running=$false
    foreach ($pr in (Get-CimInstance Win32_Process -Filter "Name=''python.exe''" | Where-Object { $_.CommandLine -like "*robust_pull*" })) { if ($pr.CommandLine -like "* $($ports[$n]) *") { $running=$true } }
    if (-not $running) {
      Start-Process -FilePath $py -ArgumentList $rp,"NDX","2018-01-01","2026-12-31",$ports[$n].ToString(),"$cfgd\config_$n.properties",$n,3,"14","bulk_hist/option/eod" -RedirectStandardOutput $f -RedirectStandardError "$f.err" -WindowStyle Hidden
      Add-Content "$log\ndx_relauncher.log" "$(Get-Date -Format ''HH:mm:ss'') relaunched dead shard $n"
    }
  }
  $c=(Get-ChildItem D:\data\raw\thetadata -Recurse -File | Measure-Object).Count
  Add-Content "$log\ndx_relauncher.log" "$(Get-Date -Format ''HH:mm:ss'') cache=$c"
  if ($alldone) { Add-Content "$log\ndx_relauncher.log" "$(Get-Date -Format ''HH:mm:ss'') ALL NDX SHARDS DONE"; break }
  Start-Sleep 100
}
