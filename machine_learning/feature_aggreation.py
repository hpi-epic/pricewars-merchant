import numpy as np
import pandas as pd

import sys
sys.path.append('../')
from merchant_sdk.api import KafkaApi

kafka_api = KafkaApi()

'''
    Input
'''
merchant_token = ''
merchant_id = 'sN7jrROVR1hljMZ5OHSLG6cKTwAxKmqDO0OAtWql7Ms='

'''
    Output
'''
data_products = {}
model_products = {}


def match_timestamps(continuous_timestamps, point_timestamps):
    t_ms = pd.DataFrame({
        'timestamp': continuous_timestamps,
        'origin': np.zeros((len(continuous_timestamps)))
    })
    t_bo = pd.DataFrame({
        'timestamp': point_timestamps,
        'origin': np.ones((len(point_timestamps)))
    })

    t_combined = pd.concat([t_ms, t_bo], axis=0).sort_values(by='timestamp')
    original_locs = t_combined['origin'] == 1

    t_combined.loc[original_locs, 'timestamp'] = np.nan
    while t_combined['timestamp'].isnull().any():
        t_combined.loc[original_locs, 'timestamp'] = t_combined['timestamp'].shift(1)[original_locs]

    return t_combined[original_locs]['timestamp']


def aggregate():
    global data_products
    """
    aggregate is going to download all data (csv) and transform it into a suitable data format, based on:
        $timestamp_1, $merchant_id_1, $product_id, $quality, $price
        $timestamp_1, $product_id, $sku, $price

        $timestamp_1, $sold_yes_no, $own_price, $own_price_rank, $cheapest_competitor, $best_competitor_quality
    :return:
    """
    # kafka_api.download_csv_for_topic('buyOffer', 'buyOffer.csv')
    # kafka_api.download_csv_for_topic('marketSituation', 'marketSituation.csv')

    # alternative: use url from KafkaApi:
    # request_csv_export_for_topic()
    buy_offer_df = pd.read_csv('buyOffer.csv')
    market_situation_df = pd.read_csv('marketSituation.csv')

    # TODO: filter market situation to only contain authorized parts
    # own_ms_view = market_situation_df[market_situation_df['triggering_merchant_id'] == merchant_id]
    own_ms_view = market_situation_df
    own_sales = buy_offer_df[buy_offer_df['merchant_id'] == merchant_id]
    own_sales.loc[:, 'timestamp'] = match_timestamps(own_ms_view['timestamp'], own_sales['timestamp'])

    for product_id in np.unique(own_ms_view['product_id']):
        ms_df_prod = own_ms_view[own_ms_view['product_id'] == product_id]

        dict_array = []
        for timestamp, group in ms_df_prod.groupby('timestamp'):
            competitors = group[group['merchant_id'] != merchant_id]
            own_situation = group[group['merchant_id'] == merchant_id]
            has_offer = len(own_situation) > 0
            own_price = float(own_situation['price'].mean()) if has_offer else np.nan
            own_price_rank = (group['price'] < own_price).sum() + 1 if has_offer else np.nan

            dict_array.append({
                'timestamp': timestamp,
                'sold': own_sales[own_sales['timestamp'] == timestamp]['amount'].sum(),
                'own_price': own_price,
                'own_price_rank': own_price_rank,
                'cheapest_competitor': competitors['price'].min(),
                'best_competitor_quality': competitors['quality'].max(),
            })

        data_products[product_id] = pd.DataFrame(dict_array)
    

if __name__ == '__main__':
    aggregate()
