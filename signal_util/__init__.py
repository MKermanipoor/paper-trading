import re
from typing import List

import numpy as np
import pandas as pd
from signal_util.indicator import *

SIGNALS = {
    'MACD': MACD,
    'SIGNAL': signal,
    'HISTOGRAM': histogram,
    'SMA': SMA,
    'EMA': EMA
}

def get_majority_signal(candles: pd.DataFrame, signals: List[str]) -> pd.Series:
    _ = pd.Series(np.zeros(len(candles)), index=candles.index)
    for s in signals:
        _ += get_signal(candles, s)

    return _ > len(signals)/2


def get_indicator(candles: pd.DataFrame, indicator_key: str) -> pd.Series:
    kwargs = {
        'candles': candles
    }

    if re.match(r'\d+', indicator_key):
        return number(candles, int(indicator_key))

    if re.match(r'SLOPE\s*\(.*\)', indicator_key):
        new_indicator_key = (indicator_key.replace('SLOPE', '').strip()[1:-1]
                             .strip())
        return slope(get_indicator(candles, new_indicator_key))

    if 'SMA' in indicator_key or 'EMA' in indicator_key:
        p = re.search(r'\(\s*\d+\s*\)', indicator_key).group()
        kwargs['window'] = int(re.search(r'\d+', p).group())

        indicator_key = indicator_key[:indicator_key.find('(')].strip()

    return SIGNALS[indicator_key](**kwargs)


def get_signal(candles: pd.DataFrame, signal_key: str) -> pd.Series:
    operator = re.search(r'(<=?)|(>=?)|=', signal_key)

    indicator_1 = signal_key[:operator.start()].strip().upper()
    indicator_2 = signal_key[operator.end():].strip().upper()

    indicator_1 = get_indicator(candles, indicator_1)
    indicator_2 = get_indicator(candles, indicator_2)

    operator = operator.group().strip()

    if operator == '>':
        return indicator_1 > indicator_2

    elif operator == '<':
        return indicator_1 < indicator_2

    elif operator == '>=':
        return indicator_1 >= indicator_2

    elif operator == '<=':
        return indicator_1 <= indicator_2

    elif operator == '=':
        return indicator_1 == indicator_2

    else:
        raise 'unable to handle the operator'