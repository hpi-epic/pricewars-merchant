from abc import ABCMeta, abstractmethod
import traceback
import time
import threading
import hashlib
import base64

from server import MerchantServer
from models import SoldOffer


class PricewarsMerchant:
    __metaclass__ = ABCMeta

    def __init__(self, port: int):
        self.settings = {}
        self.interval = 5
        self.thread = None
        self.state = 'running'
        self.server_thread = self.start_server(port)

    @staticmethod
    def calculate_id(token):
        return base64.b64encode(hashlib.sha256(token.encode('utf-8')).digest()).decode('utf-8')

    def run(self):
        while True:
            if self.state == 'running':
                try:
                    self.interval = self.execute_logic() or self.interval
                except Exception as e:
                    print('error on merchantLogic:\n', e)
                    traceback.print_exc()
                    print('safely stop Merchant')
                    self.stop()
            else:
                self.interval = 5

            time.sleep(max(0, self.interval))

    '''
        Settings and merchant controls for Web-Frontend
    '''

    def get_settings(self):
        return self.settings

    def update_settings(self, new_settings):
        def cast_to_expected_type(key, value, def_settings=self.settings):
            if key in def_settings:
                return type(def_settings[key])(value)
            else:
                return value

        new_settings_casted = dict([
            (key, cast_to_expected_type(key, new_settings[key]))
            for key in new_settings
        ])

        self.settings.update(new_settings_casted)
        return self.settings

    @abstractmethod
    def execute_logic(self):
        """
        Entry point for regular merchant activity
        The base logic class takes care of the possible states of the merchant,
        i.e. this method is not called when the merchant is stopping
        :return: time in seconds (float) to the next wanted execution
        """
        return self.interval

    def get_state(self):
        return self.state

    def start(self):
        if self.state == 'initialized':
            self.setup()
        self.state = 'running'

    def stop(self):
        if self.state == 'running':
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
