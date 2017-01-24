import csv
import json
import threading
import time
import pandas as pd
from random import randint
from datetime import datetime, timedelta

'''
    The following methods realizing different pricing strategies which can be used dynamically via settings.
'''


'''
    be_cheapest: Evaluation the current market situation and setting the price with regards to the cheapest player
                 in the market and the configured underprice to be the new cheapest player.
'''
def be_cheapest(market_situation, product_uid, settings, purchase_price):
    underprice = settings['underprice']
    offers = []
    cheapest_offer = 999
    [offers.append(offer) for i,offer in enumerate(market_situation) if offer["uid"] == product_uid]
    if len(offers) == 0:
        return 2*purchase_price
    for i,offer in enumerate(offers):
        if offer["price"] < cheapest_offer:
            cheapest_offer = offer["price"]
    return (cheapest_offer - underprice)

'''
    be_second: Evaluation the current market situation and setting the price with regards to the cheapest player
            in the market and the configured underprice to be the second cheapest player.
'''
def be_second(market_situation, product_uid, settings, purchase_price):
    underprice = settings['underprice']
    offers = []
    most_expensive_offer = 999
    [offers.append(offer) for i,offer in enumerate(market_situation) if offer["uid"] == product_uid]
    if len(offers) == 0:
        return 2*purchase_price
    for i,offer in enumerate(offers):
        if offer["price"] > most_expensive_offer:
            most_expensive_offer = offer["price"]
    return (most_expensive_offer - underprice)

'''
    use_fix_price: Simple using a fix price based on purchase price and global margin
'''
def use_fix_price(market_situation, product_uid, settings, purchase_price):
    margin = settings['globalProfitMarginForFixPrice']
    return (purchase_price + margin)
