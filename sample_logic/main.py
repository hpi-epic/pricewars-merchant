import threading
import time
import random
import json
import requests

from flask import Flask, request, Response

ownHost = "127.0.0.1"
ownHost = 'merchant'
ownEndpoint = 'http://{:s}:5000'.format(ownHost)

marketplaceEndpoint = 'http://marketplace:8080'
producerEndpoint = 'http://producer:3000'

def getFromListByKey(dictList, key, value):
    return [elem for elem in dictList if elem[key] == value][0]

class MerchantLogic(object):
    def __init__(self):
        self.merchantID = self.registerToMarketplace()
        self.registerToProducer()
        self.products = self.getProducts()
        print('products', self.products)
        self.offers = []
        
        for product in self.products:
            newOffer = self.createOffer(product)
            newOffer['id'] = self.addOfferToMarketplace(newOffer)
            self.offers.append(newOffer)

        print('offers', self.offers)

        # Thread handling
        self.interval = 3
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        """ Method that runs forever """
        while True:
            self.interval = random.randint(2, 10)
            self.executeLogic()
            time.sleep(self.interval)

    def getProducts(self):
        r = requests.get(producerEndpoint + '/buyers')
        products = [merchant['products'] for merchant in r.json() if merchant['merchantID'] == self.merchantID][0]
        for product in products:
            product['amount'] = 1
        return products

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
        r = requests.post(marketplaceEndpoint + '/offers', json=offer)
        print('addOfferToMarketplace', r.text)
        return r.json()['offer_id']

    def registerToMarketplace(self):
        requestObject = {
            "api_endpoint_url": ownEndpoint,
            "merchant_name": "Sample Merchant",
            "algorithm_name": "IncreasePrice"
        }
        r = requests.post(marketplaceEndpoint + '/merchants', json=requestObject)
        print('registerToMarketplace', r.json())
        return r.json()['merchant_id']

    def registerToProducer(self):
        requestObject = {
            "merchantID": self.merchantID
        }
        r = requests.post(producerEndpoint + '/buyers', json=requestObject)
        print('registerToProducer')

    def adjustPrices(self):
        offer = random.choice(self.offers)
        offer['price'] = max(offer['price'] - 1, 17)
        self.updateOffer(offer)

    def updateOffer(self, newOffer):
        print('update offer:', newOffer)
        try:
            r = requests.put(marketplaceEndpoint + '/offers/{:d}'.format(newOffer['id']), json=newOffer)
        except Exception as e:
            print('failed to update offer', e)

    def getOffers(self):
        r = requests.get(marketplaceEndpoint + '/offers')

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
            print('product {:d} is out of stock!'.format(int(product['product_id'])))

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
        r = requests.get(producerEndpoint + '/products/buy?merchantID={:s}'.format(self.merchantID))
        productObject = r.json()
        print('bought new product', productObject)
        product = getFromListByKey(self.products, 'product_id', productObject['product_id'])
        product['amount'] += 1
        return product


app = Flask(__name__)

merchantLogic = None

@app.route('/sold', methods=['POST'])
def item_sold():
    global merchantLogic
    
    if merchantLogic:
        print(request.json)
        offer_id = request.json['offer_id']
        amount = request.json['amount']
        price = request.json['price']
        consumer_id = ''
        if 'consumer_id' in request.json:
            consumer_id = request.json['consumer_id']
        print('sold {:d} items of the offer {:d} to {:s} for {:d}'.format(amount, offer_id, consumer_id, price))
        merchantLogic.soldProduct(offer_id, amount, price)
    else:
        print('merchantlogic not started')

    js = json.dumps({})
    resp = Response(js, status=200, mimetype='application/json')
    return resp

if __name__ == "__main__":
    merchantLogic = MerchantLogic()
    app.run(host=ownHost)
