from merchant_sdk.api import MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer

marketplace = MarketplaceApi()
marketplace.wait_for_host()
r = marketplace.register(endpoint_url_or_port=5009, merchant_name='TEST', algorithm_name='test')
merchant_id = r.merchant_id
token = r.merchant_token
print('token', token)

producer = ProducerApi(token)
product = producer.buy_products(1000)
print(product)
