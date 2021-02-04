'''TODO'''

import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy, Analysis
from utils import utils as u


class Put(Strategy):
    '''TODO'''
    def __init__(self, ticker='IBM', direction='long'):
        super().__init__(ticker)

        self.name = 'put'
        self.add_leg(1, 'put', direction, 130.0)


    def __str__(self):
        return f'{self.legs[0].long_short} {self.name}'


    def analyze(self):
        dframe = None
        legs = 0

        if len(self.legs) > 0:
            self.legs[0].calculate()

            # Calculate net debit or credit
            self.analysis.amount = self.legs[0].price * self.legs[0].quantity

            # Generate profit table
            self.analysis.table = self._generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self._calc_max_gain_loss()

            # Calculate breakeven
            if self.legs[0].long_short == 'long':
                self.analysis.breakeven = self.legs[0].strike - self.analysis.amount
            else:
                self.analysis.breakeven = self.legs[0].strike + self.analysis.amount

            legs = 1

        return legs


    def _generate_profit_table(self):
        if self.legs[0].long_short == 'long':
            self.analysis.credit_debit = 'debit'
        else:
            self.analysis.credit_debit = 'credit'

        price = self.legs[0].price

        if self.legs[0].long_short == 'long':
            dframe = self.legs[0].table - price
            dframe = dframe.applymap(lambda x: x if x > -price else -price)
        else:
            dframe = self.legs[0].table
            dframe = dframe.applymap(lambda x: (price - x) if x < price else -(x - price))

        dframe.style.applymap(lambda x: 'color:red' if x is not str and x < 0 else 'color:black')

        return dframe


    def _calc_max_gain_loss(self):
        if self.legs[0].long_short == 'long':
            self.analysis.sentiment = 'bearish'
            max_gain = self.legs[0].strike - self.legs[0].price
            max_loss = self.legs[0].price
        else:
            self.analysis.sentiment = 'bullish'
            max_gain = self.legs[0].price
            max_loss = self.legs[0].strike - self.legs[0].price

        return max_gain, max_loss


    def _calc_price_min_max_step(self):
        if len(self.legs) <= 0:
            min_ = max_ = step_ = 0
        else:
            min_ = int(min(self.legs[0].strike, self.legs[0].symbol.spot)) - 10
            max_ = int(max(self.legs[0].strike, self.legs[0].symbol.spot)) + 11
            step_ = 1

        return min_, max_, step_
