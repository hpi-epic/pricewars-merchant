# Merchant

This repository contains the merchant-component of the Pricewars-simulation. The merchant represents a vendor trying to sell their products at the highest possible profit at the marketplace. As such, they also represent a certain pricing strategy that is to be tested against other pricing strategies. Such a pricing strategy can be either very simple and rule-driven, such as "always be 10 cents cheaper than your competitors" or data-driven and use machine learning strategies.

This repository contains multiple sample merchants that each implement one of the following strategies:

* Cheapest
* Second Cheapest
* Random Third
  * randomly chooses either the first, second or third position in the price ranking
* Two Bound 
  * has a minimum and maximum profit margin
  * keeps decreasing the price to maintain the 1st position in the price rank until the minimum bound is reached
  * then set the price back to the maximum margin
* Fix Price
* Maximize Highest Expected Profit
  * i.e. a data-driven, machine learning merchant using logistic regression

Moreover, the repository contains an SDK to easily build arbitrary merchant behaviors yourself.

The meta repository containing general information can be found [here](https://github.com/hpi-epic/masterproject-pricewars).

## Application Overview

| Repo | Branch 	| Deployment to  	| Status | Description |
|--- |---	|---	|---  |---   |
| [UI](https://github.com/hpi-epic/pricewars-mgmt-ui) | master  	|  [vm-mpws2016hp1-02.eaalab.hpi.uni-potsdam.de](http://vm-mpws2016hp1-02.eaalab.hpi.uni-potsdam.de) 	| [ ![Codeship Status for hpi-epic/pricewars-mgmt-ui](https://app.codeship.com/projects/d91a8460-88c2-0134-a385-7213830b2f8c/status?branch=master)](https://app.codeship.com/projects/184009) | Stable |
| [Consumer](https://github.com/hpi-epic/pricewars-consumer) | master  	|  [vm-mpws2016hp1-01.eaalab.hpi.uni-potsdam.de](http://vm-mpws2016hp1-01.eaalab.hpi.uni-potsdam.de) | [ ![Codeship Status for hpi-epic/pricewars-consumer](https://app.codeship.com/projects/96f32950-7824-0134-c83e-5251019101b9/status?branch=master)](https://app.codeship.com/projects/180119) | Stable |
| [Producer](https://github.com/hpi-epic/pricewars-producer) | master  	|  [vm-mpws2016hp1-03eaalab.hpi.uni-potsdam.de](http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de) | [ ![Codeship Status for hpi-epic/pricewars-producer](https://app.codeship.com/projects/0328e450-88c6-0134-e3d6-7213830b2f8c/status?branch=master)](https://app.codeship.com/projects/184016) | Stable |
| [Marketplace](https://github.com/hpi-epic/pricewars-marketplace) | master  	|  [vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de/marketplace](http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de/marketplace/offers) 	| [ ![Codeship Status for hpi-epic/pricewars-marketplace](https://app.codeship.com/projects/e9d9b3e0-88c5-0134-6167-4a60797e4d29/status?branch=master)](https://app.codeship.com/projects/184015) | Stable |
| [Merchant](https://github.com/hpi-epic/pricewars-merchant) | master  	|  [vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de/](http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de/) 	| [ ![Codeship Status for hpi-epic/pricewars-merchant](https://app.codeship.com/projects/a7d3be30-88c5-0134-ea9c-5ad89f4798f3/status?branch=master)](https://app.codeship.com/projects/184013) | Stable |

## Requirements

The merchants are written in Python. Ensure to have [Python](https://www.python.org/) installed and set up on your computer. 

_The SDK requires a Python version of at least 3.5!_ 

It is type-hinted, so using an IDE (e.g. PyCharm) is helpful.

## Setup

After cloning the repository, install the necessary dependencies from the `merchant_sdk/` directory with 
`pip install -r requirements.txt` (Linux, MacOS) resp. `python -m pip install -r requirements.txt` (Windows). 

### Sample Merchants
Once the dependencies are installed, you can run a data-driven sample merchant by executing eg:

```
cd sample_merchant
python CheapestMerchantApp.py
``` 

To run the sample machine learning merchant, you need additional dependencies before running it. In the top-folder, execute:

```
cd machine_learning
pip install -r requirements.txt
python MLMerchant.py
```

## Configuration

The default URLs to all components needed for the merchant are set in `MerchantBaseLogic.py` in the _merchant_sdk/_-folder from line 27 onwards. If defined, variables from the environment are used instead: `PRICEWARS_MARKETPLACE_URL`, `PRICEWARS_PRODUCER_URL` and `PRICEWARS_KAFKA_REVERSE_PROXY_URL`.

## Concept

The merchant sells _products_ to _consumers_ on the _marketplace_. The interface to do so, is derived from real world online marketplaces. Thus, a merchant:

* has to **register** at the marketplace, which will grant him an identification and authorization token. This token can be mandatory for certain actions and is also used to keep track of all earnings and expenses of a merchant (e.g. in logs).
* can **buy products** form the producer. These are randomly chosen, so the merchant cannot actively choose products. This is due to the fact, that merchants should focus on pricing.
* can **put** products as **offers** on the marketplace, increase amount of products of an offer (**restock**) and reprice offers (requests are limited)
* needs to accept notifications about **sales** (as http request on `/sold`)

A merchant is both, a service and a client. It needs to steadily interact on the marketplace and thus, should implement a kind of game loop or a series of scheduled events. The Merchant SDK offers a web server for sale/start/stop requests and and a base merchant loop. Subclassing and overwriting the `execute_logic` method is all one needs to get a merchant started.

## Merchant SDK

*Note*: Have a look at the samples in the merchant_sdk folder, [this one](merchant_sdk/samples/Handling\ products\ and\ offers.ipynb) shows how to use the sdk to call producer and marketplace APIs to implement product and offer handling.

The SDK contains models and request APIs to ease the development of a merchant:

* Models
	* Offer
	* Product
	* Error
* API to (using models according to [Swagger API](https://hpi-epic.github.io/masterproject-pricewars/))
	* Marketplace (get/add/restock offers, register)
	* Producer (buy products)
	* Kafka REST service (get log data as CSV)
* MerchantServer
	* provides web server to accept sold interface, updating settings and simple execution states (stop/stop)
* MerchantBaseLogic
	* defines interface for Merchants to work with the MerchantServer

## Machine Learning Sample Merchant

Note: Look at [this notebook](merchant_sdk/samples/Working\ with\ Kafka\ data.ipynb) for a quick access to the Kafka data using pandas and the merchant sdk.

### Concept

A machine learning merchant is like any other merchant, interacting on the marketplace. The difference is, that it uses trained models for predicting the demand of the customer for a product. These models need to be created and updated over time, which takes too much time to do on each price update. So updates to the models are done concurrently (asynchronously) by another process.

The `machine_learning` folder contains

* a new Merchant `MLMerchant.py`
	* works as the sample merchants
	* does not react to sold notifications
	* maintains a constant amount of offers on the market
	* update price of offers:
		* randomly (exponential price distribution); if no model is available
		* calculating the price that optimizes the expected profit for predicted customer demand; if model is available
* `market_learning.py` download log data and trains a customer demand model. Overwrites model on filesystem

The MLMerchant process invokes the `market_learning.py` script regularly and always reloads the model from the filesystem.


### Data

We recommend to use the data that is logged to Kafka (which can be raw or processed by Flink). In order to access it more easily, we built a reverse REST service (_kafka-reverse-proxy_). It provides the data by topics and you should have a look at [this documentation](https://github.com/hpi-epic/pricewars-kafka-reverse-proxy#filtered-data-view-as-csv).

To estimate the demand and compute a good price, we join the sales of a product (topic: *buyOffer*) and periodical snapshots of the available offers on the marketplace (topic: *marketSituation*). FYI: logging and data format is [documented here](https://github.com/hpi-epic/pricewars-marketplace#logging).

#### fetch data using the merchant-sdk

The merchant_sdk also provides nice methods to download the data. The returned URL to the csv can be used with pandas to directly download a csv and turn it into a DataFrame. [This](machine_learning/market_learning.py) is a good example to learn a model.

```python
sys.path.append('../') # path to folder containing merchant_sdk
from merchant_sdk.api import KafkaApi

host = 'http://vm-mpws2016hp1-05.eaalab.hpi.uni-potsdam.de:8001'
kafka_api = KafkaApi(host=host)

market_situation_csv_url = kafka_api.request_csv_export_for_topic('marketSituation')
market_situation_df = pd.read_csv(market_situation_csv_url)
```