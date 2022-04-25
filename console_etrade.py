import datetime as dt
import logging
import webbrowser

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


def _callback(url: str) -> str:
    webbrowser.open(url)
    code = ui.input_alphanum('Please accept agreement and enter text code from browser: ')
    return code


class Client:
    def __init__(self):
        self.session: OAuth1Session | None = None
        self.accounts = None
        self.account_index = -1
        self.account_name = ''

        if self.session is None:
            self.session = auth.authorize(_callback)

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
                '4': 'Alerts',
                '5': 'Quotes',
                '6': 'Options Expiry',
                '7': 'Options Chain',
                '8': 'Lookup Symbol',
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
                self.show_alerts()
            elif selection == 5:
                self.show_quotes()
            elif selection == 6:
                self.show_options_expiry()
            elif selection == 7:
                self.show_options_chain()
            elif selection == 8:
                self.show_symbol()
            elif selection == 0:
                break
            else:
                print('Unknown operation selected')

    def show_accounts(self) -> None:
        self.accounts = Accounts(self.session)
        acct_table = self.accounts.list()

        if self.accounts.message == 'success':
            menu_items = {str(acct.Index+1): f'{acct.accountDesc} ({acct.accountId})' for acct in acct_table.itertuples()}
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
                ui.print_message(f'Balance for {balance["accountId"]}', pre_creturn=1, post_creturn=1)
                print(f'Account Nickname: {balance.get("accountDescription", "")}')
                print(f'Account Type: {balance.get("accountType", 0.0)}')
                print(f'Net Account Value: ${balance.get("Computed", {}).get("RealTimeValues", {}).get("totalAccountValue", 0.0):,.2f}')
                print(f'Margin Buying Power: ${balance.get("Computed", {}).get("marginBuyingPower", 0.0):,.2f}')
                print(f'Cash Buying Power: ${balance.get("Computed", {}).get("cashBuyingPower"):,.2f}')
                print(f'Option Level: {balance.get("optionLevel", "error")}')
            else:
                ui.print_error(self.accounts.message)
        else:
            ui.print_error('Must first select an account')

    def show_portfolio(self) -> None:
        if self.account_index >= 0:
            portfolio = self.accounts.portfolio(self.account_index)

            if not portfolio.empty:
                ui.print_message('Portfolio', pre_creturn=1, post_creturn=1)
                for position in portfolio.itertuples():
                    print(f'{str(position.symbolDescription)}')
                    print(f'Qty={position.quantity}')
                    print(f'Price={position.Quick["lastTrade"]:,.02f}')
                    print(f'Paid={position.pricePaid:,.02f}')
                    print(f'Gain={position.totalGain:,.02f}')
                    print(f'Value={position.marketValue:,.02f}')
                    print()
            else:
                ui.print_error(self.accounts.message)
        else:
            ui.print_error('Must first select an account')

    def show_alerts(self):
        alerts = Alerts(self.session)
        alert_data = alerts.alerts()

        if not alert_data.empty:
            ui.print_message('Alerts', pre_creturn=1, post_creturn=1)
            for item in alert_data.itertuples():
                if item:
                    alert = f'ID: {item.id}'
                    timestamp = dt.datetime.fromtimestamp(item.createTime).strftime('%Y-%m-%d %H:%M:%S')
                    alert += f', Time: {timestamp}'
                    alert += f', Subject: {item.subject}'
                    alert += f', Status: {item.status}'

                print(alert)
        else:
            ui.print_message(alerts.message)

    def show_symbol(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()
        lookup = Lookup(self.session)
        lookup_data = lookup.lookup(symbol)

        if not lookup_data.empty:
            ui.print_message(f'Security information for {symbol}', pre_creturn=1, post_creturn=1)
            for item in lookup_data.itertuples():
                if item:
                    print(f'Symbol: {item.symbol}')
                    print(f'Type: {item.type}')
                    print(f'Desc: {item.description}')

                print()
        else:
            ui.print_error(f'No information for {symbol} located')

    def show_quotes(self) -> None:
        quotes = Quotes(self.session)
        symbols = ui.input_list('Please enter symbols separated with commas: ').upper()
        quote_data = quotes.quote(symbols.split(','))

        if quotes.message == 'success':
            ui.print_message('Quotes', pre_creturn=1, post_creturn=1)
            for quote in quote_data:
                if quote is not None:
                    print(f'Date Time: {quote.get("dateTime", "")}')
                    print(f'Symbol: {quote.get("Product", "").get("symbol", "")}')
                    print(f'Security Type: {quote.get("Product", {}).get("securityType", "")}')
                    if 'All' in quote:
                        all = quote["All"]
                        print(f'Last Price: {all.get("lastTrade", "")}')
                        print(f'Today\'s Change: {all.get("changeClose", 0.0):,.3f}) ({all.get("changeClosePercentage", 0.0)}%)')
                        print(f'Open: {all.get("open", 0.0):,.2f}')
                        print(f'Previous Close: {all.get("previousClose", 0.0):,.2f}')
                        print(f'Bid (Size): {all.get("bid", 0.0):,.2f}x{all.get("bidSize")}')
                        print(f'Ask (Size): {all.get("ask", 0.0):,.2f}x{all.get("askSize")}')
                        print(f'Day\'s Range: {all.get("low", 0.0):,.2f} - {all.get("high", 0.0):,.2f}')
                        print(f'Volume: {all.get("totalVolume"):,}')
                    print()
        else:
            ui.print_error(quotes.message)

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


def main():
    Client()


if __name__ == '__main__':
    main()
