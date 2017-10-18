
from merchant_sdk.api import MarketplaceApi, ProducerApi
from register import get_ip_address

marketplace_url = 'marketplace:8080'
ip_addr = get_ip_address(marketplace_url)
port = 5009
endpoint_url = 'http://' + ip_addr + ':' + str(port)

marketplace = MarketplaceApi(token, host='http://' + marketplace_url)

r = marketplace.register_merchant(api_endpoint_url=endpoint_url, merchant_name='TEST', algorithm_name='test')
merchant_id = r.merchant_id
token = r.merchant_token
print('token', token)

producer = ProducerApi(token, host='http://producer:3050/')
product = producer.buy_products(1000)
print(product)
