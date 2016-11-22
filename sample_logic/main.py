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

import threading
import time
import random
import json
import requests

from flask import Flask, request, Response
from flask_cors import CORS, cross_origin

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
        self.runLogicLoop()

    def runLogicLoop(self):
        self.interval = 3
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True                            # Daemonize thread
        self.thread.start()                                  # Start the execution

    def run(self):
        """ Method that runs forever """
        while not self.state == 'exiting':
            print('loop running, merchant in state:', self.state)
            # default interval to avoid busy waiting, but merchant logic should still
            # be in charge of setting the interval (that is random, currently, but could change)
            self.interval = 5

            if self.state == 'running':
                self.interval = random.randint(2, 10)
                self.executeLogic()
            
            time.sleep(self.interval)

        self.onExit()

    def gameInit(self):
        self.products = self.registerToProducerAndGetProducts()
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

    def registerToProducerAndGetProducts(self):
        print('registerToProducer')
        requestObject = {
            "merchant_id": self.merchantID
        }
        r = requests.post(settings['producerEndpoint'] + '/buyers/register', json=requestObject)
        products = r.json()
        for product in products:
            product['amount'] = 1
        return products

    def adjustPrices(self):
        offer = random.choice(self.offers)
        offer['price'] = max(offer['price'] - 1, 17)
        self.updateOffer(offer)

    def updateOffer(self, newOffer):
        print('update offer:', newOffer)
        try:
            r = requests.put(settings['marketplaceEndpoint'] + '/offers/{:d}'.format(newOffer['id']), json=newOffer)
        except Exception as e:
            print('failed to update offer', e)

    def getOffers(self):
        r = requests.get(settings['marketplaceEndpoint'] + '/offers')

    def executeLogic(self):
        self.getOffers()
        self.adjustPrices()
        #self.buyProductAndUpdateOffer()

    def soldProduct(self, offer_id, amount, price):
        print('soldProduct')
        offer = [offer for offer in self.offers if offer['id'] == offer_id][0]
        print('found offer:', offer)
        offer['amount'] -= 1
        product = [product for product in self.products if product['product_id'] == offer['product_id']][0]
        print('found product:', product)
        product['amount'] -= 1
        if (product['amount'] <= 0):
            print('product {:d} is out of stock!'.format(product['product_id']))

        # sample logic: TODO: improve
        self.buyProductAndUpdateOffer()

    def buyProductAndUpdateOffer(self):
        print('buy Product and update')
        newProduct = self.buyRandomProduct()
        print('bought:', newProduct)
        offer = getFromListByKey(self.offers, 'product_id', newProduct['product_id'])
        print('in this offer:', offer)
        offer['amount'] = newProduct['amount']
        offer['price'] += 5
        print('new offer:', offer)
        self.updateOffer(offer)

    # returns product
    def buyRandomProduct(self):
        r = requests.get(settings['producerEndpoint'] + '/products/buy?merchant_id={:d}'.format(self.merchantID))
        productObject = r.json()
        print('bought new product', productObject)
        product = getFromListByKey(self.products, 'product_id', productObject['product_id'])
        product['amount'] += 1
        return product


app = Flask(__name__)
CORS(app)
merchantLogic = None

def jsonResponse(obj):
    js = json.dumps(obj)
    resp = Response(js, status=200, mimetype='application/json')
    return resp

@app.route('/settings', methods=['GET'])
def get_settings():
    return jsonResponse(settings)

@app.route('/settings', methods=['PUT', 'POST'])
def put_settings():
    global settings
    newSettings = request.json
    settings.update(newSettings)
    return jsonResponse(settings)

@app.route('/settings/execution', methods=['POST'])
def set_state():
    global settings
    global merchantLogic

    nextState = request.json['nextState']
    print(nextState)
    if nextState == 'init':
        settings.update({ 'ownEndpoint': request.json['merchant_url'] }) if 'merchant_url' in request.json else None
        print('updated settings', settings)
        if not merchantLogic:
            print('new merchant')
            merchantLogic = MerchantLogic()
    elif nextState == 'start':
        print('merchant start')
        merchantLogic.start()
    elif nextState == 'stop':
        print('merchant stop')
        merchantLogic.stop()
    elif nextState == 'kill':
        print('merchant kill')
        merchantLogic.terminate()
        merchantLogic = None

    return jsonResponse({})

@app.route('/sold', methods=['POST'])
def item_sold():
    global merchantLogic
    
    if merchantLogic:
        print(request.json)
        # ignore 'consumer_id' and 'prime'
        offer_id = request.json['offer_id']
        amount = request.json['amount']
        price = request.json['price']

        consumer_id = request.json['consumer_id'] if 'consumer_id' in request.json else ''
        prime = request.json['prime'] if 'prime' in request.json else ''
        
        print('sold {:d} items of the offer {:d} to {:s} for {:d}'.format(amount, offer_id, consumer_id, price))
        merchantLogic.sold_product(offer_id, amount, price)
    else:
        print('merchantlogic not started')

    return jsonResponse({})

if __name__ == "__main__":
    app.run(host='0.0.0.0')
