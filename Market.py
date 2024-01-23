import json
from time import sleep

import pytz
from tzlocal import get_localzone
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from app.models import Account, Position, Order
from app import app


def get_candles(asset_symbol: str, interval: str) -> pd.DataFrame:
    stock = yf.Ticker(asset_symbol)
    start_time = datetime.now() - timedelta(days=365)
    if 'm' in interval:
        start_time = datetime.now() - timedelta(days=14)
    start_time = start_time.strftime('%Y-%m-%d')
    return stock.history(interval=interval, start=start_time)


def __get_authorize_header(account: Account) -> dict:
    return {
        'APCA-API-KEY-ID': account.api_key,
        'APCA-API-SECRET-KEY': account.secret_key,
        'accept': 'application/json'
    }


def __cast_str_to_time(time_str:str) -> datetime:
    if time_str is None:
        return None

    return datetime.strptime(time_str[:26], '%Y-%m-%dT%H:%M:%S.%f')\
        .replace(tzinfo=pytz.utc) \
        .astimezone(get_localzone())

def cast_to_order(order_json: dict) -> Order:
    order = Order()
    order.shares = float(order_json['filled_qty']) if order_json['filled_qty'] else None
    order.average_price = float(order_json['filled_avg_price']) if order_json['filled_avg_price'] else None
    order.type = Position.buy if order_json['side'] == 'buy' else Position.sell
    order.alpaca_id = order_json['id']

    order.action_time = __cast_str_to_time(order_json['submitted_at'])
    order.filled_at = __cast_str_to_time(order_json['filled_at'])

    return order


def cancel_order(account: Account, order_id: str):
    bser_url = "https://paper-api.alpaca.markets/v2/orders/" + order_id
    headers = __get_authorize_header(account)
    requests.delete(bser_url, headers=headers)


def get_order_detail(account: Account, order_id: str):
    bser_url = "https://paper-api.alpaca.markets/v2/orders/" + str(order_id)
    headers = __get_authorize_header(account)

    response = requests.get(bser_url, headers=headers)
    if response.status_code != 200:
        raise f'the request got {response.status_code} status code, with this data: {response.text}'

    return json.loads(response.text)


def create_order(account: Account, asset_symbol: str, position: Position, price_amount=None,
                 number_of_share=None) -> Order:
    if price_amount is None and number_of_share is None:
        raise 'the amount should be buy is unknown'

    if price_amount is not None and number_of_share is not None:
        raise 'the function calls by price and number of share, together'

    bser_url = "https://paper-api.alpaca.markets/v2/orders"
    data = {
        "side": position.name,
        "type": "market",
        "time_in_force": "day",
        "symbol": asset_symbol,
    }
    if price_amount is not None:
        data["notional"] = price_amount
    elif number_of_share is not None:
        data['qty'] = number_of_share

    headers = {
        'APCA-API-KEY-ID': account.api_key,
        'APCA-API-SECRET-KEY': account.secret_key,
        'accept': 'application/json'
    }

    response = requests.post(bser_url, json=data, headers=headers)
    if response.status_code != 200:
        app.logger.warning('the request got ' + str(response.status_code) + ' status code, with this data: ' + response.text)
        raise Exception('the request got ' + str(response.status_code) + ' status code, with this data: ' + response.text)

    response_data = json.loads(response.text)
    return cast_to_order(response_data)
