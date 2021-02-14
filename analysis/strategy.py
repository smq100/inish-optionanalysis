'''TODO'''

import math

import pandas as pd


class StrategyAnalysis:
    '''TODO'''

    def __init__(self):
        self.table = None
        self.credit_debit = ''
        self.sentiment = ''
        self.amount = 0.0
        self.max_gain = 0.0
        self.max_loss = 0.0
        self.breakeven = 0.0


    def __str__(self):
        if self.table is not None:
            if self.max_gain >= 0.0:
                gain = f'${self.max_gain:.2f}'
            else:
                gain = 'Unlimited'

            if self.max_loss >= 0.0:
                loss = f'${self.max_loss:.2f}'
            else:
                loss = 'Unlimited'

            output = '\n'\
                f'Type:      {self.credit_debit.title()}\n'\
                f'Sentiment: {self.sentiment.title()}\n'\
                f'Amount:    ${abs(self.amount):.2f} {self.credit_debit}\n'\
                f'Max Gain:  {gain}\n'\
                f'Max Loss:  {loss}\n'\
                f'Breakeven: ${self.breakeven:.2f} at expiry\n'
        else:
            output = 'Not yet analyzed'

        return output


    def compress_table(self, rows, cols):
        ''' TODO '''

        if self.table is not None:
            table = self.table
            srows, scols = table.shape

            if cols > 0 and cols < scols:
                # thin out cols
                step = int(math.ceil(scols/cols))
                end = table[table.columns[-2::]]        # Save the last two cols
                table = table[table.columns[:-2:step]]  # Thin the table (less the last two cols)
                table = pd.concat([table, end], axis=1) # Add back the last two cols

            if rows > 0 and rows < srows:
                # Thin out rows
                step = int(math.ceil(srows/rows))
                table = table.iloc[::step]

        return table
