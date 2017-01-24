from typing import List
import csv
import json
import threading
import time
import pandas as pd
from random import randint
from datetime import datetime, timedelta
from ..models.Offer import Offer

'''
    The following methods realizing different pricing strategies which can be used dynamically via settings.
'''

'''
    be_cheapest: Evaluate the current market situation and set the price with regards to the cheapest player
                 in the market and the configured underprice to be the new cheapest player.
'''


def be_cheapest(market_situation: List[Offer], product_uid, settings, purchase_price):
    underprice = settings['underprice']
    offers = []
    cheapest_offer = 999
    [offers.append(offer) for i, offer in enumerate(market_situation) if offer["uid"] == product_uid]
    if len(offers) == 0:
        return 2 * purchase_price
    for i, offer in enumerate(offers):
        if offer["price"] < cheapest_offer:
            cheapest_offer = offer["price"]
    return (cheapest_offer - underprice)


'''
    be_second_expensive: Evaluate the current market situation and set the price with regards to the most expensive player
                         in the market and the configured underprice to be the second expensive player.
'''


def be_second_expensive(market_situation: List[Offer], product_uid, settings, purchase_price):
    underprice = settings['underprice']
    offers = []
    most_expensive_offer = 0
    [offers.append(offer) for i, offer in enumerate(market_situation) if offer["uid"] == product_uid]
    if len(offers) == 0:
        return 2 * purchase_price
    for i, offer in enumerate(offers):
        if offer["price"] > most_expensive_offer:
            most_expensive_offer = offer["price"]
    return (most_expensive_offer - underprice)


'''
    be_second_cheapest: Evaluate the current market situation and set the price with regards to the cheapest player
                        in the market and the configured underprice to be the second cheapest player.
'''


def be_second_cheapest(market_situation: List[Offer], product_uid, settings, purchase_price):
    underprice = settings['underprice']
    second_cheapest_offer = cheapest_offer = 2 * purchase_price
    offers = [offer for offer in market_situation if offer.uid == product_uid]

    for offer in sorted(offers, key=lambda offer_entry: offer_entry.price, reverse=True):
        if offer.price < cheapest_offer:
            second_cheapest_offer = cheapest_offer - underprice
            cheapest_offer = offer.price

    return second_cheapest_offer


'''
    be_third_cheapest: Evaluate the current market situation and set the price with regards to the cheapest player
                       in the market and the configured underprice to be the second cheapest player.
'''


def be_third_cheapest(market_situation: List[Offer], product_uid, settings, purchase_price):
    underprice = settings['underprice']
    offers = []
    cheapest_offer = 2 * purchase_price
    second_cheapest_offer = cheapest_offer
    third_cheapest_offer = second_cheapest_offer
    [offers.append(offer) for i, offer in enumerate(market_situation) if offer["uid"] == product_uid]
    # TODO: Sort by price: highest first
    for i, offer in enumerate(offers):
        if offer["price"] < cheapest_offer:
            third_cheapest_offer = second_cheapest_offer - underprice
            second_cheapest_offer = cheapest_offer
            cheapest_offer = offer["price"]
    return third_cheapest_offer


'''
    use_fix_price: Use a fix price based on purchase price and global margin
'''


def use_fix_price(market_situation: List[Offer], product_uid, settings, purchase_price):
    margin = settings['globalProfitMarginForFixPrice']
    return (purchase_price + margin)


'''
    be_random_1_2_3:
'''


def be_random_1_2_3(market_situation: List[Offer], product_uid, settings, purchase_price):
    return ()
