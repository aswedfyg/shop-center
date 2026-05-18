# Shop Center Appium Tests

产品中心自动化测试项目，统一管理 Android 与 iOS 测试代码。

## 目录结构

```text
android/    Android 产品中心测试流程、定位器、运行入口
ios/        iOS Appium smoke 与后续 macOS iOS 项目迁入位置
common/     跨平台共享配置、报告生成、样式
dashboard/  Web 控制台
tests/      本地单元测试
docs/       用例、流程图、结构说明
scripts/    Windows/PowerShell 启动脚本
reports/    本地生成的 HTML 报告，不提交 Git
```

## 常用命令

Android 产品中心测试：

```powershell
.\scripts\run_product_center.ps1 -Mode smoke
```

指定单个用例：

```powershell
.\scripts\run_product_center.ps1 -Tests test_03_purchase_channels_jump
```

启动控制台：

```powershell
.\scripts\run_dashboard.ps1
```

iOS Appium 连接冒烟测试：

```powershell
.\scripts\run_ios_smoke.ps1
```

本地单元测试：

```powershell
python -m unittest tests.test_product_center_config tests.test_product_center_flow_observation
```

或：

```powershell
pytest
```

## 平台边界

- Windows 本机主要跑 Android：`android/` + `scripts/run_product_center.ps1`。
- macOS 机器跑 iOS：后续把 iOS 项目代码放入 `ios/`。
- 业务数据、链接期望、报告能力放在 `common/`。
- 平台独有的定位器、恢复逻辑、Appium capabilities 留在各自平台目录。

## 关键文件

| 路径 | 说明 |
| --- | --- |
| `common/config.py` | Appium 参数、国家/渠道/商品配置、跳转期望 |
| `common/report.py` | HTML 测试报告生成 |
| `android/product_center_flow.py` | Android 产品中心测试主流程 |
| `android/product_center_locators.py` | Android 产品中心定位器 |
| `android/run_product_center.py` | Android 测试运行入口 |
| `ios/appium_smoke.py` | iOS Appium 连接冒烟入口 |
| `dashboard/app.py` | Web 控制台 |
| `docs/PROJECT_LAYOUT.md` | 项目结构约定 |

## 报告

测试完成后会在本地生成：

```text
reports/latest_product_center_report.html
reports/product_center_report_YYYYMMDD_HHMMSS.html
```

`reports/` 已加入 `.gitignore`，不会上传到 GitHub。

