from merchant_sdk.api import MarketplaceApi, ProducerApi

marketplace = MarketplaceApi()
r = marketplace.register_merchant(merchant_name='TEST', algorithm_name='test', port=5009)
merchant_id = r.merchant_id
token = r.merchant_token
print('token', token)

producer = ProducerApi(token)
product = producer.buy_products(1000)
print(product)
