import argparse
import sys
import os
import numpy as np
import pandas as pd
from sklearn.externals import joblib

sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer

from machine_learning.market_learning import extract_features_from_offer_snapshot

merchant_token = "{{API_TOKEN}}"
#merchant_token = '2ZnJAUNCcv8l2ILULiCwANo7LGEsHCRJlFdvj18MvG8yYTTtCfqN3fTOuhGCthWf'

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'marketplace_url': os.getenv('PRICEWARS_MARKETPLACE_URL', 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace'),
    'producer_url': os.getenv('PRICEWARS_PRODUCER_URL', 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de'),
    'debug': True,
    'max_amount_of_offers': 15,
    'shipping': 5,
    'primeShipping': 1,
    'max_req_per_sec': 10
}


def make_relative_path(path):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_dir, path)


class MLMerchant(MerchantBaseLogic):
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
        self.producer_api = ProducerApi(host=self.settings['producer_url'])

        '''
            Setup ML model
        '''
        self.models_per_product = self.load_models_from_filesystem()

        '''
            Start Logic Loop
        '''
        self.run_logic_loop()

    @staticmethod
    def load_models_from_filesystem(folder='models'):
        result = {}
        for root, dirs, files in os.walk(make_relative_path(folder)):
            pkl_files = [f for f in files if f.endswith('.pkl')]
            for pkl_file in pkl_files:
                complete_path = os.path.join(root, pkl_file)
                product_id = int(pkl_file.split('.')[0])
                result[product_id] = joblib.load(complete_path)
        return result

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

    def update_settings(self, new_settings):
        MerchantBaseLogic.update_settings(self, new_settings)
        self.update_api_endpoints()
        return self.settings

    def sold_offer(self, offer):
        pass

    '''
        Merchant Logic
    '''

    def price_product(self, product, current_offers=None):
        """
        Computes a price for a product based on trained models or (exponential) random fallback
        :param product: product object that is to be priced
        :param current_offers: list of offers
        :return:
        """
        if not current_offers or product.product_id not in self.models_per_product:
            return product.price * (np.random.exponential() + 0.98)

        model = self.models_per_product[product.product_id]

        offer_df = pd.DataFrame([o.to_dict() for o in current_offers])
        offer_df = offer_df[offer_df['product_id'] == product.product_id]
        own_offers = offer_df['merchant_id'] == self.merchant_id

        features = []
        for potential_perc_margin in range(0, 1000, 25):
            potential_price = product.price * (1 + (potential_perc_margin / 100.0))
            offer_df.loc[own_offers, 'price'] = potential_price
            features.append(extract_features_from_offer_snapshot(offer_df, self.merchant_id, product_id=product.product_id))

        data = pd.DataFrame(features).dropna()
        data['sell_prob'] = model.predict_proba(data)
        data['expected_profit'] = data['sell_prob'] * data['own_price']
        # TODO: use bellmann equation: boost early profit
        return data['own_price'][data['expected_profit'].argmax()]

    def execute_logic(self):
        self.models_per_product = self.load_models_from_filesystem()

        offers = self.marketplace_api.get_offers(include_empty_offers=True)
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
                    offer.price = self.price_product(product, current_offers=offers)
                    self.marketplace_api.update_offer(offer)
                else:
                    offer = Offer.from_product(product)
                    offer.price = self.price_product(product, current_offers=offers)
                    offer.prime = True
                    offer.shipping_time['standard'] = self.settings['shipping']
                    offer.shipping_time['prime'] = self.settings['primeShipping']
                    self.marketplace_api.add_offer(offer)
            except Exception as e:
                print('could not handle product:', product, e)

        return 1.0 / settings['max_req_per_sec']


merchant_logic = MLMerchant()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
