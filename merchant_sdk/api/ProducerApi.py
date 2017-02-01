from typing import List, Type

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

    def get_products(self):
        r = self.request('get', 'products')
        return Product.from_list(r.json())

    def add_products(self, products: List[Type[Product]]):
        product_dict_list = [p.to_dict() for p in products]
        self.request('post', 'products', json=product_dict_list)

    def update_products(self, products: List[Type[Product]]):
        product_dict_list = [p.to_dict() for p in products]
        self.request('put', 'products', json=product_dict_list)

    def get_product(self, product_uid):
        r = self.request('get', 'products/{}'.format(product_uid))
        return Product.from_dict(r.json())

    def add_product(self, product: Type[Product]):
        self.request('post', 'products', json=product.to_dict())

    def update_product(self, product: Type[Product]):
        self.request('put', 'products/{}'.format(product.uid), json=product.to_dict())

    def delete_product(self, product_uid):
        self.request('delete', 'products/{}'.format(product_uid))
