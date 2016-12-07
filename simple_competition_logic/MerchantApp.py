#   Doc:
#   run this file - it starts HTTP Server (Thread 1)
#   post {nextState: 'init'} to Server:
#       - it starts Logic in state 'init' (Thread 2) which registers to Market
#
#   UI posts:
#       - {nextState: 'start'} --> Logic registers to producer etc. adds offers, switches to 'running'
#       - {nextState: 'stop'} --> Logic stops, switches to 'stopping'
#       - {nextState: 'start'} --> Logic continues changing prices, getting products, switches to 'running'
#       - {nextState: 'kill'} --> Logic unregisters to Market and termintes (exit Thread 2), switches to 'exiting'
#
#   To restart, use external Tool to post
#       - {nextState: 'init'}

import argparse
import json
import random
import threading
import time
from posixpath import join as urljoin
import traceback

import requests
from flask import Flask, request, Response
from flask_cors import CORS

# TODO: use config.ini file for initial endpoints or remove their hardcoded strings if unused
settings = {
    'merchant_id': 0,
    'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'priceDecrease': 1,
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


class MerchantLogic(object):
    def __init__(self):
        global settings
        self.execQueue = []
        self.state = 'init'
        self.interval = 5
        self.thread = None
        self.products = []
        self.offers = []
        self.request_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=300, pool_maxsize=300)
        self.request_session.mount('http://', adapter) # TODO: what is with https?

        self.merchantID = self.register_to_marketplace()
        settings.update({'merchant_id': self.merchantID})
        self.run_logic_loop()

    def run_logic_loop(self):
        self.interval = 3
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True  # Demonize thread
        self.thread.start()  # Start the execution

    def run(self):
        """ Method that runs forever """
        while not self.state == 'exiting':
            # default interval to avoid busy waiting, but merchant logic should still
            # be in charge of setting the interval (that is random, currently, but could change)
            self.interval = 5

            if self.state == 'running':
                self.interval = random.randint(2, 10) / 10.0
                try:
                    self.execute_logic()
                except Exception as e:
                    print('error on merchantLogic:\n', e)
                    traceback.print_exc()
                    print('safely stop Merchant')
                    self.stop()

            time.sleep(self.interval)

        self.on_exit()

    def game_init(self):        
        url = urljoin(settings['producerEndpoint'], 'buy?merchant_id={:d}'.format(self.merchantID))
        products = {}
        offers = {}
        
        for i in range(settings['initialProducts']):
            r = self.request_session.get(url)
            product = r.json()
            
            old_product = get_from_list_by_key(self.products, 'uid', product['uid'])
            if old_product:
                old_product['amount'] += 1
                old_product['signature'] = new_product['signature']
                offer = get_from_list_by_key(self.offers, 'uid', product['uid'])
                url2 = urljoin(settings['marketplace_url'], 'offers/{:d}/restock'.format(offer['id']))
                offer['amount'] = old_product['amount']
                offer['signature'] = old_product['signature']
                self.request_session.patch(url2, json={'amount': 1})
            else:
                newOffer = self.create_offer(product)
                products[product['uid']] = product
                newOffer['id'] = self.add_offer_to_marketplace(newOffer)
                self.offers.append(newOffer)
                
        self.products = list(products.values())

    def start(self):
        if self.state == 'init':
            self.game_init()
        self.state = 'running'

    def stop(self):
        self.state = 'stopping'

    def terminate(self):
        if self.state == 'init':
            self.on_exit()
        else:
            self.state = 'exiting'

    def on_exit(self):
        self.unregister_to_marketplace()

    def create_offer(self, product):
        return {
            "product_id": product['product_id'],
            "merchant_id": self.merchantID,
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
        url = urljoin(settings['marketplace_url'], 'merchants/{:d}'.format(self.merchantID))
        print('unRegisterToMarketplace')

        self.request_session.delete(url)

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
                if offer['merchant_id'] != self.merchantID and offer['product_id'] == product['product_id']:
                    competitor_offers.append(offer['price'])
            if len(competitor_offers) > 0:
                offer = get_from_list_by_key(self.offers, 'product_id', product['product_id'])
                self.adjust_prices(offer=offer, product=product, lowest_competitor_price=min(competitor_offers))

    def sold_product(self, offer_id, amount, price):
        print('soldProduct')
        offer = [offer for offer in self.offers if offer['id'] == offer_id]
        if offer:
            offer = offer[0]
            print('found offer:', offer)
            offer['amount'] -= amount
            product = [product for product in self.products if product['uid'] == offer['uid']][0]
            print('found product:', product)

            product['amount'] -= amount
            if product['amount'] <= 0:
                print('product {:d} is out of stock!'.format(product['product_id']))

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
            self.request_session.patch(url, json={'amount': 1})
        else:
            self.products.append(new_product)
            new_offer = self.create_offer(new_product)
            new_offer['id'] = self.add_offer_to_marketplace(new_offer)
            self.offers.append(new_offer)

    # returns product
    def buy_random_product(self):
        url = urljoin(settings['producerEndpoint'], 'buy?merchant_id={:d}'.format(self.merchantID))
        r = self.request_session.get(url)
        product = r.json()
        print('bought new product', product)
        return product


app = Flask(__name__)
CORS(app)
merchantLogic = None


def json_response(obj, status=200):
    js = json.dumps(obj)
    resp = Response(js, status=status, mimetype='application/json')
    return resp


@app.route('/settings', methods=['GET'])
def get_settings():
    global settings
    state = 'No merchant initialized, i.e. not registered! You should not be able to see this message. Most certainly an error on the marketplace!'
    if merchantLogic:
        state = merchantLogic.state
    settings.update({'state': state})
    return json_response(settings)


@app.route('/settings', methods=['PUT', 'POST'])
def put_settings():
    global settings
    new_settings = request.json
    new_settings = dict([(key, type(settings[key])(new_settings[key])) for key in new_settings])
    settings.update(new_settings)
    return json_response(settings)


@app.route('/settings/execution', methods=['POST'])
def set_state():
    global settings
    global merchantLogic

    next_state = request.json['nextState']
    print(next_state)
    if next_state == 'init':
        # set endpoint url settings on init
        for keyword in ['merchant_url', 'marketplace_url']:
            if keyword in request.json:
                settings.update({keyword: request.json[keyword]})
        print('updated settings', settings)
        if merchantLogic:
            merchantLogic.terminate()
        print('new merchant')
        merchantLogic = MerchantLogic()
    elif next_state == 'start':
        print('merchant start')
        merchantLogic.start()
    elif next_state == 'stop':
        print('merchant stop')
        merchantLogic.stop()
    elif next_state == 'kill':
        print('merchant kill')
        merchantLogic.terminate()
        merchantLogic = None

    return json_response({})


@app.route('/sold', methods=['POST'])
def item_sold():
    global merchantLogic

    if merchantLogic:
        sent_json = request.get_json(force=True)
        # ignore 'consumer_id' and 'prime'
        # offer_id = int(sentJSON['offer_id'])
        # amount = int(sentJSON['amount'])
        # price = float(sentJSON['price'])

        offer_id = sent_json['offer_id']
        amount = sent_json['amount']
        price = sent_json['price']

        # consumer_id = sentJSON['consumer_id'] if 'consumer_id' in sentJSON else ''
        # prime = sentJSON['prime'] if 'prime' in sentJSON else ''

        print('sold {:d} items of the offer {:d} for {:f}'.format(amount, offer_id, price))
        merchantLogic.execQueue.append((merchantLogic.sold_product, (offer_id, amount, price)))
    else:
        print('merchantlogic not started')
        return json_response({}, status=428)

    return json_response({})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
