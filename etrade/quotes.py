import json

from requests_oauthlib import OAuth1Session

import etrade.auth as auth
from utils import logger

_logger = logger.get_logger()


class Quotes:
    def __init__(self):
        if auth.Session is None:
            raise AssertionError('Etrade session not initialized')

        self.session: OAuth1Session = auth.Session
        self.message = ''

    def quote(self, symbols: list[str]) -> list[dict]:
        self.message = 'success'
        quote_data = None

        url = f'{auth.base_url}/v1/market/quote/{",".join(symbols)}.json'
        params = {
            'detailFlag': ['ALL']
        }

        response = self.session.get(url, params=params)

        if response is not None and response.status_code == 200:
            quote_data = response.json()
            if 'QuoteResponse' in quote_data and 'QuoteData' in quote_data['QuoteResponse']:
                parsed = json.dumps(quote_data, indent=2, sort_keys=True)
                _logger.debug(f'{__name__}: {parsed}')
            elif 'QuoteResponse' in quote_data and 'Messages' in quote_data['QuoteResponse']:
                parsed = json.dumps(quote_data, indent=2, sort_keys=True)
                _logger.debug(f'{__name__}: {parsed}')
                self.message = quote_data['QuoteResponse']['Messages']['Message'][0]['description']
            else:
                self.message = 'E*TRADE API service error'
        else:
            _logger.debug(f'{__name__}: Response Body: {response}')
            self.message = f'E*TRADE API service error: {response}'

        data = []
        if self.message == 'success':
            data = quote_data['QuoteResponse']['QuoteData']

        return data


'''
Sample QuoteResponse

{
  "QuoteResponse": {
    "QuoteData": [
      {
        "All": {
          "ExtendedHourQuoteDetail": {
            "ask": 161.5,
            "askSize": 400,
            "bid": 161.37,
            "bidSize": 200,
            "change": -4.92,
            "lastPrice": 161.5,
            "percentChange": -2.96,
            "quoteStatus": "EH_CLOSED",
            "timeOfLastTrade": 1650671995,
            "timeZone": "",
            "volume": 84882424
          },
          "adjustedFlag": false,
          "ask": 161.5,
          "askSize": 400,
          "askTime": "19:59:55 EDT 04-22-2022",
          "averageVolume": 74353570,
          "beta": 1.21,
          "bid": 161.37,
          "bidExchange": " ",
          "bidSize": 200,
          "bidTime": "19:59:55 EDT 04-22-2022",
          "cashDeliverable": 0,
          "changeClose": -4.63,
          "changeClosePercentage": -2.78,
          "companyName": "APPLE INC COM",
          "contractSize": 0.0,
          "daysToExpiration": 0,
          "declaredDividend": 0.22,
          "dirLast": "2",
          "dividend": 0.22,
          "dividendPayableDate": 1644526643,
          "eps": 6.0233,
          "estEarnings": 6.167,
          "exDividendDate": 1644008243,
          "expirationDate": 0,
          "high": 167.8699,
          "high52": 182.94,
          "intrinsicValue": 0.0,
          "lastTrade": 161.79,
          "low": 161.5,
          "low52": 122.25,
          "marketCap": 2640322359390.0,
          "nextEarningDate": "",
          "open": 166.46,
          "openInterest": 0,
          "optionMultiplier": 0.0,
          "optionStyle": "",
          "optionUnderlier": "",
          "pe": 27.6296,
          "previousClose": 166.42,
          "previousDayVolume": 67866314,
          "primaryExchange": "NSDQ",
          "sharesOutstanding": 16319441000,
          "symbolDescription": "APPLE INC COM",
          "timeOfLastTrade": 1650657600,
          "timePremium": 0.0,
          "totalVolume": 84882424,
          "upc": 0,
          "week52HiDate": 1641329843,
          "week52LowDate": 1620849443,
          "yield": 0.5288
        },
        "Product": {
          "securityType": "EQ",
          "symbol": "AAPL"
        },
        "ahFlag": "true",
        "dateTime": "19:59:55 EDT 04-22-2022",
        "dateTimeUTC": 1650671995,
        "hasMiniOptions": false,
        "quoteStatus": "CLOSING"
      }
    ]
  }
}
'''
