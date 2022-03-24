import pandas as pd


class Analysis:
    def __init__(self, ticker: str):
        if not ticker:
            raise ValueError('Invalid ticker')

        self.ticker = ticker.upper()
        self.table = pd.DataFrame()
        self.summary = pd.DataFrame()
        self.credit_debit = ''
        self.sentiment = ''
        self.total = 0.0
        self.max_gain = 0.0
        self.max_loss = 0.0
        self.gain = ''
        self.loss = ''
        self.upside = 0.0
        self.breakeven = [0.0]

    def __str__(self):
        if not self.table.empty:
            output = \
                f'Type:      {self.credit_debit.title()}\n'\
                f'Sentiment: {self.sentiment.title()}\n'\
                f'Total:     ${abs(self.total):.2f} {self.credit_debit}\n'\
                f'Max Gain:  {self.gain}\n'\
                f'Max Loss:  {self.loss}\n'\
                f'Return:    {self.upside*100:.2f}%\n'

            for breakeven in self.breakeven:
                output += f'Breakeven: ${breakeven:.2f} at expiry\n'
        else:
            output = 'Not yet analyzed'

        return output

    def summarize(self):
        if not self.table.empty:
            self.gain = 'Unlimited' if self.max_gain < 0.0 else f'${self.max_gain:.2f}'
            self.loss = 'Unlimited' if self.max_loss < 0.0 else f'${self.max_loss:.2f}'

            data = {
                'credit_debit': self.credit_debit,
                'sentiment': self.sentiment,
                'total': self.total,
                'max_gain': self.max_gain,
                'max_loss': self.max_loss,
                'return': self.upside,
                'breakeven1': self.breakeven[0],
                'breakeven2': self.breakeven[1] if len(self.breakeven) > 1 else 0.0
            }

            self.summary = pd.DataFrame(data, index=[self.ticker])
