# Project Layout

This repository uses one codebase with platform-specific execution.

```text
android/
  product_center_flow.py       Android product-center flow
  product_center_locators.py   Android locators
  product_center_test.py       unittest/pytest entry
  run_product_center.py        HTML-report runner

ios/
  appium_smoke.py              iOS Appium connection smoke
  README.md                    iOS migration notes

common/
  config.py                    Shared environment config and business data
  report.py                    Shared HTML report runner
  styles.py                    Shared dashboard/report styles

dashboard/
  app.py                       Web dashboard

tests/
  test_*.py                    Local unit tests

docs/
  FLOWCHART.md
  TEST_CASES.md
  PROJECT_LAYOUT.md

scripts/
  run_product_center.ps1
  run_dashboard.ps1
  run_ios_smoke.ps1
  START.bat
```

## Rules

- Keep Android execution on Windows with Android SDK/Appium/UiAutomator2.
- Keep iOS execution on macOS with Xcode/Appium/XCUITest/WebDriverAgent.
- Put shared business expectations and report helpers in `common`.
- Put platform-specific locators, capabilities, shell tooling, and recovery logic in `android` or `ios`.
- Keep generated reports, logs, caches, IDE files, and screenshots out of Git.

