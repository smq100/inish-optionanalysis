import sys, os, json
import logging
import datetime

from analysis.scoring import ScoringAnalysis
from analysis.technical import Technical
from analysis.trend import SupportResistance, Line
from company import fetcher as f
from utils import utils as u


logger = u.get_logger(logging.WARNING)


class Interface:
    def __init__(self, ticker, script=''):
        ticker = ticker.upper()

        # Initialize data fetcher
        f.initialize()

        if f.validate_ticker(ticker):
            start = datetime.datetime.today() - datetime.timedelta(days=365)
            self.technical = Technical(ticker, start=start)
            self.scoring = ScoringAnalysis(ticker)

            if script:
                if os.path.exists(script):
                    try:
                        with open(script) as file_:
                            data = json.load(file_)
                            print(data)
                    except Exception as e:
                        u.print_error('File read error')
                else:
                    u.print_error(f'File "{script}" not found')
            else:
                self.calculate(True)
                self.main_menu()
        else:
            u.print_error('Invalid ticker symbol specified')

    def main_menu(self):
        while True:
            menu_items = {
                '1': f'Change Symbol ({self.scoring.ticker})',
                '2': 'Calculate',
                '0': 'Exit'
            }

            selection = u.menu(menu_items, 'Select Operation', 0, 2)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.calculate(True)
            elif selection == 0:
                break

    def select_symbol(self):
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = f.validate_ticker(ticker)
                if valid:
                    start = datetime.datetime.today() - datetime.timedelta(days=365)
                    self.scoring = ScoringAnalysis(ticker)
                else:
                    u.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
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
            print(u.delimeter(f"Yesterday's {self.scoring.ticker} Technicals", True))
            print(f'EMA 21:    {self.scoring.ema["21"][-1]:.2f}')
            print(f'EMA 50:    {self.scoring.ema["50"][-1]:.2f}')
            print(f'EMA 200:   {self.scoring.ema["200"][-1]:.2f}')
            print(f'RSA:       {self.scoring.rsa[-1]:.2f}')
            print(f'VWAP:      {self.scoring.vwap[-1]:.2f}')
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
    subparser = parser.add_subparsers(help='Specify the desired command')

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Load an operation')
    parser_a.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='IBM')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Execute a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='script.json')

    command = vars(parser.parse_args())

    if 'script' in command.keys():
        Interface('IBM', script=command['script'])
    elif 'ticker' in command.keys():
        Interface(command['ticker'])
    else:
        Interface('IBM')
