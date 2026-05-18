param(
    [string]$AppiumServerUrl = "http://192.168.12.69:4723/wd/hub",
    [string]$DeviceName = "iPad (2)",
    [string]$DeviceUdid = "00008110-000A291C3431401E",
    [string]$PlatformVersion = "18.3",
    [string]$BundleId = "com.accsoon.Mercury",
    [string]$AppPath = "",
    [string]$WebDriverAgentUrl = "",
    [string]$WdaLocalPort = "8100",
    [int]$WdaLaunchTimeout = 120000,
    [int]$WdaConnectionTimeout = 120000,
    [string]$UpdatedWdaBundleId = "",
    [string]$XcodeOrgId = "SKNT88U6LT",
    [string]$XcodeSigningId = "Apple Development",
    [switch]$UsePreinstalledWda,
    [switch]$UsePrebuiltWda,
    [switch]$ShowXcodeLog
)

$env:APPIUM_SERVER_URL = $AppiumServerUrl
$env:PLATFORM_NAME = "iOS"
$env:DEVICE_NAME = $DeviceName
$env:DEVICE_UDID = $DeviceUdid
$env:PLATFORM_VERSION = $PlatformVersion
$env:IOS_BUNDLE_ID = $BundleId
$env:IOS_APP_PATH = $AppPath
$env:IOS_WEB_DRIVER_AGENT_URL = $WebDriverAgentUrl
$env:IOS_SHOW_XCODE_LOG = if ($ShowXcodeLog) { "1" } else { "0" }
$env:IOS_WDA_LAUNCH_TIMEOUT = [string]$WdaLaunchTimeout
$env:IOS_WDA_CONNECTION_TIMEOUT = [string]$WdaConnectionTimeout
if ($WebDriverAgentUrl) {
    $env:IOS_USE_PREINSTALLED_WDA = "0"
} else {
    $env:IOS_USE_PREINSTALLED_WDA = if ($UsePreinstalledWda) { "1" } else { "0" }
}
$env:IOS_USE_PREBUILT_WDA = if ($UsePrebuiltWda) { "1" } else { "0" }
$env:PYTHONUTF8 = "1"

if ($WdaLocalPort) {
    $env:IOS_WDA_LOCAL_PORT = $WdaLocalPort
} else {
    Remove-Item Env:IOS_WDA_LOCAL_PORT -ErrorAction SilentlyContinue
}

if ($UpdatedWdaBundleId) {
    $env:IOS_UPDATED_WDA_BUNDLE_ID = $UpdatedWdaBundleId
} else {
    Remove-Item Env:IOS_UPDATED_WDA_BUNDLE_ID -ErrorAction SilentlyContinue
}

if ($XcodeOrgId) {
    $env:IOS_XCODE_ORG_ID = $XcodeOrgId
    $env:IOS_XCODE_SIGNING_ID = $XcodeSigningId
} else {
    Remove-Item Env:IOS_XCODE_ORG_ID -ErrorAction SilentlyContinue
    Remove-Item Env:IOS_XCODE_SIGNING_ID -ErrorAction SilentlyContinue
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
python (Join-Path $Root "ios\appium_smoke.py")
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ("iOS Appium smoke failed, exit code: {0}" -f $exitCode) -ForegroundColor Red
    exit $exitCode
}

exit 0
