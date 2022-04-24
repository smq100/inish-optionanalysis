import datetime as dt
import logging

import pandas as pd
from requests_oauthlib import OAuth1Session
from tabulate import tabulate

import etrade.auth as auth
from etrade.accounts import Accounts
from etrade.quotes import Quotes
from etrade.options import Options
from etrade.lookup import Lookup
from etrade.alerts import Alerts
from utils import math as m
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Client:
    def __init__(self):
        self.session: OAuth1Session | None = None
        self.accounts = None
        self.account_index = -1
        self.account_name = ''

        if self.session is None:
            self.session = auth.authorize()

        if self.session is not None:
            self.main_menu()
        else:
            ui.print_error('Invalid authorizaton text')

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': 'Accounts',
                '2': 'Balance',
                '3': 'Portfolio',
                '4': 'Orders',
                '5': 'Alerts',
                '6': 'Quotes',
                '7': 'Options Expiry',
                '8': 'Options Chain',
                '9': 'Lookup Symbol',
                '0': 'Exit'
            }

            if self.account_name:
                menu_items['1'] += f' ({self.account_name})'

            selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)
            if selection == 1:
                self.show_accounts()
            elif selection == 2:
                self.show_balance()
            elif selection == 3:
                self.show_portfolio()
            elif selection == 4:
                self.show_orders()
            elif selection == 5:
                self.show_alerts()
            elif selection == 6:
                self.show_quotes()
            elif selection == 7:
                self.show_options_expiry()
            elif selection == 8:
                self.show_options_chain()
            elif selection == 9:
                self.show_symbol()
            elif selection == 0:
                break
            else:
                print('Unknown operation selected')

    def show_accounts(self) -> None:
        self.accounts = Accounts(self.session)
        acct_table = self.accounts.list()

        if self.accounts.message == 'success':
            menu_items = {str(acct.Index+1): f'{acct.accountId} {acct.accountDesc}' for acct in acct_table.itertuples()}
            menu_items['0'] = 'Cancel'

            selection = ui.menu(menu_items, 'Select Accounts', 0, len(menu_items)-1)
            if selection > 0:
                self.account_index = selection - 1
                self.account_name = menu_items[str(selection-1)]
            else:
                self.account_index = -1
                self.account_name = ''
        else:
            self.accounts = None

    def show_balance(self) -> None:
        if self.account_index >= 0:
            balance = self.accounts.balance(self.account_index)

            if balance:
                ui.print_message(f'Balance for {balance["accountId"]}')
                if 'accountDescription' in balance:
                    print(f'Account Nickname: {balance["accountDescription"]}')
                if 'accountType' in balance:
                    print(f'Account Type: {balance["accountType"]}')
                if 'Computed' in balance \
                        and 'RealTimeValues' in balance['Computed'] \
                        and 'totalAccountValue' in balance['Computed']['RealTimeValues']:
                    print(f'Net Account Value: ${balance["Computed"]["RealTimeValues"]["totalAccountValue"]:,.2f}')
                if 'Computed' in balance \
                        and 'marginBuyingPower' in balance['Computed']:
                    print(f'Margin Buying Power: ${balance["Computed"]["marginBuyingPower"]:,.2f}')
                if 'Computed' in balance \
                        and 'cashBuyingPower' in balance['Computed']:
                    print(f'Cash Buying Power: ${balance["Computed"]["cashBuyingPower"]:,.2f}')
                if 'accountDescription' in balance:
                    print(f'Option Level: {balance["optionLevel"]}')
            else:
                ui.print_error(self.accounts.message)
        else:
            ui.print_error('Must first select an account')

    def show_portfolio(self) -> None:
        if self.account_index >= 0:
            portfolio = self.accounts.portfolio(self.account_index)

            if not portfolio.empty:
                ui.print_message('Portfolio')
                for position in portfolio.itertuples():
                    print_str = ''
                    if position.symbolDescription:
                        print_str += f'{str(position.symbolDescription):<5}'
                    if position.quantity:
                        print_str += f'Q={position.quantity:<3}'
                    if position.Quick and 'lastTrade' in position.Quick:
                        print_str += f' Price={position.Quick["lastTrade"]:,.02f}'
                    if position.pricePaid:
                        print_str += f' Paid={position.pricePaid:,.02f}'
                    if position.totalGain:
                        print_str += f' Gain={position.totalGain:,.02f}'
                    if position.marketValue:
                        print_str += f' Value={position.marketValue:,.02f}'

                    print(print_str)
            else:
                ui.print_error(self.accounts.message)
        else:
            ui.print_error('Must first select an account')

    def show_alerts(self):
        alerts = Alerts(self.session)
        alert_data = alerts.alerts()

        if alert_data:
            alert = ''
            ui.print_message('Alerts')
            print(alert_data)
        else:
            ui.print_message(alerts.message)

    def show_symbol(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()
        lookup = Lookup(self.session)
        message, lookup_data = lookup.lookup(symbol)

        if lookup_data is not None:
            out = ''
            ui.print_message(f'Security information for {symbol}')
            for item in lookup_data['LookupResponse']['Data']:
                if item is not None and 'symbol' in item:
                    out += f'Symbol: {item["symbol"]}'
                if item is not None and 'type' in item:
                    out += f', Type: {item["type"]}'
                if item is not None and 'description' in item:
                    out += f', Desc: {item["description"]}'
                print(out)
        else:
            ui.print_error(message)

    def show_quotes(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()
        quotes = Quotes(self.session)
        message, quote_data = quotes.quote(symbol)

        if quote_data is not None:
            ui.print_message('Quotes')
            for quote in quote_data['QuoteResponse']['QuoteData']:
                if quote is not None:
                    if 'dateTime' in quote:
                        print(f'Date Time: {quote["dateTime"]}')
                    if 'Product' in quote and 'symbol' in quote['Product']:
                        print(f'Symbol: {quote["Product"]["symbol"]}')
                    if 'Product' in quote and 'securityType' in quote['Product']:
                        print(f'Security Type: {quote["Product"]["securityType"]}')
                    if 'All' in quote:
                        if 'lastTrade' in quote['All']:
                            print(f'Last Price: {quote["All"]["lastTrade"]}')
                        if 'changeClose' in quote['All'] and 'changeClosePercentage' in quote['All']:
                            print(f"Today's Change: {quote['All']['changeClose']:,.3f} ({quote['All']['changeClosePercentage']}%)")
                        if 'open' in quote['All']:
                            print(f'Open: {quote["All"]["open"]:,.2f}')
                        if 'previousClose' in quote['All']:
                            print(f'Previous Close: {quote["All"]["previousClose"]:,.2f}')
                        if 'bid' in quote['All'] and 'bidSize' in quote['All']:
                            print(f'Bid (Size): {quote["All"]["bid"]:,.2f} x{quote["All"]["bidSize"]}')
                        if 'ask' in quote['All'] and 'askSize' in quote['All']:
                            print(f'Ask (Size): {quote["All"]["ask"]:,.2f} x{quote["All"]["askSize"]}')
                        if 'low' in quote['All'] and 'high' in quote['All']:
                            print(f"Day's Range: {quote['All']['low']} - {quote['All']['high']}")
                        if 'totalVolume' in quote['All']:
                            print(f'Volume: {quote["All"]["totalVolume"]:,}')
        else:
            ui.print_error(message)

    def show_options_chain(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()

        date = m.third_friday()
        options = Options(self.session)
        chain_calls, chain_puts = options.chain(symbol, date.month, date.year)

        if 'error' in options.message.lower():
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif chain_calls is None:
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif chain_puts is None:
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        else:
            drop = [
                'OptionGreeks',
                'adjustedFlag',
                'ask',
                'askSize',
                'bid',
                'bidSize',
                'displaySymbol',
                # 'inTheMoney',
                # 'lastPrice',
                'netChange',
                'openInterest',
                'optionCategory',
                'optionRootSymbol',
                'optionType',
                'osiKey',
                'quoteDetail',
                # 'strikePrice',
                # 'symbol',
                'timeStamp',
                # 'volume'
            ]

            order = [
                'symbol',
                'strikePrice',
                'lastPrice',
                'inTheMoney',
                'volume'
            ]

            ui.print_message('Options Call Chain', post_creturn=1)
            chain_calls.drop(drop, axis=1, inplace=True)
            chain_calls = chain_calls.reindex(columns=order)
            print(tabulate(chain_calls, headers=chain_calls.columns, tablefmt=ui.TABULATE_FORMAT, floatfmt='.02f'))

            ui.print_message('Options Put Chain', post_creturn=1)
            chain_puts.drop(drop, axis=1, inplace=True)
            chain_puts = chain_puts.reindex(columns=order)
            print(tabulate(chain_puts, headers=chain_puts.columns, tablefmt=ui.TABULATE_FORMAT, floatfmt='.02f'))

    def show_options_expiry(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()

        options = Options(self.session)
        expiry_data = options.expiry(symbol)

        if 'error' in options.message.lower():
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif expiry_data.empty:
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        else:
            ui.print_message('Options Chain', post_creturn=1)
            expiry_data['date'] = pd.to_datetime(expiry_data['date']).dt.strftime(ui.DATE_FORMAT)
            print(tabulate(expiry_data, headers=expiry_data.columns, tablefmt=ui.TABULATE_FORMAT))

    def show_orders(self) -> None:
        if self.account_index >= 0:
            ui.print_error('TODO')
        else:
            ui.print_error('Must first select an account')

def main():
    Client()

if __name__ == '__main__':
    main()
