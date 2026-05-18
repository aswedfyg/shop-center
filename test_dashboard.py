# -*- coding: utf-8 -*-

import socket
import unittest

from dashboard import allocate_unique_port, find_available_port, format_index_html, normalize_devices


class DashboardTest(unittest.TestCase):
    def test_normalize_devices_deduplicates_udid(self):
        payload = {
            "devices": [
                {"name": "Phone A", "udid": "device-1"},
                {"name": "Phone A Duplicate", "udid": "device-1"},
                {"name": "Phone B", "udid": "device-2"},
            ]
        }

        self.assertEqual(
            [{"name": "Phone A", "udid": "device-1"}, {"name": "Phone B", "udid": "device-2"}],
            normalize_devices(payload),
        )

    def test_allocate_unique_port_skips_reserved_and_busy_ports(self):
        reserved = set()
        busy_port = find_available_port("127.0.0.1", 8800)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", busy_port))

            allocated = allocate_unique_port("127.0.0.1", busy_port, reserved)

        self.assertNotEqual(busy_port, allocated)
        self.assertIn(allocated, reserved)

    def test_index_html_unescapes_template_braces(self):
        html = format_index_html()

        self.assertIn("body {", html)
        self.assertIn(".device-summary {", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("}}", html)

    def test_quick_fill_syncs_picker_inputs(self):
        html = format_index_html()

        self.assertIn("function syncInputFromChecks(name)", html)
        self.assertIn('setChecks("products", ["CoMo SE", "CoMo"]);', html)
        self.assertIn('onchange="syncInputFromChecks', html)
        self.assertIn("function fillLatestFailureBreakpoint()", html)
        self.assertIn('id="strictProductDestination" type="checkbox" checked', html)
        self.assertIn('id="productTextFallback" type="checkbox"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
