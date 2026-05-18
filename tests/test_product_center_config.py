# -*- coding: utf-8 -*-

import unittest

from common.config import (
    ALL_COUNTRIES,
    CHINA,
    COUNTRIES_WITH_CHANNELS,
    COUNTRY_CHANNELS,
    DIRECT_WEB_CHANNEL,
    DIRECT_WEB_COUNTRY,
    EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS,
    EXPECTED_MISSING_FEATURED_PRODUCT_LINKS,
    EXPECTED_PRODUCT_LINKS,
    EXPECTED_PRODUCT_LINKS_BY_CHANNEL,
    EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL,
    EXPECTED_STORE_LINKS,
    EXPECTED_STORE_SOURCE_URLS,
    FEATURED_PRODUCT_CHANNELS_BY_COUNTRY,
    FEATURED_PRODUCT_COUNTRIES,
    FEATURED_PRODUCTS,
    FULL_FEATURED_PRODUCTS,
    expected_fragments_from_url,
    validate_backend_link_config,
)


class ProductCenterConfigTest(unittest.TestCase):
    def test_backend_link_config_is_valid(self):
        self.assertEqual([], validate_backend_link_config())

    def test_country_channel_matrix_matches_feature_spec(self):
        self.assertEqual(["淘宝", "JD"], COUNTRY_CHANNELS[CHINA])
        self.assertNotIn(DIRECT_WEB_COUNTRY, COUNTRY_CHANNELS)
        self.assertEqual(COUNTRIES_WITH_CHANNELS + [DIRECT_WEB_COUNTRY], ALL_COUNTRIES)

        for country in COUNTRIES_WITH_CHANNELS:
            with self.subTest(country=country):
                self.assertIn(country, COUNTRY_CHANNELS)
                if country == CHINA:
                    self.assertEqual(["淘宝", "JD"], COUNTRY_CHANNELS[country])
                else:
                    self.assertEqual(["Amazon", "AliExpress", DIRECT_WEB_CHANNEL], COUNTRY_CHANNELS[country])

    def test_hidden_master_4k_ii_is_not_in_default_featured_products(self):
        self.assertNotIn("大师4K II", FULL_FEATURED_PRODUCTS)
        self.assertNotIn("大师4K II", FEATURED_PRODUCTS)

    def test_default_featured_product_order_matches_visible_grid(self):
        self.assertEqual(
            [
                "大师4K Lite",
                "SE 4K",
                "大师 4K",
                "SeeMo 4k",
                "M7系列",
                "CoMo",
                "CoMo SE",
                "S60 滑轨",
            ],
            FULL_FEATURED_PRODUCTS,
        )

    def test_expected_store_links_cover_displayed_channels(self):
        for country, channels in COUNTRY_CHANNELS.items():
            for channel in channels:
                with self.subTest(country=country, channel=channel):
                    self.assertIn((country, channel), EXPECTED_STORE_LINKS)
                    self.assertIn((country, channel), EXPECTED_STORE_SOURCE_URLS)
                    self.assertTrue(EXPECTED_STORE_LINKS[(country, channel)])
                    self.assertTrue(EXPECTED_STORE_SOURCE_URLS[(country, channel)])

        self.assertIn((DIRECT_WEB_COUNTRY, DIRECT_WEB_CHANNEL), EXPECTED_STORE_LINKS)
        self.assertIn((DIRECT_WEB_COUNTRY, DIRECT_WEB_CHANNEL), EXPECTED_STORE_SOURCE_URLS)

    def test_featured_product_channel_link_matrix_is_explicit(self):
        for country in FEATURED_PRODUCT_COUNTRIES:
            for channel in FEATURED_PRODUCT_CHANNELS_BY_COUNTRY.get(country, []):
                for product in FEATURED_PRODUCTS:
                    with self.subTest(country=country, channel=channel, product=product):
                        configured = (country, channel, product) in EXPECTED_PRODUCT_LINKS_BY_CHANNEL
                        expected_missing = (
                            country,
                            channel,
                            product,
                        ) in EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS
                        self.assertNotEqual(configured, expected_missing)

    def test_missing_overseas_platform_product_link_falls_back_to_global_official_url(self):
        key = ("墨西哥", "Amazon", "大师4K Lite")

        self.assertEqual(
            [["accsoon.com/cineview-master-4k-lite"]],
            EXPECTED_PRODUCT_LINKS_BY_CHANNEL[key],
        )
        self.assertEqual(
            ["https://accsoon.com/cineview-master-4k-lite/"],
            EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL[key],
        )
        self.assertNotIn(key, EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS)

    def test_missing_china_platform_product_link_falls_back_to_cn_official_url(self):
        key = (CHINA, "JD", "CoMo")

        self.assertEqual(
            [["accsoon.cn/accsoon-como"]],
            EXPECTED_PRODUCT_LINKS_BY_CHANNEL[key],
        )
        self.assertEqual(
            ["https://accsoon.cn/accsoon-como/"],
            EXPECTED_PRODUCT_SOURCE_URLS_BY_CHANNEL[key],
        )
        self.assertNotIn(key, EXPECTED_MISSING_FEATURED_PRODUCT_CHANNEL_LINKS)

    def test_other_region_featured_product_links_are_explicit(self):
        for product in FEATURED_PRODUCTS:
            with self.subTest(country=DIRECT_WEB_COUNTRY, product=product):
                configured = (DIRECT_WEB_COUNTRY, product) in EXPECTED_PRODUCT_LINKS
                expected_missing = (DIRECT_WEB_COUNTRY, product) in EXPECTED_MISSING_FEATURED_PRODUCT_LINKS
                self.assertNotEqual(configured, expected_missing)

    def test_expected_url_fragments_extract_marketplace_identifiers(self):
        self.assertEqual(
            [["amazon.com", "b0dknjtmnp"]],
            expected_fragments_from_url("https://www.amazon.com/dp/B0DKNJTMNP?th=1"),
        )
        self.assertEqual(
            [["aliexpress", "1005007997162678"]],
            expected_fragments_from_url("https://www.aliexpress.com/item/1005007997162678.html"),
        )
        self.assertEqual(
            [["item.jd.com", "10187128773918"], ["10187128773918"]],
            expected_fragments_from_url("https://item.jd.com/10187128773918.html"),
        )
        self.assertEqual(
            [["taobao", "981646008175"], ["981646008175"]],
            expected_fragments_from_url("https://item.taobao.com/item.htm?id=981646008175&spm=abc"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
