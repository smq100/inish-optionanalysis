import logging

from analysis.scoring import ScoringAnalysis
from analysis.technical import Technical
from data import store as store
from utils import utils


logger = utils.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, ticker:str):
        ticker = ticker.upper()

        if store.is_ticker(ticker):
            self.technical = Technical(ticker, None, 365)
            self.scoring = ScoringAnalysis(ticker)

            self.calculate(True)
            self.main_menu()
        else:
            utils.print_error('Invalid ticker specified')

    def main_menu(self):
        while True:
            menu_items = {
                '1': f'Change Ticker ({self.scoring.ticker})',
                '2': 'Calculate',
                '0': 'Exit'
            }

            selection = utils.menu(menu_items, 'Select Operation', 0, 2)

            if selection == 1:
                self.select_ticker()
            elif selection == 2:
                self.calculate(True)
            elif selection == 0:
                break

    def select_ticker(self):
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.scoring = ScoringAnalysis(ticker)
                else:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def calculate(self, show=False):
        # EMA
        self.scoring.ema = {}
        df1 = self.technical.calc_ema(21)
        df2 = self.technical.calc_ema(50)
        df3 = self.technical.calc_ema(200)
        self.scoring.ema = {'21': df1, '50':df2, '200':df3}

        # RSA
        self.scoring.rsa = self.technical.calc_rsi()

        # VWAP
        self.scoring.vwap = self.technical.calc_vwap()

        # MACD
        self.scoring.macd = self.technical.calc_macd()

        # Bollinger Bands
        self.scoring.bb = self.technical.calc_bb()

        if show:
            utils.print_message(f"Yesterday's {self.scoring.ticker} Technicals")
            print(f'EMA 21:    {self.scoring.ema["21"].iloc[-1]:.2f}')
            print(f'EMA 50:    {self.scoring.ema["50"].iloc[-1]:.2f}')
            print(f'EMA 200:   {self.scoring.ema["200"].iloc[-1]:.2f}')
            print(f'RSA:       {self.scoring.rsa.iloc[-1]:.2f}')
            print(f'VWAP:      {self.scoring.vwap.iloc[-1]:.2f}')
            print(f'MACD Diff: {self.scoring.macd.iloc[-1]["Diff"]:.2f}')
            print(f'MACD:      {self.scoring.macd.iloc[-1]["MACD"]:.2f}')
            print(f'MACD Sig:  {self.scoring.macd.iloc[-1]["Signal"]:.2f}')
            print(f'MACD Diff: {self.scoring.bb.iloc[-1]["High"]:.2f}')
            print(f'MACD:      {self.scoring.bb.iloc[-1]["Mid"]:.2f}')
            print(f'MACD Sig:  {self.scoring.bb.iloc[-1]["Low"]:.2f}')


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Scoring')
    parser.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='IBM')

    command = vars(parser.parse_args())

    if 'ticker' in command.keys():
        Interface(command['ticker'])
    else:
        Interface('IBM')
