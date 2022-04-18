import sys
import time
import math
import threading
import datetime as dt
import logging

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as clrs
import matplotlib.ticker as mticker
from tabulate import tabulate

import strategies as s
from strategies.strategy import Strategy
from strategies.call import Call
from strategies.put import Put
from strategies.vertical import Vertical
from strategies.iron_condor import IronCondor
from strategies.iron_butterfly import IronButterfly
from data import store
from utils import math as m
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface():
    def __init__(self,
        *,
        ticker: str,
        strategy: str,
        product: str,
        direction: str,
        strike: float = -1.0,
        width1: int = 0,
        width2: int = 0,
        quantity: int = 1,
        expiry: str = '',
        volatility: str = '-1.0',
        load_contracts: bool = False,
        analyze: bool = False,
        exit: bool = False):

        self.strategy: Strategy = None
        self.strategy_name: str = strategy
        self.load_contracts = load_contracts

        self.dirty_analyze = True
        self.task: threading.Thread = None

        pd.options.display.float_format = '{:,.2f}'.format

        # Set strike to closest ITM if strike < 0.0
        if direction == 'long':
            strike = strike if strike > 0.0 else float(math.floor(store.get_last_price(ticker)))
            if strike <= 0.0:
                strike = 0.50
        else:
            strike = strike if strike > 0.0 else float(math.ceil(store.get_last_price(ticker)))

        # Decode volatility
        proceed1 = True
        percent = False
        neg = False
        if '%' in volatility:
            if 'n' in volatility:
                neg = True

            volatility = volatility.replace('%', '')
            volatility = volatility.replace(' ', '')
            volatility = volatility.replace('N', '')
            volatility = volatility.replace('n', '')
            volatility = volatility.replace('P', '')
            volatility = volatility.replace('p', '')
            percent = True

        volatility = float(volatility) if not neg else -float(volatility)

        try:
            if not percent:
                volatility = (volatility, 0.0)
            elif self.load_contracts:
                volatility = (-1.0, volatility / 100.0)
            else:
                volatility = (0.0, volatility / 100.0)
        except ValueError:
            proceed1 = False
        else:
            self.expiry = expiry

        # Check if expiry date valid
        proceed2 = True
        if expiry:
            try:
                dt.datetime.strptime(expiry, ui.DATE_FORMAT)
            except ValueError:
                proceed2 = False

        if not proceed1:
            ui.print_error('Invalid volatility specified')
        elif not proceed2:
            ui.print_error('Invalid expiry date specified')
        elif not store.is_live_connection():
            ui.print_error('Internet connection required')
        elif not store.is_ticker(ticker):
            ui.print_error('Invalid ticker specified')
        elif strategy not in s.STRATEGIES:
            ui.print_error('Invalid strategy specified')
        elif direction not in s.DIRECTIONS:
            ui.print_error('Invalid direction specified')
        elif product not in s.PRODUCTS:
            ui.print_error('Invalid product specified')
        elif width1 < 0:
            ui.print_error('Invalid width specified')
        elif width2 < 0:
            ui.print_error('Invalid width specified')
        elif quantity < 1:
            ui.print_error('Invalid quantity specified')
        elif strategy == 'vert' and width1 < 1:
            ui.print_error('Invalid width specified')
        elif strategy == 'ic' and (width1 < 1 or width2 < 1):
            ui.print_error('Invalid width specified')
        elif strategy == 'ib' and width1 < 1:
            ui.print_error('Invalid width specified')
        else:
            if self.load_contracts:
                strike = float(math.floor(store.get_last_price(ticker)))
                width1 = width2 = 1
            else:
                sentiment = Strategy.calculate_sentiment(self.strategy_name, product, direction)
                strike, width1, width2 = m.calculate_strike_and_widths(self.strategy_name, sentiment, store.get_last_price(ticker))

            if self.load_strategy(
                ticker,
                self.strategy_name,
                product,
                direction,
                strike,
                width1,
                width2,
                quantity,
                expiry,
                volatility,
                load_contracts,
                analyze or exit):

                if not exit:
                    self.main_menu()
            else:
                ui.print_error('Problem loading strategy')

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': f'Change Symbol ({self.strategy.ticker})',
                '2': f'Change Strategy ({self.strategy})',
                '3': 'Select Option',
                '4': 'View Option Details',
                '5': 'View Value',
                '6': 'Analyze Stategy',
                '7': 'View Analysis',
                '8': 'Settings',
                '0': 'Exit'
            }

            loaded = '' if self.strategy.legs[0].option.price_last > 0 else '*'
            expire = f'{self.strategy.legs[0].option.expiry:%Y-%m-%d}'

            if self.strategy_name == s.STRATEGIES_BROAD[2]: # Vertical
                menu_items['3'] += f's ({expire}, '\
                    f'L:${self.strategy.legs[0].option.strike:.2f}{loaded}, '\
                    f'S:${self.strategy.legs[1].option.strike:.2f}{loaded})'
            elif self.strategy_name == s.STRATEGIES_BROAD[3]: # Iron Condor
                menu_items['3'] += f's ({expire}, '\
                    f'${self.strategy.legs[0].option.strike:.2f}{loaded}, '\
                    f'${self.strategy.legs[1].option.strike:.2f}{loaded}, '\
                    f'${self.strategy.legs[2].option.strike:.2f}{loaded}, '\
                    f'${self.strategy.legs[3].option.strike:.2f}{loaded})'
            else: # Call or Put
                menu_items['3'] += f' ({expire}, ${self.strategy.legs[0].option.strike:.2f}{loaded})'

            if self.dirty_analyze:
                menu_items['6'] += ' *'

            selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

            if selection == 1:
                self.select_ticker()
            elif selection == 2:
                self.select_strategy()
            elif selection == 3:
                self.select_chain()
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

    def load_strategy(self,
            ticker: str,
            strategy: str,
            product: str,
            direction: str,
            strike: float,
            width1: int,
            width2: int,
            quantity: int,
            expiry: str,
            volatility: tuple[float, float],
            load_contracts: bool = False,
            analyze: bool = False) -> bool:

        modified = True

        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if strategy not in s.STRATEGIES:
            raise ValueError('Invalid strategy')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if strike < 0.0:
            raise ValueError('Invalid strike')
        if width1 < 0:
            raise ValueError('Invalid width')
        if width2 < 0:
            raise ValueError('Invalid width')
        if quantity < 1:
            raise ValueError('Invalid quantity')
        if strategy == 'vert' and width1 < 1:
            raise ValueError(f'Invalid width specified: {width1}')
        if strategy == 'ic' and (width1 < 1 or width2 < 1):
            raise ValueError(f'Invalid width specified: {width1}, {width2}')
        if strategy == 'ib' and width1 < 1:
            raise ValueError(f'Invalid width specified: {width1}')

        expiry_dt = dt.datetime.strptime(expiry, ui.DATE_FORMAT) if expiry else None

        name = strategy.lower()
        try:
            if name == 'call':
                self.strategy_name = name
                self.strategy = Call(ticker, 'call', direction, strike, quantity=quantity,
                    expiry=expiry_dt, volatility=volatility, load_contracts=load_contracts)
            elif name == 'put':
                self.strategy_name = name
                self.strategy = Put(ticker, 'put', direction, strike, quantity=quantity,
                    expiry=expiry_dt, volatility=volatility, load_contracts=load_contracts)
            elif name == 'vert':
                self.strategy_name = name
                self.strategy = Vertical(ticker, product, direction, strike, width=width1, quantity=quantity,
                    expiry=expiry_dt, volatility=volatility, load_contracts=load_contracts)
            elif name == 'ic':
                self.strategy_name = name
                self.strategy = IronCondor(ticker, 'hybrid', direction, strike, width1=width1, width2=width2, quantity=quantity,
                    expiry=expiry_dt, volatility=volatility, load_contracts=load_contracts)
            elif name == 'ib':
                self.strategy_name = name
                self.strategy = IronButterfly(ticker, 'hybrid', direction, strike, width1=width1, quantity=quantity,
                    expiry=expiry_dt, volatility=volatility, load_contracts=load_contracts)
            else:
                modified = False
                ui.print_error('Unknown argument')
        except Exception as e:
            ui.print_error(f'{str(sys.exc_info()[1])}')
            modified = False

        if modified:
            self.dirty_analyze = True

            if analyze:
                modified = self.analyze()

        return modified

    def analyze(self) -> bool:
        valid = self.strategy.validate()
        if valid:
            self.task = threading.Thread(target=self.strategy.analyze)
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            self.dirty_analyze = False

            self.show_analysis(style=1)
            self.show_analysis(style=2)
        else:
            ui.print_error(self.strategy.error)

        return valid

    def reset(self) -> None:
        self.strategy.reset()

    def show_value(self, style: int = 0) -> None:
        if not self.dirty_analyze:
            if len(self.strategy.legs) > 1:
                leg = ui.input_integer('Enter Leg: ', 1, len(self.strategy.legs)) - 1
            else:
                leg = 0

            value = self.strategy.legs[leg].value_table * 100.0
            if value is not None:
                if style == 0:
                    style = ui.input_integer('(1) Table, (2) Chart, (3) Contour, (4) Surface, or (0) Cancel: ', 0, 4)
                if style > 0:
                    title = f'{self.strategy.legs[leg].description()}'
                    greeks = f'{self.strategy.legs[leg].description(greeks=True)}'

                    rows, cols = value.shape
                    rows = m.VALUETABLE_ROWS if rows > m.VALUETABLE_ROWS else -1
                    cols = m.VALUETABLE_COLS if cols > m.VALUETABLE_COLS else -1

                    if rows > 0 or cols > 0:
                        value = m.compress_table(value, rows, cols)

                    if style == 1:
                        headers = ['Price']
                        headers += value.columns.to_list()
                        ui.print_message(title)
                        ui.print_message(greeks, pre_creturn=0, post_creturn=1)
                        print(tabulate(value, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
                    elif style == 2:
                        self._show_chart(value, title, charttype='chart')
                    elif style == 3:
                        self._show_chart(value, title, charttype='contour')
                    elif style == 4:
                        self._show_chart(value, title, charttype='surface')
            else:
                ui.print_error('No tables calculated')
        else:
            ui.print_error('Please first perform calculation')

    def show_analysis(self, style: int = 0) -> None:
        if not self.dirty_analyze:
            analysis = self.strategy.analysis.profit_table * 100.0
            if analysis is not None:
                if style == 0:
                    style = ui.input_integer('(1) Summary, (2) Table, (3) Chart, (4) Contour, (5) Surface, or (0) Cancel: ', 0, 5)

                if style > 0:
                    rows, cols = analysis.shape
                    rows = m.VALUETABLE_ROWS if rows > m.VALUETABLE_ROWS else -1
                    cols = m.VALUETABLE_COLS if cols > m.VALUETABLE_COLS else -1

                    if rows > 0 or cols > 0:
                        analysis = m.compress_table(analysis, rows, cols)

                    expiry = analysis.columns[-1]
                    title = f'Profit Summary for {self.strategy.name.title()}: {self.strategy.ticker} ({expiry})'

                    if style == 1:
                        ui.print_message(title, pre_creturn=2)
                        print(self.strategy.analysis)
                        if self.strategy.legs[0].option.contract:
                            ui.print_message('Option Contracts', pre_creturn=0)
                            for leg in self.strategy.legs:
                                print(f'{leg.option.contract}')

                        self.show_legs()
                    elif style == 2:
                        headers = ['Price']
                        headers += analysis.columns.to_list()
                        ui.print_message(title, post_creturn=1)
                        print(tabulate(analysis, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
                        print()
                    elif style == 3:
                        self._show_chart(analysis, title, charttype='chart')
                    elif style == 4:
                        self._show_chart(analysis, title, charttype='contour')
                    elif style == 5:
                        self._show_chart(analysis, title, charttype='surface')
            else:
                ui.print_error('No tables calculated')
        else:
            ui.print_error('Please first perform analysis')

    def show_options(self) -> None:
        if len(self.strategy.legs) > 0:
            if len(self.strategy.legs) > 1:
                leg = ui.input_integer('Enter Leg (0=all): ', 0, 2) - 1
            else:
                leg = 0

            if leg < 0:
                ui.print_message('Leg 1 Option Metrics')
            else:
                ui.print_message(f'Leg {leg+1} Option Metrics')

            if leg < 0:
                print(f'{self.strategy.legs[0].option}')
                ui.print_message('Leg 2 Option Metrics')
                print(f'{self.strategy.legs[1].option}')
            else:
                print(f'{self.strategy.legs[leg].option}')
        else:
            print('No option legs configured')

    def show_legs(self, leg: int = -1, delimeter: bool = True) -> None:
        if delimeter:
            ui.print_message('Option Legs')

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
            ui.print_error('Invalid leg')

    def select_ticker(self) -> bool:
        valid = False
        modified = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if not valid:
                    ui.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

        if valid:
            volatility = (-1.0, 0.0)
            self.dirty_analyze = True
            modified = True
            expiry = None

            if self.load_contracts:
                strike = float(math.floor(store.get_last_price(ticker)))
                width1 = width2 = 1
            else:
                sentiment = Strategy.calculate_sentiment(self.strategy_name, self.strategy.product, self.strategy.direction)
                strike, width1, width2 = m.calculate_strike_and_widths(self.strategy_name, sentiment, store.get_last_price(ticker))

            self.load_strategy(ticker, self.strategy_name, self.strategy.product, self.strategy.direction, strike, width1, width2, self.strategy.quantity, expiry, volatility)

        return modified

    def select_strategy(self) -> bool:
        menu_items = {
            '1': 'Call',
            '2': 'Put',
            '3': 'Vertical',
            '4': 'Iron Condor',
            '5': 'Iron Butterfly',
            '0': 'Done/Cancel',
        }

        modified = False
        selection = ui.menu(menu_items, 'Select Strategy', 0, len(menu_items)-1)

        if selection > 0:
            self.load_contracts = False
            price = store.get_last_price(self.strategy.ticker)
            expiry = None
            volatility = (0.0, 0.0)

            if selection == 1:
                strategy = product = 'call'
                d = ui.input_integer('(1) Long, or (2) Short: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
                strike = ui.input_float_range(f'Enter strike ({price:.2f}): ', price, 20.0)
                modified = self.load_strategy(self.strategy.ticker, strategy, product, direction, strike, 0, 0, self.strategy.quantity, expiry, volatility)

            elif selection == 2:
                strategy = product = 'put'
                d = ui.input_integer('(1) Long, or (2) Short: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
                strike = ui.input_float_range(f'Enter strike ({price:.2f}): ', price, 20.0)
                modified = self.load_strategy(self.strategy.ticker, strategy, product, direction, strike, 0, 0, self.strategy.quantity, expiry, volatility)

            elif selection == 3:
                strategy = 'vert'
                p = ui.input_integer('(1) Call, or (2) Put: ', 1, 2)
                product = 'call' if p == 1 else 'put'
                d = ui.input_integer('(1) Debit, or (2) Credit: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
                strike = ui.input_float_range(f'Enter strike ({price:.2f}): ', price, 20.0)

                sentiment = Strategy.calculate_sentiment(strategy, product, direction)
                _, width1, _ = m.calculate_strike_and_widths(strategy, sentiment, store.get_last_price(self.strategy.ticker))

                modified = self.load_strategy(self.strategy.ticker, strategy, product, direction, strike, width1, 0, self.strategy.quantity, expiry, volatility)

            elif selection == 4:
                strategy = 'ic'
                product = 'hybrid'
                d = ui.input_integer('(1) Debit, or (2) Credit: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
                strike = ui.input_float_range(f'Enter strike ({price:.2f}): ', price, 20.0)

                sentiment = Strategy.calculate_sentiment(strategy, product, direction)
                _, width1, width2 = m.calculate_strike_and_widths(strategy, sentiment, store.get_last_price(self.strategy.ticker))

                modified = self.load_strategy(self.strategy.ticker, strategy, product, direction, strike, width1, width2, self.strategy.quantity, expiry, volatility)

            elif selection == 5:
                strategy = 'ib'
                product = 'hybrid'
                d = ui.input_integer('(1) Debit, or (2) Credit: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
                strike = ui.input_float_range(f'Enter strike ({price:.2f}): ', price, 20.0)

                sentiment = Strategy.calculate_sentiment(strategy, product, direction)
                _, width1, _ = m.calculate_strike_and_widths(strategy, sentiment, store.get_last_price(self.strategy.ticker))

                modified = self.load_strategy(self.strategy.ticker, strategy, product, direction, strike, width1, 0, self.strategy.quantity, expiry, volatility)

        return modified

    def select_chain(self) -> list[str]:
        contracts = []

        # Go directly to get expire date if not already entered
        if not self.strategy.chain.expire:
            exp = self.select_chain_expiry()
            self.strategy.update_expiry(exp)
            if self.strategy.name != 'vertical':
                # Go directly to choose option if only one leg in strategy
                if self.strategy.legs[0].option.product == 'call':
                    contracts = self.select_chain_options('call', 1)
                else:
                    contracts = self.select_chain_options('put', 1)

                if contracts:
                    self.strategy.legs[0].option.load_contract(contracts[0])
                    print()

        if not contracts:
            done = False
            while not done:
                expiry = self.strategy.chain.expire if self.strategy.chain.expire else 'None selected'
                width = 1
                quantity = 1
                success = True

                menu_items = {
                    '1': f'Select Expiry Date ({expiry.strftime((ui.DATE_FORMAT))})',
                    '2': f'Quantity ({self.strategy.quantity})',
                    '3': f'Width ({self.strategy.width1})',
                    '4': f'Select Option',
                    '0': 'Done'
                }

                loaded = '' if self.strategy.legs[0].option.price_last > 0 else '*'

                if self.strategy.name == 'vertical':
                    menu_items['4'] += f's '\
                        f'(L:${self.strategy.legs[0].option.strike:.2f}{loaded}'\
                        f' S:${self.strategy.legs[1].option.strike:.2f}{loaded})'
                else:
                    menu_items['4'] += f' (${self.strategy.legs[0].option.strike:.2f}{loaded})'

                selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

                if selection == 1:
                    exp = self.select_chain_expiry()
                    self.strategy.update_expiry(exp)
                elif selection == 2:
                    quantity = ui.input_integer('Enter quantity (1 - 10): ', 1, 10)
                elif selection == 3:
                    width = ui.input_integer('Enter width (1 - 5): ', 1, 5)
                elif selection == 4:
                    if self.strategy.chain.expire:
                        leg = 0
                        if self.strategy.legs[leg].option.product == 'call':
                            contracts = self.select_chain_options('call', width)
                        else:
                            contracts = self.select_chain_options('put', width)

                        if contracts:
                            for leg, contract in enumerate(contracts):
                                success = self.strategy.legs[leg].option.load_contract(contract)
                            done = True
                    else:
                        ui.print_error('Please first select expiry date')
                elif selection == 0:
                    done = True

                if not success:
                    ui.print_error('Error loading option. Please try again')

        return contracts

    def select_chain_expiry(self) -> dt.datetime:
        expiry = m.third_friday()
        dates = self.strategy.chain.get_expiry()

        menu_items = {}
        for i, exp in enumerate(dates):
            menu_items[f'{i+1}'] = f'{exp}'

        select = ui.menu(menu_items, 'Select expiration date, or 0 to cancel: ', 0, i+1)
        if select > 0:
            expiry = dt.datetime.strptime(dates[select-1], ui.DATE_FORMAT)
            self.strategy.chain.expire = expiry

            self.dirty_analyze = True

        return expiry

    def select_chain_options(self, product: str, width: int) -> list[str]:
        options = None
        contracts = []
        if not self.strategy.chain.expire:
            ui.print_error('No expiry date delected')
        elif product == 'call':
            options = self.strategy.chain.get_chain('call')
        elif product == 'put':
            options = self.strategy.chain.get_chain('put')

        if options is not None:
            menu_items = {}
            for i, row in enumerate(options.itertuples()):
                itm = 'ITM' if bool(row.inTheMoney) else 'OTM'
                menu_items[f'{i+1}'] = f'${row.strike:7.2f} ${row.lastPrice:6.2f} {itm}'

            prompt = 'Select long option, or 0 to cancel: ' if self.strategy.name == 'vertical' else 'Select option, or 0 to cancel: '
            select = ui.menu(menu_items, prompt, 0, i+1)
            if select > 0:
                select -= 1
                sel_row = options.iloc[select]
                contracts = [sel_row['contractSymbol']]  # First contract

                if width > 0:
                    if product == 'call':
                        if self.strategy.direction == 'long':
                            sel_row = options.iloc[select+width] if (select+width) < options.shape[0] else None
                        else:
                            sel_row = options.iloc[select-width] if (select-width) >= 0 else None
                    elif self.strategy.direction == 'long':
                        sel_row = options.iloc[select-width] if (select-width) >= 0 else None
                    else:
                        sel_row = options.iloc[select+width] if (select+width) < options.shape[0] else None

                    if sel_row is not None:
                        contracts += [sel_row['contractSymbol']]  # Second contract
                    else:
                        contracts = []

                self.dirty_analyze = True
        else:
            ui.print_error('Invalid selection')

        return contracts

    def select_settings(self) -> None:
        while True:
            menu_items = {
                '1': f'Pricing Method ({self.strategy.legs[0].pricing_method.title()})',
                '0': 'Done',
            }

            selection = ui.menu(menu_items, 'Select Setting', 0, len(menu_items)-1)

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
            selection = ui.menu(menu_items, 'Select Method', 0, len(menu_items)-1)

            if selection == 1:
                self.strategy.set_pricing_method('black-scholes')
                self.dirty_analyze = True
                break

            if selection == 2:
                self.strategy.set_pricing_method('monte-carlo')
                self.dirty_analyze = True
                break

            if selection == 0:
                break

            ui.print_error('Unknown method selected')

    def show_progress(self) -> None:
        ui.progress_bar(0, 0, prefix='Analyzing', suffix=self.strategy.ticker, reset=True)

        while self.task.is_alive():
            time.sleep(0.20)
            ui.progress_bar(0, 0, prefix='Analyzing', suffix=self.strategy.ticker)

    def _show_chart(self, table: str, title: str, charttype: str) -> None:
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
        major, minor = self._calculate_major_minor_ticks(height)
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
        if min_ < 0.0 and max_ > 0.0:
            norm = clrs.TwoSlopeNorm(0.0, vmin=min_, vmax=max_)
            cmap = clrs.LinearSegmentedColormap.from_list(name='analysis', colors=['red', 'lightgray', 'green'], N=15)
        elif min_ >= 0.0:
            norm = None
            cmap = clrs.LinearSegmentedColormap.from_list(name='value', colors=['lightgray', 'green'], N=15)
        elif max_ <= 0.0:
            norm = None
            cmap = clrs.LinearSegmentedColormap.from_list(name='value', colors=['red', 'lightgray'], N=15)
        else:
            norm = None
            cmap = clrs.LinearSegmentedColormap.from_list(name='value', colors=['lightgray', 'gray'], N=15)

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

        for breakeven in self.strategy.analysis.breakeven:
            ax.axhline(breakeven, color='k', linestyle='-', linewidth=0.5)

        plt.show()

    @staticmethod
    def _calculate_major_minor_ticks(width: int) -> tuple[float, float]:
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


def main():
    parser = argparse.ArgumentParser(description='Option Strategy Analyzer')
    parser.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='AAPL')
    parser.add_argument('-s', '--strategy', help='Load and analyze strategy', required=False, choices=['call', 'put', 'vert', 'ic', 'ib'], default='call')
    parser.add_argument('-d', '--direction', help='Specify the direction', required=False, choices=['long', 'short'], default='long')
    parser.add_argument('-p', '--product', help='Specify the product', required=False, choices=['call', 'put'], default='call')
    parser.add_argument('-k', '--strike', help='Specify the strike price', required=False, default='-1.0')
    parser.add_argument('-1', '--width1', help='Specify the inner width', required=False, default='1')
    parser.add_argument('-2', '--width2', help='Specify the outer width', required=False, default='1')
    parser.add_argument('-q', '--quantity', help='Specify the quantity', required=False, default='1')
    parser.add_argument('-e', '--expiry', help='Specify the expiry date (ex: "2022-03-29")', required=False, default='')
    parser.add_argument('-v', '--volatility', help='Specify the option volatility', required=False, default=-1.0)
    parser.add_argument('-f', '--default', help='Load the default options', required=False, action='store_true')
    parser.add_argument('-a', '--analyze', help='Analyze the strategy', required=False, action='store_true')
    parser.add_argument('-x', '--exit', help='Run and exit', required=False, action='store_true')

    command = vars(parser.parse_args())
    Interface(ticker=command['ticker'], strategy=command['strategy'], product=command['product'], direction=command['direction'],
        width1=int(command['width1']), width2=int(command['width2']), quantity=int(command['quantity']), load_contracts=command['default'],
        expiry=command['expiry'], analyze=command['analyze'], exit=command['exit'], strike=float(command['strike']), volatility=str(command['volatility']))


if __name__ == '__main__':
    main()
