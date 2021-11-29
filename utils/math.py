_MIN_MAX_PERCENT = 0.20


def mround(n:float, precision:float) -> float:
    val = float(round(n / precision) * precision)
    if val < 0.01: val = 0.01

    return val

def isnumeric(value) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def calculate_min_max_step(strike:float) -> tuple[float, float, float]:
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