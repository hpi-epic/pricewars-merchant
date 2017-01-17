from posixpath import join as urljoin

from .PricewarsRequester import request_session


class PricewarsBaseApi:

    def __init__(self, host=''):
        self.host = host

    def request(self, method, resource, *args, **kwargs):
        """
        Unified request function
        Use for error handling
        :param method:
        :param resource:
        :param args:
        :param kwargs:
        :return:
        """
        print('request', self.__class__, method, resource, args, kwargs)
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
            response = func(url, *args, **kwargs)
            print('response', 'status({:d})'.format(response.status_code), response.text)
            return response
        except Exception as e:
            print('api request failed', e)
            return None
