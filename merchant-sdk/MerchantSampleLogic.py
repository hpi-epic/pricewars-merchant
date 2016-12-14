import argparse
from posixpath import join as urljoin
import requests
import requests.adapters

from MerchantBaseLogic import MerchantBaseLogic
from MerchantServer import MerchantServer

settings = {
    'merchant_id': 0,
    'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'priceDecrease': 1,
    'interval': 1,
    'initialProducts': 25,
    'minPriceMargin': 16,
    'maxPriceMargin': 32,
    'shipping': 5,
    'primeShipping': 1,
    'debug': False
}


def get_from_list_by_key(dict_list, key, value):
    elements = [elem for elem in dict_list if elem[key] == value]
    if elements:
        return elements[0]
    return None


class MerchantSampleLogic(MerchantBaseLogic):
    def __init__(self):
        global settings
        self.settings = settings

        '''
            Internal state handling
        '''
        self.execQueue = []

        '''
            Information store
        '''
        self.products = []
        self.offers = []
        self.merchant_id = None

        '''
            Setup connection pools

            otherwise, requests is going to open a new connection for each request,
            leaving resources on the destination allocated.
        '''
        self.request_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=300, pool_maxsize=300)
        self.request_session.mount('http://', adapter)

    '''
        Implement Abstract methods / Interface
    '''

    def get_settings(self):
        return self.settings

    def update_settings(self, new_settings):
        self.settings.update(new_settings)
        return self.settings

    def init(self):
        MerchantBaseLogic.init(self)

        self.merchant_id = self.register_to_marketplace()
        self.settings.update({'merchant_id': self.merchant_id})
        self.run_logic_loop()

    def terminate(self):
        MerchantBaseLogic.terminate(self)

        self.unregister_to_marketplace()
        self.products = []
        self.offers = []
        self.merchant_id = None

    def sold_offer(self, offer_json):
        offer_id = offer_json['offer_id']
        amount = offer_json['amount']
        price = offer_json['price']
        self.execQueue.append((self.sold_product, (offer_id, amount, price)))

    '''
        Merchant Logic
    '''

    def setup(self):
        url = urljoin(settings['producerEndpoint'], 'buy?merchant_id={:d}'.format(self.merchant_id))
        products = {}

        for i in range(settings['initialProducts']):
            r = self.request_session.get(url)
            product = r.json()

            old_product = get_from_list_by_key(self.products, 'uid', product['uid'])
            if old_product:
                old_product['amount'] += 1
                old_product['signature'] = product['signature']
                offer = get_from_list_by_key(self.offers, 'uid', product['uid'])
                url2 = urljoin(settings['marketplace_url'], 'offers/{:d}/restock'.format(offer['id']))
                offer['amount'] = old_product['amount']
                offer['signature'] = old_product['signature']
                self.request_session.patch(url2, json={'amount': 1, 'signature': old_product['signature']})
            else:
                new_offer = self.create_offer(product)
                products[product['uid']] = product
                new_offer['id'] = self.add_offer_to_marketplace(new_offer)
                self.offers.append(new_offer)

        self.products = list(products.values())

    def execute_logic(self):
        # execute queued methods
        tmp_queue = [e for e in self.execQueue]
        self.execQueue = []
        for method, kwargs in tmp_queue:
            method(*kwargs)

        offers = self.get_offers()
        for product in self.products:
            competitor_offers = []
            for offer in offers:
                if offer['merchant_id'] != self.merchant_id and offer['uid'] == product['uid']:
                    competitor_offers.append(offer['price'])
            if len(competitor_offers) > 0:
                offer = get_from_list_by_key(self.offers, 'uid', product['uid'])
                self.adjust_prices(offer=offer, product=product, lowest_competitor_price=min(competitor_offers))

        return self.settings['interval']

    def register_to_marketplace(self):
        request_object = {
            "api_endpoint_url": settings['merchant_url'],
            "merchant_name": "Sample Merchant",
            "algorithm_name": "IncreasePrice"
        }
        url = urljoin(settings['marketplace_url'], 'merchants')

        r = self.request_session.post(url, json=request_object)
        print('registerToMarketplace', r.json())
        return r.json()['merchant_id']

    def unregister_to_marketplace(self):
        url = urljoin(settings['marketplace_url'], 'merchants/{:d}'.format(self.merchant_id))
        print('unRegisterToMarketplace')

        self.request_session.delete(url)

    def create_offer(self, product):
        return {
            "product_id": product['product_id'],
            "merchant_id": self.merchant_id,
            "signature": product['signature'],
            "uid": product['uid'],
            "quality": product['quality'],
            "amount": product['amount'],
            "price": product['price'] + settings['maxPriceMargin'],
            "shipping_time": {
                "standard": settings['shipping'],
                "prime": settings['primeShipping']
            },
            "prime": True
        }

    def add_offer_to_marketplace(self, offer):
        url = urljoin(settings['marketplace_url'], 'offers')

        r = self.request_session.post(url, json=offer)
        return r.json()['offer_id']

    def update_offer(self, new_offer):
        print('update offer:', new_offer)
        url = urljoin(settings['marketplace_url'], 'offers/{:d}'.format(new_offer['id']))

        try:
            self.request_session.put(url, json=new_offer)
        except Exception as e:
            print('failed to update offer', e)

    def adjust_prices(self, offer=None, product=None, lowest_competitor_price=0):
        if not offer or not product:
            return

        min_price = product['price'] + settings['minPriceMargin']
        max_price = product['price'] + settings['maxPriceMargin']

        price = lowest_competitor_price - settings['priceDecrease']
        price = min(price, max_price)
        if price < min_price:
            price = max_price

        offer['price'] = price
        self.update_offer(offer)

    def get_offers(self, ):
        url = urljoin(settings['marketplace_url'], 'offers')

        r = self.request_session.get(url)
        offers = r.json()
        return offers

    def sold_product(self, offer_id, amount, price):
        print('soldProduct', price)
        offer = [offer for offer in self.offers if offer['id'] == offer_id]
        if offer:
            offer = offer[0]
            offer['amount'] -= amount
            product = [product for product in self.products if product['uid'] == offer['uid']][0]

            product['amount'] -= amount
            if product['amount'] <= 0:
                print('product {:d} is out of stock!'.format(product['uid']))

            # sample logic: TODO: improve
            self.buy_product_and_update_offer()

    def buy_product_and_update_offer(self):
        print('buy Product and update')
        new_product = self.buy_random_product()

        old_product = get_from_list_by_key(self.products, 'uid', new_product['uid'])
        if old_product:
            old_product['amount'] += 1
            old_product['signature'] = new_product['signature']
            offer = get_from_list_by_key(self.offers, 'uid', new_product['uid'])
            print('in this offer:', offer)
            url = urljoin(settings['marketplace_url'], 'offers/{:d}/restock'.format(offer['id']))
            offer['amount'] = old_product['amount']
            offer['signature'] = old_product['signature']
            self.request_session.patch(url, json={'amount': 1, 'signature': offer['signature']})
        else:
            self.products.append(new_product)
            new_offer = self.create_offer(new_product)
            new_offer['id'] = self.add_offer_to_marketplace(new_offer)
            self.offers.append(new_offer)

    # returns product
    def buy_random_product(self):
        url = urljoin(settings['producerEndpoint'], 'buy?merchant_id={:d}'.format(self.merchant_id))
        r = self.request_session.get(url)
        product = r.json()
        print('bought new product', product)
        return product


merchant_logic = MerchantSampleLogic()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
