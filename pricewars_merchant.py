import json
from abc import ABCMeta, abstractmethod
import time
import threading
import hashlib
import base64
from typing import Optional, List

from api import Marketplace, Producer
from server import MerchantServer
from models import SoldOffer, Offer


class PricewarsMerchant(metaclass=ABCMeta):
    TOKEN_FILE = 'auth_tokens.json'

    def __init__(self, port: int, token: Optional[str], marketplace_url: str, producer_url: str, merchant_name: str):
        self.settings = {
            'update interval': 5,
            'restock limit': 20,
            'order threshold': 0,
            'shipping': 5,
            'primeShipping': 1,
        }
        self.state = 'running'
        self.server_thread = self.start_server(port)

        if not token:
            token = self.load_tokens().get(merchant_name)

        self.marketplace = Marketplace(token, host=marketplace_url)
        self.marketplace.wait_for_host()

        if token:
            merchant_id = self.calculate_id(token)
            if not self.marketplace.merchant_exists(merchant_id):
                print('Existing token appears to be outdated.')
                token = None
            else:
                print('Running with existing token "%s".' % token)
                self.token = token
                self.merchant_id = merchant_id

        if token is None:
            register_response = self.marketplace.register(port, merchant_name)
            self.token = register_response.merchant_token
            self.merchant_id = register_response.merchant_id
            self.save_token(merchant_name)
            print('Registered new merchant with token "%s".' % self.token)

        # request current request limitations from market place.
        req_limit = self.marketplace.get_request_limit()

        # Update rate has to account of (i) getting market situations,
        # (ii) posting updates, (iii) getting products, (iv) posting
        # new products. As restocking should not occur too often,
        # we use a rather conservative factor of 2.5x factor.
        self.settings['update interval'] = (1 / req_limit) * 2.5

        self.producer = Producer(self.token, host=producer_url)

    def load_tokens(self) -> dict:
        try:
            with open(self.TOKEN_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_token(self, name: str) -> None:
        tokens = self.load_tokens()
        with open(self.TOKEN_FILE, 'w') as f:
            tokens[name] = self.token
            json.dump(tokens, f)

    @staticmethod
    def calculate_id(token: str) -> str:
        return base64.b64encode(hashlib.sha256(token.encode('utf-8')).digest()).decode('utf-8')

    def run(self):
        start_time = time.time()
        while True:
            if self.state == 'running':
                self.update_offers()
            # Waiting for the length of the update interval minus the execution time
            time.sleep(self.settings['update interval'] -
                       ((time.time() - start_time) % self.settings['update interval']))

    def update_offers(self) -> None:
        """
        Entry point for regular merchant activity.
        When the merchant is running, this is called in each update interval.
        """
        market_situation = self.marketplace.get_offers()
        own_offers = [offer for offer in market_situation if offer.merchant_id == self.merchant_id]

        inventory_level = sum(offer.amount for offer in own_offers)
        if inventory_level <= self.settings['order threshold']:
            self.restock(inventory_level, market_situation)

        for offer in own_offers:
            offer.price = self.calculate_price(offer.offer_id, market_situation)
            self.marketplace.update_offer(offer)

    def restock(self, inventory_level, market_situation):
        order = self.producer.order(self.settings['restock limit'] - inventory_level)
        product = order.product
        shipping_time = {
            'standard': self.settings['shipping'],
            'prime': self.settings['primeShipping']
        }
        offer = Offer.from_product(product, 0, shipping_time)
        offer.merchant_id = self.merchant_id
        offer.price = self.calculate_price(offer.offer_id, market_situation + [offer])
        self.marketplace.add_offer(offer)

    def sold_offer(self, offer: SoldOffer) -> None:
        """
        This method is called whenever the merchant sells a product.
        """
        print('Product sold')

    def start(self):
        self.state = 'running'

    def stop(self):
        self.state = 'stopping'

    def update_settings(self, new_settings: dict) -> None:
        for key, value in new_settings.items():
            if key in self.settings:
                # Cast value type to the type that is already in the settings dictionary
                value = type(self.settings[key])(value)
            self.settings[key] = value

    def start_server(self, port):
        server = MerchantServer(self)
        thread = threading.Thread(target=server.app.run, kwargs={'host': '0.0.0.0', 'port': port})
        thread.daemon = True
        thread.start()
        return thread

    @abstractmethod
    def calculate_price(self, offer_id: int, market_situation: List[Offer]) -> float:
        """
        Calculate the price for the offer indicated by 'offer_id' given the current market situation.
        The offer id is guaranteed to be in the market situation.
        """
        pass
