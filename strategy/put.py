'''TODO'''

import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy, Analysis


class Put(Strategy):
    '''TODO'''
    def __init__(self, ticker=''):
        super().__init__(ticker)

        self.name = 'put'
        self.add_leg(1, 'put', 'long', 100.0)


    def __str__(self):
        return f'{self.legs[0].long_short} {self.name}'


    def analyze(self):
        dframe = None
        legs = 0

        if len(self.legs) > 0:
            self.legs[0].calculate()

            # *** Generate profit table
            self.analysis.table = self._generate_profit_table()

            # *** Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self._calc_max_gain_loss()

            legs = 1

        return legs


    def _generate_profit_table(self):
        if self.legs[0].long_short == 'long':
            self.analysis.credit_debit = 'debit'
        else:
            self.analysis.credit_debit = 'credit'

        legs = 1
        price = self.legs[0].price
        dframe = self.legs[0].table - price
        dframe = dframe.applymap(lambda x: x if x > -price else -price)

        return dframe


    def _calc_max_gain_loss(self):
        if self.legs[0].long_short == 'long':
            self.analysis.sentiment = 'bearish'
            max_gain = self.legs[0].symbol.spot - self.legs[0].price
            max_loss = self.legs[0].price
        else:
            self.analysis.sentiment = 'bullish'
            max_gain = self.legs[0].price
            max_loss = self.legs[0].symbol.spot - self.legs[0].price

        return max_gain, max_loss


    def _calc_price_min_max_step(self):
        if len(self.legs) <= 0:
            min_ = max_ = step_ = 0
        else:
            min_ = int(self.legs[0].strike) - 10
            max_ = int(self.legs[0].strike) + 11
            step_ = 1

        return min_, max_, step_
