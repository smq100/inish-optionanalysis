'''TODO'''
import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy


class Vertical(Strategy):
    '''TODO'''
    def __init__(self, name='vertical', pricing_method='black-scholes'):
        super().__init__(name, pricing_method)

    def analyze(self):
        dframe = None
        legs = 0

        if len(self.legs) <= 0:
            pass
        else:
            legs = 2
            self.calculate_leg(0)
            self.calculate_leg(1)

            if self.legs[0].long_short == 'long':
                dframe = self.legs[0].table_value - self.legs[1].table_value
            else:
                dframe = self.legs[1].table_value - self.legs[0].table_value

            self.analysis.table_value = dframe

        return legs

    def _calc_price_min_max_step(self):
        if len(self.legs) <= 0:
            min_ = max_ = step_ = 0
        else:
            min_ = int(min([self.legs[0].strike, self.legs[1].strike])) - 10
            max_ = int(max([self.legs[0].strike, self.legs[1].strike])) + 11
            step_ = 1

        return min_, max_, step_
