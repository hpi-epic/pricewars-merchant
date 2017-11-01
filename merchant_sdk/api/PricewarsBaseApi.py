from urllib.parse import urljoin
import requests
from typing import Optional


class PricewarsBaseApi:

    def __init__(self, token: Optional[str], host: str, debug: bool):
        self.host = host
        self.debug = debug
        self.session = requests.Session()
        if token is not None:
            self.set_auth_token(token)

    def request(self, method: str, resource: str, **kwargs):
        if self.debug:
            print('request', self.__class__, method, resource, kwargs)

        url = urljoin(self.host, resource)
        response = self.session.request(method, url, **kwargs)

        if self.debug:
            print('response', 'status({:d})'.format(response.status_code), response.text)

        response.raise_for_status()
        return response

    def set_auth_token(self, token: str):
        self.session.headers.update({'Authorization': 'Token {:s}'.format(token)})
