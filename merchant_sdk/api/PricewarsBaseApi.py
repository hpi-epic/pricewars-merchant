from urllib.parse import urljoin
import requests

from merchant_sdk.models import ApiException


class PricewarsBaseApi:

    def __init__(self, token: str, host: str, debug: bool):
        self.host = host
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'Token {:s}'.format(token)})

    def request(self, method: str, resource: str, **kwargs):
        if self.debug:
            print('request', self.__class__, method, resource, kwargs)

        url = urljoin(self.host, resource)
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError:
            raise RuntimeError('Cannot connect to ' + self.host)

        if self.debug:
            print('response', 'status({:d})'.format(response.status_code), response.text)

        if 400 <= response.status_code < 600:
            try:
                error_msg = response.json()
            except ValueError:
                error_msg = {}
            raise ApiException(error_msg)

        return response
