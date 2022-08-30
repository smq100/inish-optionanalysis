import math
import datetime as dt
import collections

import pandas as pd

import strategies as s
from strategies.analysis import calculate_sentiment
from utils import ui


VALUETABLE_ROWS = 50
VALUETABLE_COLS = 9

range_type = collections.namedtuple('range_type', ['min', 'max', 'step'])


def mround(n: float, precision: float, floor: bool = False) -> float:
    if floor:
        val = float((n // precision) * precision)
    else:
        val = float(round(n / precision) * precision)
    if val < 0.01:
        val = 0.01

    return val


def isnumeric(value) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def calculate_min_max_step(strike: float) -> range_type:
    min_ = 0.0
    max_ = 0.0
    step = 0.0

    if strike < 1.0:
        step = 0.05
    elif strike < 2.5:
        step = 0.10
    elif strike < 5.0:
        step = 0.25
    elif strike < 10.0:
        step = 0.10
    elif strike < 25.0:
        step = 0.2
    elif strike < 50.0:
        step = 0.50
    elif strike < 100.0:
        step = 1.0
    elif strike < 250.0:
        step = 2.0
    elif strike < 500.0:
        step = 4.0
    elif strike < 1000.0:
        step = 8.0
    elif strike < 2000.0:
        step = 16.0
    else:
        step = 30.0

    min_ = strike - ((VALUETABLE_ROWS / 2.0) * step)
    max_ = strike + ((VALUETABLE_ROWS / 2.0) * step)

    if min_ < step:
        min_ = step

    return range_type(min_, max_, step)


def calculate_strike_and_widths(strategy: s.StrategyType, product: s.ProductType, direction: s.DirectionType, strike: float) -> tuple[float, float, float]:
    width1 = 0.0
    width2 = 0.0

    if strike < 1.0:
        width1 = 0.10
    elif strike < 2.5:
        width1 = 0.25
    elif strike < 5.0:
        width1 = 0.50
    elif strike < 10.0:
        width1 = 1.00
    elif strike < 25.0:
        width1 = 2.00
    elif strike < 50.0:
        width1 = 2.50
    elif strike < 100.0:
        width1 = 5.00
    elif strike < 250.0:
        width1 = 10.00
    elif strike < 500.0:
        width1 = 20.00
    elif strike < 1000.0:
        width1 = 50.00
    elif strike < 2000.0:
        width1 = 100.00
    else:
        width1 = 30.0

    # Calculate to closest value ITM using width as multiple
    strike = mround(strike, width1, floor=True)
    sentiment = calculate_sentiment(strategy, product, direction)
    if sentiment == s.SentimentType.Bearish:
        strike += width1

    if strategy == s.StrategyType.IronCondor:
        width2 = width1

    return strike, width1, width2


def compress_table(table: pd.DataFrame, rows: int, cols: int, auto: bool = True) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame):
        raise ValueError('\'table\' must be a Pandas DataFrame')

    compressed = pd.DataFrame()

    if auto:
        cols = ui.TERMINAL_SIZE.columns - 10  # Subtract approx price column width
        cols = cols // 15  # Floor-divide by approx col size

    # Thin out cols
    srows, scols = table.shape
    if cols > 0 and cols < scols:
        step = math.ceil(scols/cols) + 1
        end = table[table.columns[-1::]]  # Save the last col (expiry)
        compressed = table[table.columns[:-1:step]].copy()  # Thin the table, less the last col
        compressed = pd.concat([compressed, end], axis=1)  # Add back the last col

    # Thin out rows
    if rows > 0 and rows < srows:
        step = math.ceil(srows/rows)
        compressed = compressed.iloc[::step]

    return compressed


def third_friday() -> dt.datetime:
    today = dt.datetime.today()
    today += dt.timedelta(days=32)

    # The 15th is the first possible third day of the month
    third = dt.datetime(today.year, today.month, 15)

    w = third.weekday()
    if w != 4:
        third = third.replace(day=(15 + (4 - w) % 7))

    third.replace(hour=0, minute=0, second=0, microsecond=0)

    return third


if __name__ == '__main__':
    friday = third_friday()
    print(friday)
