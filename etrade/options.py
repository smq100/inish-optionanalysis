import json
import datetime as dt

import pandas as pd
from requests_oauthlib import OAuth1Session

import etrade.auth as auth
from utils import logger

_logger = logger.get_logger()

URL_CHAIN = '/v1/market/optionchains.json'
URL_EXPIRY = '/v1/market/optionexpiredate.json'


class Options:
    def __init__(self):
        if auth.Session is None:
            raise AssertionError('Etrade session not initialized')

        self.session: OAuth1Session = auth.Session
        self.message = ''
        self.raw = ''

    def expiry(self, symbol: str) -> pd.DataFrame:
        self.message = 'success'
        self.raw = ''
        expiry_data = {}

        url = f'{auth.base_url}{URL_EXPIRY}'
        params = {'symbol': f'{symbol}'}

        response = self.session.get(url, params=params)

        if response is not None and response.status_code == 200:
            expiry_data = json.loads(response.text)
            if expiry_data is not None and 'OptionExpireDateResponse' in expiry_data and 'ExpirationDate' in expiry_data['OptionExpireDateResponse']:
                self.raw = json.dumps(expiry_data, indent=2, sort_keys=True)
            else:
                self.message = 'E*TRADE API service error'
        else:
            _logger.debug(f'Response Body: {response.text}')
            self.message = f'Error: E*TRADE API service error: {response.text}'

        expiry_table = pd.DataFrame()
        if self.message == 'success':
            expiry_data = expiry_data['OptionExpireDateResponse']['ExpirationDate']
            data = [(dt.datetime(item['year'], item['month'], item['day'], 0, 0, 0), item['expiryType'].title()) for item in expiry_data]
            expiry_table = pd.DataFrame(data, columns=['date', 'expiryType'])

        return expiry_table

    def chain(self,
              ticker: str,
              expiry_month: int,
              expiry_year: int,
              strikes: int = 10,
              weekly: bool = False,
              otype: str = 'CALLPUT') -> pd.DataFrame:

        self.message = 'success'
        self.raw = ''
        chain_data = {}

        url = f'{auth.base_url}{URL_CHAIN}'
        params = {
            'chainType': f'{otype}',
            'noOfStrikes': f'{strikes}',
            'includeWeekly': f'{str(weekly)}',
            'expiryMonth': f'{expiry_month}',
            'expiryYear': f'{expiry_year}',
            'symbol': f'{ticker}'
        }

        response = self.session.get(url, params=params)

        if response is not None and response.status_code == 200:
            chain_data = json.loads(response.text)
            if chain_data is not None and 'OptionChainResponse' in chain_data and 'OptionPair' in chain_data['OptionChainResponse']:
                self.raw = json.dumps(chain_data, indent=2, sort_keys=True)
            else:
                self.message = 'E*TRADE API service error'
        else:
            _logger.debug(f'Response Body: {response.text}')
            self.message = f'Error: E*TRADE API service error: {response.text}'

        calls_table = pd.DataFrame()
        puts_table = pd.DataFrame()
        if self.message == 'success':
            data = chain_data['OptionChainResponse']['OptionPair']

            calls = [item['Call'] for item in data]
            calls_table = pd.DataFrame(calls)
            calls_table['type'] = 'call'

            puts = [item['Put'] for item in data]
            puts_table = pd.DataFrame(puts)
            puts_table['type'] = 'put'

            chain = pd.concat([calls_table, puts_table], axis=0)

            # E*Trade does not include impliedVolatility. Add for compatability with yfinance. This will force calculated volatility to be used
            chain['impliedVolatility'] = -1.0

        return chain


'''
Sample OptionChainResponse response

{
  "OptionChainResponse": {
    "OptionPair": [
      {
        "Call": {
          "OptionGreeks": {
            "currentValue": true,
            "delta": 0.6355,
            "gamma": 0.0345,
            "iv": 0.3988,
            "rho": 0.0383,
            "theta": -0.0754,
            "vega": 0.1051
          },
          "adjustedFlag": false,
          "ask": 6.2,
          "askSize": 43,
          "bid": 5.95,
          "bidSize": 461,
          "displaySymbol": "COP May 20 '22 $97 Call",
          "inTheMoney": "y",
          "lastPrice": 0.0,
          "netChange": 0.0,
          "openInterest": 0,
          "optionCategory": "STANDARD",
          "optionRootSymbol": "COP",
          "optionType": "CALL",
          "osiKey": "COP---220520C00097000",
          "quoteDetail": "https://api.etrade.com/v1/market/quote/COP:2022:5:20:CALL:97.000000.json",
          "strikePrice": 97.0,
          "symbol": "COP",
          "timeStamp": 1650561786,
          "volume": 0
        }
      },
      {
          "Put": ...
      }
    ]
  }
'''

'''
Sample OptionDateResponse response

{
  "OptionExpireDateResponse": {
    "ExpirationDate": [
      {
        "day": 22,
        "expiryType": "WEEKLY",
        "month": 4,
        "year": 2022
      },
      {
          ...
      }
    ]
  }
}
'''
