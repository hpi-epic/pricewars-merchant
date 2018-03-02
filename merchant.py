import argparse

from pricewars_merchant import PricewarsMerchant
from api import Marketplace, Producer
from models import Offer


class Merchant(PricewarsMerchant):
    def __init__(self, token, port, marketplace_url, producer_url):
        super().__init__(port)

        self.settings.update({
            'initialProducts': 5,
            'shipping': 5,
            'primeShipping': 1,
            'maxReqPerSec': 40.0,
            'price_decrement': 0.05,
            'default price': 30
        })

        self.marketplace_url = marketplace_url
        self.producer_url = producer_url
        self.marketplace = Marketplace(token, host=self.marketplace_url)
        self.marketplace.wait_for_host()
        self.merchant_token = token or self.marketplace.register(endpoint_url_or_port=port, merchant_name='Cheapest').merchant_token

        self.settings['merchant_id'] = PricewarsMerchant.calculate_id(self.merchant_token)

        self.products = {}
        self.offers = {}

        self.merchant_id = self.settings['merchant_id']

        self.producer = Producer(self.merchant_token, host=self.producer_url)
        self.setup()

    def sold_offer(self, offer):
        print('Product sold')
        # TODO: we store the amount in self.offers but do not decrease it here
        if self.state != 'running':
            return
        try:
            offers = self.marketplace.get_offers()
            self.buy_product_and_update_offer(offers)
        except Exception as e:
            print('error on handling a sold offer:', e)

    '''
        Merchant Logic for being the cheapest
    '''

    def setup(self):
        try:
            marketplace_offers = self.marketplace.get_offers()
            for i in range(self.settings['initialProducts']):
                self.buy_product_and_update_offer(marketplace_offers)
        except Exception as e:
            print('error on setup:', e)

    def update_offers(self):
        try:
            offers = self.marketplace.get_offers()

            items_offered = sum(o.amount for o in offers if o.merchant_id == self.settings['merchant_id'])
            while items_offered < (self.settings['initialProducts'] - 1):
                self.buy_product_and_update_offer(offers)
                items_offered = sum(o.amount for o in self.marketplace.get_offers() if
                                    o.merchant_id == self.settings['merchant_id'])

            for product in self.products.values():
                if product.uid in self.offers:
                    offer = self.offers[product.uid]
                    offer.price = self.calculate_prices(offers, product.product_id)
                    try:
                        self.marketplace.update_offer(offer)
                    except Exception as e:
                        print('error on updating an offer:', e)
                else:
                    print('ERROR: product UID is not in offers; skipping.')
        except Exception as e:
            print('error on executing the logic:', e)
        return self.settings['maxReqPerSec'] / 10

    def calculate_prices(self, marketplace_offers, product_id):
        competitive_offers = [offer for offer in marketplace_offers if
                              offer.merchant_id != self.merchant_id and offer.product_id == product_id]
        cheapest_offer = 999

        if len(competitive_offers) == 0:
            return self.settings['default price']
        for offer in competitive_offers:
            if offer.price < cheapest_offer:
                cheapest_offer = offer.price

        new_price = cheapest_offer - self.settings['price_decrement']

        return new_price

    def add_new_product_to_offers(self, new_product, marketplace_offers):
        price = self.calculate_prices(marketplace_offers, new_product.product_id)
        shipping_time = {
            'standard': self.settings['shipping'],
            'prime': self.settings['primeShipping']
        }
        new_offer = Offer.from_product(new_product, price, shipping_time)
        new_offer = self.marketplace.add_offer(new_offer)
        self.products[new_product.uid] = new_product
        self.offers[new_product.uid] = new_offer

    def restock_existing_product(self, new_product, marketplace_offers):
        product = self.products[new_product.uid]
        product.amount += new_product.amount
        product.signature = new_product.signature

        offer = self.offers[product.uid]
        offer.price = self.calculate_prices(marketplace_offers, product.product_id)
        offer.amount = product.amount
        offer.signature = product.signature
        self.marketplace.restock(offer.offer_id, new_product.amount, offer.signature)

    def buy_product_and_update_offer(self, marketplace_offers):
        order = self.producer.order(1)
        product = order.product

        if product.uid in self.products:
            self.restock_existing_product(product, marketplace_offers)
        else:
            self.add_new_product_to_offers(product, marketplace_offers)


def parse_arguments():
    parser = argparse.ArgumentParser(description='PriceWars Merchant Being Cheapest')
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
