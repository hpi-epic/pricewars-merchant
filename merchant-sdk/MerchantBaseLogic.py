from abc import ABCMeta, abstractmethod

import traceback
import threading
import time

base_settings = {}


class MerchantBaseLogic:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.interval = 5
        self.thread = None
        self.state = 'uninitialized'

    '''
        Threading Logic
    '''

    def run_logic_loop(self):
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True  # Demonize thread
        self.thread.start()  # Start the execution

    def run(self):
        """ Method that should run forever """
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

            time.sleep(self.interval)

    '''
        Settings and merchant controls for Web-Frontend
    '''

    @abstractmethod
    def get_settings(self):
        return base_settings

    @abstractmethod
    def update_settings(self, settings):
        global base_settings
        base_settings.update(settings)

    @abstractmethod
    def setup(self):
        pass

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

    def init(self):
        self.state = 'initialized'

    def start(self):
        if self.state == 'uninitialized':
            self.init()

        if self.state == 'initialized':
            self.setup()

        self.state = 'running'

    def stop(self):
        if self.state == 'running':
            self.state = 'stopping'

    def terminate(self):
        if self.state == 'uninitialized':
            return

        self.state = 'uninitialized'

    '''
        Simulation API
    '''

    @abstractmethod
    def sold_offer(self, offer_json):
        """
        Do not block execution
        :param offer_json:
        :return:
        """
        pass
