import pandas as pd


class Analysis:
    table: pd.DataFrame = None
    summary: pd.DataFrame = None
    credit_debit = ''
    sentiment = ''
    amount = 0.0
    max_gain = 0.0
    max_loss = 0.0
    breakeven = 0.0
    upside = 0.0
    gain = ''
    loss = ''

    def __init__(self, ticker: str):
        if not ticker:
            raise ValueError('Invalid ticker')

        self.ticker = ticker.upper()

    def __str__(self):
        if self.table is not None:
            output = \
                f'Type:      {self.credit_debit.title()}\n'\
                f'Sentiment: {self.sentiment.title()}\n'\
                f'Amount:    ${abs(self.amount):.2f} {self.credit_debit}\n'\
                f'Max Gain:  {self.gain}\n'\
                f'Max Loss:  {self.loss}\n'\
                f'Breakeven: ${self.breakeven:.2f} at expiry\n'\
                f'Upside:    {self.upside:.2f}\n'
        else:
            output = 'Not yet analyzed'

        return output

    def summarize(self):
        if self.table is not None:
            self.gain = 'Unlimited' if self.max_gain < 0.0 else f'${self.max_gain:.2f}'
            self.loss = 'Unlimited' if self.max_loss < 0.0 else f'${self.max_loss:.2f}'

            data = {
                'credit_debit': self.credit_debit,
                'sentiment': self.sentiment,
                'amount': self.amount,
                'max_gain': self.max_gain,
                'max_loss': self.max_loss,
                'breakeven': self.breakeven,
                'upside': self.upside,
                'gain': self.gain,
                'loss': self.loss
            }
            self.summary = pd.DataFrame(data, index=[self.ticker])
