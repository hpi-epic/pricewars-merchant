from .PricewarsObject import PricewarsObject


class MerchantRegisterResponse(PricewarsObject):

    def __init__(self, api_endpoint_url='', merchant_name='', algorithm_name='', color='', merchant_id='', merchant_token=''):
        self.api_endpoint_url = api_endpoint_url
        self.merchant_name = merchant_name
        self.algorithm_name = algorithm_name
        self.color = color
        self.merchant_id = merchant_id
        self.merchant_token = merchant_token
