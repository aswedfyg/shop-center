from appium import webdriver

from common.config import APPIUM_SERVER_URL, IOS_BUNDLE_ID, PLATFORM_NAME, build_driver_options


def main():
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=build_driver_options())
    try:
        print(f"Appium 连接成功，platform={PLATFORM_NAME}")
        if PLATFORM_NAME.lower() == "ios":
            print(f"iOS bundleId={IOS_BUNDLE_ID}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
