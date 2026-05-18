import unittest
import sys

from android.product_center_flow import ProductCenterAutomationCase
from common.report import ProductCenterHtmlRunner


class ProductCenterTest(ProductCenterAutomationCase):
    __test__ = True


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(ProductCenterTest)


if __name__ == "__main__":
    print("开始运行 Android 产品中心自动化测试...")
    test_names = sys.argv[1:]
    if test_names:
        suite = unittest.TestSuite()
        for test_name in test_names:
            if "." not in test_name:
                test_name = f"ProductCenterTest.{test_name}"
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName(test_name, module=sys.modules[__name__]))
    else:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProductCenterTest)
    result = ProductCenterHtmlRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
