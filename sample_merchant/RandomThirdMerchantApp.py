import argparse
import sys

sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer
from random import randint

'''
    Template for Ruby deployment to insert defined tokens
'''
merchant_token = "{{API_TOKEN}}"
#merchant_token = 'GEKDWUPsjYDMH7jUlhw3tD5YZZowGneW3yjZT8RDgfZxmJSY1OaubfSBFH8V6m28'

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'marketplace_url': MerchantBaseLogic.get_marketplace_url(),
    'producer_url': MerchantBaseLogic.get_producer_url(),
    'initialProducts': 5,
    'shipping': 5,
    'primeShipping': 1,
    'max_req_per_sec': 10.0,
    'underprice': 0.5,
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
            Internal state handling
        '''
        self.execQueue = []

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
        self.producer_api = ProducerApi(host=self.settings['producer_url'])

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
        self.execQueue.append((self.sold_product, [offer]))

    '''
        Merchant Logic
    '''

    def setup(self):
        try:
            for i in range(settings['initialProducts']):
                self.buy_product_and_update_offer()
        except Exception as e:
            print('error on setup:', e)

    def execute_logic(self):
        # execute queued methods
        tmp_queue = [e for e in self.execQueue]
        self.execQueue = []
        for method, args in tmp_queue:
            method(*args)

        try:
            offers = self.marketplace_api.get_offers()

            for product in self.products.values():
                if product['amount'] > 0:
                    competitor_offers = []
                    for offer in offers:
                        if offer.merchant_id != self.merchant_id and offer.product_id == product.product_id:
                            competitor_offers.append(offer.price)
                    offer = self.offers[product.uid]
                    if len(competitor_offers) >0:
                        competitor_offers.sort()
                        if len(competitor_offers) > 2:
                            self.adjust_prices(offer=offer, product=product, lowest_competitor_price=competitor_offers[0], second_competitor_price=competitor_offers[1], third_competitor_price=competitor_offers[2])
                        elif len(competitor_offers) > 1:
                            self.adjust_prices(offer=offer, product=product, lowest_competitor_price=competitor_offers[0], second_competitor_price=competitor_offers[1],third_competitor_price=0)
                        else:
                            self.adjust_prices(offer=offer, product=product, lowest_competitor_price=competitor_offers[0], second_competitor_price=0, third_competitor_price=0)

        except Exception as e:
            print('error on executing logic:', e)
        # returns sleep value;
        return 60.0 / settings['max_req_per_sec']

    def adjust_prices(self, offer=None, product=None, lowest_competitor_price=0,second_competitor_price=0,third_competitor_price=0):
        if not offer or not product:
            return
        min_price = product.price
        max_price = product.price*2
        target_position = randint(1,3)
        if (target_position == 3 and third_competitor_price > 0):
            price = third_competitor_price - settings['underprice']
        elif (target_position == 2 and second_competitor_price > 0):
            price = second_competitor_price - settings['underprice']
        else:
            price = lowest_competitor_price - settings['underprice']
        price = min(price, max_price)
        if price < min_price:
            price = max_price
        offer.price = price
        try:
            self.marketplace_api.update_offer(offer)
        except Exception as e:
            print('error on updating offer:', e)

    def sold_product(self, sold_offer):
        print('soldProduct, offer:', sold_offer)
        if sold_offer.uid in self.offers:
            print('found in offers')
            offer = self.offers[sold_offer.uid]
            offer.amount -= sold_offer.amount_sold
            product = self.products[sold_offer.uid]
            product.amount -= sold_offer.amount_sold
            if product.amount <= 0:
                print('product {:d} is out of stock!'.format(product.uid))
            self.buy_product_and_update_offer()

    def add_new_product_to_offers(self, new_product):
        new_offer = Offer.from_product(new_product)
        new_offer.price = new_offer.price*2
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        self.products[new_product.uid] = new_product
        new_offer.offer_id = self.marketplace_api.add_offer(new_offer).offer_id
        self.offers[new_product.uid] = new_offer

    def restock_existing_product(self, new_product):
        print('restock product', new_product)
        product = self.products[new_product.uid]
        product.amount += new_product.amount
        product.signature = new_product.signature

        offer = self.offers[product.uid]
        print('in this offer:', offer)
        offer.amount = product.amount
        offer.signature = product.signature
        try:
            self.marketplace_api.restock(offer.offer_id, new_product.amount, offer.signature)
        except Exception as e:
            print('error on restocking offer:', e)

    def buy_product_and_update_offer(self):
        print('buy Product and update')
        try:
            new_product = self.producer_api.buy_product()

            if new_product.uid in self.products:
                self.restock_existing_product(new_product)
            else:
                self.add_new_product_to_offers(new_product)
        except Exception as e:
            print('error on buying a new product:', e)


merchant_logic = MerchantSampleLogic()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
