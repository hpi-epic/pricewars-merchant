import argparse
import sys

sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer

'''
    Start implementation
'''

merchant_token = 'PlmNksxJyL9bei6288Utupsi1vecpdPGOCd96aS4wbfbLmdTu8NpxFYxBDa1q1HF'
merchant_id = 'MpWsNBYFvUgqq+rI0FGDTPYJ/RLB9ED7KLmIQwGqzAk='

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'listedOffers': 10,
    'shipping': 5,
    'primeShipping': 1,
    'max_req_per_sec': 10,
    'priceDifference': 0.01
}


class SecondCheapestMerchantApp(MerchantBaseLogic):
    def __init__(self):
        MerchantBaseLogic.__init__(self)
        global settings
        self.settings = settings

        '''
            Predefined API token
        '''
        self.merchant_id = settings['merchant_id']
        self.merchant_token = merchant_token

        '''
            Setup API
        '''
        PricewarsRequester.add_api_token(merchant_token)
        self.marketplace_api = MarketplaceApi(host=self.settings['marketplace_url'])
        self.producer_api = ProducerApi(host=self.settings['producerEndpoint'])

        '''
            Start Logic Loop
        '''
        self.run_logic_loop()

    def update_api_endpoints(self):
        self.marketplace_api.host = self.settings['marketplace_url']
        self.producer_api.host = self.settings['producerEndpoint']

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

    def buy_product_and_post_to_marketplace(self):
        print('buy Product and update')
        new_product = self.producer_api.buy_product(merchant_token=self.merchant_token)
        existing_offers = self.get_existing_uid_offers_from_marketplace(new_product.uid)
        target_price = self.get_second_cheapest_price(existing_offers, new_product.price)
        existing_offer_id = self.is_product_uid_offered_by_myself(existing_offers)
        self.post_offer(new_product, target_price, existing_offer_id)

    def get_existing_uid_offers_from_marketplace(self, product_uid):
        all_offers = self.marketplace_api.get_offers()
        uid_offers = [offer for offer in all_offers if offer.uid == product_uid]
        return uid_offers

    def get_second_cheapest_price(self, offers, purchase_price):
        second_cheapest_offer = cheapest_offer = 2 * purchase_price
        for offer in sorted(offers, key=lambda offer_entry: offer_entry.price, reverse=True):
            if offer.merchant_id == self.merchant_id:
                continue

            if offer.price < cheapest_offer:
                second_cheapest_offer = cheapest_offer - self.settings['priceDifference']
                cheapest_offer = offer.price

        return second_cheapest_offer

    def is_product_uid_offered_by_myself(self, offers):
        return next((offer.offer_id for offer in offers if offer.merchant_id == self.merchant_id), None)

    def post_offer(self, product, price, existing_offer_id):
        new_offer = Offer.from_product(product)
        new_offer.price = price
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        if existing_offer_id is None:
            self.marketplace_api.add_offer(new_offer)
        else:
            self.marketplace_api.restock(existing_offer_id, product.amount, product.signature)

    def get_amount_of_own_offers(self):
        all_offers = self.marketplace_api.get_offers()
        own_offers = [offer for offer in all_offers if offer.merchant_id == self.merchant_id]
        return len(own_offers)

    def setup(self, existing_offers=0):
        try:
            for i in range(settings['listedOffers']):
                self.buy_product_and_post_to_marketplace()
        except Exception as e:
            print('error on setup or increasing offer amount:', e)

    def execute_logic(self):
        amount_of_own_offers = self.get_amount_of_own_offers()
        self.setup(amount_of_own_offers)
        return self.interval

    def sold_offer(self, offer_json):
        self.buy_product_and_post_to_marketplace()


'''
    Setup main function to start flask server in Development
'''

merchant_logic = SecondCheapestMerchantApp()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
