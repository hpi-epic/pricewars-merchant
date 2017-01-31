import argparse
import sys

sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer

'''
    Template for Ruby deployment to insert defined tokens
'''
merchant_token = "{{API_TOKEN}}"
#merchant_token = 'Mz7J8Y8lKOFZ0fWH4MBMpG8BFCnJQXymX66feERzcgZcL6uQR6mHMuSb7GuXntKL'

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'merchant_url': 'http://172.16.56.166:5000',
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'intervalMin': 1.0,
    'intervalMax': 1.0,
    'initialProducts': 5,
    'shipping': 5,
    'primeShipping': 1,
    'maxReqPerSec': 10,
    'outstandingProductsToBuy': 1,
    'underprice': 0.5
    }

def get_from_list_by_key(dict_list, key, value):
    elements = [elem for elem in dict_list if elem[key] == value]
    if elements:
        return elements[0]
    return None


class MerchantSampleLogic(MerchantBaseLogic):
    def __init__(self):
        MerchantBaseLogic.__init__(self)
        global settings
        self.settings = settings

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
        self.marketplace_api = MarketplaceApi(host=self.settings['marketplace_url'])
        self.producer_api = ProducerApi(host=self.settings['producerEndpoint'])

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
        self.producer_api.host = self.settings['producerEndpoint']

    '''
        Implement Abstract methods / Interface
    '''

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
        settings['outstandingProductsToBuy'] += 1

    '''
        Merchant Logic for being the cheapest
    '''
    def setup(self):
        try:
            marketplace_offers = self.marketplace_api.get_offers()
            for i in range(settings['initialProducts']):
                self.buy_product_and_update_offer(marketplace_offers)
        except Exception as e:
            print('error on setup:', e)

    def execute_logic(self):
        offers = self.marketplace_api.get_offers()

        missing_offers = self.settings["initialProducts"] - len(self.offers)
        if missing_offers < 0:
            missing_offers = 0
        for missing_offer in range(missing_offers):
            self.buy_product_and_update_offer(offers)

        for product in self.products.values():
            offer = self.offers[product.uid]
            offer = self.offers[product.uid]
            offer.price = self.calculate_prices(offers, product.uid, product.price)
            self.marketplace_api.update_offer(offer)
        return settings['maxReqPerSec']/10

    def calculate_prices(self, marketplace_offers, product_uid, purchase_price):
        competitive_offers = []
        [competitive_offers.append(offer) for offer in marketplace_offers if offer.merchant_id != self.merchant_id and offer.uid == product_uid]
        cheapest_offer = 999

        if len(competitive_offers) == 0:
            return 2 * purchase_price
        for offer in competitive_offers:
            if offer.price < cheapest_offer:
                cheapest_offer = offer.price

        return cheapest_offer - settings['underprice']

    def add_new_product_to_offers(self, new_product, marketplace_offers):
        new_offer = Offer.from_product(new_product)
        new_offer.price = self.calculate_prices(marketplace_offers, new_product.uid, new_product.price)
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        self.products[new_product.uid] = new_product
        new_offer.offer_id = self.marketplace_api.add_offer(new_offer).offer_id
        self.offers[new_product.uid] = new_offer

    def restock_existing_product(self, new_product, marketplace_offers):
        print('restock product', new_product)
        product = self.products[new_product.uid]
        product.amount += new_product.amount
        product.signature = new_product.signature

        offer = self.offers[product.uid]
        print('in this offer:', offer)
        offer.price = self.calculate_prices(marketplace_offers, product.uid, product.price)
        offer.amount = product.amount
        offer.signature = product.signature
        self.marketplace_api.restock(offer.offer_id, new_product.amount, offer.signature)

    def buy_product_and_update_offer(self, marketplace_offers):
        new_product = self.producer_api.buy_product(merchant_token=self.merchant_token)

        if new_product.uid in self.products:
            self.restock_existing_product(new_product, marketplace_offers)
        else:
            self.add_new_product_to_offers(new_product, marketplace_offers)


merchant_logic = MerchantSampleLogic()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant Being Cheapest')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
