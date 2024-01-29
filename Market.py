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


def __get_authorize_header(account: Account.AccountDTO) -> dict:
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


def cancel_order(account: Account.AccountDTO, order_id: str):
    bser_url = "https://paper-api.alpaca.markets/v2/orders/" + str(order_id)
    headers = __get_authorize_header(account)
    requests.delete(bser_url, headers=headers)


def get_order_detail(account: Account.AccountDTO, order_id: str):
    bser_url = "https://paper-api.alpaca.markets/v2/orders/" + str(order_id)
    headers = __get_authorize_header(account)

    response = requests.get(bser_url, headers=headers)
    if response.status_code != 200:
        raise f'the request got {response.status_code} status code, with this data: {response.text}'

    return json.loads(response.text)


def create_order(account: Account.AccountDTO, asset_symbol: str, position: Position, price_amount=None,
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


class AccountPerformanceItem:
    def __init__(self, time: int, profit_loss: int):
        self.__date = datetime.fromtimestamp(time).date()
        self.__profit_loss = profit_loss

    def get_date(self):
        return self.__date

    def get_profit_loss(self):
        return self.__profit_loss



def get_performance(account: Account.AccountDTO, number_of_day: int = 5):
    base_url = "https://paper-api.alpaca.markets/v2/account/portfolio/history"
    param = {
        'period': f'{number_of_day}D',
        'timeframe': '1D',
        'intraday_reporting': 'market_hours',
        'pnl_reset': 'per_day'
    }
    headers = __get_authorize_header(account)
    response = requests.get(base_url, param, headers=headers)

    if response.status_code != 200:
        raise Exception(f'unable to get the performance of the account and got {response.status_code}: {response.text}')

    response = json.loads(response.text)
    performance_items = []
    for i in range(len(response['timestamp'])):
        performance_items.append(AccountPerformanceItem(response['timestamp'][i], response['profit_loss'][i]))

    return performance_items


if __name__ == '__main__':
    a = Account()
    a.secret_key = '6QOgIWFfp9ut6tScmVD3SVWeqkeuU1J10oOxKS2F'
    a.api_key = 'PKUTWRTNWLSMZHVEPJR9'
    for item in get_performance(a, 10):
        print(item)
