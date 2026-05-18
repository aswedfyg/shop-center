import unittest

class SimpleTest(unittest.TestCase):
    def test_one(self):
        print("Running test_one...")
        self.assertEqual(1, 1)
        print("test_one passed!")

    def test_two(self):
        print("Running test_two...")
        self.assertEqual(2, 2)
        print("test_two passed!")

if __name__ == '__main__':
    print("Starting tests...")
    unittest.main()
    print("Tests completed!")
