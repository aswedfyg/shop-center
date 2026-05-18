# -*- coding: utf-8 -*-

from appium.webdriver.common.appiumby import AppiumBy

from common.config import APP_PACKAGE


def product_center_title_locators():
    titles = ["产品中心", "Accsoon News"]
    locators = []
    for title in titles:
        locators.extend(
            [
                (AppiumBy.ACCESSIBILITY_ID, title),
                (AppiumBy.XPATH, f"//*[@content-desc='{title}' or @text='{title}']"),
            ]
        )
    return locators


def country_dropdown_locators(current_country):
    return [
        (AppiumBy.ACCESSIBILITY_ID, f"购买渠道\n{current_country}\n{current_country}"),
        (AppiumBy.ACCESSIBILITY_ID, f"购买渠道 {current_country} {current_country}"),
        (
            AppiumBy.XPATH,
            f"//*[contains(@content-desc, '购买渠道') and contains(@content-desc, '{current_country}')]",
        ),
    ]


def selected_country_locators(country):
    return [
        (AppiumBy.ACCESSIBILITY_ID, f"购买渠道\n{country}\n{country}"),
        (AppiumBy.ACCESSIBILITY_ID, f"购买渠道 {country} {country}"),
        (
            AppiumBy.XPATH,
            f"//*[contains(@content-desc, '购买渠道') and contains(@content-desc, '{country}')]",
        ),
    ]


def country_option_locators(country):
    return [
        (AppiumBy.XPATH, f"//android.widget.Button[@content-desc='{country}']"),
        (AppiumBy.ACCESSIBILITY_ID, country),
    ]


def country_dropdown_opened_locators():
    return [
        (AppiumBy.XPATH, "//*[@content-desc='美国']"),
        (AppiumBy.ACCESSIBILITY_ID, "美国"),
        (AppiumBy.XPATH, "//*[@content-desc='其他地区']"),
        (AppiumBy.ACCESSIBILITY_ID, "其他地区"),
    ]


def channel_locators(channel):
    aliases = {
        "JD": ["JD", "京东"],
        "本地经销商": ["本地经销商", "Local Dealer"],
    }.get(channel, [channel])

    locators = []
    for alias in aliases:
        locators.extend(
            [
                (AppiumBy.XPATH, f"(//*[@content-desc='{alias}' or @text='{alias}'])[last()]"),
                (AppiumBy.ACCESSIBILITY_ID, alias),
            ]
        )
    for alias in aliases:
        locators.append(
            (
                AppiumBy.XPATH,
                f"(//*[contains(@content-desc, '{alias}') or contains(@text, '{alias}')])[last()]",
            )
        )
    return locators


def featured_product_channel_locators(channel):
    desc = {
        "Amazon": "Ama.",
        "AliExpress": "Ali.",
    }.get(channel, channel)
    return [
        (AppiumBy.XPATH, f"(//*[@content-desc='{desc}'])[1]"),
    ]


def product_locators(product):
    return [
        (AppiumBy.ACCESSIBILITY_ID, product),
        (AppiumBy.XPATH, f"//*[@content-desc='{product}']"),
    ]


def home_menu_locators():
    return [(AppiumBy.ID, f"{APP_PACKAGE}:id/menu_btn")]
