import json

from requests_oauthlib import OAuth1Session

import etrade.auth.auth as auth
from utils import logger

_logger = logger.get_logger()


class Options:
    def __init__(self, session):
        if not auth.base_url:
            raise AssertionError('Etrade session not initialized')

        self.session: OAuth1Session = session


    def chain(self,
              symbol: str,
              expiry_month: int,
              expiry_year: int,
              strikes: int = 10,
              weekly: bool = False,
              otype: str = 'CALLPUT') -> tuple[str, dict]:

        message = 'success'
        url = auth.base_url + '/v1/market/optionchains.json'
        params = {
            'chainType': f'{otype}',
            'noOfStrikes': f'{strikes}',
            'includeWeekly': f'{str(weekly)}',
            'expiryMonth': f'{expiry_month}',
            'expiryYear': f'{expiry_year}',
            'symbol': f'{symbol}'
        }
        chain_data = None

        response = self.session.get(url, params=params)
        if response is not None and response.status_code == 200:
            chain_data = json.loads(response.text)
            parsed = json.dumps(chain_data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if chain_data is not None and 'OptionChainResponse' in chain_data and 'OptionPair' in chain_data['OptionChainResponse']:
                pass
            else:
                message = 'Chain error'
        elif response is not None and response.status_code == 400:
            _logger.debug(f'Response Body: {response}')
            chain_data = json.loads(response.text)
            message = f'\nError ({chain_data["Error"]["code"]}): {chain_data["Error"]["message"]}'
        else:
            _logger.debug(f'Response Body: {response}')
            message = 'E*TRADE API service error'

        return message, chain_data

'''
Sample response

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
          "Put" here
      }
    ]
  }
'''