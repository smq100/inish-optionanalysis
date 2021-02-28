import pandas as pd
from utils import utils as u

logger = u.get_logger()

class StrategyAnalysis:
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
