# Unified Android/iOS Test Layout

This repository is organized as one project with platform-specific execution.

```text
common/
  config.py              Shared configuration import path.
  report.py              Shared HTML report runner import path.

android/
  product_center_flow.py Android product-center flow entry.
  product_center_test.py Android unittest/pytest entry.
  run_product_center.py  Android HTML-report runner.

ios/
  appium_smoke.py        iOS Appium connection smoke runner.
  README.md              Notes for migrating the macOS iOS project.

reports/
  latest_product_center_report.html
  product_center_report_*.html
```

## Current Migration State

The existing Android implementation remains in the root `product_center_*.py`
modules so current dashboard and report tooling keep working. The new package
paths are the preferred paths for new code:

- Android flow: `android.product_center_flow`
- Shared config: `common.config`
- Shared report runner: `common.report`
- iOS smoke: `ios.appium_smoke`

## Platform Rule

Use one repository, but keep runtime environments separate:

- Run Android tests on Windows with Android SDK/Appium/UiAutomator2.
- Run iOS tests on macOS with Xcode/Appium/XCUITest/WebDriverAgent.
- Share business expectations, report helpers, and test data through `common`.
- Keep locators, capabilities, recovery logic, and platform shell tooling in
  `android` or `ios`.

## Commands

Android on Windows:

```powershell
.\run_product_center.ps1 -Mode smoke
```

iOS smoke on macOS:

```powershell
.\run_ios_smoke.ps1 -AppiumServerUrl "http://127.0.0.1:4723/wd/hub"
```

When the macOS iOS project is moved in, put its flow and locator modules under
`ios/` and import shared data from `common.config`.

