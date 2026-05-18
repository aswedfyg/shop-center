param(
    [string[]]$Tests = @(),
    [ValidateSet("full", "smoke")]
    [string]$Mode = "full",
    [string[]]$Countries = @(),
    [string[]]$Channels = @(),
    [string[]]$Products = @(),
    [string]$StartAt = "",
    [string]$EndAt = "",
    [int]$ChannelMax = 0,
    [int]$ProductMax = 0,
    [string]$DeviceName = "",
    [string]$DeviceUdid = "",
    [int]$SystemPort = 0,
    [switch]$RelaxedBrowser,
    [switch]$StrictOfficialUrl
)

$env:PRODUCT_CENTER_RUN_MODE = $Mode
$env:CHANNEL_JUMP_MAX_CASES = [string]$ChannelMax
$env:FEATURED_PRODUCT_MAX_CASES = [string]$ProductMax
$env:RELAXED_EXTERNAL_BROWSER_CHECK = if ($RelaxedBrowser) { "1" } else { "0" }
$env:STRICT_OFFICIAL_PRODUCT_URL = if ($StrictOfficialUrl) { "1" } else { "0" }

if ($DeviceName) {
    $env:DEVICE_NAME = $DeviceName
}

if ($DeviceUdid) {
    $env:DEVICE_UDID = $DeviceUdid
} else {
    Remove-Item Env:DEVICE_UDID -ErrorAction SilentlyContinue
}

if ($SystemPort -gt 0) {
    $env:APPIUM_SYSTEM_PORT = [string]$SystemPort
} else {
    Remove-Item Env:APPIUM_SYSTEM_PORT -ErrorAction SilentlyContinue
}

if ($Countries.Count -gt 0) {
    $env:FEATURED_PRODUCT_COUNTRIES = ($Countries -join ",")
} else {
    Remove-Item Env:FEATURED_PRODUCT_COUNTRIES -ErrorAction SilentlyContinue
}

if ($Channels.Count -gt 0) {
    $env:FEATURED_PRODUCT_CHANNELS = ($Channels -join ",")
} else {
    Remove-Item Env:FEATURED_PRODUCT_CHANNELS -ErrorAction SilentlyContinue
}

if ($Products.Count -gt 0) {
    $env:FEATURED_PRODUCTS = ($Products -join ",")
} else {
    Remove-Item Env:FEATURED_PRODUCTS -ErrorAction SilentlyContinue
}

if ($StartAt) {
    $env:FEATURED_PRODUCT_START_AT = $StartAt
} else {
    Remove-Item Env:FEATURED_PRODUCT_START_AT -ErrorAction SilentlyContinue
}

if ($EndAt) {
    $env:FEATURED_PRODUCT_END_AT = $EndAt
} else {
    Remove-Item Env:FEATURED_PRODUCT_END_AT -ErrorAction SilentlyContinue
}

$env:PYTHONUTF8 = "1"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
python (Join-Path $Root "android\run_product_center.py") @Tests
$exitCode = $LASTEXITCODE

Remove-Item Env:FEATURED_PRODUCT_START_AT -ErrorAction SilentlyContinue
Remove-Item Env:FEATURED_PRODUCT_END_AT -ErrorAction SilentlyContinue

if ($exitCode -ne 0) {
    Write-Host ("Product center test failed, exit code: {0}" -f $exitCode) -ForegroundColor Red
    exit $exitCode
}

exit 0
