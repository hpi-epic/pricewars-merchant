from posixpath import join as urljoin
import requests

from .PricewarsRequester import request_session
from merchant_sdk.models import ApiException


class PricewarsBaseApi:

    def __init__(self, host: str='', debug=True):
        self.host = host
        self.debug = debug

    def request(self, method, resource, **kwargs):
        """
        Unified request function
        Use for error handling
        :param method:
        :param resource:
        :param args:
        :param kwargs:
        :return:
        """
        if self.debug:
            print('request', self.__class__, method, resource, kwargs)
        url = urljoin(self.host, resource)
        func = {
            'options': request_session.options,
            'head': request_session.head,
            'get': request_session.get,
            'post': request_session.post,
            'put': request_session.put,
            'patch': request_session.patch,
            'delete': request_session.delete
        }[method.lower()]

        try:
            response = func(url, **kwargs)
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
