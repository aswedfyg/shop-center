# -*- coding: utf-8 -*-

import os
import re
from urllib.parse import parse_qs, urlparse

from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions


ADB_PATH = os.getenv("ADB_PATH", "adb")
PLATFORM_NAME = os.getenv("PLATFORM_NAME", "Android").strip() or "Android"
APP_PACKAGE = os.getenv("APP_PACKAGE", "com.accsoon.uvctransmission")
APP_ACTIVITY = os.getenv("APP_ACTIVITY", ".baseproject.ui.SplashActivity")
IOS_BUNDLE_ID = os.getenv("IOS_BUNDLE_ID", "com.accsoon.Mercury").strip()
IOS_APP_PATH = os.getenv("IOS_APP_PATH", "").strip()
IOS_WEB_DRIVER_AGENT_URL = os.getenv("IOS_WEB_DRIVER_AGENT_URL", "").strip()
IOS_WDA_LOCAL_PORT = os.getenv("IOS_WDA_LOCAL_PORT", "").strip()
IOS_WDA_LAUNCH_TIMEOUT = int(os.getenv("IOS_WDA_LAUNCH_TIMEOUT", "120000"))
IOS_WDA_CONNECTION_TIMEOUT = int(os.getenv("IOS_WDA_CONNECTION_TIMEOUT", "120000"))
IOS_UPDATED_WDA_BUNDLE_ID = os.getenv("IOS_UPDATED_WDA_BUNDLE_ID", "").strip()
IOS_XCODE_ORG_ID = os.getenv("IOS_XCODE_ORG_ID", "").strip()
IOS_XCODE_SIGNING_ID = os.getenv("IOS_XCODE_SIGNING_ID", "").strip()
IOS_USE_PREINSTALLED_WDA = os.getenv("IOS_USE_PREINSTALLED_WDA", "0") != "0"
IOS_USE_PREBUILT_WDA = os.getenv("IOS_USE_PREBUILT_WDA", "0") != "0"
IOS_USE_NEW_WDA = os.getenv("IOS_USE_NEW_WDA", "0") != "0"
IOS_SHOW_XCODE_LOG = os.getenv("IOS_SHOW_XCODE_LOG", "0") != "0"
APPIUM_SERVER_URL = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4725/wd/hub")
APPIUM_AUTO_START = os.getenv("APPIUM_AUTO_START", "1") != "0"
APPIUM_COMMAND = os.getenv("APPIUM_COMMAND", "appium")
APPIUM_START_TIMEOUT = int(os.getenv("APPIUM_START_TIMEOUT", "25"))
APPIUM_HTTP_TIMEOUT = int(os.getenv("APPIUM_HTTP_TIMEOUT", "20"))
DEVICE_NAME = os.getenv("DEVICE_NAME", "Android")
DEVICE_UDID = os.getenv("DEVICE_UDID", "").strip()
PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", "").strip()
APPIUM_SYSTEM_PORT = os.getenv("APPIUM_SYSTEM_PORT", "").strip()
APPIUM_CHROMEDRIVER_PORT = os.getenv("APPIUM_CHROMEDRIVER_PORT", "").strip()
APPIUM_MJPEG_SERVER_PORT = os.getenv("APPIUM_MJPEG_SERVER_PORT", "").strip()
WAIT_TIMEOUT = int(os.getenv("WAIT_TIMEOUT", "10"))
SHORT_TIMEOUT = float(os.getenv("SHORT_TIMEOUT", "1.5"))
AFTER_CLICK_TIMEOUT = float(os.getenv("AFTER_CLICK_TIMEOUT", "1"))
FEATURED_CHANNEL_SWITCH_WAIT = float(os.getenv("FEATURED_CHANNEL_SWITCH_WAIT", "1.5"))
RESTORE_TIMEOUT = int(os.getenv("RESTORE_TIMEOUT", "30"))
PRODUCT_CENTER_RUN_MODE = os.getenv("PRODUCT_CENTER_RUN_MODE", "full").strip().lower()
CHANNEL_JUMP_MAX_CASES = int(os.getenv("CHANNEL_JUMP_MAX_CASES", "0"))
FEATURED_PRODUCT_MAX_CASES = int(os.getenv("FEATURED_PRODUCT_MAX_CASES", "0"))
FEATURED_PRODUCT_START_AT = os.getenv("FEATURED_PRODUCT_START_AT", "").strip()
FEATURED_PRODUCT_END_AT = os.getenv("FEATURED_PRODUCT_END_AT", "").strip()
HARD_RESET_AFTER_JUMP = os.getenv("HARD_RESET_AFTER_JUMP", "0") != "0"
RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP = os.getenv("RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP", "0") != "0"
STRICT_OFFICIAL_PRODUCT_URL = os.getenv("STRICT_OFFICIAL_PRODUCT_URL", "0") != "0"
STRICT_PRODUCT_DESTINATION = os.getenv("STRICT_PRODUCT_DESTINATION", "0") != "0"
PRODUCT_TEXT_FALLBACK = os.getenv("PRODUCT_TEXT_FALLBACK", "0") != "0"
RELAXED_EXTERNAL_BROWSER_CHECK = os.getenv("RELAXED_EXTERNAL_BROWSER_CHECK", "0") != "0"
MAX_SESSION_RECREATES_PER_TEST = int(os.getenv("MAX_SESSION_RECREATES_PER_TEST", "12"))
UIAUTOMATOR2_SERVER_LAUNCH_TIMEOUT = int(os.getenv("UIAUTOMATOR2_SERVER_LAUNCH_TIMEOUT", "60000"))
UIAUTOMATOR2_SERVER_INSTALL_TIMEOUT = int(os.getenv("UIAUTOMATOR2_SERVER_INSTALL_TIMEOUT", "120000"))
ADB_EXEC_TIMEOUT = int(os.getenv("ADB_EXEC_TIMEOUT", "120000"))
SKIP_UIAUTOMATOR2_SERVER_INSTALL = os.getenv("SKIP_UIAUTOMATOR2_SERVER_INSTALL", "0") != "0"
COUNTRY_DROPDOWN_TAP_X = int(os.getenv("COUNTRY_DROPDOWN_TAP_X", "1209"))
COUNTRY_DROPDOWN_TAP_Y = int(os.getenv("COUNTRY_DROPDOWN_TAP_Y", "2228"))
BASE_SCREEN_WIDTH = int(os.getenv("BASE_SCREEN_WIDTH", "1440"))
BASE_SCREEN_HEIGHT = int(os.getenv("BASE_SCREEN_HEIGHT", "3120"))


def optional_int(value):
    value = str(value or "").strip()
    return int(value) if value else None


def is_ios_platform():
    return PLATFORM_NAME.lower() == "ios"


def is_android_platform():
    return PLATFORM_NAME.lower() == "android"


def adb_command(*args):
    command = [ADB_PATH]
    if DEVICE_UDID:
        command.extend(["-s", DEVICE_UDID])
    command.extend(args)
    return command

CHINA = "中国"
DIRECT_WEB_COUNTRY = "其他地区"
DIRECT_WEB_CHANNEL = "本地经销商"
COUNTRIES_WITH_CHANNELS = ["中国", "美国", "加拿大", "墨西哥", "英国", "德国", "法国", "日本"]
ALL_COUNTRIES = COUNTRIES_WITH_CHANNELS + [DIRECT_WEB_COUNTRY]

COUNTRY_CHANNELS = {
    "中国": ["淘宝", "JD"],
    "美国": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
    "加拿大": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
    "墨西哥": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
    "英国": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
    "德国": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
    "法国": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
    "日本": ["Amazon", "AliExpress", DIRECT_WEB_CHANNEL],
}

EXPECTED_MISSING_CHANNEL_LINKS = set()

FULL_FEATURED_PRODUCTS = [
    "大师4K Lite",
    "SE 4K",
    "大师 4K",
    "SeeMo 4k",
    "M7系列",
    "CoMo",
    "CoMo SE",
    "S60 滑轨",
]
SMOKE_FEATURED_PRODUCTS = ["CoMo SE", "CoMo"]
DEFAULT_FEATURED_PRODUCTS = SMOKE_FEATURED_PRODUCTS if PRODUCT_CENTER_RUN_MODE == "smoke" else FULL_FEATURED_PRODUCTS

FEATURED_PRODUCTS = [
    product.strip()
    for product in os.getenv("FEATURED_PRODUCTS", ",".join(DEFAULT_FEATURED_PRODUCTS)).split(",")
    if product.strip()
]

DEFAULT_FEATURED_PRODUCT_COUNTRIES = ["中国", "美国", "英国"] if PRODUCT_CENTER_RUN_MODE == "smoke" else COUNTRIES_WITH_CHANNELS

FEATURED_PRODUCT_COUNTRIES = [
    country.strip()
    for country in os.getenv("FEATURED_PRODUCT_COUNTRIES", ",".join(DEFAULT_FEATURED_PRODUCT_COUNTRIES)).split(",")
    if country.strip()
]

FEATURED_PRODUCT_CHANNELS_BY_COUNTRY = {
    country: [channel for channel in channels if channel != DIRECT_WEB_CHANNEL]
    for country, channels in COUNTRY_CHANNELS.items()
}

FEATURED_PRODUCT_CHANNEL_FILTER = [
    channel.strip()
    for channel in os.getenv("FEATURED_PRODUCT_CHANNELS", "").split(",")
    if channel.strip()
]
if FEATURED_PRODUCT_CHANNEL_FILTER:
    FEATURED_PRODUCT_CHANNELS_BY_COUNTRY = {
        country: [channel for channel in channels if channel in FEATURED_PRODUCT_CHANNEL_FILTER]
        for country, channels in FEATURED_PRODUCT_CHANNELS_BY_COUNTRY.items()
    }

EXPECTED_MISSING_FEATURED_PRODUCT_LINKS = set()

KNOWN_EXTERNAL_PACKAGES = {
    "com.taobao.taobao",
    "com.jd.jrapp",
    "com.jingdong.app.mall",
    "com.amazon.mShop.android.shopping",
    "com.alibaba.aliexpresshd",
    "com.android.chrome",
    "com.heytap.browser",
    "com.coloros.browser",
    "com.huawei.browser",
    "com.hihonor.browser",
    "com.mi.globalbrowser",
    "com.vivo.browser",
    "com.microsoft.emmx",
    "com.sec.android.app.sbrowser",
    "com.UCMobile",
    "com.baidu.browser.apps",
    "com.qihoo.browser",
    "org.mozilla.firefox",
}

SHOPPING_APP_PACKAGES = {
    "com.taobao.taobao": "淘宝 App",
    "com.jd.jrapp": "京东金融 App",
    "com.jingdong.app.mall": "京东 App",
    "com.amazon.mShop.android.shopping": "Amazon App",
    "com.alibaba.aliexpresshd": "AliExpress App",
}

BROWSER_PACKAGES = {
    "com.android.chrome": "Chrome 网页",
    "com.heytap.browser": "OPPO 浏览器网页",
    "com.coloros.browser": "ColorOS 浏览器网页",
    "com.huawei.browser": "华为浏览器网页",
    "com.hihonor.browser": "荣耀浏览器网页",
    "com.mi.globalbrowser": "小米浏览器网页",
    "com.vivo.browser": "vivo 浏览器网页",
    "com.microsoft.emmx": "Microsoft Edge 网页",
    "com.sec.android.app.sbrowser": "Samsung 浏览器网页",
    "com.UCMobile": "UC 浏览器网页",
    "com.baidu.browser.apps": "百度浏览器网页",
    "com.qihoo.browser": "360 浏览器网页",
    "org.mozilla.firefox": "Firefox 网页",
}

AMAZON_COUNTRY_MARKERS = {
    "美国": ["amazon.com", "United States", "美国"],
    "加拿大": ["amazon.ca", "Canada", "加拿大"],
    "墨西哥": ["amazon.com.mx", "Mexico", "México", "墨西哥"],
    "英国": ["amazon.co.uk", "United Kingdom", "UK", "英国"],
    "德国": ["amazon.de", "Germany", "Deutschland", "德国"],
    "法国": ["amazon.fr", "France", "法国"],
    "日本": ["amazon.co.jp", "Japan", "日本"],
}

ALIEXPRESS_MARKERS = ["aliexpress", "AliExpress", "速卖通"]
OFFICIAL_SITE_MARKERS = ["accsoon", "accsoon.com", "Accsoon", "产品网页", "官网"]
TAOBAO_MARKERS = ["taobao", "淘宝"]
JD_MARKERS = ["jd.com", "jingdong", "京东", "JD"]

REGION_COUNTRY_NAMES = {
    "CN": "中国",
    "US": "美国",
    "CA": "加拿大",
    "MX": "墨西哥",
    "UK": "英国",
    "DE": "德国",
    "FR": "法国",
    "JP": "日本",
}

SHOP_REGION_LINKS = {
    "CA": {
        "shopLinks": {
            "amazon": "https://www.amazon.ca/stores/page/5C870985-EAA7-4870-ACE9-93D7A43096B9",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
    "CN": {
        "shopLinks": {
            "jd": "https://accsoon.jd.com/?cid=0",
            "tmall": "https://shop171333153.taobao.com/",
        },
        "webpageUrl": "https://accsoon.cn/",
    },
    "DE": {
        "shopLinks": {
            "amazon": "https://www.amazon.de/stores/page/47CCBAE8-EE23-4790-B8C8-F7409A557285?ingress=3",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
    "FR": {
        "shopLinks": {
            "amazon": "https://www.amazon.fr/stores/page/C5D389E0-65B6-4769-84D7-349AC7EEA98D?ingress=3",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
    "JP": {
        "shopLinks": {
            "amazon": "https://www.amazon.co.jp/stores/page/6284A2E6-0CCC-4607-B81F-BE8309AB1B49",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
    "MX": {
        "shopLinks": {
            "amazon": "https://www.amazon.com.mx/stores/Accsoonofficialstore/page/D79B31B3-1A8E-4A0B-B8D0-5972809C2E8E?lp_",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
    "UK": {
        "shopLinks": {
            "amazon": "https://www.amazon.co.uk/stores/page/0BDBC522-6A65-473E-8872-40421DF35706",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
    "US": {
        "shopLinks": {
            "amazon": "https://www.amazon.com/stores/page/D34483C1-CA53-4C39-9D89-744AB8F9A19C?ingress=3",
            "aliexpress_app": "https://m.aliexpress.com/store/storeHome.htm?storeNo=1102209313&tracelog=store2mobilestore",
            "aliexpress_web": "https://accsoonofficialstore.aliexpress.com/store/1102209313",
        },
        "webpageUrl": "https://accsoon.com/",
    },
}

LOCAL_DEALER_COUNTRIES = [country for country in COUNTRIES_WITH_CHANNELS if country != CHINA] + [DIRECT_WEB_COUNTRY]

EXPECTED_STORE_LINKS = {
    (country, DIRECT_WEB_CHANNEL): [["accsoon.com"]]
    for country in LOCAL_DEALER_COUNTRIES
}
EXPECTED_STORE_SOURCE_URLS = {
    (country, DIRECT_WEB_CHANNEL): ["https://accsoon.com/"]
    for country in LOCAL_DEALER_COUNTRIES
}

for region, region_config in SHOP_REGION_LINKS.items():
    country = REGION_COUNTRY_NAMES[region]
    shop_links = region_config["shopLinks"]
    if "tmall" in shop_links:
        EXPECTED_STORE_LINKS[(country, "淘宝")] = [[shop_links["tmall"]], ["taobao"], ["淘宝"]]
        EXPECTED_STORE_SOURCE_URLS[(country, "淘宝")] = [shop_links["tmall"]]
    if "jd" in shop_links:
        EXPECTED_STORE_LINKS[(country, "JD")] = [[shop_links["jd"]], ["jd.com"], ["jingdong"], ["京东"]]
        EXPECTED_STORE_SOURCE_URLS[(country, "JD")] = [shop_links["jd"]]
    if "amazon" in shop_links:
        amazon_domain = AMAZON_COUNTRY_MARKERS[country][0]
        EXPECTED_STORE_LINKS[(country, "Amazon")] = [
            [shop_links["amazon"]],
            [amazon_domain, "accsoon"],
            [amazon_domain],
        ]
        EXPECTED_STORE_SOURCE_URLS[(country, "Amazon")] = [shop_links["amazon"]]
    if "aliexpress_app" in shop_links or "aliexpress_web" in shop_links:
        aliexpress_urls = [
            url for url in (shop_links.get("aliexpress_app"), shop_links.get("aliexpress_web")) if url
        ]
        EXPECTED_STORE_LINKS[(country, "AliExpress")] = [
            [shop_links.get("aliexpress_app")],
            [shop_links.get("aliexpress_web")],
            ["aliexpress", "1102209313"],
            ["aliexpress", "accsoon"],
        ]
        EXPECTED_STORE_SOURCE_URLS[(country, "AliExpress")] = aliexpress_urls

COUNTRY_LINK_PREFIXES = {
    "中国": ("cn_",),
    "美国": ("us_",),
    "加拿大": ("ca_",),
    "墨西哥": ("mx_",),
    "英国": ("uk_",),
    "德国": ("de_",),
    "法国": ("fr_",),
    "日本": ("jp_",),
    "其他地区": ("global_",),
}

PRODUCT_PURCHASE_LINKS = {
    "大师4K II": {"url": "null"},
    "SeeMo 4K": {"url": "null"},
    "SeeMo 4k": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "ca_amazon": "https://www.amazon.ca/gp/product/B0FDGN3WHC?th=1",
        "cn_jd": "https://item.jd.com/10161349823178.html",
        "cn_officialproducturl": "https://accsoon.cn/seemo-4k-for-android/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=937681059668&spm=a21dvs.23580594.0.0.4fee2c1buSsgk3",
        "de_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "de_amazon": "https://www.amazon.de/Accsoon-HDMI-zu-USB-Video-Transmitter-Echtzeit-Monitoring-Livestreaming-kompatibel/dp/B0FDK9Z9KD",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "fr_amazon": "https://www.amazon.fr/Accsoon-Transmetteur-Enregistrement-Surveillance-ult%C3%A9rieures/dp/B0FDK9Z9KD",
        "global_officialproducturl": "https://accsoon.cn/seemo-4k-for-android/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0FDKW4V9S?ref_=ast_sto_dp&th=1",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "mx_amazon": "https://www.amazon.com.mx/gp/product/B0FDGMJHLJ?th=1",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "uk_amazon": "https://www.amazon.co.uk/Accsoon-Transmitter-Transmission-Monitoring-Compatible/dp/B0FDKF9HBB",
        "us_aliexpress": "https://www.aliexpress.com/item/1005004837189880.html",
        "us_amazon": "https://www.amazon.com/dp/B0FDKCS2NN",
    },
    "CoMo SE": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "ca_amazon": "https://www.amazon.ca/dp/B0DKNJTMNP",
        "cn_jd": "https://item.jd.com/10187128773918.html",
        "cn_officialproducturl": "https://accsoon.cn/accsoon-como-se/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=981646008175&spm=a21dvs.23580594.0.0.4fee2c1ba9mRkt",
        "de_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "de_amazon": "https://www.amazon.de/dp/B0DK574S7L",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "fr_amazon": "https://www.amazon.fr/dp/B0DK574S7L",
        "global_officialproducturl": "https://accsoon.com/accsoon-como-se/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0DT6LLDXV",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0DK574S7L?th=1",
        "us_aliexpress": "https://www.aliexpress.com/item/1005007997162678.html",
        "us_amazon": "https://www.amazon.com/dp/B0DKNJTMNP",
    },
    "S60 滑轨": {
        "ca_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "ca_amazon": "https://www.amazon.ca/dp/B0GHXP33WS",
        "cn_jd": "https://item.jd.com/10137155287309.html",
        "cn_officialproducturl": "https://accsoon.cn/toprig-s40-s60/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=717963126059&spm=a21dvs.23580594.0.0.4fee2c1ba9mRkt",
        "de_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "de_amazon": "https://www.amazon.de/dp/B0CLD6PBNS",
        "fr_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "fr_amazon": "https://www.amazon.fr/dp/B0CLD6PBNS?th=1",
        "global_officialproducturl": "https://accsoon.com/toprig-s40-s60/",
        "jp_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0D1K26HY7",
        "mx_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "mx_amazon": "https://www.amazon.com.mx/dp/B0CKYLVKPM",
        "uk_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0GJYJ8LC5",
        "us_aliexpress": "https://www.aliexpress.us/item/3256810591993457.html?gatewayAdapt=glo2usa4itemAdapt",
        "us_amazon": "https://www.amazon.com/dp/B0CKYLVKPM",
    },
    "大师4K Lite": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "ca_amazon": "https://www.amazon.ca/dp/B0GRVRDHDF",
        "cn_jd": "https://item.jd.com/10213835365725.html",
        "cn_officialproducturl": "https://accsoon.cn/master-4k-lite/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=1032220135394&spm=a21dvs.23580594.0.0.4fee2c1ba9mRkt",
        "de_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "de_amazon": "https://www.amazon.de/dp/B0GRZYWJFP",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "fr_amazon": "https://www.amazon.fr/dp/B0GRZYWJFP",
        "global_officialproducturl": "https://accsoon.com/cineview-master-4k-lite/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0GS22M1XH",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0GRXS7QSW",
        "us_aliexpress": "https://www.aliexpress.com/item/1005010777430031.html",
        "us_amazon": "https://www.amazon.com/dp/B0GRVRDHDF",
    },
    "CoMo": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "cn_officialproducturl": "https://accsoon.cn/accsoon-como/",
        "de_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "de_amazon": "https://www.amazon.de/dp/B0DB8GK58V",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "fr_amazon": "https://www.amazon.fr/dp/B0DB8GK58V",
        "global_officialproducturl": "https://accsoon.com/accsoon-como/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0DCBB763K",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0DB8GK58V?th=1",
        "us_aliexpress": "https://www.aliexpress.com/item/1005009371832090.html",
        "us_amazon": "https://www.amazon.com/dp/B0DBDD9TD7",
    },
    "M7系列": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "ca_amazon": "https://www.amazon.ca/dp/B0FG2T6R41?th=1",
        "cn_jd": "https://item.jd.com/10163125227903.html",
        "cn_officialproducturl": "https://accsoon.cn/cineview-m7series/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=944739653170&spm=a21dvs.23580594.0.0.4fee2c1ba9mRkt",
        "de_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "de_amazon": "https://www.amazon.de/dp/B0FGDHXVWW?th=1",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "fr_amazon": "https://www.amazon.fr/dp/B0FGDHXVWW",
        "global_officialproducturl": "https://accsoon.com/cineview-m7-series/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0FGJ4JHRV",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0FGDB249Q?th=1",
        "us_aliexpress": "https://www.aliexpress.com/item/1005010180144952.html",
        "us_amazon": "https://www.amazon.com/dp/B0FG2T6R41?th=1",
    },
    "大师 4K": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "ca_amazon": "https://www.amazon.ca/dp/B0FB7ZNHGW",
        "cn_jd": "https://item.jd.com/10117552947120.html",
        "cn_officialproducturl": "https://accsoon.cn/cineview-master-4k/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=836970868622&spm=a21dvs.23580594.0.0.4fee2c1ba9mRkt",
        "de_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "de_amazon": "https://www.amazon.de/dp/B0DJ2VK8KV",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "fr_amazon": "https://www.amazon.fr/dp/B0DJ2VK8KV",
        "global_officialproducturl": "https://accsoon.com/cineview-master-4k/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0DJQH6CV6",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0DJ2VK8KV?th=1",
        "us_aliexpress": "https://www.aliexpress.com/item/1005007872226176.html",
        "us_amazon": "https://www.amazon.com/dp/B0DJ2V1WDK",
    },
    "SE 4K": {
        "ca_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "ca_amazon": "https://www.amazon.ca/dp/B0GLN74JJ5",
        "cn_jd": "https://item.jd.com/10212712894631.html",
        "cn_officialproducturl": "https://accsoon.cn/cineview-se4k/",
        "cn_tmall": "https://item.taobao.com/item.htm?ft=t&id=1027907240962&spm=a21dvs.23580594.0.0.4fee2c1ba9mRkt",
        "de_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "de_amazon": "https://www.amazon.de/dp/B0GL815DRK",
        "fr_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "fr_amazon": "https://www.amazon.fr/dp/B0GL815DRK",
        "global_officialproducturl": "https://accsoon.com/cineview-se-4k/",
        "jp_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "jp_amazon": "https://www.amazon.co.jp/dp/B0GLP4YP8K",
        "mx_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "uk_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "uk_amazon": "https://www.amazon.co.uk/dp/B0GL7VL5MM?th=1",
        "us_aliexpress": "https://www.aliexpress.com/item/1005011703137886.html",
        "us_amazon": "https://www.amazon.com/dp/B0GLN74JJ5",
    },
}


def expected_fragments_from_url(url):
    normalized = str(url or "").strip()
    if not normalized or normalized.lower() in {"null", "none"}:
        return []

    lowered = normalized.lower()
    if "amazon." in lowered and ("/dp/" in lowered or "/gp/product/" in lowered):
        host = lowered.split("//", 1)[-1].split("/", 1)[0].replace("www.", "")
        asin_source = lowered.split("/dp/", 1)[1] if "/dp/" in lowered else lowered.split("/gp/product/", 1)[1]
        asin = asin_source.split("/", 1)[0].split("?", 1)[0]
        return [[host, asin]]

    if "aliexpress." in lowered and "/item/" in lowered:
        item_id = lowered.split("/item/", 1)[1].split(".", 1)[0].split("/", 1)[0].split("?", 1)[0]
        return [["aliexpress", item_id]]

    if "item.jd.com" in lowered:
        item_id = lowered.rsplit("/", 1)[-1].split(".", 1)[0].split("?", 1)[0]
        return [["item.jd.com", item_id], [item_id]]

    if "taobao.com" in lowered:
        match = normalized.split("id=", 1)
        if len(match) > 1:
            item_id = match[1].split("&", 1)[0]
            return [["taobao", item_id], [item_id]]
        return [["taobao"]]

    clean_url = lowered.split("//", 1)[-1].split("?", 1)[0].rstrip("/")
    return [[clean_url]]


def validate_backend_link_config():
    issues = []
    issues.extend(validate_shop_backend_links())
    issues.extend(validate_product_backend_links())
    return issues


def validate_shop_backend_links():
    issues = []
    expected_regions = set(REGION_COUNTRY_NAMES)
    actual_regions = set(SHOP_REGION_LINKS)
    for region in sorted(expected_regions - actual_regions):
        issues.append(f"店铺后台缺少地区：{region}")

    for region, config in SHOP_REGION_LINKS.items():
        country = REGION_COUNTRY_NAMES.get(region)
        shop_links = config.get("shopLinks", {})
        webpage_url = config.get("webpageUrl")
        if not country:
            issues.append(f"店铺后台地区未映射到国家：{region}")
            continue
        if not valid_http_url(webpage_url):
            issues.append(f"{region} webpageUrl 不是有效 http(s) 链接：{webpage_url}")
        elif region == "CN" and urlparse(webpage_url).netloc.lower() != "accsoon.cn":
            issues.append(f"{region} webpageUrl 应为 accsoon.cn：{webpage_url}")
        elif region != "CN" and urlparse(webpage_url).netloc.lower() != "accsoon.com":
            issues.append(f"{region} webpageUrl 应为 accsoon.com：{webpage_url}")

        for key, url in shop_links.items():
            if not valid_http_url(url):
                issues.append(f"{region}.{key} 不是有效 http(s) 链接：{url}")
                continue
            parsed = urlparse(url)
            host = parsed.netloc.lower().replace("www.", "")
            if key == "amazon":
                expected_domain = AMAZON_COUNTRY_MARKERS[country][0]
                if host != expected_domain:
                    issues.append(f"{region}.amazon 域名应为 {expected_domain}：{url}")
                if "stores" not in parsed.path.lower() or "page" not in parsed.path.lower():
                    issues.append(f"{region}.amazon 不是 Amazon 店铺页链接：{url}")
            elif key == "aliexpress_app":
                query = parse_qs(parsed.query)
                if query.get("storeNo", [""])[0] != "1102209313":
                    issues.append(f"{region}.aliexpress_app storeNo 应为 1102209313：{url}")
            elif key == "aliexpress_web":
                if host != "accsoonofficialstore.aliexpress.com" or "1102209313" not in parsed.path:
                    issues.append(f"{region}.aliexpress_web 应为官方 AliExpress 店铺 1102209313：{url}")
            elif key == "jd":
                if host != "accsoon.jd.com":
                    issues.append(f"{region}.jd 应为 accsoon.jd.com：{url}")
            elif key == "tmall":
                if host != "shop171333153.taobao.com":
                    issues.append(f"{region}.tmall 应为 shop171333153.taobao.com：{url}")
            else:
                issues.append(f"{region} 存在未知店铺链接字段：{key}")

    return issues


def validate_product_backend_links():
    issues = []
    expected_countries = set(COUNTRY_LINK_PREFIXES)
    for product in FEATURED_PRODUCTS:
        if product not in PRODUCT_PURCHASE_LINKS:
            issues.append(f"产品后台缺少主打产品：{product}")

    for product, links in PRODUCT_PURCHASE_LINKS.items():
        if not isinstance(links, dict):
            issues.append(f"{product} purchaseLinks 不是对象")
            continue

        for key, url in links.items():
            if str(url).strip().lower() in {"null", "none", ""}:
                continue
            if not valid_http_url(url):
                issues.append(f"{product}.{key} 不是有效 http(s) 链接：{url}")
                continue
            issues.extend(validate_product_link_field(product, key, url))

        for country, prefixes in COUNTRY_LINK_PREFIXES.items():
            has_country_link = any(
                any(key.startswith(prefix) for prefix in prefixes)
                and str(url).strip().lower() not in {"null", "none", ""}
                for key, url in links.items()
            )
            if product in FEATURED_PRODUCTS and not has_country_link:
                missing_expected = (country, product) in EXPECTED_MISSING_FEATURED_PRODUCT_LINKS
                if not missing_expected:
                    issues.append(f"{product} 缺少 {country} 链接，且未标记为预期缺失")

    for country, product in EXPECTED_MISSING_FEATURED_PRODUCT_LINKS:
        if country not in expected_countries:
            issues.append(f"预期缺失产品链接中存在未知国家：{country} / {product}")
        if product not in FEATURED_PRODUCTS:
            issues.append(f"预期缺失产品链接中存在非主打产品：{country} / {product}")

    return issues


def validate_product_link_field(product, key, url):
    issues = []
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    lowered_key = key.lower()
    region_prefix = lowered_key.split("_", 1)[0] if "_" in lowered_key else ""
    expected_amazon_domains = {
        "ca": "amazon.ca",
        "de": "amazon.de",
        "fr": "amazon.fr",
        "jp": "amazon.co.jp",
        "mx": "amazon.com.mx",
        "uk": "amazon.co.uk",
        "us": "amazon.com",
    }

    if lowered_key.endswith("_amazon"):
        expected_domain = expected_amazon_domains.get(region_prefix)
        if expected_domain and host != expected_domain:
            issues.append(f"{product}.{key} Amazon 域名应为 {expected_domain}：{url}")
        if not re.search(r"/(dp|gp/product)/[A-Z0-9]{10}", parsed.path, re.IGNORECASE):
            issues.append(f"{product}.{key} Amazon 链接缺少有效 ASIN：{url}")
    elif lowered_key.endswith("_aliexpress"):
        if "aliexpress." not in host:
            issues.append(f"{product}.{key} 应为 AliExpress 链接：{url}")
        if not re.search(r"/item/\d+", parsed.path, re.IGNORECASE):
            issues.append(f"{product}.{key} AliExpress 链接缺少 item id：{url}")
    elif lowered_key.endswith("_jd"):
        if host != "item.jd.com":
            issues.append(f"{product}.{key} JD 商品链接域名应为 item.jd.com：{url}")
        if not re.search(r"/\d+\.html$", parsed.path):
            issues.append(f"{product}.{key} JD 链接缺少商品 id：{url}")
    elif lowered_key.endswith("_tmall"):
        if "taobao.com" not in host:
            issues.append(f"{product}.{key} 淘宝/天猫商品链接域名异常：{url}")
        if "id=" not in parsed.query:
            issues.append(f"{product}.{key} 淘宝/天猫链接缺少 id 参数：{url}")
    elif lowered_key.endswith("_officialproducturl"):
        expected_hosts = {"accsoon.cn"} if lowered_key.startswith("cn_") else {"accsoon.com"}
        if product == "SeeMo 4k":
            expected_hosts.add("accsoon.cn")
        if host not in expected_hosts:
            issues.append(f"{product}.{key} 官网域名应为 {' 或 '.join(sorted(expected_hosts))}：{url}")
        if not parsed.path.strip("/"):
            issues.append(f"{product}.{key} 官网链接缺少产品路径：{url}")
    else:
        issues.append(f"{product} 存在未知产品链接字段：{key}")

    return issues


def valid_http_url(url):
    parsed = urlparse(str(url or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def official_product_link_key_for_country(country):
    return "cn_officialproducturl" if country == CHINA else "global_officialproducturl"


def expected_product_link_values(links, keys):
    expected_options = []
    expected_source_urls = []
    for key in keys:
        url = links.get(key)
        expected_options.extend(expected_fragments_from_url(url))
        if str(url or "").strip().lower() not in {"null", "none", ""}:
            expected_source_urls.append(url)
    return expected_options, expected_source_urls


def channel_product_link_keys(country, channel):
    country_prefix = COUNTRY_LINK_PREFIXES[country][0]
    if channel == "淘宝":
        return [f"{country_prefix}tmall"]
    if channel == "JD":
        return [f"{country_prefix}jd"]
    if channel == "Amazon":
        return [f"{country_prefix}amazon"]
    if channel == "AliExpress":
        return [f"{country_prefix}aliexpress"]
    return []


EXPECTED_PRODUCT_LINKS = {}
EXPECTED_PRODUCT_SOURCE_URLS = {}
EXPECTED_PRODUCT_LINKS_BY_CHANNEL = {}
EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL = {}
EXPECTED_MISSING_FEATURED_PRODUCT_LINKS = set()
EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS = set()
for product, links in PRODUCT_PURCHASE_LINKS.items():
    for country, prefixes in COUNTRY_LINK_PREFIXES.items():
        expected_options = []
        expected_source_urls = []
        for key, url in links.items():
            if any(key.startswith(prefix) for prefix in prefixes):
                expected_options.extend(expected_fragments_from_url(url))
                if str(url).strip().lower() not in {"null", "none", ""}:
                    expected_source_urls.append(url)
        if expected_options:
            EXPECTED_PRODUCT_LINKS[(country, product)] = expected_options
            EXPECTED_PRODUCT_SOURCE_URLS[(country, product)] = expected_source_urls
        elif product in FEATURED_PRODUCTS:
            EXPECTED_MISSING_FEATURED_PRODUCT_LINKS.add((country, product))

    for country, channels in FEATURED_PRODUCT_CHANNELS_BY_COUNTRY.items():
        for channel in channels:
            link_keys = channel_product_link_keys(country, channel)
            expected_options, expected_source_urls = expected_product_link_values(links, link_keys)
            if not expected_options:
                expected_options, expected_source_urls = expected_product_link_values(
                    links,
                    [official_product_link_key_for_country(country)],
                )

            if expected_options:
                EXPECTED_PRODUCT_LINKS_BY_CHANNEL[(country, channel, product)] = expected_options
                EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL[(country, channel, product)] = expected_source_urls
            elif product in FEATURED_PRODUCTS:
                EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS.add((country, channel, product))


def build_android_options():
    options = UiAutomator2Options()
    options.platform_name = "Android"
    if PLATFORM_VERSION:
        options.platform_version = PLATFORM_VERSION
    options.device_name = DEVICE_NAME
    if DEVICE_UDID:
        options.udid = DEVICE_UDID
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.no_reset = True
    options.ensure_webviews_have_pages = True
    options.native_web_screenshot = True
    options.new_command_timeout = 180
    options.connect_hardware_keyboard = True
    options.set_capability("uiautomator2ServerLaunchTimeout", UIAUTOMATOR2_SERVER_LAUNCH_TIMEOUT)
    options.set_capability("uiautomator2ServerInstallTimeout", UIAUTOMATOR2_SERVER_INSTALL_TIMEOUT)
    options.set_capability("adbExecTimeout", ADB_EXEC_TIMEOUT)
    for env_value, capability in (
        (APPIUM_SYSTEM_PORT, "systemPort"),
        (APPIUM_CHROMEDRIVER_PORT, "chromedriverPort"),
        (APPIUM_MJPEG_SERVER_PORT, "mjpegServerPort"),
    ):
        port = optional_int(env_value)
        if port:
            options.set_capability(capability, port)
    if SKIP_UIAUTOMATOR2_SERVER_INSTALL:
        options.set_capability("skipServerInstallation", True)
    return options


def build_ios_options():
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.set_capability("automationName", "XCUITest")
    if PLATFORM_VERSION:
        options.platform_version = PLATFORM_VERSION
    options.device_name = DEVICE_NAME
    if DEVICE_UDID:
        options.udid = DEVICE_UDID
    if IOS_APP_PATH:
        options.app = IOS_APP_PATH
    elif IOS_BUNDLE_ID:
        options.bundle_id = IOS_BUNDLE_ID
    if IOS_WEB_DRIVER_AGENT_URL:
        options.set_capability("webDriverAgentUrl", IOS_WEB_DRIVER_AGENT_URL)
    options.no_reset = True
    options.new_command_timeout = 180
    options.set_capability("autoAcceptAlerts", True)
    options.set_capability("includeSafariInWebviews", True)
    options.set_capability("safariAllowPopups", True)
    options.set_capability("showXcodeLog", IOS_SHOW_XCODE_LOG)
    options.set_capability("wdaLaunchTimeout", IOS_WDA_LAUNCH_TIMEOUT)
    options.set_capability("wdaConnectionTimeout", IOS_WDA_CONNECTION_TIMEOUT)
    port = optional_int(IOS_WDA_LOCAL_PORT)
    if port:
        options.set_capability("wdaLocalPort", port)
    if IOS_UPDATED_WDA_BUNDLE_ID:
        options.set_capability("updatedWDABundleId", IOS_UPDATED_WDA_BUNDLE_ID)
    if IOS_XCODE_ORG_ID:
        options.set_capability("xcodeOrgId", IOS_XCODE_ORG_ID)
    if IOS_XCODE_SIGNING_ID:
        options.set_capability("xcodeSigningId", IOS_XCODE_SIGNING_ID)
    if IOS_USE_PREINSTALLED_WDA:
        options.set_capability("usePreinstalledWDA", True)
    if IOS_USE_PREBUILT_WDA:
        options.set_capability("usePrebuiltWDA", True)
    options.set_capability("useNewWDA", IOS_USE_NEW_WDA)
    return options


def build_driver_options():
    if is_ios_platform():
        return build_ios_options()
    if is_android_platform():
        return build_android_options()
    raise ValueError(f"Unsupported PLATFORM_NAME: {PLATFORM_NAME}")
