import ta
import pandas as pd
import numpy as np


def MACD (candles: pd.DataFrame):
    return ta.trend.macd(candles['Close'], window_fast=5, window_slow=18)


def signal(candles: pd.DataFrame):
    return ta.trend.macd_signal(candles['Close'], window_sign=7, window_fast=5, window_slow=18)


def histogram (candles: pd.DataFrame):
    return ta.trend.macd_diff(candles['Close'], window_sign=7, window_fast=5, window_slow=18)


def SMA (candles: pd.DataFrame, window: int):
    return ta.trend.sma_indicator(candles['Close'], window)


def SMA (candles: pd.DataFrame, window: int):
    return ta.trend.sma_indicator(candles['Close'], window)


def EMA (candles: pd.DataFrame, window: int):
    return ta.trend.ema_indicator(candles['Close'], window)


def number(candles: pd.DataFrame, num: int):
    return pd.Series(np.full(len(candles), num), index=candles.index)


def slope(indicator: pd.Series):
    return indicator - indicator.shift(1)