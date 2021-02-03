'''TODO'''
import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy


class Put(Strategy):
    '''TODO'''
    def __init__(self, name='put'):
        super().__init__(name)

    def analyze(self):
        dframe = None
        legs = 0

        if len(self.legs) <= 0:
            pass
        else:
            self.legs[0].calculate()

            legs = 1
            price = self.legs[0].price
            dframe = self.legs[0].table - price
            dframe = dframe.applymap(lambda x: x if x > -price else -price)
            self.analysis.table = dframe

        return legs

    def _calc_price_min_max_step(self):
        if len(self.legs) <= 0:
            min_ = max_ = step_ = 0
        else:
            min_ = int(self.legs[0].strike) - 10
            max_ = int(self.legs[0].strike) + 11
            step_ = 1

        return min_, max_, step_
