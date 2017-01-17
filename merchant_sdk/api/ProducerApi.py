from .PricewarsBaseApi import PricewarsBaseApi
from ..models import Product


class ProducerApi(PricewarsBaseApi):

    def __init__(self, host='http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de'):
        PricewarsBaseApi.__init__(self, host=host)

    def buy_product(self, merchant_token=''):
        params = {
            'merchant_token': merchant_token
        }
        r = self.request('get', 'buy', params=params)
        return Product.from_dict(r.json())
