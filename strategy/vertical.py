'''TODO'''

import datetime
import logging

import pandas as pd

from strategy.strategy import Strategy, Analysis
from utils import utils as u


class Vertical(Strategy):
    '''TODO'''

    def __init__(self, ticker, product, direction):
        super().__init__(ticker, product, direction)

        self.name = 'vertical'

        # Add legs (long leg is first)
        if product == 'call':
            if direction == 'long':
                self.add_leg(1, product, 'long', self.initial_spot)
                self.add_leg(1, product, 'short', self.initial_spot + 2.0)
            else:
                self.add_leg(1, product, 'long', self.initial_spot + 2.0)
                self.add_leg(1, product, 'short', self.initial_spot)
        else:
            if direction == 'long':
                self.add_leg(1, product, 'long', self.initial_spot + 2.0)
                self.add_leg(1, product, 'short', self.initial_spot)
            else:
                self.add_leg(1, product, 'long', self.initial_spot)
                self.add_leg(1, product, 'short', self.initial_spot + 2.0)

    def __str__(self):
        return f'{self.name} {self.product} {self.analysis.credit_debit} spread'


    def analyze(self):
        ''' Analyze the stratwgy (Important: Assumes the long leg is the index-0 leg)'''

        if self._validate():
            self.legs[0].calculate()
            self.legs[1].calculate()

            if self.direction == 'long':
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            # Calculate net debit or credit
            self.analysis.amount = self.legs[1].price * self.legs[1].quantity
            self.analysis.amount -= (self.legs[0].price * self.legs[0].quantity)

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calc_max_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = -1.0


    def generate_profit_table(self):
        # Create net-value table

        dframe = self.legs[0].table - self.legs[1].table + self.analysis.amount

        dframe.style.applymap(lambda x: 'color:red' if x is not str and x < 0 else 'color:black')

        return dframe


    def calc_max_gain_loss(self):
        gain = loss = 0.0

        if self.direction == 'long':
            gain = abs(self.legs[0].strike - self.legs[1].strike)
            loss = abs(self.analysis.amount)

            if self.product == 'call':
                self.analysis.sentiment = 'bullish'
            else:
                self.analysis.sentiment = 'bearish'
        else:
            gain = abs(self.analysis.amount)
            loss = abs(self.legs[0].strike - self.legs[1].strike)

            if self.product == 'call':
                self.analysis.sentiment = 'bearish'
            else:
                self.analysis.sentiment = 'bullish'

        return gain, loss


    def _validate(self):
        return len(self.legs) > 1
