import unittest
import MerchantApp
import json
import requests
from flask import Flask, request, Response

class MerchantTestCase(unittest.TestCase):

    def setUp(self):
        self.app = MerchantApp.app.test_client()
        
    def test_get_settings(self):
        rv = self.app.get('/settings')
        settings = {
            'merchant_id': 0,
            'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
            'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de',
            'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
            'priceDecrease': 1,
            'initialProducts': 5,
            'minPriceMargin': 16,
            'maxPriceMargin': 32,
            'shipping': 5,
            'primeShipping': 1,
            'debug': False
        }
        js = json.dumps(settings)
        resp = Response(js, status=200, mimetype='application/json')
        return resp
        assert b'resp' in rv.data
        
if __name__ == '__main__':
    unittest.main()