import argparse
from typing import Optional

from pricewars_merchant import PricewarsMerchant
from api import Marketplace, Producer
from models import Offer


class Merchant(PricewarsMerchant):
    def __init__(self, token: Optional[str], port: int, marketplace_url: str, producer_url: str, name='Cheapest'):
        super().__init__(port)

        self.settings.update({
            'max stock': 20,
            'shipping': 5,
            'primeShipping': 1,
            'price decrement': 0.05,
            'default price': 30
        })

        self.marketplace = Marketplace(token, host=marketplace_url)
        self.marketplace.wait_for_host()

        if token:
            self.token = token
            self.merchant_id = self.calculate_id(token)
        else:
            register_response = self.marketplace.register(port, name)
            self.token = register_response.merchant_token
            self.merchant_id = register_response.merchant_id

        self.producer = Producer(self.token, host=producer_url)

    def sold_offer(self, offer):
        print('Product sold')

    def update_offers(self):
        market_situation = self.marketplace.get_offers()
        own_offers = [offer for offer in market_situation if offer.merchant_id == self.merchant_id]
        competitor_offers = [offer for offer in market_situation if offer.merchant_id != self.merchant_id]

        inventory_level = sum(offer.amount for offer in own_offers)
        if inventory_level == 0:
            self.restock(competitor_offers)

        self.update_prices(own_offers, competitor_offers)

    def restock(self, competitor_offers):
        order = self.producer.order(self.settings['max stock'])
        product = order.product
        price = self.calculate_prices(competitor_offers, product.product_id)
        shipping_time = {
            'standard': self.settings['shipping'],
            'prime': self.settings['primeShipping']
        }
        offer = Offer.from_product(product, price, shipping_time)
        self.marketplace.add_offer(offer)

    def update_prices(self, own_offers, competitor_offers):
        for offer in own_offers:
            price = self.calculate_prices(competitor_offers, offer.product_id)
            offer.price = price
            self.marketplace.update_offer(offer)

    def calculate_prices(self, competitor_offers, product_id):
        offers = [offer for offer in competitor_offers if offer.product_id == product_id]
        if not offers:
            return self.settings['default price']

        cheapest_offer = min(offers, key=lambda offer: offer.price)
        return cheapest_offer.price - self.settings['price decrement']


def parse_arguments():
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--port', type=int, help='port to bind flask App to')
    group.add_argument('--token', type=str, help='Merchant secret token')
    parser.add_argument('--marketplace', type=str, default=Marketplace.DEFAULT_URL, help='Marketplace URL')
    parser.add_argument('--producer', type=str, default=Producer.DEFAULT_URL, help='Producer URL')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    merchant = Merchant(args.token, args.port, args.marketplace, args.producer)
    merchant.run()
