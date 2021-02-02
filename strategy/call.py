'''TODO'''
import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy


class Call(Strategy):
    '''TODO'''
    def __init__(self, strategy='call', pricing_method='black-scholes'):
        super().__init__(strategy, pricing_method)

    def analyze_strategy(self):
        dframe = None
        legs = 0

        if len(self.legs) <= 0:
            pass
        else:
            self.calculate_leg(0)

            legs = 1
            price = self.legs[0].price
            dframe = self.legs[0].table_value - price
            dframe = dframe.applymap(lambda x: x if x > -price else -price)

        return dframe, legs

    def _calc_price_min_max_step(self):
        if len(self.legs) <= 0:
            min_ = max_ = step_ = 0
        else:
            min_ = int(self.legs[0].strike) - 10
            max_ = int(self.legs[0].strike) + 11
            step_ = 1

        return min_, max_, step_