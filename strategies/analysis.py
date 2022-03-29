from dataclasses import dataclass, field
import pandas as pd


@dataclass
class Analysis:
    ticker: str = ''
    table: pd.DataFrame = pd.DataFrame()
    summary: pd.DataFrame = pd.DataFrame()
    credit_debit: str = ''
    sentiment: str = ''
    total: float = 0.0
    max_gain: float = 0.0
    max_loss: float = 0.0
    gain: str = ''
    loss: str = ''
    upside: float = 0.0
    pop: float = 0.0
    volatility: str = 'calculated'
    breakeven: list[float] = field(default_factory=list)

    def __str__(self):
        if not self.table.empty:
            output = \
                f'Type:       {self.credit_debit.title()}\n'\
                f'Sentiment:  {self.sentiment.title()}\n'\
                f'Total:      ${abs(self.total*100):.2f} {self.credit_debit}\n'\
                f'Max Gain:   {self.gain}\n'\
                f'Max Loss:   {self.loss}\n'\
                f'Return:     {self.upside * 100.0:.2f}%\n'\
                f'POP:        {self.pop * 100.0:.2f}%\n'\
                f'Volatility: {self.volatility}\n'

            for breakeven in self.breakeven:
                output += f'Breakeven:  ${breakeven:.2f} at expiry\n'
        else:
            output = 'Not yet analyzed\n'

        return output

    def summarize(self) -> pd.DataFrame:
        if not self.table.empty:
            self.gain = 'Unlimited' if self.max_gain < 0.0 else f'${self.max_gain*100:.2f}'
            self.loss = 'Unlimited' if self.max_loss < 0.0 else f'${self.max_loss*100:.2f}'

            data = {
                'credit_debit': self.credit_debit,
                'sentiment': self.sentiment,
                'total': self.total*100,
                'max_gain': self.max_gain*100 if self.max_gain >= 0.0 else 'unlimited',
                'max_loss': self.max_loss*100 if self.max_loss >= 0.0 else 'unlimited',
                'return': self.upside if self.upside >= 0.0 else 'unlimited',
                'pop': self.pop,
                'volatility': self.volatility,
            }

            if len(self.breakeven) > 1:
                data['breakeven1'] = self.breakeven[0]
                data['breakeven2'] = self.breakeven[1]
            else:
                data['breakeven'] = self.breakeven[0]

            self.summary = pd.DataFrame(data, index=[self.ticker])
