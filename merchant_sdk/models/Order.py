from typing import Union

from merchant_sdk.models.PricewarsObject import PricewarsObject
from merchant_sdk.models import Product


class Order(PricewarsObject):
    def __init__(self, price: float = 0.0, stock: int = -1, left_in_stock: int = 0,
                 product: Union[Product, dict] = None):
        self.price = price
        self.stock = stock
        self.left_in_stock = left_in_stock
        if type(product) == dict:
            self.product = Product.from_dict(product)
        else:
            self.product = product
