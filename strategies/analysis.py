from dataclasses import dataclass, field
import pandas as pd


@dataclass(order=True)
class Analysis:
    ticker: str = ''
    table: pd.DataFrame = pd.DataFrame()
    summary: pd.DataFrame = pd.DataFrame()
    credit_debit: str = ''
    sentiment: str = ''
    total: float = 0.0
    max_gain: float = 0.0
    max_loss: float = 0.0
    upside: float = 0.0
    pop: float = 0.0
    score_options: float = -1.0
    score_screen: float = -1.0
    breakeven: list[float] = field(default_factory=list)

    def __post_init__(self):
         self.sort_index = self.score_options

    def __str__(self):
        if not self.table.empty:
            gain = 'Unlimited' if self.max_gain < 0.0 else f'${self.max_gain*100:.2f}'
            loss = 'Unlimited' if self.max_loss < 0.0 else f'${self.max_loss*100:.2f}'
            return_text = f'{self.upside * 100.0:.2f}%' if self.upside >= 0.0 else 'Unlimited'
            output = \
                f'Type:             {self.credit_debit.title()}\n'\
                f'Sentiment:        {self.sentiment.title()}\n'\
                f'Total:            {abs(self.total*100.0):.2f} {self.credit_debit}\n'\
                f'Max Gain:         {gain}\n'\
                f'Max Loss:         {loss}\n'\
                f'Return:           {return_text}\n'\
                f'POP:              {self.pop*100.0:.2f}%\n'\
                f'Score Options:    {self.score_options:.2f}\n'\
                f'Score Screen:     {self.score_screen:.2f}\n'
        else:
            output = 'Not yet analyzed\n'

        return output

    def summarize(self) -> pd.DataFrame:
        if not self.table.empty:
            data = {
                'credit_debit': self.credit_debit,
                'sentiment': self.sentiment,
                'total': self.total*100,
                'max_gain': self.max_gain*100.0 if self.max_gain >= 0.0 else 'unlimited',
                'max_loss': self.max_loss*100.0 if self.max_loss >= 0.0 else 'unlimited',
                'return': self.upside if self.upside >= 0.0 else 'unlimited',
                'pop': self.pop,
                'score_option': self.score_options,
                'score_screen': self.score_screen
            }


            self.summary = pd.DataFrame(data, index=[self.ticker])
