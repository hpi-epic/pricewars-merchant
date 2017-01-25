import argparse
import sys
import operator

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
    'listedOffers': 15,
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

        '''
            save purchase prices for offer updates
        '''
        self.purchase_prices = {}

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

    def buy_product_and_post_to_marketplace(self, all_offers):
        print('buy Product and update')
        new_product = self.buy_product()
        existing_offers = self.get_existing_uid_offers_from_marketplace(all_offers, new_product.uid)
        target_price = self.get_second_cheapest_price(existing_offers, new_product.price)
        existing_offer = self.get_own_offer_for_product_uid(existing_offers, new_product.uid)
        self.post_offer(new_product, target_price, existing_offer)

    def buy_product(self):
        new_product = self.producer_api.buy_product(merchant_token=self.merchant_token)
        if new_product.uid not in self.purchase_prices:
            self.purchase_prices[new_product.uid] = new_product.price
        return new_product

    def get_existing_uid_offers_from_marketplace(self, all_offers, product_uid):
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

    def get_own_offer_for_product_uid(self, offers, product_uid):
        return next((offer for offer in offers if offer.merchant_id == self.merchant_id and offer.uid == product_uid), None)

    def post_offer(self, product, price, existing_offer):
        new_offer = Offer.from_product(product)
        new_offer.price = price
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        if existing_offer is None:
            self.marketplace_api.add_offer(new_offer)
        else:
            self.marketplace_api.restock(existing_offer.offer_id, product.amount, product.signature)

    def update_offer(self, own_offer, target_price):
        own_offer.price = target_price
        self.marketplace_api.update_offer(own_offer)

    def get_amount_of_own_offers(self, all_offers):
        own_offers = [offer for offer in all_offers if offer.merchant_id == self.merchant_id]
        return sum(offer.amount for offer in own_offers)

    def adjust_prices(self, all_offers):
        print('Update offer')
        try:
            my_offered_product_uids = [offer.uid for offer in all_offers if offer.merchant_id == self.merchant_id]
            all_offers_i_offer_as_well = [offer for offer in all_offers if offer.uid in my_offered_product_uids]

            offers_per_traded_product = {}
            for offer in all_offers_i_offer_as_well:
                offers_per_traded_product[offer.uid] = offers_per_traded_product.get(offer.uid, 0) + 1

            for product_uid in [uid[0] for uid in sorted(offers_per_traded_product.items(), key=operator.itemgetter(1), reverse=True)]:
                existing_offers_for_product_id = self.get_existing_uid_offers_from_marketplace(all_offers_i_offer_as_well, product_uid)
                purchase_price = self.purchase_prices[product_uid]
                target_price = self.get_second_cheapest_price(existing_offers_for_product_id, purchase_price)
                existing_offer = self.get_own_offer_for_product_uid(existing_offers_for_product_id, product_uid)
                self.update_offer(existing_offer, target_price)
        except Exception as e:
            print('error on adjusting prices:', e)

    def refill_offers(self, all_offers=None):
        if not all_offers:
            all_offers = self.marketplace_api.get_offers()

        existing_offers = self.get_amount_of_own_offers(all_offers)
        try:
            for i in range(settings['listedOffers'] - existing_offers):
                self.buy_product_and_post_to_marketplace(all_offers)
        except Exception as e:
            print('error on refilling offers:', e)

    def setup(self):
        all_offers = self.marketplace_api.get_offers()
        self.refill_offers(all_offers)

    def execute_logic(self):
        all_offers = self.marketplace_api.get_offers()
        self.adjust_prices(all_offers)
        self.refill_offers(all_offers)
        return self.interval

    def sold_offer(self, offer_json):
        all_offers = self.marketplace_api.get_offers()
        self.refill_offers(all_offers)


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
