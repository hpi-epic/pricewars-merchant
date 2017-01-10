import sys

sys.path.insert(0, '/var/www/pricewars-merchant/current/merchant-sdk/')
sys.path.insert(0, '/var/www/pricewars-merchant/current/simple_competition_logic/')


def application(environ, start_response):
	print('deploy Merchant', 'env:', environ)
	
	from MerchantApp import app as _application
	return _application(environ, start_response)