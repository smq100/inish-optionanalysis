import math
import datetime as dt
import collections

import pandas as pd


VALUETABLE_ROWS = 50
VALUETABLE_COLS = 9

range_type = collections.namedtuple('range', ['min', 'max', 'step'])

def mround(n: float, precision: float) -> float:
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


def calculate_min_max_step(strike: float) -> tuple[float, float, float]:
    min_ = 0.0
    max_ = 0.0
    step = 0.0

    if strike > 500.0:
        step = 10.0
    elif strike > 100.0:
        step = 1.0
    elif strike > 50.0:
        step = 0.50
    elif strike > 20.0:
        step = 0.10
    else:
        step = 0.05

    min_ = strike - ((VALUETABLE_ROWS / 2.0) * step)
    max_ = strike + ((VALUETABLE_ROWS / 2.0) * step)

    if min_ < step:
        min_ = step

    return range_type(min_, max_, step)


def compress_table(table: pd.DataFrame, rows: int, cols: int) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame):
        raise ValueError("'table' must be a Pandas DataFrame")

    compressed = pd.DataFrame()

    # Thin out cols
    srows, scols = table.shape
    if cols > 0 and cols < scols:
        step = math.ceil(scols/cols) + 1
        end = table[table.columns[-1::]]  # Save the last col (expiry)
        compressed = table[table.columns[:-1:step]]  # Thin the table, less the last two cols
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

    # Contracts seem to list Thursday as last day for monthly options (last day to trade)
    third -= dt.timedelta(days=1)

    return third


if __name__ == '__main__':
    friday = third_friday()
    print(friday)
