import threading
import time
import random
import json
import requests

from flask import Flask, request


marketplaceEndpoint = 'http://127.0.0.1:8000'


class MerchantLogic(object):
    def __init__(self):
        self.merchantID = self.register()
        self.products = self.getProducts()
        self.offers = []
        
        for product in self.products:
            newOffer = self.createOffer(product)
            newOffer['id'] = self.addOfferToMarketplace(newOffer)
            self.offers.append(newOffer)

        # Thread handling
        self.interval = 3
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        """ Method that runs forever """
        while True:
            print('Loop tick')
            self.interval = random.randint(2, 10)
            self.executeLogic()
            time.sleep(self.interval)

    def getProducts(self):
        # TODO: add producer API call
        return [
            {
                "product_id": "CD-1",
                "name": "Jan and Marv EP 1",
                "condition": 0
            },
            {
                "product_id": "CD-2",
                "name": "Jan and Marv EP 2",
                "condition": 0
            },
        ]

    def createOffer(self, product):
        return {
            "product_id": product['product_id'],
            "seller_id": "Jan und Marv",
            "amount": 1337,
            "price": 42,
            "shipping_time": 1,
            "prime": True
        }

    def addOfferToMarketplace(self, offer):
        r = requests.post(marketplaceEndpoint + '/offers', json=offer)
        print("new offer, ID:", r.text)
        return int(r.text)

    def register(self):
        return 0

    def adjustPrices(self):
        offer = self.offers[0]
        offer['price'] += 1
        print('update offer price:', offer['price'])
        try:
            r = requests.put(marketplaceEndpoint + '/offers', json=offer)
        except:
            print('failed to update offer')

    def getOffers(self):
        r = requests.get(marketplaceEndpoint + '/offers')
        print(r.json())

    def executeLogic(self):
        self.getOffers()
        self.adjustPrices()


app = Flask(__name__)

@app.route('/sold', methods=['POST'])
def item_sold():
    offer_id = request.json['offer_id']
    amount = request.json['amount']
    return "ok"

if __name__ == "__main__":
    merchantLogic = MerchantLogic()
    app.run()
