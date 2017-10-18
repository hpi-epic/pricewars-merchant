from typing import List
from typing import Optional
import socket
from urllib.parse import urlparse

from.PricewarsBaseApi import PricewarsBaseApi
from ..models import Offer, MerchantRegisterResponse


class MarketplaceApi(PricewarsBaseApi):

    def __init__(self, token: Optional[str]=None, host: str='http://marketplace:8080', debug: bool=False):
        super().__init__(token, host, debug)

    def get_offers(self, include_empty_offers=False) -> List[Offer]:
        params = {}
        if include_empty_offers:
            params['include_empty_offer'] = True
        r = self.request('get', 'offers', params=params)
        return Offer.from_list(r.json())

    def add_offer(self, offer: Offer) -> Offer:
        r = self.request('post', 'offers', json=offer.to_dict())
        return Offer.from_dict(r.json())

    def update_offer(self, offer: Offer):
        self.request('put', 'offers/{:d}'.format(offer.offer_id), json=offer.to_dict())

    def restock(self, offer_id=-1, amount=0, signature=''):
        body = {
            'amount': amount,
            'signature': signature
        }
        self.request('patch', 'offers/{:d}/restock'.format(offer_id), json=body)

    def register_merchant(self, merchant_name: str, algorithm_name: str = '', api_endpoint_url: Optional[str] = None,
                          port: Optional[int] = None) -> MerchantRegisterResponse:

        if api_endpoint_url is None and port is None:
            raise RuntimeError('api_endpoint_url or port must be set')

        if api_endpoint_url is None:
            api_endpoint_url = 'http://{}:{}'.format(self._get_ip_address(self.host), port)

        body = {
            'api_endpoint_url': api_endpoint_url,
            'merchant_name': merchant_name,
            'algorithm_name': algorithm_name
        }
        r = self.request('post', 'merchants', json=body)
        response = MerchantRegisterResponse.from_dict(r.json())
        self.set_auth_token(response.merchant_token)
        return response

    def unregister_merchant(self, merchant_token=''):
        self.request('delete', 'merchants/{:s}'.format(merchant_token))

    @staticmethod
    def _get_ip_address(destination: str):
        url = urlparse(destination)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((url.hostname, url.port))
        return s.getsockname()[0]
