import json

from requests_oauthlib import OAuth1Session
import pandas as pd

import etrade.auth as auth
from utils import logger

_logger = logger.get_logger()

URL_ACCTLIST = '/v1/accounts/list.json'


class Accounts:
    def __init__(self, session):
        if not auth.base_url:
            raise AssertionError('Etrade session not initialized')

        self.session: OAuth1Session = session
        self.accounts: list[pd.DataFrame] = []
        self.message = ''

    def list(self) -> pd.DataFrame:
        url = f'{auth.base_url}{URL_ACCTLIST}'
        response = self.session.get(url)
        self.message = 'success'

        if response is not None and response.status_code == 200:
            acct_data = response.json()
            if acct_data is not None and 'AccountListResponse' in acct_data and 'Accounts' in acct_data['AccountListResponse']:
                parsed = json.dumps(acct_data, indent=2, sort_keys=True)
                _logger.debug(f'{__name__}: {parsed}')
            else:
                self.message = 'E*TRADE API service error'
        else:
            _logger.debug(f'{__name__}: Response Body: {response.text}')
            self.message = f'Error: E*TRADE API service error: {response.text}'

        self.accounts = []
        if self.message == 'success':
            data = acct_data['AccountListResponse']['Accounts']['Account']
            self.accounts = pd.DataFrame.from_dict(data)

        return self.accounts

    def balance(self, account_index: int) -> dict:
        self.message = 'success'
        url = auth.base_url + '/v1/accounts/' + self.accounts.iloc[account_index]['accountIdKey'] + '/balance.json'
        params = {'instType': self.accounts.iloc[account_index]['institutionType'], 'realTimeNAV': 'true'}
        headers = {'consumerkey': auth.key}

        response = self.session.get(url, params=params, headers=headers)
        if response is not None and response.status_code == 200:
            acct_data = json.loads(response.text)
            parsed = json.dumps(acct_data, indent=2, sort_keys=True)
            _logger.debug(f'{__name__}: {parsed}')
        else:
            _logger.debug(f'{__name__}: Response Body: {response.text}')
            self.message = f'Error: E*TRADE API service error: {response.text}'

        balance_table = {}
        if self.message == 'success':
            balance_table = acct_data['BalanceResponse']

        return balance_table

    def portfolio(self, account_index: int) -> pd.DataFrame:
        self.message = 'success'
        url = auth.base_url + '/v1/accounts/' + self.accounts.iloc[account_index]['accountIdKey'] + '/portfolio.json'

        response = self.session.get(url)
        if response is not None and response.status_code == 200:
            portfolio_data = json.loads(response.text)
            parsed = json.dumps(portfolio_data, indent=2, sort_keys=True)
            _logger.debug(f'{__name__}: {parsed}')
        else:
            _logger.debug(f'{__name__}: Response Body: {response.text}')
            self.message = f'Error: E*TRADE API service error: {response.text}'

        portfolio_table = pd.DataFrame()
        if self.message == 'success':
            data = portfolio_data['PortfolioResponse']['AccountPortfolio'][0]['Position']
            portfolio_table = pd.DataFrame.from_dict(data)

        return portfolio_table


'''
Sample AccountListResponse

{
  "AccountListResponse": {
    "Accounts": {
      "Account": [
        {
          "accountDesc": "Trading",
          "accountId": "000",
          "accountIdKey": "000",
          "accountMode": "MARGIN",
          "accountName": "Trading",
          "accountStatus": "ACTIVE",
          "accountType": "INDIVIDUAL",
          "closedDate": 0,
          "institutionType": "BROKERAGE",
          "shareWorksAccount": false
        },
        {
            ...
        }
      ]
    }
  }
}
'''

'''
Sample BalanceResponse

{
  "BalanceResponse": {
    "Cash": {
      "fundsForOpenOrdersCash": 0,
      "moneyMktBalance": 0.0
    },
    "Computed": {
      "OpenCalls": {
        "cashCall": 0,
        "fedCall": 0,
        "houseCall": 0,
        "minEquityCall": 0
      },
      "RealTimeValues": {
        "netMv": 0.0,
        "netMvLong": 0.0,
        "netMvShort": 0.0,
        "totalAccountValue": 0.0
      },
      "accountBalance": 0.0,
      "cashAvailableForInvestment": 0.0,
      "cashAvailableForWithdrawal": 0.0,
      "cashBalance": 0,
      "cashBuyingPower": 0.0,
      "dtCashBuyingPower": 0,
      "dtMarginBuyingPower": 0,
      "fundsWithheldFromPurchasePower": 0,
      "fundsWithheldFromWithdrawal": 0,
      "marginBalance": 0,
      "marginBuyingPower": 0.0,
      "netCash": 0.0,
      "regtEquity": 0.0,
      "regtEquityPercent": 0,
      "settledCashForInvestment": 0,
      "shortAdjustBalance": 0,
      "totalAvailableForWithdrawal": 0.0,
      "unSettledCashForInvestment": 0
    },
    "accountDescription": "John Doe",
    "accountId": "0000000",
    "accountMode": "MARGIN",
    "accountType": "MARGIN",
    "dayTraderStatus": "NO_PDT",
    "optionLevel": "LEVEL_3",
    "quoteMode": 0
  }
}
'''

'''
Sample PortfolioResponse

{
  "PortfolioResponse": {
    "AccountPortfolio": [
      {
        "accountId": "83359700",
        "totalPages": 1
        "Position": [
          {
            "Product": {
              "expiryDay": 0,
              "expiryMonth": 0,
              "expiryYear": 0,
              "productId": {
                "symbol": "BR"
              },
              "securityType": "EQ",
              "strikePrice": 0,
              "symbol": "BR"
            },
            "Quick": {
              "change": -0.28,
              "changePct": -1.3346,
              "lastTrade": 20.7,
              "lastTradeTime": 1343160240,
              "volume": 431591
            },
            "commissions": 0,
            "costPerShare": 0,
            "dateAcquired": -57600000,
            "daysGain": -2.7999,
            "daysGainPct": -1.3346,
            "lotsDetails": "",
            "marketValue": 207,
            "otherFees": 0,
            "pctOfPortfolio": 0.0018,
            "positionId": 27005131,
            "positionIndicator": "TYPE2",
            "positionType": "LONG",
            "pricePaid": 0,
            "quantity": 10,
            "quoteDetails": "",
            "symbolDescription": "BR",
            "todayCommissions": 0,
            "todayFees": 0,
            "todayPricePaid": 0,
            "todayQuantity": 0,
            "totalCost": 0,
            "totalGain": 207,
            "totalGainPct": 0
          },
          {
              ...
          }
        ]
    }
}
'''
