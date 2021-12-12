import json

from utils import ui

_logger = ui.get_logger()


class Quotes:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def quotes(self, symbols):
        # Make API call for GET request
        url = f'{self.base_url}/v1/market/quote/{symbols}.json'
        response = self.session.get(url)

        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'QuoteResponse' in data and 'QuoteData' in data['QuoteResponse']:
                ui.print_message('Quotes')
                for quote in data['QuoteResponse']['QuoteData']:
                    if quote is not None:
                        if 'dateTime' in quote:
                            print(f'Date Time: {quote["dateTime"]}')
                        if 'Product' in quote and 'symbol' in quote['Product']:
                            print(f'Symbol: {quote["Product"]["symbol"]}')
                        if 'Product' in quote and 'securityType' in quote['Product']:
                            print(
                                f'Security Type: {quote["Product"]["securityType"]}')
                        if 'All' in quote:
                            if 'lastTrade' in quote['All']:
                                print(
                                    f'Last Price: {quote["All"]["lastTrade"]}')
                            if 'changeClose' in quote['All'] and 'changeClosePercentage' in quote['All']:
                                print(
                                    f"Today's Change: {quote['All']['changeClose']:,.3f} ({quote['All']['changeClosePercentage']}%)")
                            if 'open' in quote['All']:
                                print(f'Open: {quote["All"]["open"]:,.2f}')
                            if 'previousClose' in quote['All']:
                                print(
                                    f'Previous Close: {quote["All"]["previousClose"]:,.2f}')
                            if 'bid' in quote['All'] and 'bidSize' in quote['All']:
                                print(
                                    f'Bid (Size): {quote["All"]["bid"]:,.2f} x{quote["All"]["bidSize"]}')
                            if 'ask' in quote['All'] and 'askSize' in quote['All']:
                                print(
                                    f'Ask (Size): {quote["All"]["ask"]:,.2f} x{quote["All"]["askSize"]}')
                            if 'low' in quote['All'] and 'high' in quote['All']:
                                print(
                                    f"Day's Range: {quote['All']['low']} - {quote['All']['high']}")
                            if 'totalVolume' in quote['All']:
                                print(
                                    f'Volume: {quote["All"]["totalVolume"]:,}')
                    print()
            else:
                if data is not None and 'QuoteResponse' in data \
                        and 'Messages' in data['QuoteResponse'] \
                        and 'Message' in data['QuoteResponse']['Messages'] \
                        and data['QuoteResponse']['Messages']['Message'] is not None:

                    ui.print_error('Error')
                    for error_message in data['QuoteResponse']['Messages']['Message']:
                        print('Error: ' + error_message['description'])
                    print()
                else:
                    print('Error: Quote API service error')
        elif response is not None and response.status_code == 400:
            _logger.debug(f'Response: {response.text}')
            data = json.loads(response.text)

            ui.print_error('Error')
            print(
                f'\nError ({data["Error"]["code"]}): {data["Error"]["message"]}')
            print()
        else:
            _logger.debug(f'Response: {response.text}')
            print('\nError: E*TRADE API service error')
