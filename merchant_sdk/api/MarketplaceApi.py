from.PricewarsBaseApi import PricewarsBaseApi
from ..models import Offer, MerchantRegisterResponse


class MarketplaceApi(PricewarsBaseApi):

    def __init__(self, host='http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace'):
        PricewarsBaseApi.__init__(self, host=host)

    def get_offers(self):
        r = self.request('get', 'offers')
        return Offer.from_list(r.json())

    def add_offer(self, offer):
        r = self.request('post', 'offers', json=offer.to_dict())
        return Offer.from_dict(r.json())

    def update_offer(self, offer):
        self.request('put', 'offers/{:d}'.format(offer.offer_id), json=offer.to_dict())

    def restock(self, offer_id=-1, amount=0, signature=''):
        body = {
            'amount': amount,
            'signature': signature
        }
        self.request('patch', 'offers/{:d}/restock'.format(offer_id), json=body)

    def register_merchant(self, api_endpoint_url='', merchant_name='', algorithm_name=''):
        body = {
            'api_endpoint_url': api_endpoint_url,
            'merchant_name': merchant_name,
            'algorithm_name': algorithm_name
        }
        r = self.request('post', 'merchants', json=body)
        return MerchantRegisterResponse.from_dict(r.json())

    def unregister_merchant(self, merchant_token=''):
        self.request('delete', 'merchants/{:s}'.format(merchant_token))
