import argparse
import sys

sys.path.append('./')
sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, Marketplace, Producer
from merchant_sdk.models import Offer
import time

merchant_token = "{{API_TOKEN}}"

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'marketplace_url': MerchantBaseLogic.get_marketplace_url(),
    'producer_url': MerchantBaseLogic.get_producer_url(),
    'price_decrement': 0.05,
    'initialProducts': 3,
    'minPriceMargin': 3.0,
    'maxPriceMargin': 12.0,
    'shipping': 1,
    'primeShipping': 1,
    'max_req_per_sec': 10.0
}


class MerchantD(MerchantBaseLogic):
    def __init__(self):
        MerchantBaseLogic.__init__(self)
        global settings
        self.settings = settings

        '''
            Internal state handling
        '''
        self.execQueue = []
        self.marketplace_requests = []


        '''
            Information store
        '''
        self.products = {}
        self.offers = {}

        '''
            Predefined API token
        '''
        self.merchant_id = settings['merchant_id']
        self.merchant_token = merchant_token

        '''
            Setup API
        '''
        PricewarsRequester.add_api_token(self.merchant_token)
        self.marketplace_api = Marketplace(host=self.settings['marketplace_url'], debug=False)
        self.producer_api = Producer(host=self.settings['producer_url'], debug=False)

        '''
            Start Logic Loop
        '''
        self.run_logic_loop()

    def update_api_endpoints(self):
        """
        Updated settings may contain new endpoints, so they need to be set in the api client as well.
        However, changing the endpoint (after simulation start) may lead to an inconsistent state
        :return: None
        """
        self.marketplace_api.host = self.settings['marketplace_url']
        self.producer_api.host = self.settings['producer_url']

    def get_settings(self):
        return self.settings

    def update_settings(self, new_settings):
        def cast_to_expected_type(key, value, def_settings=self.settings):
            if key in def_settings:
                return type(def_settings[key])(value)
            else:
                return value

        new_settings_casted = dict([
            (key, cast_to_expected_type(key, new_settings[key]))
            for key in new_settings
        ])

        self.settings.update(new_settings_casted)
        self.update_api_endpoints()
        return self.settings

    def sold_offer(self, offer):
        # print("sold offer")
        self.execQueue.append((self.sold_product, [offer]))

    def buy_missing_products(self):
        for i in range(self.settings["initialProducts"] - sum(offer.amount for offer in self.offers.values())):
            self.buy_product_and_update_offer()

    def setup(self):
        try:
            # get all products for later comparison over all qualities
            self.product = {}
            for product in self.producer_api.get_products():
                self.products[product.uid] = product

            # get all existing offers from marketplace
            self.offer = {}
            for offer in self.marketplace_api.get_offers():
                if offer.merchant_id == self.merchant_id:
                    self.offers[offer.uid] = offer

            # buy new products if none or not enough exist
            self.buy_missing_products()

        except Exception as e:
            print('error on setup:', e)

    def execute_logic(self):
        # execute queued methods
        tmp_queue = [e for e in self.execQueue]
        self.execQueue = []
        for method, args in tmp_queue:
            method(*args)

        # if initialProducts setting increased after start, get new products
        self.buy_missing_products()

        self.update_market_situation()

        return self.calculate_intervall()

    def base_price_diff(self, offer):
        try:
            product = self.products[offer.uid]
        except KeyError:
            # we see a product that we have not yet received from the producer
            products = [p for p in self.producer_api.get_products() if p.uid == offer.uid]
            product = products[0] # there should be only one product for a given uid
            self.products[product.uid] = product
        return offer.price - product.price

    def adjust_prices(self, offer=None, lowest_price_diff=0):
        product = self.products[offer.uid]
        if not offer or not product:
            return
        price_diff = min(lowest_price_diff - settings['price_decrement'], settings['maxPriceMargin'])
        if price_diff < settings['minPriceMargin']:
            price_diff = settings['maxPriceMargin']
        new_product_price = product.price + price_diff
        if new_product_price != offer.price:
            offer.price = new_product_price
            # print("update to new price ", new_product_price)
            self.marketplace_api.update_offer(offer)
            self.request_done()

    def update_market_situation(self):
        marketplace_offers = self.marketplace_api.get_offers()
        for own_offer in self.offers.values():
            if self.quora_exhausted():
                break
            if own_offer.amount > 0:
                competitor_offers_price_diff = []
                for marketplace_offer in marketplace_offers:
                    if marketplace_offer.merchant_id != self.merchant_id and marketplace_offer.product_id == own_offer.product_id:
                        competitor_offers_price_diff.append(self.base_price_diff(marketplace_offer))
                if len(competitor_offers_price_diff) > 0:
                    self.adjust_prices(offer=own_offer, lowest_price_diff=min(competitor_offers_price_diff))
                else:
                    self.adjust_prices(offer=own_offer)

    def sold_product(self, sold_offer):
        # print('soldProduct, offer:', sold_offer)
        if sold_offer.uid in self.offers:
            # print('found in offers')
            offer = self.offers[sold_offer.uid]
            offer.amount -= sold_offer.amount_sold
            product = self.products[sold_offer.uid]
            product.amount -= sold_offer.amount_sold
            if product.amount <= 0:
                pass
                # print('product {:d} is out of stock!'.format(product.uid))
            self.buy_product_and_update_offer()

    def add_new_product_to_offers(self, new_product):
        new_offer = Offer.from_product(new_product)
        new_offer.price += settings['maxPriceMargin']
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        self.products[new_product.uid] = new_product
        new_offer.offer_id = self.marketplace_api.add_offer(new_offer).offer_id
        self.offers[new_product.uid] = new_offer

    def restock_existing_product(self, new_product):
        # print('restock product', new_product)
        product = self.products[new_product.uid]
        product.amount += new_product.amount
        product.signature = new_product.signature

        offer = self.offers[product.uid]
        # print('in this offer:', offer)
        offer.amount = product.amount
        offer.signature = product.signature
        self.marketplace_api.restock(offer.offer_id, new_product.amount, offer.signature)

    def buy_product_and_update_offer(self):
        # print('buy Product and update')
        new_product = self.producer_api.buy_product()

        if new_product.uid in self.offers:
            self.restock_existing_product(new_product)
        else:
            self.add_new_product_to_offers(new_product)

    def request_done(self):
        self.marketplace_requests.insert(0,time.time())

    def quora_exhausted(self):
        while len(self.marketplace_requests) > 0:
            last = self.marketplace_requests.pop()
            now = time.time()
            if now - last < 1:
                self.marketplace_requests.append(last)
                break

        return len(self.marketplace_requests) >= settings['max_req_per_sec']

    def active_offers_count(self):
        offer_count = 0
        for offer in self.offers.values():
            if offer.amount > 0:
                offer_count += 1
        return offer_count

    def calculate_intervall(self):
        if len(self.marketplace_requests) == 0:
            return 0
        else:
            offer_count = self.active_offers_count()
            remaining_reqs = max(1, settings['max_req_per_sec'] - len(self.marketplace_requests))
            time_to_next_release = time.time() - self.marketplace_requests[-1]
            return (offer_count / remaining_reqs) * time_to_next_release


merchant_logic = MerchantD()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')

    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
