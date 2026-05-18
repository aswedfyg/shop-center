# -*- coding: utf-8 -*-

import unittest

from android import product_center_flow as flow


class DestinationObservationTest(unittest.TestCase):
    def make_case(self, text):
        case = flow.ProductCenterAutomationCase(methodName="runTest")
        case.destination_observation_text = lambda: text
        return case

    def test_observed_destination_urls_extracts_bare_browser_address(self):
        case = self.make_case("Address www.aliexpress.com/item/1005009371832090.html")

        self.assertEqual(
            ["www.aliexpress.com/item/1005009371832090.html"],
            case.observed_destination_urls(),
        )

    def test_observed_destination_urls_extracts_event_log_intent_url(self):
        case = self.make_case(
            "am_create_activity: Intent { act=android.intent.action.VIEW "
            "dat=https://www.aliexpress.com/item/1005009371832090.html }"
        )

        self.assertEqual(
            ["https://www.aliexpress.com/item/1005009371832090.html"],
            case.observed_destination_urls(),
        )

    def test_observed_destination_urls_ignores_amazon_package_names(self):
        case = self.make_case(
            "com.amazon.mShop.android.shopping "
            "com.amazon.mShop.android.shopping/com.amazon.mShop.publicurl.PublicURLActivity "
            "com.amazon.mShop.android.shopping-abc/base.apk"
        )

        self.assertEqual([], case.observed_destination_urls())

    def test_observed_destination_urls_extracts_amazon_mx_bare_url(self):
        case = self.make_case("Address amazon.com.mx/dp/B0CKYLVKPM")

        self.assertEqual(["amazon.com.mx/dp/B0CKYLVKPM"], case.observed_destination_urls())

    def test_observed_destination_urls_extracts_escaped_intent_url(self):
        case = self.make_case("uri=https%3A%2F%2Fwww.amazon.com.mx%2Fdp%2FB0CKYLVKPM")

        self.assertEqual(["https://www.amazon.com.mx/dp/B0CKYLVKPM"], case.observed_destination_urls())

    def test_observed_destination_urls_filters_google_probe_noise(self):
        case = self.make_case(
            "https://www.google.com/generate_204\n"
            "http://www.google.com/gen_204\n"
            "https://www.amazon.com.mx/dp/B0CKYLVKPM"
        )

        self.assertEqual(["https://www.amazon.com.mx/dp/B0CKYLVKPM"], case.observed_destination_urls())

    def test_amazon_native_app_hidden_url_fallback_requires_amazon_app(self):
        case = flow.ProductCenterAutomationCase(methodName="runTest")
        case.safe_current_package = lambda: "com.amazon.mShop.android.shopping"
        case.safe_current_activity = lambda: "com.amazon.mShop.navigation.MainActivity"
        case.safe_page_source = lambda: "<hierarchy package='com.amazon.mShop.android.shopping' />"
        case.destination_contains_expected_fragments = lambda *args, **kwargs: None

        self.assertTrue(case.amazon_native_app_url_hidden_fallback_matches("Amazon", [["amazon.com.mx", "b0ckylvkpm"]]))
        self.assertFalse(case.amazon_native_app_url_hidden_fallback_matches("AliExpress", [["aliexpress"]]))

    def test_browser_url_candidates_extracts_native_address_field(self):
        case = flow.ProductCenterAutomationCase(methodName="runTest")
        source = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <android.widget.EditText
    resource-id="com.sec.android.app.sbrowser:id/location_bar_edit_text"
    text="www.aliexpress.com/item/1005009371832090.html"
    content-desc="" />
</hierarchy>"""

        self.assertEqual(
            ["www.aliexpress.com/item/1005009371832090.html"],
            case.browser_url_candidates_from_source(source),
        )

    def test_prepare_destination_observation_clears_logs_before_baseline(self):
        case = flow.ProductCenterAutomationCase(methodName="runTest")
        calls = []
        case.clear_logcat = lambda: calls.append("clear")
        case.observed_destination_urls = lambda exclude_baseline=True: calls.append("observe") or []

        case.prepare_destination_observation()

        self.assertEqual(["clear", "observe"], calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
