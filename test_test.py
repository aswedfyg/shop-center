import unittest

class TestTest(unittest.TestCase):
    def test_simple(self):
        print("Running simple test...")
        self.assertEqual(1, 1)
        print("Simple test passed!")

if __name__ == '__main__':
    print("开始运行测试...")
    unittest.main()
    print("测试运行完成")
