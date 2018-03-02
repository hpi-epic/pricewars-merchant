from abc import ABCMeta, abstractmethod
import time
import threading
import hashlib
import base64

from server import MerchantServer
from models import SoldOffer


class PricewarsMerchant:
    __metaclass__ = ABCMeta

    def __init__(self, port: int):
        self.settings = {'update interval': 5}
        self.state = 'running'
        self.server_thread = self.start_server(port)

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

    def update_settings(self, new_settings: dict) -> None:
        for key, value in new_settings.items():
            if key in self.settings:
                # Cast value type to the type that is already in the settings dictionary
                value = type(self.settings[key])(value)
            self.settings[key] = value

    @abstractmethod
    def update_offers(self) -> None:
        """
        Entry point for regular merchant activity.
        When the merchant is running, this is called in each update interval.
        """
        pass

    def start(self):
        self.state = 'running'

    def stop(self):
        self.state = 'stopping'

    @abstractmethod
    def sold_offer(self, offer: SoldOffer) -> None:
        """
        This method is called whenever the merchant sells a product.
        """
        pass

    def start_server(self, port):
        server = MerchantServer(self)
        thread = threading.Thread(target=server.app.run, kwargs={'host': '0.0.0.0', 'port': port})
        thread.daemon = True
        thread.start()
        return thread
