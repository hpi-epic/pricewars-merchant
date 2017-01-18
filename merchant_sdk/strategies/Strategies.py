import csv
import json
import threading
import time
import pandas as pd
from random import randint
from datetime import datetime, timedelta

def be_cheapest(market_situation, product_uid, underprice, purchase_price):
    offers = []
    cheapest_offer = 999
    [offers.append(offer) for i,offer in enumerate(market_situation) if offer["uid"] == product_uid]
    if len(offers) == 0:
        return purchase_price*purchase_price
    for i,offer in enumerate(offers):
        if offer["price"] < cheapest_offer:
            cheapest_offer = offer["price"]
    return (cheapest_offer - underprice)

def be_second(market_situation, product_uid, underprice, purchase_price):
    offers = []
    most_expensive_offer = 999
    [offers.append(offer) for i,offer in enumerate(market_situation) if offer["uid"] == product_uid]
    if len(offers) == 0:
        return purchase_price*purchase_price
    for i,offer in enumerate(offers):
        if offer["price"] > most_expensive_offer:
            most_expensive_offer = offer["price"]
    return (most_expensive_offer - underprice)
