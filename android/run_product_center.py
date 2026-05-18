import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android.product_center_flow import ProductCenterAutomationCase
from common.report import ProductCenterHtmlRunner


class ProductCenterTest(ProductCenterAutomationCase):
    __test__ = True


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(ProductCenterTest)


def build_suite(test_names):
    if any(name in {"-h", "--help", "/?"} for name in test_names):
        print("Usage: python android/run_product_center.py [test_method ...]")
        print("Example: python android/run_product_center.py test_03_purchase_channels_jump")
        raise SystemExit(0)

    if not test_names:
        return unittest.defaultTestLoader.loadTestsFromTestCase(ProductCenterTest)

    suite = unittest.TestSuite()
    for test_name in test_names:
        if "." not in test_name:
            test_name = f"ProductCenterTest.{test_name}"
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(test_name, module=sys.modules[__name__]))
    return suite


if __name__ == "__main__":
    suite = build_suite(sys.argv[1:])
    print("开始运行 Android 产品中心自动化测试...")
    result = ProductCenterHtmlRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
