from pricewars.api.PricewarsBaseApi import PricewarsBaseApi


class Kafka(PricewarsBaseApi):
    DEFAULT_URL = 'http://kafka-reverse-proxy:8001'

    def __init__(self, token: str, host: str = DEFAULT_URL, debug: bool = False):
        super().__init__(token, host, debug)

    def _request_data_export(self, topic):
        r = self.request('get', 'export/data/{:s}'.format(topic))
        return r.json()['url']

    def download_csv_for_topic(self, topic, local_filename):
        url = self._request_data_export(topic)
        r = self.request('get', url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        return True

    def request_csv_export_for_topic(self, topic):
        url = self._request_data_export(topic)
        return '{:s}/{:s}'.format(self.host, url)
