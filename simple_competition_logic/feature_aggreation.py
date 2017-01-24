import numpy as np
import pandas as pd

import sys
sys.path.append('../')
from merchant_sdk.api import KafkaApi

kafka_api = KafkaApi()

def aggregate():
    # kafka_api.download_csv_for_topic('buyOffer', 'buyOffer.csv')
    # kafka_api.download_csv_for_topic('marketSituation', 'marketSituation.csv')

    # alternative: use url from KafkaApi:
    # request_csv_export_for_topic()
    buy_offer_df = pd.read_csv('buyOffer.csv')
    market_situation_df = pd.read_csv('marketSituation.csv')

    print(buy_offer_df)
    print(market_situation_df)
    
    # $timestamp_1, $merchant_id_1, $product_id, $quality, $price
    # $timestamp_1, $product_id, $sku, $price
    
    # $timestamp_1, $sold_yes_no, $own_price, $own_price_rank, $cheapest_competitor, $best_competitor_quality

if __name__ == '__main__':
    aggregate()
