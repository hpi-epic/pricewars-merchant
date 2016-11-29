import unittest
import MerchantApp
import json
import requests
from flask import Flask, request, Response

class MerchantTestCase(unittest.TestCase):

    def setUp(self):
        self.app = MerchantApp.app.test_client()
    
    @staticmethod
    def equal_dicts(self, d1, d2):
        return len(d1.items() & d2.items()) == len(d1.items())
    
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
        response_json = json.loads(rv.data.decode("utf-8"))
        js = json.dumps(settings)
        assert self.equal_dicts(self, settings, response_json) & (js in rv.data.decode("utf-8"))
        
    def test_post_settings(self):
        settings = {
            'merchant_id': 0,
            'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
            'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de',
            'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
            'priceDecrease': 1,
            'initialProducts': 5,
            'minPriceMargin': 17,
            'maxPriceMargin': 32,
            'shipping': 5,
            'primeShipping': 1,
            'debug': False
        }
        rv = self.app.post('/settings',data=json.dumps(dict(settings)),content_type='application/json')
        response_json = json.loads(rv.data.decode('utf-8'))
        assert (response_json['minPriceMargin'] == 17) & self.equal_dicts(self, settings, response_json)

    
    def test_put_settings(self):
        settings = {
            'merchant_id': 0,
            'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
            'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de',
            'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
            'priceDecrease': 1,
            'initialProducts': 5,
            'minPriceMargin': 16,
            'maxPriceMargin': 33,
            'shipping': 5,
            'primeShipping': 1,
            'debug': False
        }
        rv = self.app.put('/settings',data=json.dumps(dict(settings)),content_type='application/json')
        response_json = json.loads(rv.data.decode('utf-8'))
        assert (response_json['maxPriceMargin'] == 33) & self.equal_dicts(self, settings, response_json)

    def test_post_sold(self):
        sold_offer = {
            'offer_id': 0,
            'amount': 0,
            'consumer_id': 'string',
            'price': 0,
            'prime': True
        }
        rv = self.app.post('/sold', data=json.dumps(dict(sold_offer)),content_type='application/json')
        response_json = json.loads(rv.data.decode('utf-8'))
        assert response_json == {}
        
    
if __name__ == '__main__':
    unittest.main()