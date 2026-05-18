# -*- coding: utf-8 -*-

import socket
import subprocess
import time
import unittest
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.parse import unquote, urlparse

from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from product_center_config import (
    AFTER_CLICK_TIMEOUT,
    ALIEXPRESS_MARKERS,
    ALL_COUNTRIES,
    AMAZON_COUNTRY_MARKERS,
    APPIUM_AUTO_START,
    APPIUM_COMMAND,
    APPIUM_HTTP_TIMEOUT,
    APP_ACTIVITY,
    APP_PACKAGE,
    APPIUM_SERVER_URL,
    APPIUM_START_TIMEOUT,
    BASE_SCREEN_HEIGHT,
    BASE_SCREEN_WIDTH,
    BROWSER_PACKAGES,
    CHINA,
    COUNTRY_CHANNELS,
    COUNTRY_DROPDOWN_TAP_X,
    COUNTRY_DROPDOWN_TAP_Y,
    DIRECT_WEB_CHANNEL,
    DIRECT_WEB_COUNTRY,
    EXPECTED_MISSING_CHANNEL_LINKS,
    EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS,
    EXPECTED_MISSING_FEATURED_PRODUCT_LINKS,
    EXPECTED_PRODUCT_LINKS_BY_CHANNEL,
    EXPECTED_PRODUCT_LINKS,
    EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL,
    EXPECTED_PRODUCT_SOURCE_URLS,
    EXPECTED_STORE_LINKS,
    EXPECTED_STORE_SOURCE_URLS,
    FEATURED_PRODUCT_CHANNELS_BY_COUNTRY,
    FEATURED_PRODUCT_END_AT,
    FEATURED_PRODUCT_MAX_CASES,
    FEATURED_PRODUCT_START_AT,
    FEATURED_CHANNEL_SWITCH_WAIT,
    FEATURED_PRODUCT_COUNTRIES,
    FEATURED_PRODUCTS,
    HARD_RESET_AFTER_JUMP,
    JD_MARKERS,
    CHANNEL_JUMP_MAX_CASES,
    MAX_SESSION_RECREATES_PER_TEST,
    OFFICIAL_SITE_MARKERS,
    PRODUCT_CENTER_RUN_MODE,
    PRODUCT_TEXT_FALLBACK,
    RELAXED_EXTERNAL_BROWSER_CHECK,
    RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP,
    RESTORE_TIMEOUT,
    SHOPPING_APP_PACKAGES,
    SHORT_TIMEOUT,
    STRICT_PRODUCT_DESTINATION,
    STRICT_OFFICIAL_PRODUCT_URL,
    TAOBAO_MARKERS,
    WAIT_TIMEOUT,
    adb_command,
    build_driver_options,
    is_android_platform,
    validate_backend_link_config,
)
import product_center_locators as locators


class DeviceConnectionUnavailable(RuntimeError):
    pass


class ProductCenterAutomationCase(unittest.TestCase):
    __test__ = False
    supports_click_gesture = True
    appium_process = None
    backend_links_checked = False

    def setUp(self):
        self.assert_backend_links_valid()
        print("开始配置 Appium 驱动...")
        self.ensure_appium_server_running()
        self.session_recreated = False
        self.session_recreate_count = 0
        self.device_connection_unavailable = False
        try:
            self.create_driver_session()
        except DeviceConnectionUnavailable as exc:
            self.device_connection_unavailable = True
            raise AssertionError(str(exc)) from exc
        print("Appium 服务器连接成功")

    @classmethod
    def assert_backend_links_valid(cls):
        if cls.backend_links_checked:
            return
        issues = validate_backend_link_config()
        if issues:
            shown = "\n".join(f"- {issue}" for issue in issues[:30])
            remaining = len(issues) - 30
            if remaining > 0:
                shown += f"\n- 另有 {remaining} 个问题未展示"
            raise AssertionError(f"后台数据库链接配置校验失败：\n{shown}")
        cls.backend_links_checked = True

    def create_driver_session(self, retries=3):
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                if is_android_platform():
                    self.cleanup_uiautomator2_processes()
                RemoteConnection.set_timeout(APPIUM_HTTP_TIMEOUT)
                self.driver = webdriver.Remote(APPIUM_SERVER_URL, options=build_driver_options())
                self.wait = WebDriverWait(self.driver, WAIT_TIMEOUT)
                return
            except Exception as exc:
                last_error = exc
                if self.is_device_connection_error(exc):
                    raise DeviceConnectionUnavailable(
                        "ADB 设备连接不可用：设备 offline/unauthorized。请在手机上确认 USB 调试授权，"
                        "必要时执行 adb kill-server 后重新插拔设备，再重跑用例。"
                    ) from exc
                if attempt < retries:
                    if is_android_platform() and self.is_recoverable_session_error(exc):
                        self.cleanup_uiautomator2_processes()
                    print(f"Appium session 创建失败，重试第 {attempt + 1} 次：{self.short_error(exc)}")
                    time.sleep(2)
        raise last_error

    def cleanup_uiautomator2_processes(self):
        for package in ("io.appium.uiautomator2.server", "io.appium.uiautomator2.server.test"):
            try:
                subprocess.run(
                    adb_command("shell", "am", "force-stop", package),
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except Exception:
                pass

    def recreate_driver_session(self):
        if getattr(self, "session_recreate_count", 0) >= MAX_SESSION_RECREATES_PER_TEST:
            self.device_connection_unavailable = True
            print("Appium session 重建次数已达上限，停止后续步骤")
            return False

        self.session_recreated = True
        self.session_recreate_count = getattr(self, "session_recreate_count", 0) + 1
        print(f"Appium session 已失效，自动重建（第 {self.session_recreate_count} 次）")
        try:
            if getattr(self, "driver", None):
                self.driver.quit()
        except Exception:
            pass
        try:
            self.create_driver_session(retries=2)
        except DeviceConnectionUnavailable as exc:
            self.device_connection_unavailable = True
            raise AssertionError(str(exc)) from exc
        except Exception as exc:
            if self.is_recoverable_session_error(exc):
                self.device_connection_unavailable = True
                print(f"Appium session 重建失败，停止后续步骤：{self.short_error(exc)}")
                return False
            raise
        return True

    @classmethod
    def ensure_appium_server_running(cls):
        parsed = urlparse(APPIUM_SERVER_URL)
        host = parsed.hostname
        port = parsed.port
        if not host or not port or cls.can_connect(host, port):
            return

        if not APPIUM_AUTO_START or host not in {"127.0.0.1", "localhost"}:
            return

        base_path = parsed.path or "/"
        print(f"Appium 服务未启动，自动启动：{host}:{port}{base_path}")
        cls.appium_process = cls.start_appium_server(host, port, base_path)
        deadline = time.time() + APPIUM_START_TIMEOUT
        while time.time() < deadline:
            if cls.can_connect(host, port):
                return
            if cls.appium_process.poll() is not None:
                raise RuntimeError("Appium 自动启动失败：进程已退出，请确认 Appium 2 已安装并可通过 cmd /c appium 运行")
            time.sleep(0.5)
        raise RuntimeError(f"Appium 自动启动超时：{host}:{port}")

    @staticmethod
    def can_connect(host, port):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            return False

    @staticmethod
    def start_appium_server(host, port, base_path):
        command = [
            "cmd",
            "/c",
            APPIUM_COMMAND,
            "server",
            "--address",
            host,
            "--port",
            str(port),
            "--base-path",
            base_path,
            "--log-level",
            "info",
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

    def tearDown(self):
        if getattr(self, "driver", None):
            try:
                self.close_country_dropdown_if_open()
                self.driver.quit()
            except WebDriverException as exc:
                print(f"退出 Appium session 时设备已不可用，忽略清理异常：{self.short_error(exc)}")

    def test_01_enter_product_center(self):
        print("开始测试：进入产品中心")
        self.open_product_center()
        self.assert_visible_any(self.product_center_title_locators(), "产品中心标题")
        self.assert_visible(AppiumBy.ACCESSIBILITY_ID, "CoMo SE")
        if not self.has_country_selected(CHINA, timeout=SHORT_TIMEOUT):
            self.select_country(CHINA)
        self.assert_country_selected(CHINA)

    def test_02_country_dropdown_options(self):
        print("开始测试：国家下拉菜单")
        self.open_product_center()
        self.open_country_dropdown(CHINA)

        for country in ALL_COUNTRIES:
            with self.subTest(country=country):
                self.assert_visible_any(self.country_option_locators(country), f"国家选项：{country}")

    def test_02_country_switch_updates_purchase_channels(self):
        print("开始测试：连续切换国家后购买渠道展示")
        self.open_product_center()

        for country in [CHINA, "美国", "日本", DIRECT_WEB_COUNTRY, CHINA]:
            self.abort_if_device_unavailable()
            with self.subTest(country=country):
                self.select_country(country)
                self.assert_country_selected(country)
                self.assert_purchase_channels_visible(country)

    def test_02_purchase_channels_display(self):
        print("开始测试：各国家购买渠道展示")
        self.open_product_center()

        for country in ALL_COUNTRIES:
            self.abort_if_device_unavailable()
            with self.subTest(country=country):
                self.select_country(country)
                self.assert_country_selected(country)
                self.assert_purchase_channels_visible(country)

    def test_03_purchase_channels_jump(self):
        print("开始测试：各国家购买渠道跳转")
        if PRODUCT_CENTER_RUN_MODE == "smoke":
            print("当前为 smoke 模式：购买渠道跳转按代表性样本执行")
        self.open_product_center()

        checked_cases = 0
        for country, channels in COUNTRY_CHANNELS.items():
            self.abort_if_device_unavailable()
            self.select_country(country)
            self.assert_country_selected(country)
            for channel in channels:
                self.abort_if_device_unavailable()
                with self.subTest(country=country, channel=channel):
                    if self.channel_jump_case_limit_reached(checked_cases):
                        print(f"购买渠道跳转已达到上限：{checked_cases}，提前结束")
                        return
                    if self.is_expected_missing_channel_link(country, channel):
                        self.skipTest(f"{country} 的 {channel} 购买链接未配置，按已知缺失跳过")
                    checked_cases += 1
                    try:
                        self.assert_visible_any(self.channel_locators(channel), f"{country} 渠道：{channel}")
                        self.assert_channel_opens_external_purchase_page(country, channel)
                    except AssertionError:
                        self.recover_product_center_after_failed_jump(country)
                        raise
                    self.ensure_product_center_ready(country)
                if getattr(self, "device_connection_unavailable", False):
                    print("设备/Appium 会话已不可用，停止购买渠道跳转剩余子用例")
                    return

    def test_04_featured_products_jump(self):
        print("开始测试：主打产品跳转")
        if PRODUCT_CENTER_RUN_MODE == "smoke":
            print("当前为 smoke 模式：主打产品跳转只执行代表性国家/产品")
        if FEATURED_PRODUCT_START_AT:
            print(f"主打产品跳转从断点开始：{FEATURED_PRODUCT_START_AT}")
        if FEATURED_PRODUCT_END_AT:
            print(f"主打产品跳转到断点结束：{FEATURED_PRODUCT_END_AT}")
        print(
            "本次主打产品范围："
            f"国家={FEATURED_PRODUCT_COUNTRIES}，"
            f"渠道={FEATURED_PRODUCT_CHANNELS_BY_COUNTRY}，"
            f"产品={FEATURED_PRODUCTS}，"
            f"最大用例数={FEATURED_PRODUCT_MAX_CASES or '不限'}"
        )
        self.open_product_center()

        checked_cases = 0
        reached_start = not FEATURED_PRODUCT_START_AT
        for country in FEATURED_PRODUCT_COUNTRIES:
            self.abort_if_device_unavailable()
            self.select_country(country)
            self.assert_country_selected(country)
            for channel in FEATURED_PRODUCT_CHANNELS_BY_COUNTRY.get(country, []):
                self.abort_if_device_unavailable()
                self.select_featured_product_channel(country, channel)
                for product in FEATURED_PRODUCTS:
                    self.abort_if_device_unavailable()
                    with self.subTest(country=country, channel=channel, product=product):
                        case_key = self.featured_product_case_key(country, channel, product)
                        if not reached_start:
                            if self.case_key_matches(case_key, FEATURED_PRODUCT_START_AT):
                                reached_start = True
                            else:
                                continue
                        if self.featured_product_case_limit_reached(checked_cases):
                            print(f"主打产品跳转已达到上限：{checked_cases}，提前结束")
                            return
                        if self.is_expected_missing_featured_product_channel_link(country, channel, product):
                            self.skipTest(f"{country} 的 {channel} / {product} 购买链接未配置，按已知缺失跳过")
                        checked_cases += 1
                        try:
                            self.ensure_featured_product_ready(product)
                            self.assert_product_opens_external_purchase_page(country, channel, product)
                        except AssertionError:
                            self.recover_product_center_after_failed_jump(country)
                            raise
                        self.ensure_product_center_ready(country)
                        self.select_featured_product_channel(country, channel)
                        if FEATURED_PRODUCT_END_AT and self.case_key_matches(case_key, FEATURED_PRODUCT_END_AT):
                            print(f"主打产品跳转已到结束断点：{FEATURED_PRODUCT_END_AT}")
                            return

    def test_04_featured_products_display(self):
        print("开始测试：主打产品列表展示")
        self.open_product_center()
        if not self.has_country_selected(CHINA, timeout=SHORT_TIMEOUT):
            self.select_country(CHINA)
        self.assert_country_selected(CHINA)

        for product in FEATURED_PRODUCTS:
            with self.subTest(product=product):
                self.assert_featured_product_visible(product)

    def test_05_other_region_direct_jump(self):
        print("开始测试：其他地区直接跳转")
        self.open_product_center()
        if not self.has_country_selected(DIRECT_WEB_COUNTRY, timeout=SHORT_TIMEOUT):
            self.select_country(DIRECT_WEB_COUNTRY)
        self.assert_country_selected(DIRECT_WEB_COUNTRY)
        self.assert_visible_any(self.channel_locators(DIRECT_WEB_CHANNEL), f"{DIRECT_WEB_COUNTRY} 渠道：{DIRECT_WEB_CHANNEL}")
        self.assert_direct_web_channel_opens_official_site()
        self.ensure_product_center_ready(DIRECT_WEB_COUNTRY)
        self.assert_other_region_featured_products_open_official_site()

    def assert_other_region_featured_products_open_official_site(self):
        checked_cases = 0
        for product in FEATURED_PRODUCTS:
            self.abort_if_device_unavailable()
            with self.subTest(country=DIRECT_WEB_COUNTRY, channel="主打产品官网", product=product):
                if self.featured_product_case_limit_reached(checked_cases):
                    print(f"其他地区主打产品官网跳转已达到上限：{checked_cases}，提前结束")
                    return
                if self.is_expected_missing_featured_product_link(DIRECT_WEB_COUNTRY, product):
                    self.skipTest(f"{DIRECT_WEB_COUNTRY} 的 {product} 官网产品链接未配置，按已知缺失跳过")
                checked_cases += 1
                try:
                    self.assert_visible_any(self.product_locators(product), f"{DIRECT_WEB_COUNTRY} 主打产品：{product}")
                    self.assert_product_opens_external_purchase_page(DIRECT_WEB_COUNTRY, DIRECT_WEB_CHANNEL, product)
                except AssertionError:
                    self.recover_product_center_after_failed_jump(DIRECT_WEB_COUNTRY)
                    raise
                self.ensure_product_center_ready(DIRECT_WEB_COUNTRY)

    def is_expected_missing_channel_link(self, country, channel):
        return (country, channel) in EXPECTED_MISSING_CHANNEL_LINKS

    def is_expected_missing_featured_product_link(self, country, product):
        return (country, product) in EXPECTED_MISSING_FEATURED_PRODUCT_LINKS

    def is_expected_missing_featured_product_channel_link(self, country, channel, product):
        return (country, channel, product) in EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS

    def expected_purchase_channels(self, country):
        return COUNTRY_CHANNELS.get(country, [DIRECT_WEB_CHANNEL])

    def assert_purchase_channels_visible(self, country):
        for channel in self.expected_purchase_channels(country):
            self.assert_visible_any(self.channel_locators(channel), f"{country} 渠道：{channel}")

    def assert_featured_product_visible(self, product):
        if self.ensure_featured_product_ready(product, fail=False):
            return
        self.assert_visible_any(self.product_locators(product), f"主打产品：{product}")

    def ensure_featured_product_ready(self, product, fail=True):
        if self.featured_product_semantics_visible(product) or self.exists_any(self.product_locators(product), timeout=SHORT_TIMEOUT):
            return True

        for direction in ("down", "up", "up", "down"):
            self.scroll_featured_products_grid(direction)
            if self.featured_product_semantics_visible(product) or self.exists_any(self.product_locators(product), timeout=SHORT_TIMEOUT):
                return True

        if fail:
            self.fail(f"元素不可见：主打产品：{product}")
        return False

    def featured_product_semantics_visible(self, product):
        return self.find_flutter_semantics_node([product], section_desc="主打产品", prefer="top_left") is not None

    def scroll_featured_products_grid(self, direction):
        screen_width, screen_height = self.screen_size()
        left = int(screen_width * 0.05)
        top = int(screen_height * 0.35)
        width = int(screen_width * 0.90)
        height = int(screen_height * 0.50)
        try:
            self.driver.execute_script(
                "mobile: swipeGesture",
                {"left": left, "top": top, "width": width, "height": height, "direction": direction, "percent": 0.28},
            )
        except WebDriverException:
            x = int(screen_width * 0.50)
            if direction == "up":
                self.w3c_swipe_location(x, int(screen_height * 0.75), x, int(screen_height * 0.52))
            else:
                self.w3c_swipe_location(x, int(screen_height * 0.52), x, int(screen_height * 0.75))
        time.sleep(0.3)

    def channel_jump_case_limit_reached(self, checked_cases):
        limit = CHANNEL_JUMP_MAX_CASES
        if limit <= 0 and PRODUCT_CENTER_RUN_MODE == "smoke":
            limit = 4
        return limit > 0 and checked_cases >= limit

    def featured_product_case_limit_reached(self, checked_cases):
        limit = FEATURED_PRODUCT_MAX_CASES
        if limit <= 0 and PRODUCT_CENTER_RUN_MODE == "smoke":
            limit = 8
        return limit > 0 and checked_cases >= limit

    def featured_product_case_key(self, country, channel, product):
        return (country, channel, product)

    def case_key_matches(self, case_key, value):
        parts = [part.strip() for part in str(value or "").split("|")]
        return len(parts) == len(case_key) and tuple(parts) == tuple(case_key)

    def abort_if_device_unavailable(self):
        if getattr(self, "device_connection_unavailable", False):
            raise AssertionError(
                "ADB 设备连接已不可用，本条测试提前终止；请重新确认 USB 调试授权后从断点继续运行。"
            )

    def recover_product_center_after_failed_jump(self, country):
        if self.safe_current_package() == APP_PACKAGE and self.is_product_center_visible(timeout=SHORT_TIMEOUT):
            return
        try:
            self.ensure_product_center_ready(country)
        except AssertionError as exc:
            print(f"失败用例恢复产品中心未完成，继续保留原始失败：{self.short_error(exc)}")

    def open_product_center(self):
        self.close_country_dropdown_if_open()
        self.close_ad_if_present()

        if self.is_product_center_visible(timeout=SHORT_TIMEOUT):
            print("当前已在产品中心")
            return

        if not self.is_home_page_visible(timeout=SHORT_TIMEOUT):
            self.safe_activate_app(APP_PACKAGE)
            self.wait_for_app_landing()

        if self.is_product_center_visible(timeout=SHORT_TIMEOUT):
            print("当前已在产品中心")
            return

        self.click(AppiumBy.ID, f"{APP_PACKAGE}:id/menu_btn", "菜单按钮")
        self.assert_visible_any(self.product_center_title_locators(), "产品中心标题")
        print("进入产品中心成功")

    def close_ad_if_present(self, timeout=SHORT_TIMEOUT):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((AppiumBy.ID, f"{APP_PACKAGE}:id/adDialogCancel"))
            ).click()
            print("已关闭广告弹窗")
        except TimeoutException:
            pass
        except WebDriverException as exc:
            if self.is_recoverable_session_error(exc):
                self.recreate_driver_session()
                return
            print(f"检查广告弹窗时 Appium 暂不可用：{self.short_error(exc)}")

    def close_country_dropdown_if_open(self):
        try:
            if not self.country_dropdown_opened():
                return
            self.click_any(
                [(AppiumBy.ACCESSIBILITY_ID, "关闭菜单"), (AppiumBy.XPATH, "//*[@content-desc='关闭菜单']")],
                "关闭国家下拉菜单",
                after_click=lambda: not self.country_dropdown_opened(),
            )
        except Exception:
            try:
                self.driver.back()
            except Exception:
                pass

    def open_country_dropdown(self, current_country):
        if not self.has_country_selected(current_country, timeout=0.5):
            current_country = self.get_current_country_hint()
        label = f"{current_country} 国家下拉菜单"
        self.scroll_country_dropdown_into_clickable_area(current_country)
        if self.click_country_dropdown_by_flutter_semantics(current_country, label):
            return
        if self.open_flutter_country_dropdown(current_country, label):
            return
        try:
            self.click_any(
                self.country_dropdown_locators(current_country),
                label,
                after_click=self.country_dropdown_opened,
            )
            return
        except AssertionError as first_error:
            self.scroll_purchase_channel_section_into_view()
            if self.open_flutter_country_dropdown(current_country, label):
                return
            try:
                self.click_any(
                    self.country_dropdown_locators(current_country),
                    label,
                    after_click=self.country_dropdown_opened,
                )
                return
            except AssertionError:
                raise first_error

    def scroll_country_dropdown_into_clickable_area(self, current_country):
        node = self.find_country_dropdown_semantics_node(current_country)
        if not node or not node["bounds"]:
            return
        _, top, _, bottom = node["bounds"]
        _, screen_height = self.screen_size()
        if top > screen_height * 0.78 or bottom > screen_height * 0.98:
            print(f"国家下拉语义节点位置过低，先滚动到可点击区域：bounds={node['bounds']}")
            self.scroll_purchase_channel_section_into_view()

    def scroll_purchase_channel_section_into_view(self):
        for _ in range(2):
            screen_width, screen_height = self.screen_size()
            left = int(screen_width * 0.07)
            top = int(screen_height * 0.32)
            width = int(screen_width * 0.86)
            height = int(screen_height * 0.48)
            try:
                self.driver.execute_script(
                    "mobile: swipeGesture",
                    {"left": left, "top": top, "width": width, "height": height, "direction": "up", "percent": 0.35},
                )
            except WebDriverException:
                x = int(screen_width * 0.50)
                self.w3c_swipe_location(x, int(screen_height * 0.74), x, int(screen_height * 0.54))
            time.sleep(0.3)

    def click_country_dropdown_by_flutter_semantics(self, current_country, label):
        node = self.find_country_dropdown_semantics_node(current_country)
        if not node or not node["bounds"]:
            return False

        left, top, right, bottom = node["bounds"]
        width = right - left
        height = bottom - top
        points = [
            (int(left + width * 0.84), int(top + height * 0.12), "Flutter语义右上国家区域"),
            (int(left + width * 0.90), int(top + height * 0.12), "Flutter语义右上箭头区域"),
            (int(left + width * 0.50), int(top + height * 0.12), "Flutter语义标题行中部"),
        ]
        for x, y, point_name in points:
            if self.tap_location_and_confirm(x, y, f"{label}（{point_name}）", self.country_dropdown_opened):
                print(f"Flutter 语义定位：{label} content-desc={node['desc']} bounds={node['bounds']}")
                return True
            if self.adb_tap_location_and_confirm(x, y, f"{label}（{point_name}）", self.country_dropdown_opened):
                print(f"Flutter 语义定位：{label} content-desc={node['desc']} bounds={node['bounds']}")
                return True
        return False

    def find_country_dropdown_semantics_node(self, current_country):
        candidates = []
        for node in self.flutter_semantics_nodes():
            desc = node["desc"]
            if not node["bounds"] or node["visible"] is False:
                continue
            if "购买渠道" not in desc or current_country not in desc:
                continue
            candidates.append(node)
        if not candidates:
            return None
        return sorted(candidates, key=lambda node: self.bounds_area(node["bounds"]), reverse=True)[0]

    def open_flutter_country_dropdown(self, current_country, label):
        for by, value in self.country_dropdown_locators(current_country):
            try:
                element = WebDriverWait(self.driver, SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((by, value))
                )
            except Exception:
                continue

            for x, y, point_name in self.country_dropdown_tap_points(element):
                if self.tap_location_and_confirm(x, y, f"{label}（{point_name}）", self.country_dropdown_opened):
                    return True
                if self.adb_tap_location_and_confirm(x, y, f"{label}（{point_name}）", self.country_dropdown_opened):
                    return True

        fallback_points = [
            self.scale_point(COUNTRY_DROPDOWN_TAP_X, COUNTRY_DROPDOWN_TAP_Y),
            self.scale_point(1209, 2228),
            self.scale_point(1296, 2228),
            self.scale_point(720, 2475),
        ]
        tried_points = set()
        for x, y in fallback_points:
            if (x, y) in tried_points:
                continue
            tried_points.add((x, y))
            if self.tap_location_and_confirm(x, y, label, self.country_dropdown_opened):
                return True
            if self.adb_tap_location_and_confirm(x, y, label, self.country_dropdown_opened):
                return True
        return False

    def country_dropdown_tap_points(self, element):
        rect = element.rect
        left = int(rect["x"])
        top = int(rect["y"])
        width = int(rect["width"])
        height = int(rect["height"])
        return [
            (int(left + width * 0.84), int(top + height * 0.12), "右上国家区域"),
            (int(left + width * 0.90), int(top + height * 0.12), "右上箭头区域"),
            (int(left + width * 0.50), int(top + height * 0.12), "标题行中部"),
            (int(left + width * 0.50), int(top + height * 0.50), "语义节点中心"),
        ]

    def select_country(self, country):
        for attempt in range(1, 3):
            if self.has_country_selected(country, timeout=0.5):
                print(f"已选择国家：{country}")
                return
            current_country = self.get_current_country_hint()
            self.open_country_dropdown(current_country)
            self.click_any(self.country_option_locators(country), f"国家选项：{country}")
            if self.wait_for_country_selected(country, timeout=WAIT_TIMEOUT):
                print(f"已选择国家：{country}")
                return
            print(f"国家切换到 {country} 后未确认选中态，恢复页面后重试（第 {attempt} 次）")
            self.ensure_product_center_ready(current_country)
        raise AssertionError(f"国家未切换到：{country}")

    def wait_for_country_selected(self, country, timeout=WAIT_TIMEOUT):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.has_country_selected(country, timeout=0.5):
                    return True
            except WebDriverException as exc:
                if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                    return False
                raise
            except Exception as exc:
                if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                    return False
                raise
            time.sleep(0.3)
        return False

    def select_featured_product_channel(self, country, channel):
        if channel not in FEATURED_PRODUCT_CHANNELS_BY_COUNTRY.get(country, []):
            return
        label = f"主打产品渠道：{channel}"
        condition = lambda: self.safe_current_package() == APP_PACKAGE and self.is_product_center_visible(timeout=0.3)
        if not self.click_featured_product_channel_by_flutter_semantics(channel, label, condition):
            self.click_any(
                self.featured_product_channel_locators(channel),
                label,
                after_click=condition,
            )
        time.sleep(FEATURED_CHANNEL_SWITCH_WAIT)

    def select_country_expect_external_jump(self, country):
        before = self.navigation_snapshot()
        current_country = self.get_current_country_hint()
        self.open_country_dropdown(current_country)
        if country == DIRECT_WEB_COUNTRY:
            self.click_direct_web_country_option(before, current_country)
        else:
            self.click_any(
                self.country_option_locators(country),
                f"国家选项：{country}",
                after_click=lambda: self.external_navigation_status(before) is not None,
                after_click_timeout=3,
            )
        jump_type = self.wait_for_external_navigation(before, f"选择 {country} 后没有跳转到外部购买页或网页", timeout=20)
        print(f"{country} 已直接跳转：{jump_type}")

    def click_direct_web_country_option(self, before, current_country):
        label = f"国家选项：{DIRECT_WEB_COUNTRY}"

        try:
            self.click_any(self.country_option_locators(DIRECT_WEB_COUNTRY), label)
            if self.wait_for_redirect_notice_or_external(before, timeout=20):
                return
        except AssertionError:
            pass

        condition = lambda: self.redirect_notice_visible() or self.external_navigation_status(before) is not None

        if self.tap_country_option_regions(DIRECT_WEB_COUNTRY, label, condition):
            self.wait_for_external_navigation(before, f"选择 {DIRECT_WEB_COUNTRY} 后没有跳转到官网", timeout=20)
            return

        if not self.country_dropdown_opened():
            self.open_country_dropdown(current_country)

        fallback_points = [
            self.scale_point(1140, 2825),
            self.scale_point(1035, 2825),
            self.scale_point(1245, 2825),
            self.scale_point(1140, 2882),
        ]
        for x, y in fallback_points:
            if self.tap_location_and_confirm(x, y, f"{label}（固定兜底）", condition, after_click_timeout=4):
                self.wait_for_external_navigation(before, f"选择 {DIRECT_WEB_COUNTRY} 后没有跳转到官网", timeout=20)
                return
            if self.adb_tap_location_and_confirm(x, y, f"{label}（固定兜底）", condition, after_click_timeout=4):
                self.wait_for_external_navigation(before, f"选择 {DIRECT_WEB_COUNTRY} 后没有跳转到官网", timeout=20)
                return

        raise AssertionError(f"未找到或无法点击：{label}")

    def wait_for_redirect_notice_or_external(self, before, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.redirect_notice_visible():
                remaining = max(1, int(deadline - time.time()))
                self.wait_for_external_navigation(before, "出现跳转提示后没有打开官网", timeout=remaining)
                return True
            if self.external_navigation_status(before) is not None:
                return True
            time.sleep(0.5)
        return False

    def wait_for_external_navigation(self, before, message, timeout=WAIT_TIMEOUT, channel=None):
        try:
            return WebDriverWait(self.driver, timeout, poll_frequency=0.5).until(
                lambda _: self.external_navigation_status(before, channel=channel)
            )
        except TimeoutException as exc:
            raise AssertionError(message) from exc

    def redirect_notice_visible(self):
        return self.exists_any(
            [
                (AppiumBy.XPATH, "//*[contains(@text, '正在为您跳转') or contains(@content-desc, '正在为您跳转')]"),
                (AppiumBy.XPATH, "//*[contains(@text, '产品网页') or contains(@content-desc, '产品网页')]"),
                (AppiumBy.XPATH, "//*[contains(@text, '暂无销售') or contains(@content-desc, '暂无销售')]"),
                (AppiumBy.XPATH, "//*[contains(@text, '官网') or contains(@content-desc, '官网')]"),
            ],
            timeout=0.3,
        )

    def tap_country_option_regions(self, country, label, after_click):
        for by, value in self.country_option_locators(country):
            try:
                element = WebDriverWait(self.driver, SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((by, value))
                )
            except Exception:
                continue

            rect = element.rect
            left = int(rect["x"])
            top = int(rect["y"])
            width = int(rect["width"])
            height = int(rect["height"])
            points = [
                (left + int(width * 0.50), top + int(height * 0.25), "上半区"),
                (left + int(width * 0.25), top + int(height * 0.50), "左侧"),
                (left + int(width * 0.75), top + int(height * 0.50), "右侧"),
                (left + int(width * 0.50), top + int(height * 0.50), "中心"),
            ]
            for x, y, point_name in points:
                if self.tap_location_and_confirm(x, y, f"{label}（{point_name}）", after_click, after_click_timeout=4):
                    return True
                if self.adb_tap_location_and_confirm(x, y, f"{label}（{point_name}）", after_click, after_click_timeout=4):
                    return True
        return False

    def assert_channel_opens_external_purchase_page(self, country, channel):
        before = self.navigation_snapshot()
        self.prepare_destination_observation()
        self.click_purchase_channel(
            channel,
            f"购买渠道：{channel}",
            lambda: self.redirect_notice_visible() or self.external_navigation_status(before, channel=channel) is not None,
        )
        expected_urls = EXPECTED_STORE_SOURCE_URLS.get((country, channel), [])
        jump_type = self.assert_external_navigation_started(
            before,
            f"点击 {country} {channel} 后没有跳转到购物 App 或网页。后台原始链接={expected_urls}",
            channel=channel,
        )
        self.handle_post_jump_prompts(country, channel)
        self.assert_destination_matches(country, channel)
        print(f"{channel} 跳转成功：{jump_type}")

    def click_purchase_channel(self, channel, label, after_click):
        try:
            self.click_any(
                self.channel_locators(channel),
                label,
                after_click=after_click,
                after_click_timeout=5,
            )
            return
        except AssertionError as first_error:
            print(f"购买渠道首次点击失败，滚动渠道区域后重试：{channel}，{self.short_error(first_error)}")

        self.scroll_purchase_channel_section_into_view()
        try:
            self.click_any(
                self.channel_locators(channel),
                label,
                after_click=after_click,
                after_click_timeout=5,
            )
            return
        except AssertionError as second_error:
            if self.click_purchase_channel_by_flutter_semantics(channel, label, after_click):
                return
            raise AssertionError(f"未找到或无法点击：{label}（滚动和语义坐标兜底均失败）") from second_error

    def assert_direct_web_channel_opens_official_site(self):
        before = self.navigation_snapshot()
        self.prepare_destination_observation()
        self.click_purchase_channel(
            DIRECT_WEB_CHANNEL,
            f"购买渠道：{DIRECT_WEB_CHANNEL}",
            lambda: self.redirect_notice_visible() or self.external_navigation_status(before) is not None,
        )
        jump_type = self.wait_for_external_navigation(before, f"点击 {DIRECT_WEB_CHANNEL} 后没有跳转到官网", timeout=20)
        expected_links = EXPECTED_STORE_LINKS.get((DIRECT_WEB_COUNTRY, DIRECT_WEB_CHANNEL))
        if expected_links:
            self.assert_expected_destination_link(
                f"{DIRECT_WEB_COUNTRY} {DIRECT_WEB_CHANNEL}",
                expected_links,
                expected_source_urls=EXPECTED_STORE_SOURCE_URLS.get((DIRECT_WEB_COUNTRY, DIRECT_WEB_CHANNEL)),
            )
        else:
            self.assert_official_site_destination(DIRECT_WEB_CHANNEL)
        print(f"{DIRECT_WEB_CHANNEL} 跳转成功：{jump_type}")

    def assert_product_opens_external_purchase_page(self, country, channel, product):
        before = self.navigation_snapshot()
        if RESET_EXTERNAL_APPS_BEFORE_PRODUCT_JUMP:
            self.reset_external_apps_before_jump()
        self.prepare_destination_observation()
        condition = lambda: self.redirect_notice_visible() or self.external_navigation_status(before, channel=channel) is not None
        label = f"主打产品：{product}"
        if not self.click_featured_product_by_flutter_semantics(product, label, condition):
            self.click_any(
                self.product_locators(product),
                label,
                after_click=condition,
                after_click_timeout=5,
            )
        jump_type = self.assert_external_navigation_started(before, f"点击 {country} {channel} / {product} 后没有跳转到产品购买页或网页", channel=channel)
        self.handle_post_jump_prompts(country, channel)
        self.assert_product_destination_matches(country, channel, product)
        print(f"{channel} / {product} 跳转成功：{jump_type}")

    def reset_external_apps_before_jump(self):
        current_package = self.safe_current_package()
        for package in sorted((set(BROWSER_PACKAGES) | set(SHOPPING_APP_PACKAGES)) - {APP_PACKAGE}):
            if package == current_package:
                continue
            self.adb_force_stop_package(package)

    def adb_force_stop_package(self, package):
        try:
            subprocess.run(
                adb_command("shell", "am", "force-stop", package),
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            pass

    def handle_post_jump_prompts(self, country, channel):
        if channel != "Amazon":
            return

        if self.click_amazon_country_switch_if_present():
            print(f"Amazon 已确认切换到 {country} 对应站点")
            self.wait_amazon_country_dialog_closed()
            self.wait_amazon_page_loaded()

    def click_amazon_country_switch_if_present(self):
        yes_locators = [
            (AppiumBy.XPATH, "//*[@text='YES' or @content-desc='YES']"),
            (AppiumBy.XPATH, "//android.widget.Button[@text='YES' or @content-desc='YES']"),
            (AppiumBy.XPATH, "//*[contains(@text, 'YES') or contains(@content-desc, 'YES')]"),
            (AppiumBy.XPATH, "//*[@text='SI' or @text='SÍ' or @content-desc='SI' or @content-desc='SÍ']"),
            (AppiumBy.XPATH, "//android.widget.Button[@text='SI' or @text='SÍ' or @content-desc='SI' or @content-desc='SÍ']"),
            (AppiumBy.XPATH, "//*[contains(@text, 'SI') or contains(@text, 'SÍ') or contains(@content-desc, 'SI') or contains(@content-desc, 'SÍ')]"),
            (AppiumBy.XPATH, "//*[@text='Yes' or @content-desc='Yes']"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Yes') or contains(@content-desc, 'Yes')]"),
            (AppiumBy.XPATH, "//*[@text='Sí' or @text='Si' or @content-desc='Sí' or @content-desc='Si']"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Sí') or contains(@text, 'Si') or contains(@content-desc, 'Sí') or contains(@content-desc, 'Si')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Continue') or contains(@content-desc, 'Continue')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Switch') or contains(@content-desc, 'Switch')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Change') or contains(@content-desc, 'Change')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'OK') or contains(@content-desc, 'OK')]"),
            (AppiumBy.XPATH, "//*[contains(@text, '确认') or contains(@content-desc, '确认')]"),
            (AppiumBy.XPATH, "//*[contains(@text, '确定') or contains(@content-desc, '确定')]"),
            (AppiumBy.XPATH, "//*[contains(@text, '继续') or contains(@content-desc, '继续')]"),
            (AppiumBy.XPATH, "//*[contains(@text, '切换') or contains(@content-desc, '切换')]"),
            (AppiumBy.XPATH, "//*[contains(@text, '是') or contains(@content-desc, '是')]"),
        ]

        if not self.amazon_change_country_dialog_visible():
            return False

        for locator in yes_locators:
            try:
                element = WebDriverWait(self.driver, SHORT_TIMEOUT).until(
                    EC.presence_of_element_located(locator)
                )
                self.tap_element_center(element)
                print("检测到 Amazon 国家/地区切换弹框，已点击确认按钮")
                return True
            except Exception:
                continue
        return False

    def amazon_change_country_dialog_visible(self):
        dialog_locators = [
            (AppiumBy.XPATH, "//*[contains(@text, 'Change country') or contains(@content-desc, 'Change country')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Change countries') or contains(@content-desc, 'Change countries')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'This screen is available') or contains(@content-desc, 'This screen is available')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'United States') or contains(@content-desc, 'United States')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Cambiar país') or contains(@content-desc, 'Cambiar país')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Cambiar pais') or contains(@content-desc, 'Cambiar pais')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Esta pantalla') or contains(@content-desc, 'Esta pantalla')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Reino Unido') or contains(@content-desc, 'Reino Unido')]"),
            (AppiumBy.XPATH, "//*[contains(@text, 'Cambiar país y continuar') or contains(@content-desc, 'Cambiar país y continuar')]"),
        ]
        if self.exists_any(dialog_locators, timeout=SHORT_TIMEOUT):
            return True

        has_confirm = self.exists_any(
            [
                (AppiumBy.XPATH, "//*[@text='YES' or @text='Yes' or @text='SI' or @text='SÍ' or @text='Sí' or @text='Si']"),
                (AppiumBy.XPATH, "//*[@content-desc='YES' or @content-desc='Yes' or @content-desc='SI' or @content-desc='SÍ' or @content-desc='Sí' or @content-desc='Si']"),
            ],
            timeout=0.5,
        )
        has_cancel = self.exists_any(
            [
                (AppiumBy.XPATH, "//*[@text='NO' or @text='No' or @content-desc='NO' or @content-desc='No']"),
            ],
            timeout=0.5,
        )
        return has_confirm and has_cancel

    def wait_amazon_country_dialog_closed(self):
        try:
            WebDriverWait(self.driver, WAIT_TIMEOUT, poll_frequency=0.5).until(
                lambda _: not self.amazon_change_country_dialog_visible()
            )
            print("Amazon 国家/地区切换弹框已关闭")
        except TimeoutException as exc:
            raise AssertionError("点击确认后 Amazon 国家/地区切换弹框没有关闭") from exc

    def wait_amazon_page_loaded(self):
        try:
            WebDriverWait(self.driver, WAIT_TIMEOUT, poll_frequency=0.5).until(
                lambda _: self.safe_current_package() == "com.amazon.mShop.android.shopping"
                and not self.amazon_change_country_dialog_visible()
                and len(self.safe_page_source()) > 500
            )
        except TimeoutException as exc:
            raise AssertionError(
                f"Amazon 确认切换后页面没有加载完成。"
                f"package={self.safe_current_package()}, activity={self.safe_current_activity()}, "
                f"source={self.safe_page_source()[:500]}"
            ) from exc

    def assert_destination_matches(self, country, channel):
        expected_links = EXPECTED_STORE_LINKS.get((country, channel))
        if expected_links:
            self.assert_expected_destination_link(
                f"{country} {channel}",
                expected_links,
                self.expected_packages_for_channel(channel),
                EXPECTED_STORE_SOURCE_URLS.get((country, channel)),
            )
            return

        if channel == "Amazon":
            self.assert_amazon_destination(country)
        elif channel == "AliExpress":
            self.assert_channel_destination("AliExpress", {"com.alibaba.aliexpresshd"}, ALIEXPRESS_MARKERS)
        elif channel == "淘宝":
            self.assert_channel_destination("淘宝", {"com.taobao.taobao"}, TAOBAO_MARKERS)
        elif channel == "JD":
            self.assert_channel_destination("JD/京东", {"com.jd.jrapp", "com.jingdong.app.mall"}, JD_MARKERS)

    def assert_amazon_destination(self, country):
        current_package = self.safe_current_package()
        if current_package not in (None, "com.amazon.mShop.android.shopping") and current_package not in BROWSER_PACKAGES:
            self.fail(f"Amazon 跳转目标不正确：当前 package={current_package}")

        if self.amazon_change_country_dialog_visible():
            self.fail(f"Amazon 仍停留在国家/地区切换弹框，未进入 {country} 对应商品页面")

        expected_markers = AMAZON_COUNTRY_MARKERS.get(country, ["Amazon", "amazon"])
        if self.amazon_page_contains_country_marker(expected_markers, timeout=WAIT_TIMEOUT):
            print(f"Amazon 页面国家校验通过：{country}，命中 {expected_markers}")
            return

        source = self.safe_page_source()
        if self.amazon_change_country_dialog_visible():
            self.fail(f"Amazon 仍停留在国家/地区切换弹框，未进入 {country} 对应商品页面")

        lower_source = source.lower()
        wrong_markers = []
        for other_country, markers in AMAZON_COUNTRY_MARKERS.items():
            if other_country == country:
                continue
            if any(marker.lower() in lower_source for marker in markers):
                wrong_markers.append(other_country)

        if wrong_markers:
            self.fail(f"Amazon 国家校验失败：期望 {country}，但页面像是 {wrong_markers}")

        self.fail(
            f"Amazon 页面未识别到 {country} 的国家/域名标识。"
            f"package={current_package}, activity={self.safe_current_activity()}, source={source[:500]}"
        )

    def amazon_page_contains_country_marker(self, markers, timeout=SHORT_TIMEOUT):
        deadline = time.time() + timeout
        lowered_markers = [marker.lower() for marker in markers]
        while time.time() < deadline:
            if not self.amazon_change_country_dialog_visible():
                source = self.safe_page_source().lower()
                if any(marker in source for marker in lowered_markers):
                    return True
            time.sleep(0.5)
        return False

    def assert_page_contains_any(self, markers, label):
        if not self.page_contains_any(markers, timeout=WAIT_TIMEOUT):
            self.fail(
                f"{label} 跳转目标校验失败：未识别到 {markers}。"
                f"package={self.safe_current_package()}, activity={self.safe_current_activity()}, "
                f"source={self.safe_page_source()[:500]}"
            )
        print(f"{label} 跳转目标校验通过")

    def assert_channel_destination(self, label, expected_packages, markers):
        current_package = self.safe_current_package()
        if current_package in expected_packages:
            print(f"{label} App 目标校验通过：package={current_package}")
            return

        if current_package == APP_PACKAGE and self.is_product_center_visible(timeout=0.5):
            self.fail(f"{label} 跳转失败：点击后仍停留在产品中心，可能当前地区没有配置购买链接")

        self.assert_page_contains_any(markers, label)

    def assert_product_destination_matches(self, country, channel, product):
        expected_links = EXPECTED_PRODUCT_LINKS_BY_CHANNEL.get((country, channel, product))
        if expected_links:
            label = f"{country} {channel} {product}"
            try:
                self.assert_expected_destination_link(
                    label,
                    expected_links,
                    self.expected_packages_for_channel(channel),
                    EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL.get((country, channel, product)),
                    allow_native_app_without_product_match=False,
                    native_app_unconfirmed_message=(
                        f"{label} 平台正确但商品未确认：已打开目标购物 App，"
                        "但未命中商品 ID、链接片段或产品关键词。"
                    ),
                )
            except AssertionError:
                if STRICT_PRODUCT_DESTINATION and PRODUCT_TEXT_FALLBACK:
                    evidence = self.product_text_fallback_evidence(country, channel, product)
                    if evidence:
                        print(f"{label} 商品文字兜底校验通过：{evidence}")
                        return
                    if self.amazon_native_app_url_hidden_fallback_matches(channel, expected_links):
                        print(f"{label} Amazon 原生 App URL 不可观测兜底校验通过：已打开 Amazon App，但页面未暴露 ASIN/完整 URL")
                        return
                if STRICT_PRODUCT_DESTINATION:
                    self.fail_strict_product_destination(
                        label,
                        expected_links,
                        EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL.get((country, channel, product)),
                    )
                if self.product_native_app_content_matches(channel, product):
                    print(f"{label} 原生购物 App 页面内容兜底校验通过：package 正确且命中产品关键词")
                    return
                if self.product_browser_fallback_matches(country, channel, product):
                    print(f"{label} 页面内容兜底校验通过：命中渠道和产品关键词")
                    return
                if self.product_external_browser_fallback_matches(
                    expected_links,
                    EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL.get((country, channel, product)),
                ):
                    print(f"{label} 浏览器外跳兜底校验通过：已打开外部浏览器，Edge 未暴露完整商品 URL")
                    return
                raise
            return

        expected_links = EXPECTED_PRODUCT_LINKS.get((country, product))
        if expected_links:
            expected_source_urls = EXPECTED_PRODUCT_SOURCE_URLS.get((country, product))
            try:
                self.assert_expected_destination_link(
                    f"{country} {product}",
                    expected_links,
                    expected_source_urls=expected_source_urls,
                )
            except AssertionError:
                if STRICT_PRODUCT_DESTINATION and PRODUCT_TEXT_FALLBACK:
                    evidence = self.product_text_fallback_evidence(country, DIRECT_WEB_CHANNEL, product)
                    if evidence:
                        print(f"{country} {product} 商品文字兜底校验通过：{evidence}")
                        return
                if STRICT_PRODUCT_DESTINATION:
                    self.fail_strict_product_destination(f"{country} {product}", expected_links, expected_source_urls)
                if country == DIRECT_WEB_COUNTRY and self.official_product_browser_fallback_matches(
                    product,
                    expected_source_urls,
                ):
                    print(f"{country} {product} 官网页面兜底校验通过：Edge 未暴露完整 URL，已确认打开外部浏览器")
                    return
                raise
            return

        current_package = self.safe_current_package()
        if country in (CHINA, DIRECT_WEB_COUNTRY):
            self.assert_official_site_destination(product)
            return

        if current_package == "com.amazon.mShop.android.shopping":
            self.assert_amazon_destination(country)
            return
        if current_package == "com.alibaba.aliexpresshd":
            print(f"{product} AliExpress App 目标校验通过：package={current_package}")
            return

        expected_markers = AMAZON_COUNTRY_MARKERS.get(country, []) + ALIEXPRESS_MARKERS
        if expected_markers and self.page_contains_any(expected_markers, timeout=WAIT_TIMEOUT):
            print(f"{product} 产品链接目标校验通过：{country}")
            return

        self.fail(
            f"{product} 产品链接目标校验失败：未识别到 {country} 对应 Amazon 或 AliExpress 标识。"
            f"package={current_package}, activity={self.safe_current_activity()}, source={self.safe_page_source()[:500]}"
        )

    def fail_strict_product_destination(self, label, expected_options, expected_source_urls=None):
        observed_urls = self.observed_destination_urls()
        challenge_hint = "；当前疑似登录/滑块/安全验证页" if self.browser_login_or_challenge_visible() else ""
        self.fail(
            f"{label} 严格商品目标校验失败{challenge_hint}：未命中后台商品 ID/ASIN/item id/官网 slug。"
            f"预期片段={expected_options}，后台原始链接={expected_source_urls or []}。"
            f"package={self.safe_current_package()}, activity={self.safe_current_activity()}, "
            f"实际观测链接={observed_urls}, url={self.safe_current_url()}, source={self.safe_page_source()[:500]}"
        )

    def product_text_fallback_evidence(self, country, channel, product):
        package = self.safe_current_package()
        in_expected_app = package in self.expected_packages_for_channel(channel)
        in_browser = package in BROWSER_PACKAGES
        if not in_expected_app and not in_browser:
            return ""

        source_text = self.safe_page_source()
        ocr_text = self.safe_screenshot_ocr_text()
        combined_text = "\n".join(part for part in [source_text, ocr_text] if part)
        if not combined_text:
            return ""
        if self.browser_login_or_challenge_visible(combined_text):
            return ""

        normalized = self.normalize_match_text(combined_text)
        product_markers = self.product_content_markers(product)
        matched_product = [marker for marker in product_markers if marker and marker in normalized]
        if not matched_product:
            return ""

        if in_browser:
            channel_markers = {
                "Amazon": AMAZON_COUNTRY_MARKERS.get(country, ["amazon"]),
                "AliExpress": ALIEXPRESS_MARKERS,
                "淘宝": TAOBAO_MARKERS,
                "JD": JD_MARKERS + ["jd_header", "jdkey"],
                DIRECT_WEB_CHANNEL: OFFICIAL_SITE_MARKERS,
            }.get(channel, [])
            normalized_channel_markers = [self.normalize_match_text(marker) for marker in channel_markers]
            if normalized_channel_markers and not any(marker and marker in normalized for marker in normalized_channel_markers):
                return ""

        normalized_ocr = self.normalize_match_text(ocr_text)
        evidence_source = "OCR" if normalized_ocr and any(marker in normalized_ocr for marker in matched_product) else "页面文本"
        return f"{evidence_source} 命中产品关键词 {matched_product[:3]}，package={package}"

    def safe_screenshot_ocr_text(self):
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return ""
        try:
            image = Image.open(BytesIO(self.driver.get_screenshot_as_png()))
            image = image.convert("L")
            return pytesseract.image_to_string(image, lang="eng+chi_sim") or ""
        except Exception as exc:
            print(f"OCR 文字兜底不可用，跳过：{self.short_error(exc)}")
            return ""

    def product_browser_fallback_matches(self, country, channel, product):
        if self.safe_current_package() not in BROWSER_PACKAGES:
            return False

        source = self.normalize_match_text(self.safe_page_source())
        channel_markers = {
            "Amazon": AMAZON_COUNTRY_MARKERS.get(country, ["amazon"]),
            "AliExpress": ALIEXPRESS_MARKERS,
            "淘宝": TAOBAO_MARKERS,
            "JD": JD_MARKERS + ["jd_header", "jdkey"],
        }.get(channel, [])
        normalized_channel_markers = [self.normalize_match_text(marker) for marker in channel_markers]
        if not any(marker and marker in source for marker in normalized_channel_markers):
            return False

        product_markers = self.product_content_markers(product)
        return bool(product_markers) and any(marker in source for marker in product_markers)

    def product_native_app_content_matches(self, channel, product):
        current_package = self.safe_current_package()
        if current_package not in self.expected_packages_for_channel(channel):
            return False
        source = self.normalize_match_text(self.safe_page_source())
        if not source:
            return False
        product_markers = self.product_content_markers(product)
        return bool(product_markers) and any(marker in source for marker in product_markers)

    def product_external_browser_fallback_matches(self, expected_options=None, expected_source_urls=None):
        current_package = self.safe_current_package()
        if current_package not in BROWSER_PACKAGES:
            return False
        if expected_options and self.destination_contains_expected_fragments(
            expected_options,
            timeout=SHORT_TIMEOUT,
            include_page_source=False,
        ):
            return True
        source = self.safe_page_source()
        if not source:
            return False
        lowered = source.lower()
        if "chrome-error://" in lowered or "err_" in lowered:
            return False
        if RELAXED_EXTERNAL_BROWSER_CHECK and self.expected_urls_are_external_http_links(expected_source_urls):
            return True
        if self.browser_login_or_challenge_visible(source):
            return False
        return False

    def amazon_native_app_url_hidden_fallback_matches(self, channel, expected_options):
        if channel != "Amazon":
            return False
        if self.safe_current_package() != "com.amazon.mShop.android.shopping":
            return False
        if self.destination_contains_expected_fragments(
            expected_options,
            timeout=0.5,
            include_page_source=True,
        ):
            return False
        source = self.safe_page_source()
        lowered = source.lower()
        if self.browser_login_or_challenge_visible(source):
            return False
        if "amazon" not in lowered and self.safe_current_activity() != "com.amazon.mShop.navigation.MainActivity":
            return False
        return True

    def official_product_browser_fallback_matches(self, product, expected_source_urls=None):
        if self.safe_current_package() not in BROWSER_PACKAGES:
            return False
        if not self.expected_urls_are_official_site(expected_source_urls):
            return False

        source = self.safe_page_source()
        if not source:
            return False
        lowered = source.lower()
        if "chrome-error://" in lowered or "err_" in lowered:
            return False
        if self.browser_login_or_challenge_visible(source):
            return False
        if not STRICT_OFFICIAL_PRODUCT_URL and not self.observed_destination_urls() and not self.safe_current_url():
            return True

        normalized_source = self.normalize_match_text(source)
        official_markers = [self.normalize_match_text(marker) for marker in OFFICIAL_SITE_MARKERS]
        if not any(marker and marker in normalized_source for marker in official_markers):
            return False

        for option in self.official_product_match_options(product, expected_source_urls):
            normalized_option = [self.normalize_match_text(marker) for marker in option if marker]
            if normalized_option and all(marker in normalized_source for marker in normalized_option):
                return True
        return False

    def official_product_match_options(self, product, expected_source_urls):
        options = []
        for url in expected_source_urls or []:
            parsed = urlparse(str(url or ""))
            if parsed.netloc.lower().replace("www.", "") not in {"accsoon.com", "accsoon.cn"}:
                continue
            slug = parsed.path.strip("/").split("/", 1)[0]
            if slug:
                options.append([slug])

        product_options = {
            "CoMo SE": [["como", "se"], ["accsoon", "como", "se"]],
            "S60 滑轨": [["s60"], ["toprig", "s60"], ["s40", "s60"]],
            "大师4K Lite": [["master", "4k", "lite"], ["大师", "4k", "lite"]],
            "SE 4K": [["se", "4k"], ["cineview", "se", "4k"]],
            "大师 4K": [["master", "4k"], ["大师", "4k"]],
            "SeeMo 4k": [["seemo", "4k"], ["seemo", "android"]],
            "M7系列": [["m7"], ["m7", "series"]],
            "CoMo": [["como"], ["accsoon", "como"]],
        }
        options.extend(product_options.get(product, []))
        return options

    def expected_urls_are_official_site(self, expected_source_urls):
        urls = [url for url in expected_source_urls or [] if str(url or "").strip()]
        if not urls:
            return False
        for url in urls:
            parsed = urlparse(str(url))
            if parsed.netloc.lower().replace("www.", "") not in {"accsoon.com", "accsoon.cn"}:
                return False
        return True

    def expected_urls_are_external_http_links(self, expected_source_urls):
        urls = [url for url in expected_source_urls or [] if str(url or "").strip()]
        if not urls:
            return False
        for url in urls:
            parsed = urlparse(str(url))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return False
        return True

    def browser_login_or_challenge_visible(self, source=None):
        text = self.normalize_match_text(source if source is not None else self.safe_page_source())
        markers = (
            "请拖动下方滑块完成验证",
            "右滑动验证",
            "滑块完成验证",
            "通过验证以确保正常访问",
            "sign in",
            "log in",
            "login",
            "captcha",
            "security check",
            "verify",
        )
        return any(self.normalize_match_text(marker) in text for marker in markers)

    def product_content_markers(self, product):
        aliases = {
            "CoMo SE": ["como", "se", "se耳机"],
            "S60 滑轨": ["s60", "滑轨", "s40"],
            "大师4K Lite": ["master", "大师", "4k", "lite"],
            "SE 4K": ["se", "4k"],
            "大师 4K": ["master", "大师", "4k"],
            "SeeMo 4k": ["seemo", "4k", "android"],
            "M7系列": ["m7", "m7系列"],
            "CoMo": ["como"],
        }
        if product in aliases:
            return aliases[product]
        return [
            token
            for token in re.findall(r"[a-z0-9]+", self.normalize_match_text(product))
            if len(token) >= 2
        ]

    def assert_official_site_destination(self, label):
        if self.page_contains_any(OFFICIAL_SITE_MARKERS + [label], timeout=WAIT_TIMEOUT):
            print(f"{label} 官网链接目标校验通过")
            return
        self.fail(
            f"{label} 官网链接目标校验失败：未识别到官网标识。"
            f"package={self.safe_current_package()}, activity={self.safe_current_activity()}, source={self.safe_page_source()[:500]}"
        )

    def expected_packages_for_channel(self, channel):
        if channel == "Amazon":
            return {"com.amazon.mShop.android.shopping"}
        if channel == "AliExpress":
            return {"com.alibaba.aliexpresshd"}
        if channel == "淘宝":
            return {"com.taobao.taobao"}
        if channel == "JD":
            return {"com.jd.jrapp", "com.jingdong.app.mall"}
        return set()

    def assert_expected_destination_link(
        self,
        label,
        expected_options,
        expected_packages=None,
        expected_source_urls=None,
        allow_native_app_without_product_match=True,
        native_app_unconfirmed_message=None,
    ):
        expected_packages = expected_packages or set()
        current_package = self.safe_current_package()
        if current_package == APP_PACKAGE and self.is_product_center_visible(timeout=0.5):
            self.fail(f"{label} 跳转失败：点击后仍停留在产品中心")

        matched_option = self.destination_contains_expected_fragments(
            expected_options,
            timeout=WAIT_TIMEOUT,
            include_page_source=False,
        )
        if matched_option:
            print(f"{label} 链接/intent 目标校验通过：命中 {matched_option}")
            return

        if (
            allow_native_app_without_product_match
            and current_package in expected_packages
            and current_package not in BROWSER_PACKAGES
        ):
            print(f"{label} 已打开目标购物 App：package={current_package}，当前原生 App 页面未暴露完整 URL")
            return

        matched_option = self.destination_contains_expected_fragments(
            expected_options,
            timeout=SHORT_TIMEOUT,
            include_page_source=True,
        )
        if matched_option:
            print(f"{label} 页面内容目标校验通过：命中 {matched_option}")
            return

        if current_package in expected_packages and current_package not in BROWSER_PACKAGES:
            if not allow_native_app_without_product_match:
                self.fail(
                    (native_app_unconfirmed_message or f"{label} 平台正确但商品未确认")
                    + f" package={current_package}, activity={self.safe_current_activity()}, "
                    + f"后台原始链接={expected_source_urls or []}, source={self.safe_page_source()[:500]}"
                )
            print(f"{label} 已打开目标购物 App：package={current_package}，当前原生 App 页面未暴露完整 URL")
            return

        observed_urls = self.observed_destination_urls()
        challenge_hint = "，当前浏览器疑似停在登录/滑块验证页，未观测到完整商品链接" if self.browser_login_or_challenge_visible() else ""
        self.fail(
            f"{label} 链接目标校验失败{challenge_hint}：未命中预期链接片段 {expected_options}。"
            f"后台原始链接={expected_source_urls or []}。"
            f"package={current_package}, activity={self.safe_current_activity()}, "
            f"实际观测链接={observed_urls}。"
            f"url={self.safe_current_url()}, source={self.safe_page_source()[:500]}"
        )

    def destination_contains_expected_fragments(self, expected_options, timeout=SHORT_TIMEOUT, include_page_source=True):
        options = self.normalize_expected_options(expected_options)
        deadline = time.time() + timeout
        while time.time() < deadline:
            destination_text = self.normalized_destination_text(include_page_source=include_page_source)
            for option in options:
                if all(fragment in destination_text for fragment in option):
                    return option
            time.sleep(0.5)
        return None

    def normalize_expected_options(self, expected_options):
        normalized_options = []
        for option in expected_options:
            if isinstance(option, str):
                fragments = [option]
            else:
                fragments = list(option)
            normalized_fragments = [self.normalize_match_text(fragment) for fragment in fragments if fragment]
            if normalized_fragments:
                normalized_options.append(normalized_fragments)
        return normalized_options

    def normalized_destination_text(self, include_page_source=True):
        fresh_urls = self.observed_destination_urls()
        parts = list(fresh_urls)
        if include_page_source:
            parts.append(self.safe_page_source())
        return self.normalize_match_text(
            "\n".join(
                part
                for part in parts
                if part
            )
        )

    @staticmethod
    def normalize_match_text(value):
        text = unquote(str(value or "")).lower()
        text = text.replace("&amp;", "&").replace("\\/", "/")
        text = re.sub(r"https?://(www\.)?", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def prepare_destination_observation(self):
        self.destination_observation_cache = None
        self.clear_logcat()
        self.destination_url_baseline = set(self.observed_destination_urls(exclude_baseline=False))
        self.destination_observation_cache = None

    def observed_destination_urls(self, exclude_baseline=True):
        text = self.normalize_observation_text(self.destination_observation_text())
        decoded_text = self.normalize_observation_text(unquote(text))
        if decoded_text != text:
            text = "\n".join([text, decoded_text])
        urls = []
        baseline = getattr(self, "destination_url_baseline", set()) if exclude_baseline else set()
        url_pattern = (
            r"(?:https?|openapp\.jdmobile|jingdong|tbopen|taobao|aliexpress|amazon)://[^\s\"'<>}]+"
            r"|(?:www\.)?amazon\.(?:com(?:\.mx)?|ca|co\.uk|de|fr|co\.jp)(?:/[^\s\"'<>}]*)?"
            r"|(?:www\.|m\.)?aliexpress\.(?:com|us)(?:/[^\s\"'<>}]*)?"
            r"|[a-z0-9-]+\.aliexpress\.com(?:/[^\s\"'<>}]*)?"
            r"|(?:item\.)?jd\.com/[^\s\"'<>}]+"
            r"|(?:item\.)?taobao\.com/[^\s\"'<>}]+"
            r"|accsoon\.(?:com|cn)[^\s\"'<>}]*"
        )
        for match in re.findall(url_pattern, text, flags=re.IGNORECASE):
            clean = self.clean_observed_url(match)
            if not clean or clean in baseline or self.is_noise_url(clean):
                continue
            if clean not in urls:
                urls.append(clean)
            if len(urls) >= 8:
                break
        return self.drop_redundant_host_only_urls(urls)

    @classmethod
    def drop_redundant_host_only_urls(cls, urls):
        filtered = []
        normalized_urls = [(url, cls.normalize_observed_url_for_prefix(url)) for url in urls]
        for url, normalized in normalized_urls:
            if "/" not in normalized:
                prefix = normalized.rstrip("/") + "/"
                if any(other_url != url and other_normalized.startswith(prefix) for other_url, other_normalized in normalized_urls):
                    continue
            filtered.append(url)
        return filtered

    @staticmethod
    def normalize_observed_url_for_prefix(url):
        text = str(url or "").lower()
        text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", text)
        if text.startswith("www."):
            text = text[4:]
        return text.rstrip("/")

    @staticmethod
    def normalize_observation_text(text):
        return (
            str(text or "")
            .replace("&quot;", '"')
            .replace("&#34;", '"')
            .replace("&apos;", "'")
            .replace("&#39;", "'")
            .replace("&amp;", "&")
            .replace("\\/", "/")
        )

    @staticmethod
    def clean_observed_url(url):
        clean = unquote(str(url or "")).replace("&amp;", "&").replace("\\/", "/")
        clean = clean.rstrip(").,;]")
        text = (
            clean.lower()
            .replace("https://", "")
            .replace("http://", "")
        )
        if text.startswith("www."):
            text = text[4:]
        allowed_bare_hosts = (
            "amazon.com",
            "amazon.com.mx",
            "amazon.ca",
            "amazon.co.uk",
            "amazon.de",
            "amazon.fr",
            "amazon.co.jp",
            "aliexpress.com",
            "aliexpress.us",
            "accsoon.com",
            "accsoon.cn",
            "item.jd.com",
            "jd.com",
            "item.taobao.com",
            "taobao.com",
        )
        if "://" not in clean and not text.startswith(allowed_bare_hosts) and ".aliexpress.com" not in text:
            return ""
        return clean

    def destination_observation_text(self):
        now = time.time()
        cache = getattr(self, "destination_observation_cache", None)
        if cache and now - cache["time"] < 1.5:
            return cache["text"]

        text = "\n".join(
            part
            for part in [
                self.safe_current_url(),
                self.safe_webview_url(),
                self.safe_native_browser_text(),
                self.safe_activity_intent_text(),
                self.safe_recent_logcat_text(),
                self.safe_recent_event_logcat_text(),
            ]
            if part
        )
        self.destination_observation_cache = {"time": now, "text": text}
        return text

    def safe_native_browser_text(self):
        if self.safe_current_package() not in BROWSER_PACKAGES:
            return ""
        return "\n".join(self.browser_url_candidates_from_source(self.safe_page_source()))

    def browser_url_candidates_from_source(self, source):
        if not source:
            return []

        values = []
        try:
            root = ET.fromstring(source)
        except ET.ParseError:
            values.append(source)
        else:
            for element in root.iter():
                resource_id = element.attrib.get("resource-id", "").lower()
                element_values = [
                    element.attrib.get("text", ""),
                    element.attrib.get("content-desc", ""),
                ]
                if any(marker in resource_id for marker in ("url", "address", "location", "search", "omnibox")):
                    values.extend(element_values)
                    continue
                values.extend(value for value in element_values if self.text_looks_like_destination_url(value))

        candidates = []
        for value in values:
            if not self.text_looks_like_destination_url(value):
                continue
            if value not in candidates:
                candidates.append(value)
        return candidates

    @staticmethod
    def text_looks_like_destination_url(value):
        lowered = str(value or "").strip().lower()
        if not lowered:
            return False
        return any(
            marker in lowered
            for marker in (
                "http://",
                "https://",
                "aliexpress.",
                "amazon.",
                "jd.com",
                "taobao.com",
                "accsoon.com",
                "accsoon.cn",
                "openapp.jdmobile://",
                "tbopen://",
            )
        )

    @staticmethod
    def is_noise_url(url):
        lowered = str(url or "").lower()
        return any(
            marker in lowered
            for marker in (
                "crbug.com",
                "play.googleapis.com",
                "googleapis.com/auth",
                "google.com/generate_204",
                "google.com/gen_204",
                "slf4j.org",
            )
        )

    def clear_logcat(self):
        try:
            subprocess.run(
                adb_command("logcat", "-c"),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
        except Exception:
            pass

    def safe_recent_logcat_text(self):
        try:
            result = subprocess.run(
                adb_command("logcat", "-d", "-t", "300"),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
        except Exception:
            return ""

        lines = []
        for line in (result.stdout or "").splitlines():
            lowered = line.lower()
            if any(
                marker in lowered
                for marker in (
                    "http",
                    "amazon",
                    "aliexpress",
                    "jd.com",
                    "taobao",
                    "accsoon",
                    "openapp.jdmobile",
                    "jingdong",
                    "skuid",
                    "sku_id",
                    "tbopen",
                )
            ):
                lines.append(line)
        return "\n".join(lines)

    def safe_recent_event_logcat_text(self):
        try:
            result = subprocess.run(
                adb_command("logcat", "-b", "events", "-d", "-t", "500"),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
        except Exception:
            return ""

        lines = []
        for line in (result.stdout or "").splitlines():
            lowered = line.lower()
            if any(
                marker in lowered
                for marker in (
                    "http",
                    "amazon",
                    "aliexpress",
                    "jd.com",
                    "taobao",
                    "accsoon",
                    "openapp.jdmobile",
                    "jingdong",
                    "skuid",
                    "sku_id",
                    "tbopen",
                )
            ):
                lines.append(line)
        return "\n".join(lines)

    def safe_activity_intent_text(self):
        try:
            result = subprocess.run(
                adb_command("shell", "dumpsys", "activity", "activities"),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
        except Exception:
            return ""

        lines = []
        for line in (result.stdout or "").splitlines():
            lowered = line.lower()
            if any(
                marker in lowered
                for marker in (
                    "http",
                    "amazon",
                    "aliexpress",
                    "jd.com",
                    "taobao",
                    "accsoon",
                    "openapp.jdmobile",
                    "jingdong",
                    "skuid",
                    "sku_id",
                    "tbopen",
                )
            ):
                lines.append(line)
        return "\n".join(lines)

    def page_contains_any(self, markers, timeout=SHORT_TIMEOUT):
        deadline = time.time() + timeout
        lowered_markers = [marker.lower() for marker in markers]
        while time.time() < deadline:
            source = self.safe_page_source().lower()
            if any(marker in source for marker in lowered_markers):
                return True
            time.sleep(0.5)
        return False

    def ensure_product_center_ready(self, country):
        if HARD_RESET_AFTER_JUMP:
            self.hard_reset_to_product_center(country)
            return

        deadline = time.time() + RESTORE_TIMEOUT
        last_state = ""
        attempt = 0
        while time.time() < deadline:
            current_package = self.safe_current_package()
            current_activity = self.safe_current_activity()
            in_target_app = current_package == APP_PACKAGE
            product_center_visible = in_target_app and self.is_product_center_visible()
            if product_center_visible and self.has_country_selected(country):
                print(f"已回到产品中心：{country}")
                return

            last_state = (
                f"package={current_package}, "
                f"activity={current_activity}, "
                f"product_center={product_center_visible}, "
                f"home={in_target_app and self.is_home_page_visible(timeout=0.2)}"
            )

            try:
                attempt += 1
                self.restore_product_center_state(country, attempt)
            except WebDriverException:
                pass
            if self.is_product_center_visible(timeout=0.5) and self.has_country_selected(country, timeout=0.5):
                print(f"已回到产品中心：{country}")
                return
            time.sleep(0.5)
        if self.is_product_center_visible(timeout=0.5) and self.has_country_selected(country, timeout=0.5):
            print(f"已回到产品中心：{country}")
            return
        self.fail(f"跳转后未能回到产品中心：{country}，最后状态：{last_state}")

    def hard_reset_to_product_center(self, country):
        current_package = self.safe_current_package()
        print(f"执行硬重置恢复产品中心：当前 package={current_package}, 目标国家={country}")

        if current_package and current_package != APP_PACKAGE:
            self.force_stop_package(current_package)

        self.force_stop_package(APP_PACKAGE)
        self.start_target_activity()

        if not self.wait_for_app_landing():
            self.safe_activate_app(APP_PACKAGE)
            self.wait_for_app_landing()

        if self.is_home_page_visible(timeout=SHORT_TIMEOUT):
            self.open_product_center()
        elif not self.is_product_center_visible(timeout=SHORT_TIMEOUT):
            self.open_product_center()

        if not self.has_country_selected(country, timeout=SHORT_TIMEOUT):
            self.select_country(country)

        if not self.is_product_center_visible(timeout=SHORT_TIMEOUT) or not self.has_country_selected(country, timeout=SHORT_TIMEOUT):
            self.fail(
                f"硬重置后仍未回到产品中心：{country}，"
                f"package={self.safe_current_package()}, activity={self.safe_current_activity()}"
            )

        print(f"硬重置恢复完成，已回到产品中心：{country}")

    def restore_product_center_state(self, country, attempt):
        current_package = self.safe_current_package()

        if current_package is None:
            print(f"当前无法获取 package，优先重建 Appium session 并恢复产品中心（第 {attempt} 次）")
            self.recreate_driver_session()
            current_package = self.safe_current_package()
            if current_package is None:
                self.adb_launch_target_app()
                return

        if current_package != APP_PACKAGE:
            print(f"当前在外部页面 package={current_package}，尝试返回被测 App（第 {attempt} 次）")
            if current_package in BROWSER_PACKAGES:
                self.soft_reopen_target_app(country)
            elif attempt <= 2:
                self.press_back()
            else:
                self.soft_reopen_target_app(country)
            return

        if self.is_product_center_visible(timeout=0.5):
            if not self.has_country_selected(country, timeout=0.5):
                print(f"已回到产品中心，但国家不是 {country}，重新选择")
                self.select_country(country)
            return

        if self.product_center_semantics_visible(timeout=0.5):
            print(f"已在产品中心语义页面，但国家不是 {country}，重新选择")
            self.select_country(country)
            return

        if self.is_home_page_visible(timeout=0.5):
            print("跳转返回后停在首页，重新进入产品中心")
            self.open_product_center()
            if not self.has_country_selected(country, timeout=0.5):
                self.select_country(country)
            return

        print(f"当前在 App 内非产品中心页面，尝试恢复产品中心（第 {attempt} 次）")
        if attempt <= 1:
            self.press_back()
        elif attempt <= 3:
            self.start_target_activity(force_stop=False)
            self.wait_for_app_landing(timeout=3)
            self.open_product_center()
        else:
            self.soft_reopen_target_app(country)

    def wait_for_app_landing(self, timeout=WAIT_TIMEOUT, ad_timeout=0.2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_product_center_visible(timeout=0.15) or self.is_home_page_visible(timeout=0.15):
                return True
            self.close_ad_if_present(timeout=ad_timeout)
            if self.is_product_center_visible(timeout=0.15) or self.is_home_page_visible(timeout=0.15):
                return True
            time.sleep(0.2)
        return False

    def restart_target_app(self):
        print("常规返回无效，重启被测 App")
        self.safe_terminate_app(APP_PACKAGE)
        time.sleep(1)
        self.safe_activate_app(APP_PACKAGE)

    def soft_reopen_target_app(self, country):
        print("常规返回无效，切回被测 App 并重新进入产品中心")
        current_package = self.safe_current_package()
        if current_package in BROWSER_PACKAGES:
            reopen_methods = (
                self.safe_activate_target_app,
                self.adb_start_target_activity,
                self.adb_launch_target_app,
                lambda: self.start_target_activity(force_stop=False),
            )
        else:
            reopen_methods = (
                self.safe_activate_target_app,
                lambda: self.start_target_activity(force_stop=False),
                self.adb_start_target_activity,
                self.adb_launch_target_app,
            )

        for index, reopen in enumerate(reopen_methods):
            reopen()
            landing_timeout = 3 if index < len(reopen_methods) - 1 else WAIT_TIMEOUT
            if self.wait_for_app_landing(timeout=landing_timeout):
                break

        if self.is_home_page_visible(timeout=SHORT_TIMEOUT):
            self.open_product_center()
        elif not self.is_product_center_visible(timeout=SHORT_TIMEOUT):
            self.open_product_center()

        if self.is_product_center_visible(timeout=SHORT_TIMEOUT):
            if not self.has_country_selected(country, timeout=SHORT_TIMEOUT):
                self.select_country(country)

    def press_back(self):
        for action in (self.driver.back, lambda: self.driver.press_keycode(4), self.shell_back):
            try:
                action()
                time.sleep(0.5)
                return
            except WebDriverException:
                continue

    def shell_back(self):
        self.driver.execute_script("mobile: shell", {"command": "input", "args": ["keyevent", "4"]})

    def safe_activate_target_app(self):
        self.safe_activate_app(APP_PACKAGE)
        time.sleep(0.2)

    def adb_launch_target_app(self):
        try:
            subprocess.run(
                adb_command(
                    "shell",
                    "monkey",
                    "-p",
                    APP_PACKAGE,
                    "-c",
                    "android.intent.category.LAUNCHER",
                    "1",
                ),
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            time.sleep(0.3)
        except Exception as exc:
            print(f"ADB 启动被测 App 失败，继续尝试其他恢复方式：{self.short_error(exc)}")

    def adb_start_target_activity(self):
        try:
            subprocess.run(
                adb_command(
                    "shell",
                    "am",
                    "start",
                    "-W",
                    "-n",
                    f"{APP_PACKAGE}/{APP_ACTIVITY}",
                ),
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            time.sleep(0.3)
        except Exception as exc:
            print(f"ADB 打开被测 App Activity 失败，继续尝试其他恢复方式：{self.short_error(exc)}")

    def force_stop_package(self, package):
        if not package:
            return
        try:
            self.driver.execute_script("mobile: shell", {"command": "am", "args": ["force-stop", package]})
        except WebDriverException:
            self.safe_terminate_app(package)

    def start_target_activity(self, force_stop=True):
        component = f"{APP_PACKAGE}/{APP_ACTIVITY}"
        args = ["start", "-n", component]
        if force_stop:
            args = ["start", "-S", "-n", component]
        try:
            self.driver.execute_script(
                "mobile: shell",
                {"command": "am", "args": args},
            )
            time.sleep(0.3)
        except WebDriverException:
            self.safe_activate_app(APP_PACKAGE)

    def safe_activate_app(self, package):
        try:
            self.driver.activate_app(package)
        except WebDriverException:
            pass

    def safe_terminate_app(self, package):
        if not package:
            return
        try:
            self.driver.terminate_app(package)
        except WebDriverException:
            pass

    def assert_country_selected(self, country):
        if not self.has_country_selected(country):
            self.fail(f"当前页面没有显示已选择国家：{country}")

    def has_country_selected(self, country, timeout=SHORT_TIMEOUT):
        return self.exists_any(self.selected_country_locators(country), timeout=timeout)

    def get_current_country_hint(self):
        for country in ALL_COUNTRIES:
            if self.has_country_selected(country):
                return country
        return CHINA

    def is_product_center_visible(self, timeout=SHORT_TIMEOUT):
        if self.exists_any(self.product_center_title_locators(), timeout=timeout):
            return True
        return self.product_center_semantics_visible(timeout=timeout)

    def product_center_semantics_visible(self, timeout=SHORT_TIMEOUT):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.safe_current_package() != APP_PACKAGE:
                return False
            source = self.safe_page_source()
            if self.source_looks_like_product_center(source):
                return True
            time.sleep(0.2)
        return False

    def source_looks_like_product_center(self, source):
        if not source:
            return False
        markers = (
            'content-desc="产品中心"',
            'text="产品中心"',
            'content-desc="Accsoon News"',
            'text="Accsoon News"',
            'content-desc="主打产品"',
            'content-desc="购买渠道',
            'content-desc="CoMo SE"',
            'content-desc="Amazon"',
            'content-desc="AliExpress"',
            'content-desc="本地经销商"',
        )
        return any(marker in source for marker in markers)

    def is_home_page_visible(self, timeout=SHORT_TIMEOUT):
        return self.exists(AppiumBy.ID, f"{APP_PACKAGE}:id/menu_btn", timeout=timeout)

    def assert_external_navigation_started(self, before, message, channel=None):
        return self.wait_until(lambda _: self.external_navigation_status(before, channel=channel), message)

    def external_navigation_status(self, before, channel=None):
        current_package = self.safe_current_package()
        current_activity = self.safe_current_activity()
        contexts = self.safe_contexts()

        if current_package is None and current_activity is None:
            return None

        if current_package in SHOPPING_APP_PACKAGES:
            return f"购物 App：{SHOPPING_APP_PACKAGES[current_package]}，package={current_package}"

        if current_package in BROWSER_PACKAGES:
            return f"浏览器网页：{BROWSER_PACKAGES[current_package]}，package={current_package}"

        if channel and current_package == APP_PACKAGE and self.is_product_center_visible(timeout=0.2):
            return None

        if any(context.startswith("WEBVIEW") for context in contexts):
            if current_package == APP_PACKAGE and set(contexts) == set(before.get("contexts", [])) and current_activity == before["activity"]:
                return None
            return f"网页(WebView)，package={current_package}, activity={current_activity}"

        if current_package not in (None, before["package"]):
            return f"外部 App：package={current_package}, activity={current_activity}"

        if current_activity not in (None, before["activity"]):
            return f"页面已跳转：package={current_package}, activity={current_activity}"

        if not self.is_product_center_visible(timeout=0.3):
            return f"已离开产品中心：package={current_package}, activity={current_activity}"

        return None

    def navigation_snapshot(self):
        return {
            "package": self.safe_current_package(),
            "activity": self.safe_current_activity(),
            "contexts": self.safe_contexts(),
        }

    def country_dropdown_locators(self, current_country):
        return locators.country_dropdown_locators(current_country)

    def product_center_title_locators(self):
        return locators.product_center_title_locators()

    def selected_country_locators(self, country):
        return locators.selected_country_locators(country)

    def country_option_locators(self, country):
        return locators.country_option_locators(country)

    def country_dropdown_opened(self):
        return self.exists_any(locators.country_dropdown_opened_locators(), timeout=0.5)

    def channel_locators(self, channel):
        return locators.channel_locators(channel)

    def featured_product_channel_locators(self, channel):
        return locators.featured_product_channel_locators(channel)

    def product_locators(self, product):
        return locators.product_locators(product)

    def click(self, by, value, label):
        try:
            element = self.wait.until(EC.element_to_be_clickable((by, value)))
            try:
                self.tap_element_center(element)
            except Exception:
                element.click()
        except WebDriverException as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                element = self.wait.until(EC.element_to_be_clickable((by, value)))
                try:
                    self.tap_element_center(element)
                except Exception:
                    element.click()
            else:
                raise
        print(f"点击成功：{label}")
        return element

    def click_any(self, locators, label, after_click=None, after_click_timeout=AFTER_CLICK_TIMEOUT):
        last_error = None
        for by, value in locators:
            for locate_attempt in range(2):
                try:
                    element = WebDriverWait(self.driver, SHORT_TIMEOUT).until(
                        EC.presence_of_element_located((by, value))
                    )
                except Exception as exc:
                    if self.is_recoverable_session_error(exc):
                        if not self.recreate_driver_session():
                            self.device_connection_unavailable = True
                            raise AssertionError("Appium session 已终止且无法继续重建，本条测试失败。") from exc
                        last_error = exc
                        if locate_attempt == 0:
                            print(f"定位时 Appium session 已重建，重新定位后重试：{label}")
                            continue
                    last_error = exc
                    break

                retry_locator = False
                for click_name, click_method in (
                    ("坐标点击", self.tap_element_center),
                    ("元素点击", self.element_click),
                ):
                    try:
                        click_method(element)
                        if after_click is None or self.after_click_succeeded(after_click, timeout=after_click_timeout):
                            print(f"点击成功：{label}（{click_name}）")
                            return element
                        print(f"点击未生效，继续重试：{label}（{click_name}）")
                    except Exception as exc:
                        if self.is_recoverable_session_error(exc):
                            if not self.recreate_driver_session():
                                self.device_connection_unavailable = True
                                raise AssertionError("Appium session 已终止且无法继续重建，本条测试失败。") from exc
                            retry_locator = True
                            last_error = exc
                            break
                        if isinstance(exc, StaleElementReferenceException):
                            retry_locator = True
                            last_error = exc
                            break
                        last_error = exc
                if not retry_locator:
                    break
                if locate_attempt == 0:
                    print(f"元素已刷新，重新定位后重试：{label}")
        raise AssertionError(f"未找到或无法点击：{label}") from last_error

    def click_featured_product_channel_by_flutter_semantics(self, channel, label, after_click):
        descs = {
            "Amazon": ["Ama.", "Amazon"],
            "AliExpress": ["Ali.", "AliExpress"],
        }.get(channel, [channel])
        return self.click_flutter_semantics(
            descs,
            label,
            section_desc="主打产品",
            after_click=after_click,
            after_click_timeout=2,
            prefer="top_right",
        )

    def click_purchase_channel_by_flutter_semantics(self, channel, label, after_click):
        aliases = {
            "JD": ["JD", "京东"],
            DIRECT_WEB_CHANNEL: [DIRECT_WEB_CHANNEL, "Local Dealer"],
        }.get(channel, [channel])

        for attempt in range(2):
            node = self.find_purchase_channel_semantics_node(aliases)
            if node and node["bounds"]:
                left, top, right, bottom = node["bounds"]
                x = int((left + right) / 2)
                y = int((top + bottom) / 2)
                if self.tap_location_and_confirm(x, y, label, after_click, after_click_timeout=5):
                    print(f"Flutter 语义定位：{label} content-desc={node['desc']} bounds={node['bounds']}")
                    return True
                if self.adb_tap_location_and_confirm(x, y, label, after_click, after_click_timeout=5):
                    print(f"Flutter 语义定位：{label} content-desc={node['desc']} bounds={node['bounds']}")
                    return True
            if attempt == 0:
                self.scroll_purchase_channel_section_into_view()
        return False

    def find_purchase_channel_semantics_node(self, aliases):
        nodes = self.flutter_semantics_nodes()
        exact_candidates = []
        partial_candidates = []
        for node in nodes:
            desc = node["desc"]
            bounds = node["bounds"]
            if not desc or not bounds or node["visible"] is False:
                continue
            if not self.bounds_center_on_screen(bounds):
                continue
            if desc in aliases:
                exact_candidates.append(node)
            elif any(alias in desc for alias in aliases):
                partial_candidates.append(node)

        candidates = exact_candidates or partial_candidates
        if not candidates:
            return None
        return sorted(candidates, key=lambda node: (node["bounds"][1], node["bounds"][0]))[0]

    def click_featured_product_by_flutter_semantics(self, product, label, after_click):
        return self.click_flutter_semantics(
            [product],
            label,
            section_desc="主打产品",
            after_click=after_click,
            after_click_timeout=5,
            prefer="top_left",
        )

    def click_flutter_semantics(
        self,
        descs,
        label,
        section_desc=None,
        after_click=None,
        after_click_timeout=AFTER_CLICK_TIMEOUT,
        prefer="top_left",
    ):
        node = self.find_flutter_semantics_node(descs, section_desc=section_desc, prefer=prefer)
        if not node:
            return False

        left, top, right, bottom = node["bounds"]
        x = int((left + right) / 2)
        y = int((top + bottom) / 2)
        condition = after_click or (lambda: True)
        if self.tap_location_and_confirm(x, y, label, condition, after_click_timeout=after_click_timeout):
            print(f"Flutter 语义定位：{label} content-desc={node['desc']} bounds={node['bounds']}")
            return True
        if self.adb_tap_location_and_confirm(x, y, label, condition, after_click_timeout=after_click_timeout):
            print(f"Flutter 语义定位：{label} content-desc={node['desc']} bounds={node['bounds']}")
            return True
        return False

    def find_flutter_semantics_node(self, descs, section_desc=None, prefer="top_left"):
        nodes = self.flutter_semantics_nodes()
        wanted_descs = set(descs)
        section_bounds = None
        if section_desc:
            sections = [node for node in nodes if node["desc"] == section_desc and node["bounds"]]
            if sections:
                section = max(sections, key=lambda node: self.bounds_area(node["bounds"]))
                section_bounds = section["bounds"]

        candidates = []
        for node in nodes:
            if node["desc"] not in wanted_descs or not node["bounds"]:
                continue
            if node["visible"] is False:
                continue
            if section_bounds and not self.bounds_inside(node["bounds"], section_bounds):
                continue
            candidates.append(node)

        if not candidates:
            return None

        if prefer == "top_right":
            return sorted(candidates, key=lambda node: (node["bounds"][1], -node["bounds"][0]))[0]
        return sorted(candidates, key=lambda node: (node["bounds"][1], node["bounds"][0]))[0]

    def flutter_semantics_nodes(self):
        source = self.safe_page_source()
        try:
            root = ET.fromstring(source)
        except ET.ParseError:
            return []

        nodes = []

        def visit(element):
            desc = element.attrib.get("content-desc", "")
            bounds = self.parse_bounds(element.attrib.get("bounds", ""))
            nodes.append(
                {
                    "desc": desc,
                    "bounds": bounds,
                    "visible": element.attrib.get("displayed") != "false",
                }
            )
            for child in list(element):
                visit(child)

        visit(root)
        return nodes

    @staticmethod
    def parse_bounds(value):
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", str(value or ""))
        if not match:
            return None
        return tuple(int(part) for part in match.groups())

    @staticmethod
    def bounds_inside(inner, outer):
        left, top, right, bottom = inner
        outer_left, outer_top, outer_right, outer_bottom = outer
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        return outer_left <= center_x <= outer_right and outer_top <= center_y <= outer_bottom

    def bounds_center_on_screen(self, bounds):
        left, top, right, bottom = bounds
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        width, height = self.screen_size()
        return 0 < center_x < width and 0 < center_y < height

    @staticmethod
    def bounds_area(bounds):
        left, top, right, bottom = bounds
        return max(0, right - left) * max(0, bottom - top)

    def element_click(self, element):
        element.click()

    def tap_element_center(self, element):
        rect = element.rect
        x = int(rect["x"] + rect["width"] / 2)
        y = int(rect["y"] + rect["height"] / 2)
        self.w3c_tap_location(x, y)

    def screen_size(self):
        try:
            size = self.driver.get_window_size()
            width = int(size.get("width", 0))
            height = int(size.get("height", 0))
            if width > 0 and height > 0:
                return width, height
        except Exception:
            pass

        try:
            result = subprocess.run(
                adb_command("shell", "wm", "size"),
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            match = re.search(r"(\d+)x(\d+)", result.stdout or "")
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass

        return BASE_SCREEN_WIDTH, BASE_SCREEN_HEIGHT

    def clamp_point(self, x, y):
        width, height = self.screen_size()
        clamped_x = min(max(int(x), 1), max(width - 1, 1))
        clamped_y = min(max(int(y), 1), max(height - 1, 1))
        return clamped_x, clamped_y

    def scale_point(self, x, y):
        width, height = self.screen_size()
        scaled_x = int(int(x) * width / BASE_SCREEN_WIDTH)
        scaled_y = int(int(y) * height / BASE_SCREEN_HEIGHT)
        return self.clamp_point(scaled_x, scaled_y)

    def tap_location_and_confirm(self, x, y, label, after_click, after_click_timeout=AFTER_CLICK_TIMEOUT):
        x, y = self.clamp_point(x, y)
        click_methods = []
        if self.supports_click_gesture:
            click_methods.append(("固定坐标点击", lambda: self.tap_location(x, y)))
        click_methods.append(("W3C坐标点击", lambda: self.w3c_tap_location(x, y)))

        for click_name, click_method in click_methods:
            try:
                click_method()
                if self.after_click_succeeded(after_click, timeout=after_click_timeout):
                    print(f"点击成功：{label}（{click_name} x={x}, y={y}）")
                    return True
                print(f"点击未生效，继续重试：{label}（{click_name} x={x}, y={y}）")
            except Exception as exc:
                if self.is_unknown_click_gesture_error(exc):
                    type(self).supports_click_gesture = False
                    print("当前 Appium 不支持 mobile: clickGesture，后续改用 W3C 坐标点击")
                else:
                    print(f"点击异常，继续重试：{label}（{click_name} x={x}, y={y}）：{self.short_error(exc)}")
        return False

    def adb_tap_location_and_confirm(self, x, y, label, after_click, after_click_timeout=AFTER_CLICK_TIMEOUT):
        x, y = self.clamp_point(x, y)
        try:
            self.adb_tap_location(x, y)
            if self.after_click_succeeded(after_click, timeout=after_click_timeout):
                print(f"点击成功：{label}（ADB坐标点击 x={x}, y={y}）")
                return True
            print(f"点击未生效，继续重试：{label}（ADB坐标点击 x={x}, y={y}）")
        except Exception as exc:
            print(f"点击异常，继续重试：{label}（ADB坐标点击 x={x}, y={y}）：{self.short_error(exc)}")
        return False

    def tap_location(self, x, y):
        x, y = self.clamp_point(x, y)
        self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})

    def adb_tap_location(self, x, y):
        x, y = self.clamp_point(x, y)
        subprocess.run(
            adb_command("shell", "input", "tap", str(int(x)), str(int(y))),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        time.sleep(0.3)

    def w3c_tap_location(self, x, y):
        x, y = self.clamp_point(x, y)
        actions = ActionChains(self.driver)
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.release()
        actions.perform()

    def w3c_swipe_location(self, start_x, start_y, end_x, end_y):
        start_x, start_y = self.clamp_point(start_x, start_y)
        end_x, end_y = self.clamp_point(end_x, end_y)
        actions = ActionChains(self.driver)
        actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.move_to_location(end_x, end_y)
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.release()
        actions.perform()

    def after_click_succeeded(self, after_click, timeout=AFTER_CLICK_TIMEOUT):
        try:
            WebDriverWait(self.driver, timeout, poll_frequency=0.15).until(lambda _: after_click())
            return True
        except TimeoutException:
            return False
        except WebDriverException as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                try:
                    WebDriverWait(self.driver, timeout, poll_frequency=0.15).until(lambda _: after_click())
                    return True
                except TimeoutException:
                    return False
            raise
        except Exception as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                try:
                    WebDriverWait(self.driver, timeout, poll_frequency=0.15).until(lambda _: after_click())
                    return True
                except TimeoutException:
                    return False
            raise

    def is_unknown_click_gesture_error(self, exc):
        return "Unknown mobile command" in str(exc) and "clickGesture" in str(exc)

    def short_error(self, exc):
        return str(exc).splitlines()[0]

    def assert_visible(self, by, value):
        try:
            return self.wait.until(EC.visibility_of_element_located((by, value)))
        except TimeoutException as exc:
            raise AssertionError(f"元素不可见：{by}={value}") from exc
        except WebDriverException as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                return self.wait.until(EC.visibility_of_element_located((by, value)))
            raise

    def assert_visible_any(self, locators, label):
        if not self.exists_any(locators):
            self.fail(f"元素不可见：{label}")

    def exists(self, by, value, timeout=WAIT_TIMEOUT):
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, value)))
            return True
        except TimeoutException:
            return False
        except WebDriverException as exc:
            if self.is_recoverable_session_error(exc):
                try:
                    self.recreate_driver_session()
                except unittest.SkipTest:
                    raise
            return False
        except Exception as exc:
            if self.is_recoverable_session_error(exc):
                try:
                    self.recreate_driver_session()
                except unittest.SkipTest:
                    raise
                return False
            raise

    def exists_any(self, locators, timeout=WAIT_TIMEOUT):
        for by, value in locators:
            if self.exists(by, value, timeout=timeout):
                return True
        return False

    def wait_until(self, condition, message):
        try:
            return self.wait.until(condition)
        except TimeoutException as exc:
            raise AssertionError(message) from exc
        except WebDriverException as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                raise AssertionError(f"{message}（Appium session 已重建，请重跑当前用例）") from exc
            raise
        except Exception as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                raise AssertionError(f"{message}（Appium session 已重建，请重跑当前用例）") from exc
            raise

    def is_recoverable_session_error(self, exc):
        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                "invalidsessionid",
                "session identified",
                "a session is either terminated or not started",
                "is not known",
                "nosuchdriverexception",
                "nosuchdrivererror",
                "socket hang up",
                "read timed out",
                "timed out",
                "timeout",
                "connection aborted",
                "connection refused",
                "max retries exceeded",
                "could not proxy command to the remote server",
                "instrumentation process cannot be initialized",
                "instrumentation process is not running",
            )
        )

    def is_device_connection_error(self, exc):
        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                "device offline",
                "device unauthorized",
                "adb.exe: device offline",
                "adb.exe: device unauthorized",
                "not in the list of connected devices",
                "was not in the list of connected devices",
            )
        )

    def safe_current_package(self):
        if is_android_platform():
            component = self.adb_current_component()
            if component:
                return component[0]
        try:
            return self.driver.current_package
        except Exception as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                try:
                    return self.driver.current_package
                except Exception:
                    pass
            component = self.adb_current_component()
            return component[0] if component else None

    def safe_current_activity(self):
        if is_android_platform():
            component = self.adb_current_component()
            if component:
                return component[1]
        try:
            return self.driver.current_activity
        except Exception as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                try:
                    return self.driver.current_activity
                except Exception:
                    pass
            component = self.adb_current_component()
            return component[1] if component else None

    def adb_current_component(self):
        try:
            result = subprocess.run(
                adb_command("shell", "dumpsys", "window"),
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            return None

        match = re.search(r"mCurrentFocus=Window\{[^ ]+ [^ ]+ (?P<package>[^/\s]+)/(?P<activity>[^}\s]+)", result.stdout)
        if not match:
            match = re.search(r"mFocusedApp=ActivityRecord\{[^ ]+ [^ ]+ (?P<package>[^/\s]+)/(?P<activity>[^ \}]+)", result.stdout)
        if not match:
            return None
        return match.group("package"), match.group("activity")

    def safe_contexts(self):
        try:
            return list(self.driver.contexts)
        except Exception as exc:
            if self.is_recoverable_session_error(exc):
                self.recreate_driver_session()
            return []

    def safe_current_url(self):
        if is_android_platform():
            current_package = self.safe_current_package()
            if current_package in SHOPPING_APP_PACKAGES:
                return ""
        try:
            current_url = self.driver.current_url
            if current_url and current_url != "about:blank":
                return current_url
        except Exception as exc:
            if self.is_recoverable_session_error(exc):
                self.recreate_driver_session()
        return ""

    def safe_webview_url(self):
        if is_android_platform():
            current_package = self.safe_current_package()
            if current_package in SHOPPING_APP_PACKAGES:
                return ""
        contexts = self.safe_contexts()
        if not any(context.startswith("WEBVIEW") for context in contexts):
            return ""

        try:
            original_context = self.driver.current_context
        except Exception:
            original_context = None

        for context in contexts:
            if not context.startswith("WEBVIEW"):
                continue
            try:
                self.driver.switch_to.context(context)
                current_url = self.driver.current_url
                if current_url and current_url != "about:blank":
                    return current_url
                script_url = self.driver.execute_script("return window.location && window.location.href")
                if script_url:
                    return str(script_url)
            except Exception:
                continue
            finally:
                if original_context:
                    try:
                        self.driver.switch_to.context(original_context)
                    except Exception:
                        pass
        return ""

    def safe_page_source(self):
        try:
            return self.driver.page_source or ""
        except Exception as exc:
            if self.is_recoverable_session_error(exc) and self.recreate_driver_session():
                try:
                    return self.driver.page_source or ""
                except Exception:
                    pass
            return ""
