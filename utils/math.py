import math
import datetime as dt

import pandas as pd

_MIN_MAX_PERCENT = 0.20


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

    min_ = strike * (1.0 - _MIN_MAX_PERCENT)
    max_ = strike * (1.0 + _MIN_MAX_PERCENT)

    step = (max_ - min_) / 40.0
    step = mround(step, step / 10.0)

    if min_ < step:
        min_ = step

    return min_, max_, step


def compress_table(table: pd.DataFrame, rows: int, cols: int) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame):
        raise ValueError("'table' must be a Pandas DataFrame")

    compressed = pd.DataFrame()

    # Thin out cols
    srows, scols = table.shape
    if cols > 0 and cols < scols:
        step = int(math.ceil(scols/cols))
        end = table[table.columns[-2::]]  # Save the last two cols
        compressed = table[table.columns[:-2:step]]  # Thin the table, less the last two cols
        compressed = pd.concat([compressed, end], axis=1)  # Add back the last two cols

    # Thin out rows
    if rows > 0 and rows < srows:
        step = int(math.ceil(srows/rows))
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

    return third


if __name__ == '__main__':
    friday = third_friday()
    print(friday)
