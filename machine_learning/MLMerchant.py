import argparse
import sys
import os
import numpy as np
import pandas as pd
import datetime
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
    'marketplace_url': MerchantBaseLogic.get_marketplace_url(),
    'producer_url': MerchantBaseLogic.get_producer_url(),
    'kafka_reverse_proxy_url': MerchantBaseLogic.get_kafka_reverse_proxy_url(),
    'debug': True,
    'max_amount_of_offers': 15,
    'shipping': 5,
    'primeShipping': 1,
    'max_req_per_sec': 10.0,
    'minutes_between_learnings': 30.0,
}


def make_relative_path(path):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_dir, path)


def trigger_learning(merchant_token, kafka_host):
    os.system('python3 market_learning.py -t "{:s}" -k "{:s}" &'.format(merchant_token, kafka_host))


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
        self.last_learning = datetime.datetime.now()
        trigger_learning(self.merchant_token, settings['kafka_reverse_proxy_url'])

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
            break
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

    def price_product(self, product_or_offer, current_offers=None):
        """
        Computes a price for a product based on trained models or (exponential) random fallback
        :param product_or_offer: product object that is to be priced
        :param current_offers: list of offers
        :return:
        """
        try:
            model = self.models_per_product[product_or_offer.product_id]

            offer_df = pd.DataFrame([o.to_dict() for o in current_offers])
            offer_df = offer_df[offer_df['product_id'] == product_or_offer.product_id]
            own_offers_mask = offer_df['merchant_id'] == self.merchant_id

            features = []
            for potential_price_candidate in range(0.5, 100, 0.5):
                potential_price = product_or_offer.price + potential_price_candidate
                offer_df.loc[own_offers_mask, 'price'] = potential_price
                features.append(extract_features_from_offer_snapshot(offer_df, self.merchant_id,
                                                                     product_id=product_or_offer.product_id))
            data = pd.DataFrame(features).dropna()
            # TODO: could be second row, currently
            data['sell_prob'] = model.predict_proba(data)[:,1]
            data['expected_profit'] = data['sell_prob'] * (data['own_price'] - product_or_offer.price)
            return data['own_price'][data['expected_profit'].argmax()]
        except (KeyError, ValueError) as e:
            if type(product_or_offer) == Offer:
                return product_or_offer.price
            else:
                print('exception', e, '--> random price')
                return product_or_offer.price * (np.random.exponential() + 0.99)
        except Exception as e:
            pass

    @property
    def execute_logic(self):
        next_training_session = self.last_learning \
                                + datetime.timedelta(minutes=self.settings['minutes_between_learnings'])
        if next_training_session >= datetime.datetime.now():
            self.last_learning = datetime.datetime.now()
            trigger_learning(self.merchant_token, self.settings['kafka_reverse_proxy_url'])

        self.models_per_product = self.load_models_from_filesystem()

        try:
            offers = self.marketplace_api.get_offers(include_empty_offers=True)
        except Exception as e:
            print('error on getting offers:', e)
        own_offers = [offer for offer in offers if offer.merchant_id == self.merchant_id]
        own_offers_by_uid = {offer.uid: offer for offer in own_offers}
        missing_offers = settings['max_amount_of_offers'] - sum(offer.amount for offer in own_offers)

        new_products = []
        for _ in range(missing_offers):
            try:
                prod = self.producer_api.buy_product()
                new_products.append(prod)
            except:
                pass

        for own_offer in own_offers:
            own_offer.price = self.price_product(own_offer, current_offers=offers)
            try:
                self.marketplace_api.update_offer(own_offer)
            except Exception as e:
                print('error on updating offer:', e)

        for product in new_products:
            try:
                if product.uid in own_offers_by_uid:
                    offer = own_offers_by_uid[product.uid]
                    offer.amount += product.amount
                    offer.signature = product.signature
                    try:
                        self.marketplace_api.restock(offer.offer_id, amount=product.amount, signature=product.signature)
                    except Exception as e:
                        print('error on restocking an offer:', e)
                    offer.price = self.price_product(product, current_offers=offers)
                    try:
                        self.marketplace_api.update_offer(offer)
                    except Exception as e:
                        print('error on updating an offer:', e)
                else:
                    offer = Offer.from_product(product)
                    offer.prime = True
                    offer.shipping_time['standard'] = self.settings['shipping']
                    offer.shipping_time['prime'] = self.settings['primeShipping']
                    offer.merchant_id = self.merchant_id
                    offer.price = self.price_product(product, current_offers=offers+[offer])
                    try:
                        self.marketplace_api.add_offer(offer)
                    except Exception as e:
                        print('error on adding an offer to the marketplace:', e)
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
