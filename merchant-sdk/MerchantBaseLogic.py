from abc import ABCMeta, abstractmethod

base_settings = {}


class MerchantBaseLogic:
    __metaclass__ = ABCMeta

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
    def init(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def terminate(self):
        pass

    '''
        Simulation API
    '''

    @abstractmethod
    def sold_offer(self, offer_json):
        pass
