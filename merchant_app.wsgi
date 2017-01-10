import sys

sys.path.insert(0, '/var/www/pricewars-merchant/current/merchant-sdk/')
sys.path.insert(0, '/var/www/pricewars-merchant/current/simple_competition_logic/')

from MerchantApp import app as _application

def application(environ, start_response):
	print('deploy Merchant', 'env:', environ)
	os.environ['TOKEN'] = environ['TOKEN']
	return _application(environ, start_response)