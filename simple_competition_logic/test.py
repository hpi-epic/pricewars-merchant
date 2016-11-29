import unittest
import MerchantApp

class MerchantTestCase(unittest.TestCase):

    def setUp(self):
        self.app = MerchantApp.app.test_client()
    
if __name__ == '__main__':
    unittest.main()