import argparse
import sys

sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer

merchant_token = "{{API_TOKEN}}"
#merchant_token = 'llhGt9Tao3YbN1ANPkI1QkDg3LC88EHt0xAu7dVvh4X45hSTSkVsVhZY3lgBzx60'

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'debug': True,
    'fixed_margin_perc': 20,
    'max_amount_of_offers': 50,
    'shipping': 5,
    'primeShipping': 1,
    'max_req_per_sec': 10
}


class MerchantSampleLogic(MerchantBaseLogic):
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

    def update_settings(self, new_settings):
        MerchantBaseLogic.update_settings(self, new_settings)
        self.update_api_endpoints()
        return self.settings

    def sold_offer(self, offer):
        print('sold offer:', offer)

    '''
        Merchant Logic
    '''

    def price_product(self, product):
        return (1.0 + self.settings['fixed_margin_perc'] / 100.0) * product.price

    def execute_logic(self):
        offers = self.marketplace_api.get_offers()
        own_offers = [offer for offer in offers if offer.merchant_id == self.merchant_id]
        own_offers_by_uid = {offer.uid: offer for offer in own_offers}
        missing_offers = settings['max_amount_of_offers'] - sum(offer.amount for offer in own_offers)

        new_products = []
        for _ in range(missing_offers):
            try:
                prod = self.producer_api.buy_product(merchant_token=self.merchant_token)
                new_products.append(prod)
            except:
                pass

        for product in new_products:
            try:
                if product.uid in own_offers_by_uid:
                    offer = own_offers_by_uid[product.uid]
                    offer.amount += product.amount
                    offer.signature = product.signature
                    self.marketplace_api.restock(offer.offer_id, amount=product.amount, signature=product.signature)

                    offer.price = self.price_product(product)
                    self.marketplace_api.update_offer(offer)
                else:
                    offer = Offer.from_product(product)
                    offer.price = self.price_product(product)
                    offer.prime = True
                    offer.shipping_time['standard'] = self.settings['shipping']
                    offer.shipping_time['prime'] = self.settings['primeShipping']
                    self.marketplace_api.add_offer(offer)
            except Exception as e:
                print('could not handle product:', product, e)

        return 1.0 / settings['max_req_per_sec']


merchant_logic = MerchantSampleLogic()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
