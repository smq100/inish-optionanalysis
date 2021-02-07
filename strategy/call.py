'''TODO'''

import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy, Analysis
from utils import utils as u


class Call(Strategy):
    '''TODO'''

    def __init__(self, ticker, product, direction, width=1):
        product = 'call'
        super().__init__(ticker, product, direction, width)

        self.name = 'call'
        expiry = datetime.datetime.today() + datetime.timedelta(days=14)
        self.add_leg(1, product, direction, self.initial_spot, expiry)


    def __str__(self):
        return f'{self.legs[0].direction} {self.name}'


    def analyze(self):
        dframe = None

        if self._validate():
            self.legs[0].calculate()

            if self.legs[0].direction == 'long':
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            # Calculate net debit or credit
            self.analysis.amount = self.legs[0].option.calc_price * self.legs[0].quantity

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calc_max_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = self.calc_breakeven()


    def generate_profit_table(self):
        price = self.legs[0].option.calc_price

        if self.legs[0].direction == 'long':
            dframe = self.legs[0].table - price
        else:
            dframe = self.legs[0].table
            dframe = dframe.applymap(lambda x: (price - x) if x < price else -(x - price))

        dframe.style.applymap(lambda x: 'color:red' if x is not str and x < 0 else 'color:black')

        return dframe


    def calc_max_gain_loss(self):
        if self.legs[0].direction == 'long':
            self.analysis.sentiment = 'bullish'
            max_gain = -1.0
            max_loss = self.legs[0].option.calc_price
        else:
            self.analysis.sentiment = 'bearish'
            max_gain = self.legs[0].option.calc_price
            max_loss = -1.0

        return max_gain, max_loss

    def calc_breakeven(self):
        if self.legs[0].direction == 'long':
            breakeven = self.legs[0].option.strike + self.analysis.amount
        else:
            breakeven = self.legs[0].option.strike - self.analysis.amount

        return breakeven
