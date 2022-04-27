import json

import pandas as pd
from requests_oauthlib import OAuth1Session

import etrade.auth as auth
from utils import logger

_logger = logger.get_logger()


class Lookup:
    def __init__(self):
        if auth.Session is None:
            raise AssertionError('Etrade session not initialized')

        self.session: OAuth1Session = auth.Session
        self.message = ''

    def lookup(self, symbol: str) -> pd.DataFrame:
        self.message = 'success'

        url = f'{auth.base_url}/v1/market/lookup/{symbol}.json'

        response = self.session.get(url)

        if response is not None and response.status_code == 200:
            alert_data = response.json()
            if alert_data is not None and 'LookupResponse' in alert_data and 'Data' in alert_data['LookupResponse']:
                parsed = json.dumps(alert_data, indent=2, sort_keys=True)
                _logger.debug(f'{__name__}: {parsed}')
            else:
                self.message = 'E*TRADE API service error'
        else:
            _logger.debug(f'{__name__}: Response Body: {response}')
            self.message = f'E*TRADE API service error: {response}'

        lookup_table = pd.DataFrame()
        if self.message == 'success':
            data = alert_data['LookupResponse']['Data']
            lookup_table = pd.DataFrame.from_dict(data)

        return lookup_table


'''
Sample LookupResponse

{
  "LookupResponse": {
    "Data": [
      {
        "description": "APPLE INC COM",
        "symbol": "AAPL",
        "type": "EQUITY"
      },
      {
        "description": "AAPL ALPHA IDX",
        "symbol": "AVSPY",
        "type": "INDEX"
      },
      {
        "description": "AAPL VS. SPY INDEX",
        "symbol": "AIX",
        "type": "INDEX"
      }
    ]
  }
}
'''
