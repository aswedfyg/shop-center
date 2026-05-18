$env:PYTHONUTF8 = "1"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
python (Join-Path $Root "dashboard\app.py")
