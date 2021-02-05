'''TODO'''

import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy, Analysis
from utils import utils as u


class Put(Strategy):
    '''TODO'''

    def __init__(self, ticker, product, direction):
        product = 'put'
        super().__init__(ticker, product, direction)

        self.name = 'put'
        self.add_leg(1, product, direction, self.initial_spot)


    def __str__(self):
        return f'{self.direction} {self.name}'


    def analyze(self):
        dframe = None

        if self._validate():
            self.legs[0].calculate()

            if self.direction == 'long':
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            # Calculate net debit or credit
            self.analysis.amount = self.legs[0].price * self.legs[0].quantity

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calc_max_gain_loss()

            # Calculate breakeven
            if self.direction == 'long':
                self.analysis.breakeven = self.legs[0].strike - self.analysis.amount
            else:
                self.analysis.breakeven = self.legs[0].strike + self.analysis.amount


    def generate_profit_table(self):
        price = self.legs[0].price

        if self.direction == 'long':
            dframe = self.legs[0].table - price
            dframe = dframe.applymap(lambda x: x if x > -price else -price)
        else:
            dframe = self.legs[0].table
            dframe = dframe.applymap(lambda x: (price - x) if x < price else -(x - price))

        dframe.style.applymap(lambda x: 'color:red' if x is not str and x < 0 else 'color:black')

        return dframe


    def calc_max_gain_loss(self):
        if self.direction == 'long':
            self.analysis.sentiment = 'bearish'
            max_gain = self.legs[0].strike - self.legs[0].price
            max_loss = self.legs[0].price
        else:
            self.analysis.sentiment = 'bullish'
            max_gain = self.legs[0].price
            max_loss = self.legs[0].strike - self.legs[0].price

        return max_gain, max_loss
