import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from sklearn.externals import joblib

import sys

sys.path.append('../')
from merchant_sdk.api import KafkaApi

kafka_api = KafkaApi(host='http://vm-mpws2016hp1-05.eaalab.hpi.uni-potsdam.de:8001')

'''
    Input
'''
merchant_token = '2ZnJAUNCcv8l2ILULiCwANo7LGEsHCRJlFdvj18MvG8yYTTtCfqN3fTOuhGCthWf'
merchant_id = 'dgOqVxP1nkkncRhIoOTflL2zJ26X1r7xRNcvP6iqlIk='
merchant_id = 'sN7jrROVR1hljMZ5OHSLG6cKTwAxKmqDO0OAtWql7Ms='

'''
    Output
'''
market_situation_df = None
buy_offer_df = None
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


def download():
    global market_situation_df, buy_offer_df

    market_situation_csv_url = kafka_api.request_csv_export_for_topic('marketSituation')
    market_situation_df = pd.read_csv(market_situation_csv_url)
    buy_offer_csv_url = kafka_api.request_csv_export_for_topic('buyOffer')
    buy_offer_df = pd.read_csv(buy_offer_csv_url)


def aggregate():
    """
    aggregate is going to transform the downloaded two csv it into a suitable data format, based on:
        $timestamp_1, $merchant_id_1, $product_id, $quality, $price
        $timestamp_1, $product_id, $sku, $price

        $timestamp_1, $sold_yes_no, $own_price, $own_price_rank, $cheapest_competitor, $best_competitor_quality
    :return:
    """
    global data_products, buy_offer_df, market_situation_df

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
        data_products[product_id].to_csv('product_{}_data.csv'.format(product_id))


def train():
    global data_products, model_products

    for product_id in data_products:
        data = data_products[product_id].dropna()
        X = data[['own_price', 'own_price_rank', 'cheapest_competitor', 'best_competitor_quality']]
        y = data['sold']
        y[y > 1] = 1

        model = LogisticRegression()
        model.fit(X, y)

        model_products[product_id] = model


def export_models():
    global model_products
    for product_id in model_products:
        model = model_products[product_id]
        joblib.dump(model, '{}.pkl'.format(product_id))


if __name__ == '__main__':
    download()
    aggregate()
    train()
    export_models()
