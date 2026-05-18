import unittest

from android.product_center_flow import ProductCenterAutomationCase


class ProductCenterTest(ProductCenterAutomationCase):
    __test__ = True


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(ProductCenterTest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
