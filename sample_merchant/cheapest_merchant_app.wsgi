import sys
import os
here = os.path.dirname(__file__)

sample_merchant = os.path.join(here, 'sample_merchant/')

sys.path.insert(0, here)
sys.path.insert(0, simple_competition_logic_path)

from CheapestMerchantApp import app as application
