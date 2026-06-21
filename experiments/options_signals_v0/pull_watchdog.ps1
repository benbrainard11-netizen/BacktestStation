# Watchdog: if the theta cache stops growing for 20 min, bounce Terminal + relaunch all pulls.
# Runs until out/_shards has all 3 SPX shard parquets (the completion signal).
$py = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$gs = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\gex_shard.py'
$t = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\theta'
$shardsDir = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards'

function CacheCount { (Get-ChildItem D:\data\raw\thetadata -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count }

$last = CacheCount
$stale = 0
while ($true) {
    Start-Sleep -Seconds 600
    $spxDone = (Get-ChildItem $shardsDir -Filter 'spx_s*.parquet' -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '*spot*' } | Measure-Object).Count
    if ($spxDone -ge 3) { "WATCHDOG: SPX shards complete"; break }
    $now = CacheCount
    # PACE floor, not just stall: healthy 3-stream pull adds >>8 files per 10-min interval.
    if (($now - $last) -lt 8) { $stale++ } else { $stale = 0 }
    $last = $now
    if ($stale -ge 2) {
        "WATCHDOG $(Get-Date -Format 'HH:mm'): pace below floor (cache=$now), bouncing PULL processes only"
        # SCOPED kill: gex_shard pythons only — research-chat engines share this machine.
        Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like '*gex_shard*' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -Confirm:$false -ErrorAction SilentlyContinue }
        Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
        Start-Process -FilePath "C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\bin\java.exe" -ArgumentList '-jar',"$t\ThetaTerminal.jar",'--creds-file',"$t\creds.txt" -WorkingDirectory $t -WindowStyle Hidden
        Start-Sleep -Seconds 20
        foreach ($i in 0..2) { Start-Process -FilePath $py -ArgumentList $gs,'SPX','2017-01-01','2026-06-10',"$i",'3' -WindowStyle Hidden; Start-Sleep -Seconds 45 }
        # small roots: single sequential chain, SAME shard split as the primary launch (0/1)
        # to avoid mixed-split rut_s* parquet collisions at merge time
        $chain = "& '$py' '$gs' RUT 2017-01-01 2026-06-10 0 1; & '$py' '$gs' DJX 2017-01-01 2026-06-10 0 1; & '$py' '$gs' NDX 2017-01-01 2026-06-10 0 1; & '$py' '$gs' GLD 2017-01-01 2026-06-10 0 1; & '$py' '$gs' SLV 2017-01-01 2026-06-10 0 1"
        Start-Process powershell -ArgumentList '-NoProfile','-Command',$chain -WindowStyle Hidden
        $stale = 0
    }
}
