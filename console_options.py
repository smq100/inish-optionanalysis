import sys
import math
import time
import threading
import logging
import datetime as dt

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as clrs
import matplotlib.ticker as mticker

import strategies
from strategies.strategy import Strategy
from strategies.vertical import Vertical
from strategies.call import Call
from strategies.put import Put
from options.chain import Chain
from data import store as store
from utils import utils

MAX_ROWS = 50
MAX_COLS = 18

_logger = utils.get_logger(logging.WARNING, logfile='')


class Interface():
    def __init__(self, ticker:str, strategy:str, direction:str, width:int=0, quantity:int=1, analyze:bool=False):
        self.ticker = ticker.upper()
        self.width = width
        self.quantity = quantity
        self.strategy:Strategy = None
        self.chain:Chain = None
        self.dirty_calculate = True
        self.dirty_analyze = True
        self.task:threading.Thread = None

        pd.options.display.float_format = '{:,.2f}'.format

        if not store.is_live_connection():
            utils.print_error('Internet connection required')
        elif not store.is_ticker(ticker):
            utils.print_error('Invalid ticker specified')
        elif strategy not in strategies.STRATEGIES:
            utils.print_error('Invalid strategy specified')
        elif direction not in strategies.DIRECTIONS:
            utils.print_error('Invalid direction specified')
        elif width < 0:
            utils.print_error('Invalid width specified')
        elif quantity < 1:
            utils.print_error('Invalid quantity specified')
        elif strategy == 'vertp' and width < 1:
            utils.print_error('Invalid width specified')
        elif strategy == 'vertc' and width < 1:
            utils.print_error('Invalid width specified')
        else:
            self.chain = Chain(self.ticker)

            if self.load_strategy(self.ticker, strategy, direction, self.width, self.quantity, analyze):
                self.main_menu()
            else:
                utils.print_error('Problem loading strategy')

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': f'Change Symbol ({self.strategy.ticker})',
                '2': f'Change Strategy ({self.strategy})',
                '3': 'Select Options',
                '4': 'View Option Details',
                '5': 'View Value',
                '6': 'Analyze Stategy',
                '7': 'View Analysis',
                '8': 'Settings',
                '0': 'Exit'
            }

            loaded = '' if  self.strategy.legs[0].option.last_price > 0 else '*'

            if self.strategy.name == 'vertical':
                menu_items['3'] += f' '\
                    f'(L:${self.strategy.legs[0].option.strike:.2f}{loaded}'\
                    f' S:${self.strategy.legs[1].option.strike:.2f}{loaded})'
            else:
                menu_items['3'] += f' (${self.strategy.legs[0].option.strike:.2f}{loaded})'

            if self.dirty_analyze:
                menu_items['6'] += ' *'

            self.show_legs()

            selection = utils.menu(menu_items, 'Select Operation', 0, 8)

            if selection == 1:
                if self.select_ticker():
                    if self.calculate():
                        self.analyze()
            elif selection == 2:
                if self.select_strategy():
                    if self.calculate():
                        self.analyze()
            elif selection == 3:
                if self.select_chain():
                    if self.calculate():
                        self.analyze()
            elif selection == 4:
                self.show_options()
            elif selection == 5:
                self.show_value()
            elif selection == 6:
                self.analyze()
            elif selection == 7:
                self.show_analysis()
            elif selection == 8:
                self.select_settings()
            elif selection == 0:
                break

    def show_value(self, val:int=0) -> None:
        if not self.dirty_calculate:
            if len(self.strategy.legs) > 1:
                leg = utils.input_integer('Enter Leg: ', 1, 2) - 1
            else:
                leg = 0

            table_ = self.strategy.legs[leg].table
            if table_ is not None:
                if val == 0:
                    val = utils.input_integer('(1) Table, (2) Chart, (3) Contour, (4) Surface, or (0) Cancel: ', 0, 4)
                if val > 0:
                        title = f'Value: {self.strategy.legs[leg].company}'
                        rows, cols = table_.shape

                        if rows > MAX_ROWS:
                            rows = MAX_ROWS
                        else:
                            rows = -1

                        if cols > MAX_COLS:
                            cols = MAX_COLS
                        else:
                            cols = -1

                        if rows > 0 or cols > 0:
                            # compress the table rows and columns
                            table_ = self._compress_table(table_, rows, cols)

                        if val == 1:
                            utils.print_message(title, 2)
                            print(table_)
                        elif val == 2:
                            self._show_chart(table_, title, charttype='chart')
                        elif val == 3:
                            self._show_chart(table_, title, charttype='contour')
                        elif val == 4:
                            self._show_chart(table_, title, charttype='surface')
            else:
                utils.print_error('No tables calculated')
        else:
            utils.print_error('Please first perform calculation')

    def show_analysis(self, val:int=0) -> None:
        if not self.dirty_analyze:
            table_ = self.strategy.analysis.table
            if table_ is not None:
                if val == 0:
                    val = utils.input_integer('(1) Summary, (2) Table, (3) Chart, (4) Contour, (5) Surface, or (0) Cancel: ', 0, 5)
                if val > 0:
                    title = f'Analysis: {self.strategy.ticker} ({self.strategy.legs[0].company}) {str(self.strategy).title()}'

                    rows, cols = table_.shape
                    if rows > MAX_ROWS:
                        rows = MAX_ROWS
                    else:
                        rows = -1

                    if cols > MAX_COLS:
                        cols = MAX_COLS
                    else:
                        cols = -1

                    if rows > 0 or cols > 0:
                        table_ = self._compress_table(table_, rows, cols)

                    if val == 1:
                        utils.print_message(title)
                        print(self.strategy.analysis)
                    elif val == 2:
                        utils.print_message(title)
                        print(table_)
                    elif val == 3:
                        self._show_chart(table_, title, charttype='chart')
                    elif val == 4:
                        self._show_chart(table_, title, charttype='contour')
                    elif val == 5:
                        self._show_chart(table_, title, charttype='surface')
            else:
                utils.print_error('No tables calculated')
        else:
            utils.print_error('Please first perform analysis')

    def show_options(self) -> None:
        if len(self.strategy.legs) > 0:
            if len(self.strategy.legs) > 1:
                leg = utils.input_integer('Enter Leg (0=all): ', 0, 2) - 1
            else:
                leg = 0

            if leg < 0:
                utils.print_message('Leg 1 Option Metrics')
            else:
                utils.print_message(f'Leg {leg+1} Option Metrics')

            if leg < 0:
                print(f'{self.strategy.legs[0].option}')
                utils.print_message('Leg 2 Option Metrics')
                print(f'{self.strategy.legs[1].option}')
            else:
                print(f'{self.strategy.legs[leg].option}')
        else:
            print('No option legs configured')

    def show_legs(self, leg:int=-1, delimeter:bool=True) -> None:
        if delimeter:
            utils.print_message('Option Leg Values')

        if len(self.strategy.legs) < 1:
            print('No legs configured')
        elif leg < 0:
            for index in range(len(self.strategy.legs)):
                # Recursive call to output each leg
                self.show_legs(index, False)
        elif leg < len(self.strategy.legs):
            output = f'{leg+1}: {self.strategy.legs[leg]}'
            print(output)
        else:
            utils.print_error('Invalid leg')

    def calculate(self) -> bool:
        try:
            self.strategy.calculate()
            self.dirty_calculate = False
            return True
        except Exception as e:
            return False

    def analyze(self) -> None:
        errors = self.strategy.get_errors()
        if not errors:
            self.task = threading.Thread(target=self.strategy.analyze)
            self.task.start()

            self._show_progress()

            self.dirty_calculate = False
            self.dirty_analyze = False

            self.show_analysis(val=1)
        else:
            utils.print_error(errors)

    def reset(self) -> None:
        self.strategy.reset()

    def select_ticker(self) -> bool:
        valid = False
        modified = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if not valid:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

        if valid:
            self.ticker = ticker
            self.dirty_calculate = True
            self.dirty_analyze = True
            modified = True

            self.chain = Chain(ticker)
            self.load_strategy(ticker, 'call', 'long', 1, analyze=True)
            utils.print_message('The strategy has been reset to a long call', False)

        return modified

    def select_strategy(self) -> bool:
        menu_items = {
            '1': 'Call',
            '2': 'Put',
            '3': 'Vertical',
            '0': 'Done/Cancel',
        }

        modified = True
        selection = utils.menu(menu_items, 'Select Strategy', 0, 3)

        if selection == 1:
            d = utils.input_integer('(1) Long, or (2) short: ', 1, 2)
            direction = 'long' if d == 1 else 'short'
            self.width = 0
            self.load_strategy(self.strategy.ticker, 'call', direction, self.width, self.quantity, analyze=False)
        elif selection == 2:
            d = utils.input_integer('(1) Long, or (2) short: ', 1, 2)
            direction = 'long' if d == 1 else 'short'
            self.width = 0
            self.load_strategy(self.strategy.ticker, 'put', direction, self.width, self.quantity, analyze=False)
        elif selection == 3:
            p = utils.input_integer('(1) Call, or (2) Put: ', 1, 2)
            product = 'call' if p == 1 else 'put'
            d = utils.input_integer('(1) Debit, or (2) credit: ', 1, 2)
            direction = 'long' if d == 1 else 'short'
            if product == 'call':
                self.load_strategy(self.strategy.ticker, 'vertc', direction, self.width, self.quantity, analyze=False)
            else:
                self.load_strategy(self.strategy.ticker, 'vertp', direction, self.width, self.quantity, analyze=False)
        else:
            modified = False

        return modified

    def select_chain(self) -> list[str]:
        contracts = []

        # Go directly to get expire date if not already entered
        if not self.chain.expire:
            exp = self.select_chain_expiry()
            self.strategy.update_expiry(exp)
            if self.strategy.name != 'vertical':
                # Go directly to choose option if only one leg in strategy
                if self.strategy.legs[0].option.product == 'call':
                    contracts = self.select_chain_options('call')
                else:
                    contracts = self.select_chain_options('put')

                if contracts:
                    self.strategy.legs[0].option.load_contract(contracts[0])

        if not contracts:
            done = False
            while not done:
                expiry = self.chain.expire if self.chain.expire else 'None selected'
                product = 'Call' if self.strategy.legs[0].option.product == 'call' else 'Put'

                menu_items = {
                    '1': f'Select Expiry Date ({expiry})',
                    '2': f'Quantity ({self.quantity})',
                    '3': f'Select {product} Option',
                    '0': 'Done'
                }

                loaded = '' if  self.strategy.legs[0].option.last_price > 0 else '*'

                if self.strategy.name == 'vertical':
                    menu_items['3'] = f'Select {product} Option'
                    menu_items['3'] += f' '\
                        f'(L:${self.strategy.legs[0].option.strike:.2f}{loaded}'\
                        f' S:${self.strategy.legs[1].option.strike:.2f}{loaded})'
                else:
                    menu_items['3'] += f' (${self.strategy.legs[0].option.strike:.2f}{loaded})'

                selection = utils.menu(menu_items, 'Select Operation', 0, 3)

                success = True
                if selection == 1:
                    exp = self.select_chain_expiry()
                    self.strategy.update_expiry(exp)
                elif selection == 2:
                    self.quantity = utils.input_integer('Enter quantity (1 - 10): ', 1, 10)
                elif selection == 3:
                    if self.chain.expire:
                        leg = 0
                        if self.strategy.legs[leg].option.product == 'call':
                            contracts = self.select_chain_options('call')
                        else:
                            contracts = self.select_chain_options('put')

                        if contracts:
                            for leg, contract in enumerate(contracts):
                                success = self.strategy.legs[leg].option.load_contract(contract)
                        else:
                            utils.print_error('No option selected')

                    else:
                        utils.print_error('Please first select expiry date')
                elif selection == 0:
                    done = True

                if not success:
                    utils.print_error('Error loading option. Please try again')

        return contracts

    def select_chain_expiry(self) -> str:
        expiry = self.chain.get_expiry()

        menu_items = {}
        for i, exp in enumerate(expiry):
            menu_items[f'{i+1}'] = f'{exp}'

        select = utils.menu(menu_items, 'Select expiration date, or 0 to cancel: ', 0, i+1)
        if select > 0:
            self.chain.expire = expiry[select-1]
            expiry = dt.datetime.strptime(self.chain.expire, '%Y-%m-%d')

            self.dirty_calculate = True
            self.dirty_analyze = True
        else:
            expiry = None

        return expiry

    def select_chain_options(self, product:str) -> list[str]:
        options = None
        contracts = []
        if not self.chain.expire:
            utils.print_error('No expiry date delected')
        elif product == 'call':
            options = self.chain.get_chain('call')
        elif product == 'put':
            options = self.chain.get_chain('put')

        if options is not None:
            menu_items = {}
            for i, row in options.iterrows():
                itm = 'ITM' if bool(row["inTheMoney"]) else 'OTM'
                menu_items[f'{i+1}'] = f'${row["strike"]:7.2f} ${row["lastPrice"]:6.2f} {itm}'

            select = utils.menu(menu_items, 'Select option, or 0 to cancel: ', 0, i+1)
            if select > 0:
                select -= 1
                sel_row = options.iloc[select]
                contracts = [sel_row['contractSymbol']] # First contract

                if self.width > 0:
                    if product == 'call':
                        if self.strategy.legs[1].direction == 'long':
                            sel_row = options.iloc[select-1] if select > 1 else None # long call (debit)
                        else:
                            sel_row = options.iloc[select+1] if select < options.shape[0] else None # short call (credit)
                    elif self.strategy.legs[1].direction == 'long':
                        sel_row = options.iloc[select-1] if select < options.shape[0] else None # long put (debit)
                    else:
                        sel_row = options.iloc[select+1] if select > 1 else None # short put (credit)

                    if sel_row is not None:
                        contracts += [sel_row['contractSymbol']] # Second contract

                self.dirty_calculate = True
                self.dirty_analyze = True
        else:
            utils.print_error('Invalid selection')

        return contracts

    def select_settings(self) -> None:
        while True:
            menu_items = {
                '1': f'Pricing Method ({self.strategy.legs[0].pricing_method.title()})',
                '0': 'Done',
            }

            selection = utils.menu(menu_items, 'Select Setting', 0, 1)

            if selection == 1:
                self.select_method()
            elif selection == 0:
                break

    def select_method(self) -> None:
        menu_items = {
            '1': 'Black-Scholes',
            '2': 'Monte Carlo',
            '0': 'Cancel',
        }

        modified = True
        while True:
            selection = utils.menu(menu_items, 'Select Method', 0, 2)

            if selection == 1:
                self.strategy.set_pricing_method('black-scholes')
                self.dirty_calculate = True
                self.dirty_analyze = True
                break

            if selection == 2:
                self.strategy.set_pricing_method('monte-carlo')
                self.dirty_calculate = True
                self.dirty_analyze = True
                break

            if selection == 0:
                break

            utils.print_error('Unknown method selected')

    def load_strategy(self, ticker:str, strategy:str, direction:str, width:int, quantity:int, analyze:bool=False) -> bool:
        modified = True

        if strategy not in strategies.STRATEGIES:
            raise ValueError('Invalid strategy')
        if direction not in strategies.DIRECTIONS:
            raise ValueError('Invalid direction')
        if quantity < 1:
            raise ValueError('Invalid quantity')
        if strategy == 'vertp' and width < 1:
            raise ValueError('Invalid width specified')
        if strategy == 'vertc' and width < 1:
            raise ValueError('Invalid width specified')

        self.ticker = ticker.upper()
        self.width = width
        self.quantity = quantity

        try:
            if strategy.lower() == 'call':
                self.width = 0
                self.strategy = Call(ticker, 'call', direction, self.width, self.quantity)
            elif strategy.lower() == 'put':
                self.width = 0
                self.strategy = Put(ticker, 'put', direction, self.width, self.quantity)
            elif strategy.lower() == 'vertc':
                self.strategy = Vertical(ticker, 'call', direction, self.width, self.quantity)
            elif strategy.lower() == 'vertp':
                self.strategy = Vertical(ticker, 'put', direction, self.width, self.quantity)
            else:
                modified = False
                utils.print_error('Unknown argument')
        except Exception as e:
            utils.print_error(str(sys.exc_info()[1]))
            modified = False

        if modified:
            self.dirty_calculate = True
            self.dirty_analyze = True

            if analyze:
                self.analyze()

        return modified

    def _show_progress(self) -> None:
        print()
        utils.progress_bar(0, 0, prefix='Analyzing', suffix=self.ticker, reset=True)

        while self.task.is_alive():
            time.sleep(0.20)
            utils.progress_bar(0, 0, prefix='Analyzing', suffix=self.ticker)

        print()

    def _show_chart(self, table:str, title:str, charttype:str) -> None:
        if not isinstance(table, pd.DataFrame):
            raise ValueError("'table' must be a Pandas DataFrame")

        if charttype == 'surface':
            dim = 3
        else:
            dim = 2

        fig = plt.figure(figsize=(8, 8))

        if dim == 3:
            ax = fig.add_subplot(111, projection='3d')
        else:
            ax = fig.add_subplot(111)

        plt.style.use('seaborn')
        plt.title(title)

        # X Axis
        ax.xaxis.tick_top()
        ax.set_xticks(range(len(table.columns)))
        ax.set_xticklabels(table.columns.tolist())
        ax.xaxis.set_major_locator(mticker.MultipleLocator(1))

        # Y Axis
        ax.yaxis.set_major_formatter('${x:.2f}')
        height = table.index[0] - table.index[-1]
        major, minor = self._calc_major_minor_ticks(height)
        if major > 0:
            ax.yaxis.set_major_locator(mticker.MultipleLocator(major))
        if minor > 0:
            ax.yaxis.set_minor_locator(mticker.MultipleLocator(minor))

        ax.set_xlabel('Date')
        if dim == 2:
            ax.set_ylabel('Value')
        else:
            ax.set_ylabel('Price')
            ax.set_zlabel('Value')

        # Color distributions
        min_ = min(table.min())
        max_ = max(table.max())
        if min_ < 0.0:
            norm = clrs.TwoSlopeNorm(0.0, vmin=min_, vmax=max_)
            cmap = clrs.LinearSegmentedColormap.from_list(name='analysis', colors =['red', 'lightgray', 'green'], N=15)
        else:
            norm=None
            cmap = clrs.LinearSegmentedColormap.from_list(name='value', colors =['lightgray', 'green'], N=15)

        # Data
        table.columns = range(len(table.columns))
        x = table.columns
        y = table.index
        X, Y = np.meshgrid(x, y)
        Z = table

        # Plot
        if charttype == 'chart':
            ax.scatter(X, Y, c=Z, norm=norm, marker='s', cmap=cmap)
        elif charttype == 'contour':
            ax.contourf(X, Y, Z, norm=norm, cmap=cmap)
        elif charttype == 'surface':
            ax.plot_surface(X, Y, Z, norm=norm, cmap=cmap)
        else:
            raise ValueError('Bad chart type')

        breakeven = self.strategy.analysis.breakeven
        ax.axhline(breakeven, color='k', linestyle='-', linewidth=0.5)

        plt.show()

    @staticmethod
    def _compress_table(table:pd.DataFrame, rows:int, cols:int) -> pd.DataFrame:
        if not isinstance(table, pd.DataFrame):
            raise ValueError("'table' must be a Pandas DataFrame")
        else:
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

    @staticmethod
    def _calc_major_minor_ticks(width:int) -> tuple[float, float]:
        if width <= 0.0:
            major = 0.0
            minor = 0.0
        elif width > 1000:
            major = 100.0
            minor = 20.0
        elif width > 500:
            major = 50.0
            minor = 10.0
        elif width > 100:
            major = 10.0
            minor = 2.0
        elif width > 40:
            major = 5.0
            minor = 1.0
        elif width > 20:
            major = 2.0
            minor = 0.0
        elif width > 10:
            major = 1.0
            minor = 0.0
        elif width > 1:
            major = 0.5
            minor = 0.0
        else:
            major = 0.1
            minor = 0.0

        return major, minor


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Option Strategy Analyzer')
    parser.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='AAPL')
    parser.add_argument('-s', '--strategy', help='Load and analyze strategy', required=False, choices=['call', 'put', 'vertc', 'vertp'], default='call')
    parser.add_argument('-d', '--direction', help='Specify the direction', required=False, choices=['long', 'short'], default='long')
    parser.add_argument('-w', '--width', help='Specify the width (used for spreads)', required=False, default='0')
    parser.add_argument('-q', '--quantity', help='Specify the quantity', required=False, default='1')
    parser.add_argument('-a', '--analyze', help='Analyze the strategy', required=False, action='store_true')

    command = vars(parser.parse_args())
    Interface(ticker=command['ticker'], strategy=command['strategy'], direction=command['direction'],
        width=int(command['width']), quantity=int(command['quantity']), analyze=command['analyze'])
