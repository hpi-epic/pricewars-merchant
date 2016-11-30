import unittest
import MerchantApp
import json
import requests
from flask import Flask, request, Response

class MerchantTestCase(unittest.TestCase):

    def setUp(self):
        self.app = MerchantApp.app.test_client()
        rv = self.app.get('/settings')
        self.settings = dict(json.loads(rv.data.decode("utf-8")))
    
    @staticmethod
    def equal_dicts(self, d1, d2):
        return len(d1.items() & d2.items()) == len(d1.items())
    
    def test_get_settings(self):
        rv = self.app.get('/settings')
        response = dict(json.loads(rv.data.decode("utf-8")))
        assert (self.settings == response) & self.equal_dicts(self, self.settings, response)
        
    def test_post_settings(self):
        self.settings['merchant_url'] = 'foo'
        rv = self.app.post('/settings',data=json.dumps(dict(self.settings)),content_type='application/json')
        response = dict(json.loads(rv.data.decode('utf-8')))
        assert (response['merchant_url'] == 'foo') & self.equal_dicts(self, self.settings, response)

    
    def test_put_settings(self):
        self.settings['marketplace_url'] = 'bar'
        rv = self.app.put('/settings',data=json.dumps(dict(self.settings)),content_type='application/json')
        response = dict(json.loads(rv.data.decode('utf-8')))
        assert (response['marketplace_url'] == 'bar') & self.equal_dicts(self, self.settings, response)

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