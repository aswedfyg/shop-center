# 产品中心自动化测试

## 测试覆盖

- 进入产品中心前置操作：如果有广告弹窗，先点击关闭，再点击菜单按钮。
- 验证产品中心页面：标题为 `产品中心` 或 `Accsoon News`、主打产品、购买渠道。
- 中国购买渠道：`淘宝`、`JD`。
- 美国、加拿大、墨西哥、英国、德国、法国、日本：`Amazon`、`AliExpress`、`本地经销商`。
- 点击购买渠道后验证会跳转到购物 App 或网页。
- 点击主打产品后验证会跳转到对应产品购买页或网页。
- 其他地区：验证本地经销商跳转官网，并验证主打产品跳转到对应 `global_officialproducturl` 官网产品页。美国到日本的 `本地经销商` 使用同一个官网跳转链接。

## 运行

先启动 Appium，并连接 Android 设备：

```powershell
appium
```

直接运行：

```powershell
python .\Untitled-1.py
```

日常快速回归建议使用 smoke 模式，只跑代表性国家、渠道和产品，避免每次执行完整外跳矩阵：

```powershell
$env:PRODUCT_CENTER_RUN_MODE="smoke"; python .\Untitled-1.py
```

也可以用封装脚本按范围运行。断点格式为 `国家|渠道|产品`：

```powershell
.\run_product_center.ps1 -Tests test_04_featured_products_jump -StartAt "美国|Amazon|大师 4K"
```

常用筛选示例：

```powershell
.\run_product_center.ps1 -Tests test_04_featured_products_jump -Countries 美国,英国 -Channels Amazon -Products "CoMo SE","CoMo"
.\run_product_center.ps1 -Tests test_04_featured_products_jump -StartAt "美国|Amazon|大师 4K" -EndAt "美国|AliExpress|CoMo"
.\run_product_center.ps1 -Tests test_05_other_region_direct_jump -Products "CoMo SE","CoMo"
.\run_product_center.ps1 -Mode smoke -ProductMax 4
.\run_product_center.ps1 -Tests test_04_featured_products_jump -StartAt "美国|AliExpress|S60 滑轨" -RelaxedBrowser
```

指定单台设备运行：

```powershell
.\run_product_center.ps1 -Mode smoke -DeviceUdid emulator-5554 -SystemPort 8200
```

可视化控制台支持从 `adb devices -l` 自动发现设备，并在页面中多选设备并行运行：

```powershell
.\run_dashboard.ps1
```

打开控制台后，在线设备会默认全部选中；也可以手动勾选部分设备。多设备运行时控制台会为每台设备自动分配独立的 `systemPort`、`chromedriverPort` 和 `mjpegServerPort`，避免 UiAutomator2 端口冲突。

需要指定抽样数量时：

```powershell
$env:CHANNEL_JUMP_MAX_CASES="2"; $env:FEATURED_PRODUCT_MAX_CASES="4"; python .\Untitled-1.py
```

完整发布前回归使用全量模式：

```powershell
$env:PRODUCT_CENTER_RUN_MODE="full"; $env:CHANNEL_JUMP_MAX_CASES="0"; $env:FEATURED_PRODUCT_MAX_CASES="0"; python .\Untitled-1.py
```

运行完成后会自动生成可视化 HTML 报告：

- `reports\latest_product_center_report.html`：最新一次报告
- `reports\product_center_report_YYYYMMDD_HHMMSS.html`：带时间戳的历史报告

或使用 pytest：

```powershell
pytest -q product_center_test.py
```

## 可配置环境变量

| 变量 | 默认值 |
| --- | --- |
| `APPIUM_SERVER_URL` | `http://127.0.0.1:4725/wd/hub` |
| `APPIUM_HTTP_TIMEOUT` | `20` |
| `DEVICE_NAME` | `Android` |
| `DEVICE_UDID` | 空 |
| `APPIUM_SYSTEM_PORT` | 空 |
| `APPIUM_CHROMEDRIVER_PORT` | 空 |
| `APPIUM_MJPEG_SERVER_PORT` | 空 |
| `PLATFORM_VERSION` | 空 |
| `APP_PACKAGE` | `com.accsoon.uvctransmission` |
| `APP_ACTIVITY` | `.baseproject.ui.SplashActivity` |
| `BASE_SCREEN_WIDTH` | `1440` |
| `BASE_SCREEN_HEIGHT` | `3120` |
| `WAIT_TIMEOUT` | `10` |
| `SHORT_TIMEOUT` | `2` |
| `RESTORE_TIMEOUT` | `30` |
| `HARD_RESET_AFTER_JUMP` | `0` |
| `PRODUCT_CENTER_RUN_MODE` | `full` |
| `CHANNEL_JUMP_MAX_CASES` | `0` |
| `FEATURED_PRODUCT_MAX_CASES` | `0` |
| `FEATURED_PRODUCT_START_AT` | 空 |
| `FEATURED_PRODUCT_END_AT` | 空 |
| `RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP` | `0` |
| `RELAXED_EXTERNAL_BROWSER_CHECK` | `0` |
| `STRICT_OFFICIAL_PRODUCT_URL` | `0` |

`APPIUM_HTTP_TIMEOUT` 用于限制单个 Appium HTTP 请求的最长等待时间，避免设备或 UiAutomator2 卡住时整轮用例一直阻塞。

`BASE_SCREEN_WIDTH` / `BASE_SCREEN_HEIGHT` 是固定坐标兜底的基准分辨率。脚本会读取当前设备屏幕尺寸并按比例缩放兜底点击/滑动坐标，默认基准为 `1440x3120`。

`HARD_RESET_AFTER_JUMP=0` 时，跳转校验后优先通过返回键、切回被测 App、重新进入产品中心等常规方式恢复，不会默认强制重启被测 App。遇到浏览器、购物 App 或 App 内网页无法返回时，可临时设为 `1` 启用硬重置。

`PRODUCT_CENTER_RUN_MODE=smoke` 时，主打产品默认只抽样 `中国/美国/英国` 和 `CoMo SE/CoMo`，购买渠道跳转默认最多 4 条，主打产品跳转默认最多 8 条。全量覆盖仍可用 `full` 模式或显式设置 `FEATURED_PRODUCTS`、`FEATURED_PRODUCT_COUNTRIES`、`FEATURED_PRODUCT_CHANNELS`。

`RELAXED_EXTERNAL_BROWSER_CHECK=1` 是快速校准模式：当 Edge 不暴露完整商品 URL 时，只确认已打开外部浏览器且未出现浏览器错误页，不反复读取页面或尝试处理登录/滑块验证。该模式适合排查 App 是否能拉起外部页面；严格验证具体商品链接时保持默认 `0`。

`STRICT_OFFICIAL_PRODUCT_URL=0` 时，其他地区主打产品官网跳转如果遇到 Edge 不暴露完整 URL，会在确认已打开外部浏览器且未出现错误页/验证页后通过；后台配置校验仍会检查 `global_officialproducturl` 是否是合法的 `accsoon.com` 产品链接。设为 `1` 可强制要求浏览器 URL 或页面内容命中完整产品路径。

## 文件结构

| 文件 | 说明 |
| --- | --- |
| `product_center_config.py` | Appium 参数、国家/渠道/商品配置、外部 App 包名和页面标识。 |
| `product_center_locators.py` | 产品中心页面定位器封装。 |
| `product_center_flow.py` | 产品中心测试流程、跳转校验和恢复逻辑。 |
| `product_center_test.py` | pytest/unittest 入口。 |
| `appium_test.py` | Appium 连接冒烟测试。 |
