### Doc:
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

import requests
from flask import Flask, request, Response
from flask_cors import CORS

settings = {
    'merchant_id': 0,
    'ownEndpoint': 'http://127.0.0.1:5000',
    'marketplaceEndpoint': 'http://192.168.2.1:8080',
    'producerEndpoint': 'http://192.168.2.7:3000',
    'minProfit': 1,
    'priceIncrease': 5,
    'priceDecrease': 1
}


def getFromListByKey(dictList, key, value):
    return [elem for elem in dictList if elem[key] == value][0]


class MerchantLogic(object):
    def __init__(self):
        global settings
        print('MerchantLogic created')
        self.merchantID = self.registerToMarketplace()
        settings.update({'merchant_id': self.merchantID})
        self.state = 'init'
        self.execQueue = []
        self.initialProducts = 5

        self.runLogicLoop()

    def runLogicLoop(self):
        self.interval = 3
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True  # Daemonize thread
        self.thread.start()  # Start the execution

    def run(self):
        """ Method that runs forever """
        while not self.state == 'exiting':
            print('loop running, merchant in state:', self.state)
            # default interval to avoid busy waiting, but merchant logic should still
            # be in charge of setting the interval (that is random, currently, but could change)
            self.interval = 5

            if self.state == 'running':
                self.interval = random.randint(2, 10) / 10.0
                self.execute_logic()

            time.sleep(self.interval)

        self.onExit()

    def gameInit(self):
        self.products = self.getInitialProducts()
        print('products', self.products)
        self.offers = []

        for product in self.products:
            newOffer = self.createOffer(product)
            newOffer['id'] = self.addOfferToMarketplace(newOffer)
            self.offers.append(newOffer)

        print('offers', self.offers)

    def start(self):
        if self.state == 'init':
            self.gameInit()
        self.state = 'running'

    def stop(self):
        self.state = 'stopping'

    def terminate(self):
        self.state = 'exiting'

    def onExit(self):
        self.unRegisterToMarketplace()

    def createOffer(self, product):
        return {
            "product_id": product['product_id'],
            "merchant_id": self.merchantID,
            "uid": product['uid'],
            "quality": product['quality'],
            "amount": product['amount'],
            "price": product['price'] + 42,
            "shipping_time": {
                "standard": 5,
                "prime": 1
            },
            "prime": True
        }

    def addOfferToMarketplace(self, offer):
        r = requests.post(settings['marketplaceEndpoint'] + '/offers', json=offer)
        print('addOfferToMarketplace', r.text)
        return r.json()['offer_id']

    def registerToMarketplace(self):
        requestObject = {
            "api_endpoint_url": settings['ownEndpoint'],
            "merchant_name": "Sample Merchant",
            "algorithm_name": "IncreasePrice"
        }
        r = requests.post(settings['marketplaceEndpoint'] + '/merchants', json=requestObject)
        print('registerToMarketplace', r.json())
        return r.json()['merchant_id']

    def unRegisterToMarketplace(self):
        print('unRegisterToMarketplace')
        r = requests.delete(settings['marketplaceEndpoint'] + '/merchants/{:d}'.format(self.merchantID))

    def getInitialProducts(self):
        products = {}
        for i in range(self.initialProducts):
            r = requests.get(settings['producerEndpoint'] + '/buy?merchant_id={:d}'.format(self.merchantID))
            product = r.json()
            if product['product_id'] in products:
                products[product['product_id']]['amount'] += 1
            else:
                products[product['product_id']] = product
        return list(products.values())

    def update_offer(self, new_offer):
        print('update offer:', new_offer)
        try:
            r = requests.put(settings['marketplaceEndpoint'] + '/offers/{:d}'.format(new_offer['id']), json=new_offer)
        except Exception as e:
            print('failed to update offer', e)

    def adjust_prices(self, offer, min_price):
        if min_price < 16:
            offer['price'] = 32
        else:
            offer['price'] = min(max(min_price - 1, 16), 32)
        self.update_offer(offer)

    def get_offers(self):
        r = requests.get(settings['marketplaceEndpoint'] + '/offers')
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
            competitor_offers = [offer['price'] for offer in offers if
                                 offer['merchant_id'] != self.merchantID and offer['product_id'] == product[
                                     'product_id']]
            if len(competitor_offers) > 0:
                self.adjust_prices(getFromListByKey(self.offers, 'product_id', product['product_id']),
                                   min(competitor_offers))

    def sold_product(self, offer_id, amount, price):
        print('soldProduct')
        offer = [offer for offer in self.offers if offer['id'] == offer_id][0]
        print('found offer:', offer)
        offer['amount'] -= amount
        product = [product for product in self.products if product['product_id'] == offer['product_id']][0]
        print('found product:', product)
        product['amount'] -= amount
        if product['amount'] <= 0:
            print('product {:d} is out of stock!'.format(product['product_id']))

        # sample logic: TODO: improve
        self.buyProductAndUpdateOffer()

    def buyProductAndUpdateOffer(self):
        print('buy Product and update')
        newProduct = self.buyRandomProduct()
        if newProduct['product_id'] in self.products:
            product = getFromListByKey(self.products, 'product_id', newProduct['product_id'])
            product['amount'] += 1
            offer = getFromListByKey(self.offers, 'product_id', newProduct['product_id'])
            print('in this offer:', offer)
            offer['amount'] = product['amount']
            r = requests.patch(settings['marketplaceEndpoint'] + '/offers/{:d}/restock'.format(offer['id']),
                               json={'amount': 1})
        else:
            self.products.append(newProduct)
            newOffer = self.createOffer(newProduct)
            newOffer['id'] = self.addOfferToMarketplace(newOffer)
            self.offers.append(newOffer)

    # returns product
    def buyRandomProduct(self):
        r = requests.get(settings['producerEndpoint'] + '/buy?merchant_id={:d}'.format(self.merchantID))
        product = r.json()
        print('bought new product', product)
        return product


app = Flask(__name__)
CORS(app)
merchantLogic = None


def json_response(obj):
    js = json.dumps(obj)
    resp = Response(js, status=200, mimetype='application/json')
    return resp


@app.route('/settings', methods=['GET'])
def get_settings():
    return json_response(settings)


@app.route('/settings', methods=['PUT', 'POST'])
def put_settings():
    global settings
    new_settings = request.json
    settings.update(new_settings)
    return json_response(settings)


@app.route('/settings/execution', methods=['POST'])
def set_state():
    global settings
    global merchantLogic

    next_state = request.json['nextState']
    print(next_state)
    if next_state == 'init':
        settings.update({'ownEndpoint': request.json['merchant_url']}) if 'merchant_url' in request.json else None
        print('updated settings', settings)
        if not merchantLogic:
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

    return json_response({})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
