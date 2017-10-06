
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from register import get_ip_address

marketplace_url = 'marketplace:8080'
ip_addr = get_ip_address(marketplace_url)
port = 5009
endpoint_url = 'http://' + ip_addr + ':' + str(port)

marketplace = MarketplaceApi(host='http://' + marketplace_url)

r = marketplace.register_merchant(api_endpoint_url=endpoint_url, merchant_name='TEST', algorithm_name='test')
merchant_id = r.merchant_id
merchant_token = r.merchant_token
print('token', merchant_token)

PricewarsRequester.add_api_token(merchant_token)

producer = ProducerApi(host='http://producer:3050/')
product = producer.buy_products(1000)
print(product)