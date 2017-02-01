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

merchant_token = "{{API_TOKEN}}"
# merchant_token = 'PlmNksxJyL9bei6288Utupsi1vecpdPGOCd96aS4wbfbLmdTu8NpxFYxBDa1q1HF'

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'listedOffers': 15,
    'shipping': 5,
    'primeShipping': 1,
    'max_req_per_sec': 10,
    'priceDifference': 0.5,
    'minimumMarginPercentile': 10
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

    def update_settings(self, new_settings):
        MerchantBaseLogic.update_settings(self, new_settings)
        self.update_api_endpoints()
        return self.settings

    def initialize_purchase_price_map(self):
        available_products = self.producer_api.get_products()
        for product in available_products:
            self.purchase_prices[product.uid] = product.price

    def buy_product_and_post_to_marketplace(self, all_offers):
        print('buy Product and update')
        new_product = self.buy_product()
        existing_offers = self.get_existing_offers_for_product_id_from_marketplace(all_offers, new_product.product_id)
        target_price = self.get_second_cheapest_price(existing_offers, new_product.price)
        existing_offer = self.get_own_offer_for_product_uid(existing_offers, new_product.uid)
        return self.post_offer(new_product, target_price, existing_offer)

    def buy_product(self):
        new_product = self.producer_api.buy_product(merchant_token=self.merchant_token)
        if new_product.uid not in self.purchase_prices:
            self.purchase_prices[new_product.uid] = new_product.price
        return new_product

    def get_existing_offers_for_product_id_from_marketplace(self, all_offers, product_id):
        product_id_offers = [offer for offer in all_offers if offer.product_id == product_id]
        return product_id_offers

    def get_second_cheapest_price(self, offers, purchase_price):
        maximum_price = 2 * purchase_price
        minimum_price = purchase_price * (1 + (self.settings['minimumMarginPercentile'] / 100.0))
        second_cheapest_offer = cheapest_offer = maximum_price
        for offer in offers:
            if offer.merchant_id == self.merchant_id:
                continue

            if offer.price < cheapest_offer:
                second_cheapest_offer = cheapest_offer
                cheapest_offer = offer.price
            elif cheapest_offer < offer.price < second_cheapest_offer:
                second_cheapest_offer = offer.price

        target_price = second_cheapest_offer - self.settings['priceDifference']
        if second_cheapest_offer < maximum_price and target_price >= cheapest_offer:
            second_cheapest_offer = target_price

        if second_cheapest_offer < minimum_price:
            second_cheapest_offer = minimum_price

        return second_cheapest_offer

    def get_own_offer_for_product_uid(self, offers, product_uid):
        return next((offer for offer in offers if offer.merchant_id == self.merchant_id and offer.uid == product_uid),
                    None)

    def post_offer(self, product, price, existing_offer):
        new_offer = Offer.from_product(product)
        new_offer.price = price
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        if existing_offer is None:
            return self.marketplace_api.add_offer(new_offer)
        else:
            self.marketplace_api.restock(existing_offer.offer_id, product.amount, product.signature)
            return None

    def update_offer(self, own_offer, target_price):
        own_offer.price = target_price
        self.marketplace_api.update_offer(own_offer)

    def get_own_offers(self, all_offers):
        return [offer for offer in all_offers if offer.merchant_id == self.merchant_id]

    def get_amount_of_own_offers(self, all_offers):
        return sum(offer.amount for offer in self.get_own_offers(all_offers))

    def adjust_prices(self, all_offers):
        print('Update offer')
        try:
            my_offered_product_ids = [offer.product_id for offer in all_offers if offer.merchant_id == self.merchant_id]
            all_offers_i_offer_as_well = [offer for offer in all_offers if offer.product_id in my_offered_product_ids]

            # Create a map with the product_id as key and the amount of offers as value (includes my own offers)
            offers_per_traded_product = {}
            for offer in all_offers_i_offer_as_well:
                offers_per_traded_product[offer.product_id] = offers_per_traded_product.get(offer.product_id, 0) + 1

            # Iterate over the traded product IDs in descending order of the amount of competitor offers
            for product_id in [offer_product_id[0] for offer_product_id in
                               sorted(offers_per_traded_product.items(), key=operator.itemgetter(1), reverse=True)]:
                existing_offers_for_product_id = self.get_existing_offers_for_product_id_from_marketplace(
                    all_offers_i_offer_as_well, product_id)

                # Iterate over my offers based on the quality, starting with the best quality (lowest quality number)
                for product_uid in [offer.uid for offer in sorted(self.get_own_offers(existing_offers_for_product_id),
                                                                  key=lambda offer_entry: offer_entry.quality)]:
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
                new_product = self.buy_product_and_post_to_marketplace(all_offers)
                if new_product:
                    all_offers.append(new_product)
                    # else: product already offered and restocked
        except Exception as e:
            print('error on refilling offers:', e)

    def setup(self):
        try:
            self.initialize_purchase_price_map()
            all_offers = self.marketplace_api.get_offers(include_empty_offers=True)
            self.refill_offers(all_offers)
        except Exception as e:
            print('error on setting up offers:', e)

    def execute_logic(self):
        try:
            all_offers = self.marketplace_api.get_offers(include_empty_offers=True)
            self.adjust_prices(all_offers)
            self.refill_offers(all_offers)
        except Exception as e:
            print('error on executing logic:', e)
        # ToDo: Return true value (calculate!)
        return self.interval

    def sold_offer(self, offer_json):
        if self.state != 'running':
            return
        try:
            all_offers = self.marketplace_api.get_offers(include_empty_offers=True)
            self.refill_offers(all_offers)
        except Exception as e:
            print('error on handling sold offers:', e)


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
