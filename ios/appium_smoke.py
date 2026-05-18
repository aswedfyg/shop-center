import sys
from pathlib import Path

from appium import webdriver

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import APPIUM_SERVER_URL, IOS_BUNDLE_ID, PLATFORM_NAME, build_driver_options


def main():
    if PLATFORM_NAME.lower() != "ios":
        raise SystemExit("Set PLATFORM_NAME=iOS before running the iOS smoke test.")

    driver = webdriver.Remote(APPIUM_SERVER_URL, options=build_driver_options())
    try:
        print(f"Appium 连接成功：platform={PLATFORM_NAME}")
        print(f"iOS bundleId={IOS_BUNDLE_ID}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
