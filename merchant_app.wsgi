import sys
import os
here = os.path.dirname(__file__)

simple_competition_logic_path = os.path.join(here, 'simple_competition_logic/')

sys.path.insert(0, here)
sys.path.insert(0, simple_competition_logic_path)

from MerchantApp import app as application
