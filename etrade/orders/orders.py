import json
import configparser
import random
import re

from utils import ui

_logger = ui.get_logger()

config = configparser.ConfigParser()
config.read('etrade/config.ini')

class Orders:
    def __init__(self, session, account, base_url):
        self.session = session
        self.account = account
        self.base_url = base_url

    def preview(self):
        # User's order selection
        order = self.user_select()

        # Assemble PUT request
        url = self.base_url + '/v1/accounts/' + \
            self.account['accountIdKey'] + '/orders/preview.json'
        headers = {'Content-Type': 'application/xml',
                   'consumerKey': config['DEFAULT']['CONSUMER_KEY']}
        payload = f'''<PreviewOrderRequest>
                       <orderType>EQ</orderType>
                       <clientOrderId>{order['client_order_id']}</clientOrderId>
                       <Order>
                           <allOrNone>false</allOrNone>
                           <priceType>{order['price_type']}</priceType>
                           <orderTerm>{order['order_term']}</orderTerm>
                           <marketSession>REGULAR</marketSession>
                           <stopPrice></stopPrice>
                           <limitPrice>{order['limit_price']}</limitPrice>
                           <Instrument>
                               <Product>
                                   <securityType>EQ</securityType>
                                   <symbol>{order['symbol']}</symbol>
                               </Product>
                               <orderAction>{order['order_action']}</orderAction>
                               <quantityType>QUANTITY</quantityType>
                               <quantity>{order['quantity']}</quantity>
                           </Instrument>
                       </Order>
                   </PreviewOrderRequest>'''
        response = self.session.post(url, headers=headers, data=payload)

        # Handle and parse response
        if response is not None and response.status_code == 200:
            data = response.json()
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            print('\nPreview Order:')

            if data is not None and 'PreviewOrderResponse' in data and 'PreviewIds' in data['PreviewOrderResponse']:
                for previewids in data['PreviewOrderResponse']['PreviewIds']:
                    print(f'Preview ID: {previewids["previewId"]}')
            else:
                # Handle errors
                data = response.json()
                if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                    print('Error: ' + data['Error']['message'])
                else:
                    print('Error: Preview Order API service error')

            if data is not None and 'PreviewOrderResponse' in data and 'Order' in data['PreviewOrderResponse']:
                for orders in data['PreviewOrderResponse']['Order']:
                    order['limitPrice'] = orders['limitPrice']

                    if orders is not None and 'Instrument' in orders:
                        for instrument in orders['Instrument']:
                            if instrument is not None and 'orderAction' in instrument:
                                print(f'Action: {instrument["orderAction"]}')
                            if instrument is not None and 'quantity' in instrument:
                                print(f'Quantity: {instrument["quantity"]}')
                            if instrument is not None and 'Product' in instrument \
                                    and 'symbol' in instrument['Product']:
                                print(
                                    f'Symbol: {instrument["Product"]["symbol"]}')
                            if instrument is not None and 'symbolDescription' in instrument:
                                print(
                                    f'Description: {instrument["symbolDescription"]}')

                    if orders is not None and 'priceType' in orders and 'limitPrice' in orders:
                        print(f'Price Type: {orders["priceType"]}')
                        if orders['priceType'] == 'MARKET':
                            print('Price: MKT')
                        else:
                            print(f'Price: {orders["limitPrice"]}')
                    if orders is not None and 'orderTerm' in orders:
                        print(f'Duration: {orders["orderTerm"]}')
                    if orders is not None and 'estimatedCommission' in orders:
                        print(
                            f'Estimated Commission: {orders["estimatedCommission"]}')
                    if orders is not None and 'estimatedTotalAmount' in orders:
                        print(
                            f'Estimated Total Cost: {orders["estimatedTotalAmount"]}')
            else:
                # Handle errors
                data = response.json()
                if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                    print('Error: ' + data['Error']['message'])
                else:
                    print('Error: Preview Order API service error')
        else:
            # Handle errors
            data = response.json()
            if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                print('Error: ' + data['Error']['message'])
            else:
                print('Error: Preview Order API service error')

    def previous(self, session, account, prev_orders):
        # Display previous instruments for user selection
        if prev_orders is not None:
            while True:
                count = 1
                for order in prev_orders:
                    print(str(count) + f')\tOrder Action: {order["order_action"]}, '
                          + f'Security Type: {order["security_type"]}, '
                          + f'Term: {order["order_term"]}, '
                          + f'Quantity: {order["quantity"]}, '
                          + f'Symbol: {order["symbol"]}, '
                          + f'Price Type: {order["price_type"]}')
                    count = count + 1
                print(str(count) + ')\t' 'Go Back')
                options_select = input('Please select an option: ')

                if options_select.isdigit() and 0 < int(options_select) < len(prev_orders) + 1:
                    # URL for the API endpoint
                    url = self.base_url + '/v1/accounts/' + \
                        account['accountIdKey'] + '/orders/preview.json'

                    # Add parameters and header information
                    headers = {'Content-Type': 'application/xml',
                               'consumerKey': config['DEFAULT']['CONSUMER_KEY']}

                    # Add payload for POST Request
                    payload = '''<PreviewOrderRequest>
                                   <orderType>{0}</orderType>
                                   <clientOrderId>{1}</clientOrderId>
                                   <Order>
                                       <allOrNone>false</allOrNone>
                                       <priceType>{2}</priceType>
                                       <orderTerm>{3}</orderTerm>
                                       <marketSession>REGULAR</marketSession>
                                       <stopPrice></stopPrice>
                                       <limitPrice>{4}</limitPrice>
                                       <Instrument>
                                           <Product>
                                               <securityType>{5}</securityType>
                                               <symbol>{6}</symbol>
                                           </Product>
                                           <orderAction>{7}</orderAction>
                                           <quantityType>QUANTITY</quantityType>
                                           <quantity>{8}</quantity>
                                       </Instrument>
                                   </Order>
                               </PreviewOrderRequest>'''

                    options_select = int(options_select)
                    prev_orders[options_select - 1]['client_order_id'] = str(
                        random.randint(1000000000, 9999999999))
                    payload = payload.format(prev_orders[options_select - 1]['order_type'],
                                             prev_orders[options_select -
                                                         1]['client_order_id'],
                                             prev_orders[options_select -
                                                         1]['price_type'],
                                             prev_orders[options_select -
                                                         1]['order_term'],
                                             prev_orders[options_select -
                                                         1]['limitPrice'],
                                             prev_orders[options_select -
                                                         1]['security_type'],
                                             prev_orders[options_select -
                                                         1]['symbol'],
                                             prev_orders[options_select -
                                                         1]['order_action'],
                                             prev_orders[options_select - 1]['quantity'])

                    # Make API call for POST request
                    response = session.post(url, headers=headers, data=payload)

                    # Handle and parse response
                    if response is not None and response.status_code == 200:
                        data = response.json()
                        parsed = json.dumps(data, indent=2, sort_keys=True)
                        _logger.debug(parsed)

                        print('\nPreview Order: ')

                        if data is not None and 'PreviewOrderResponse' in data and 'PreviewIds' in data['PreviewOrderResponse']:
                            for previewids in data['PreviewOrderResponse']['PreviewIds']:
                                print('Preview ID: ' +
                                      str(previewids['previewId']))
                        else:
                            # Handle errors
                            data = response.json()
                            _logger.debug(f'Response Body: {response.text}')
                            if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                                print('Error: ' + data['Error']['message'])
                            else:
                                print('\nError: E*TRADE API service error')

                        if data is not None and 'PreviewOrderResponse' in data and 'Order' in data['PreviewOrderResponse']:
                            for orders in data['PreviewOrderResponse']['Order']:
                                prev_orders[options_select -1]['limitPrice'] = orders['limitPrice']

                                if orders is not None and 'Instrument' in orders:
                                    for instruments in orders['Instrument']:
                                        if instruments is not None and 'orderAction' in instruments:
                                            print(
                                                f'Action: {instruments["orderAction"]}')
                                        if instruments is not None and 'quantity' in instruments:
                                            print(
                                                f'Quantity: {instruments["quantity"]}')
                                        if instruments is not None and 'Product' in instruments \
                                                and 'symbol' in instruments['Product']:
                                            print(
                                                f'Symbol: {instruments["Product"]["symbol"]}')
                                        if instruments is not None and 'symbolDescription' in instruments:
                                            print(
                                                f'Description: {instruments["symbolDescription"]}')

                                if orders is not None and 'priceType' in orders and 'limitPrice' in orders:
                                    print(f'Price Type: {orders["priceType"]}')

                                    if orders['priceType'] == 'MARKET':
                                        print('Price: MKT')
                                    else:
                                        print(f'Price: {orders["limitPrice"]}')
                                if orders is not None and 'orderTerm' in orders:
                                    print(f'Duration: {orders["orderTerm"]}')
                                if orders is not None and 'estimatedCommission' in orders:
                                    print(
                                        f'Estimated Commission: {orders["estimatedCommission"]}')
                                if orders is not None and 'estimatedTotalAmount' in orders:
                                    print(
                                        f'Estimated Total Cost: {orders["estimatedTotalAmount"]}')
                        else:
                            # Handle errors
                            data = response.json()
                            _logger.debug(f'Response Body: {response.text}')
                            if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                                print('Error: ' + data['Error']['message'])
                            else:
                                print('Error: Preview Order API service error')
                    else:
                        # Handle errors
                        data = response.json()
                        _logger.debug(f'Response Body: {response.text}')
                        if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                            print('Error: ' + data['Error']['message'])
                        else:
                            print('\nError: E*TRADE API service error')

                    break
                elif options_select.isdigit() and int(options_select) == len(prev_orders) + 1:
                    break
                else:
                    print('Unknown Option Selected!')

    @staticmethod
    def print(response, status):
        prev_orders = []
        if response is not None and 'OrdersResponse' in response and 'Order' in response['OrdersResponse']:
            for order in response['OrdersResponse']['Order']:
                if order is not None and 'OrderDetail' in order:
                    for details in order['OrderDetail']:
                        if details is not None and 'Instrument' in details:
                            for instrument in details['Instrument']:
                                order_str = ''
                                order_obj = {'price_type': None,
                                             'order_term': None,
                                             'order_indicator': None,
                                             'order_type': None,
                                             'security_type': None,
                                             'symbol': None,
                                             'order_action': None,
                                             'quantity': None}
                                if order is not None and 'orderType' in order:
                                    order_obj['order_type'] = order['orderType']

                                if order is not None and 'orderId' in order:
                                    order_str += f'#{order["orderId"]}: '
                                if instrument is not None and 'Product' in instrument and 'symbol' in instrument['Product']:
                                    order_str += f'{instrument["Product"]["symbol"]}, '
                                    order_obj['symbol'] = instrument['Product']['symbol']
                                if instrument is not None and 'Product' in instrument \
                                        and 'securityType' in instrument['Product']:
                                    order_str += f'{instrument["Product"]["securityType"]}, '
                                    order_obj['security_type'] = instrument['Product']['securityType']
                                if instrument is not None and 'orderAction' in instrument:
                                    order_str += f'{instrument["orderAction"]}, '
                                    order_obj['order_action'] = instrument['orderAction']
                                if instrument is not None and 'orderedQuantity' in instrument:
                                    order_str += f'x{instrument["orderedQuantity"]:,}, '
                                    order_obj['quantity'] = instrument['orderedQuantity']
                                if details is not None and 'priceType' in details:
                                    order_str += f'{details["priceType"]}, '
                                    order_obj['price_type'] = details['priceType']
                                if details is not None and 'orderTerm' in details:
                                    order_str += f'{details["orderTerm"]}, '
                                    order_obj['order_term'] = details['orderTerm']
                                if details is not None and 'limitPrice' in details:
                                    order_str += f'Price:{details["limitPrice"]:,.2f}, '
                                    order_obj['limitPrice'] = details['limitPrice']
                                if status == 'Open' and details is not None and 'netBid' in details:
                                    order_str += f'Bid:{details["netBid"]}, '
                                    order_obj['bid'] = details['netBid']
                                if status == 'Open' and details is not None and 'netAsk' in details:
                                    order_str += f'Ask:{details["netAsk"]}, '
                                    order_obj['ask'] = details['netAsk']
                                if status == 'Open' and details is not None and 'netPrice' in details:
                                    order_str += f'Last:{details["netPrice"]}, '
                                    order_obj['netPrice'] = details['netPrice']
                                if status == 'indiv_fills' and instrument is not None and 'filledQuantity' in instrument:
                                    order_str += f'{instrument["filledQuantity"]:,}@'
                                    order_obj['quantity'] = instrument['filledQuantity']
                                if status != 'open' and status != 'expired' and status != 'rejected' and instrument is not None \
                                        and 'averageExecutionPrice' in instrument:
                                    order_str += f'${instrument["averageExecutionPrice"]:,.2f}, '
                                if status != 'expired' and status != 'rejected' and details is not None and 'status' in details:
                                    order_str += f'{details["status"]}'

                                print(order_str)
                                prev_orders.append(order_obj)
        return prev_orders

    @staticmethod
    def options_selection(options):
        while True:
            print('')
            for num, price_type in enumerate(options, start=1):
                print(f'{num})\t{price_type}')

            options_select = input('Please select an option: ')

            if options_select.isdigit() and 0 < int(options_select) < len(options) + 1:
                return options_select
            else:
                print('Unknown Option Selected!')

    def user_select(self):
        order = {'price_type': '',
                 'order_term': '',
                 'symbol': '',
                 'order_action': '',
                 'limit_price': '',
                 'quantity': ''}

        price_type_options = ['MARKET', 'LIMIT']
        order_term_options = ['GOOD_FOR_DAY',
                              'IMMEDIATE_OR_CANCEL', 'FILL_OR_KILL']
        order_action_options = ['BUY', 'SELL', 'BUY_TO_COVER', 'SELL_SHORT']

        print('\nPrice Type:')
        order['price_type'] = price_type_options[int(
            self.options_selection(price_type_options)) - 1]

        if order['price_type'] == 'MARKET':
            order['order_term'] = 'GOOD_FOR_DAY'
        else:
            print('\nOrder Term:')
            order['order_term'] = order_term_options[int(
                self.options_selection(order_term_options)) - 1]

        order['limit_price'] = None
        if order['price_type'] == 'LIMIT':
            while order['limit_price'] is None or not order['limit_price'].isdigit() \
                    and not re.match(r'\d+(?:[.]\d{2})?$', order['limit_price']):
                order['limit_price'] = input('\nPlease input limit price: ')

        order['client_order_id'] = random.randint(1000000000, 9999999999)

        while order['symbol'] == '':
            order['symbol'] = input('\nPlease enter a stock symbol :')

        print('\nOrder Action Type:')
        order['order_action'] = order_action_options[int(
            self.options_selection(order_action_options)) - 1]

        while not order['quantity'].isdigit():
            order['quantity'] = input('\nPlease type quantity:')

        return order

    def preview_order_menu(self, session, account, prev_orders):
        menu_items = {'1': 'Select New Order',
                      '2': 'Select From Previous Orders',
                      '3': 'Go Back'}
        while True:
            selection = ui.menu(menu_items, 'Select Operation', 0, 5)
            if selection == '1':
                print('\nPreview Order: ')
                self.preview()
                break
            elif selection == '2':
                self.previous(session, account, prev_orders)
                break
            elif selection == '3':
                break
            else:
                print('Unknown Option Selected!')

    def cancel(self):
        while True:
            # Display a list of Open Orders
            # Make API call for GET request
            url = self.base_url + '/v1/accounts/' + \
                self.account['accountIdKey'] + '/orders.json'
            params_open = {'status': 'OPEN'}
            response_open = self.session.get(url, params=params_open)

            print('\nOpen Orders: ')
            # Handle and parse response
            if response_open.status_code == 204:
                print('None')
                menu_items = {'1': 'Go Back'}
                while True:
                    print('')
                    options = menu_items.keys()
                    for entry in options:
                        print(f'{entry})\t{menu_items[entry]}')

                    selection = input('Please select an option: ')
                    if selection == '1':
                        break
                    else:
                        print('Unknown Option Selected!')
                break
            elif response_open.status_code == 200:
                data = response_open.json()
                parsed = json.dumps(data, indent=2, sort_keys=True)
                _logger.debug(parsed)

                order_list = []
                count = 1
                if data is not None and 'OrdersResponse' in data and 'Order' in data['OrdersResponse']:
                    for order in data['OrdersResponse']['Order']:
                        if order is not None and 'OrderDetail' in order:
                            for details in order['OrderDetail']:
                                if details is not None and 'Instrument' in details:
                                    for instrument in details['Instrument']:
                                        order_str = ''
                                        order_obj = {'price_type': None,
                                                     'order_term': None,
                                                     'order_indicator': None,
                                                     'order_type': None,
                                                     'security_type': None,
                                                     'symbol': None,
                                                     'order_action': None,
                                                     'quantity': None}

                                        if order is not None and 'orderType' in order:
                                            order_obj['order_type'] = order['orderType']

                                        if order is not None and 'orderId' in order:
                                            order_str += f'Order {order["orderId"]} :'
                                        if instrument is not None and 'Product' in instrument and 'securityType' \
                                                in instrument['Product']:
                                            order_str += f'Type: {instrument["Product"]["securityType"]}, '
                                            order_obj['security_type'] = instrument['Product']['securityType']
                                        if instrument is not None and 'orderAction' in instrument:
                                            order_str += f'Order Type: {instrument["orderAction"]}, '
                                            order_obj['order_action'] = instrument['orderAction']
                                        if instrument is not None and 'orderedQuantity' in instrument:
                                            order_str += f'Quantity(Exec/Entered): {instrument["orderedQuantity"]:,}, '
                                            order_obj['quantity'] = instrument['orderedQuantity']
                                        if instrument is not None and 'Product' in instrument and 'symbol' in instrument['Product']:
                                            order_str += f'Symbol: {instrument["Product"]["symbol"]}, '
                                            order_obj['symbol'] = instrument['Product']['symbol']
                                        if details is not None and 'priceType' in details:
                                            order_str += f'Price Type: {details["priceType"]}, '
                                            order_obj['price_type'] = details['priceType']
                                        if details is not None and 'orderTerm' in details:
                                            order_str += f'Term: {details["orderTerm"]}, '
                                            order_obj['order_term'] = details['orderTerm']
                                        if details is not None and 'limitPrice' in details:
                                            order_str += f'Price: {details["limitPrice"]:,.2f}, '
                                            order_obj['limitPrice'] = details['limitPrice']
                                        if instrument is not None and 'filledQuantity' in instrument:
                                            order_str += f'Quantity Executed: {instrument["filledQuantity"]:,}, '
                                            order_obj['quantity'] = instrument['filledQuantity']
                                        if instrument is not None and 'averageExecutionPrice' in instrument:
                                            order_str += f'Price Executed: {instrument["averageExecutionPrice"]:,.2f}, '
                                        if details is not None and 'status' in details:
                                            order_str += f'Status: {details["status"]}'

                                        print(str(count) + ')\t' + order_str)
                                        count = 1 + count
                                        order_list.append(order['orderId'])

                    print(str(count) + ')\tGo Back')
                    selection = input('Please select an option: ')
                    if selection.isdigit() and 0 < int(selection) < len(order_list) + 1:
                        # Assemble PUT Request
                        url = self.base_url + '/v1/accounts/' + \
                            self.account['accountIdKey'] + \
                            '/orders/cancel.json'
                        headers = {'Content-Type': 'application/xml',
                                   'consumerKey': config['DEFAULT']['CONSUMER_KEY']}
                        payload = f'''<CancelOrderRequest>
                                        <orderId>{order_list[int(selection) - 1]}</orderId>
                                    </CancelOrderRequest>
                                   '''
                        response = self.session.put(
                            url, headers=headers, data=payload)

                        # Handle and parse response
                        if response is not None and response.status_code == 200:
                            data = response.json()
                            parsed = json.dumps(data, indent=2, sort_keys=True)
                            _logger.debug(parsed)

                            if data is not None and 'CancelOrderResponse' in data and 'orderId' in data['CancelOrderResponse']:
                                print(
                                    f'\nOrder number # {data["CancelOrderResponse"]["orderId"]} successfully Cancelled.')
                            else:
                                # Handle errors
                                _logger.debug(f'Response Body: {response.text}')
                                data = response.json()
                                if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                                    print('Error: ' + data['Error']['message'])
                                else:
                                    print('Error: Cancel Order API service error')
                        else:
                            # Handle errors
                            _logger.debug(f'Response Body: {response.text}')
                            data = response.json()
                            if 'Error' in data and 'message' in data['Error'] and data['Error']['message'] is not None:
                                print(f'Error: {data["Error"]["message"]}')
                            else:
                                print('Error: Cancel Order API service error')
                        break

                    elif selection.isdigit() and int(selection) == len(order_list) + 1:
                        break
                    else:
                        print('Unknown Option Selected!')
                else:
                    # Handle errors
                    _logger.debug(f'Response Body: {response_open.text}')
                    if response_open is not None and response_open.headers['Content-Type'] == 'application/json' \
                            and 'Error' in response_open.json() and 'message' in response_open.json()['Error'] \
                            and response_open.json()['Error']['message'] is not None:
                        print('Error: ' + response_open.json()
                              ['Error']['message'])
                    else:
                        print('Error: Balance API service error')
                    break
            else:
                # Handle errors
                _logger.debug(f'Response Body: {response_open.text}')
                if response_open is not None and response_open.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response_open.json() and 'message' in response_open.json()['Error'] \
                        and response_open.json()['Error']['message'] is not None:
                    print('Error: ' + response_open.json()['Error']['message'])
                else:
                    print('Error: Balance API service error')
                break

    def view(self):
        while True:
            # URL for the API endpoint
            url = self.base_url + '/v1/accounts/' + \
                self.account['accountIdKey'] + '/orders.json'

            # Add parameters and header information
            params_open = {'status': 'OPEN'}
            params_executed = {'status': 'EXECUTED'}
            params_indiv_fills = {'status': 'INDIVIDUAL_FILLS'}
            params_cancelled = {'status': 'CANCELLED'}
            params_rejected = {'status': 'REJECTED'}
            params_expired = {'status': 'EXPIRED'}

            # Make API call for GET request
            response_open = self.session.get(url, params=params_open)
            response_executed = self.session.get(url, params=params_executed)
            response_indiv_fills = self.session.get(
                url, params=params_indiv_fills)
            response_cancelled = self.session.get(url, params=params_cancelled)
            response_rejected = self.session.get(url, params=params_rejected)
            response_expired = self.session.get(url, params=params_expired)

            prev_orders = []

            print('\nOpen Orders:')
            # Handle and parse response
            if response_open.status_code == 204:
                print('None')
            elif response_open.status_code == 200:
                data = response_open.json()
                parsed = json.dumps(data, indent=2, sort_keys=True)
                _logger.debug(parsed)

                # Display list of open orders
                prev_orders.extend(self.print(data, 'open'))

            print('\nExecuted Orders:')
            # Handle and parse response
            if response_executed.status_code == 200:
                data = response_executed.json()

                # Display list of executed orders
                prev_orders.extend(self.print(data, 'executed'))
            elif response_executed.status_code == 204:
                print('None')

            print('\nIndividual Fills Orders:')
            # Handle and parse response
            if response_indiv_fills.status_code == 200:
                data = response_indiv_fills.json()
                parsed = json.dumps(data, indent=2, sort_keys=True)
                _logger.debug(parsed)

                # Display list of individual fills orders
                prev_orders.extend(self.print(data, 'indiv_fills'))
            elif response_indiv_fills.status_code == 204:
                print('None')

            print('\nCancelled Orders:')
            # Handle and parse response
            if response_cancelled.status_code == 200:
                data = response_cancelled.json()
                parsed = json.dumps(data, indent=2, sort_keys=True)
                _logger.debug(parsed)

                # Display list of open orders
                prev_orders.extend(self.print(data, 'cancelled'))
            elif response_cancelled.status_code == 204:
                print('None')

            print('\nRejected Orders:')
            # Handle and parse response
            if response_rejected.status_code == 200:
                data = response_executed.json()
                parsed = json.dumps(data, indent=2, sort_keys=True)
                _logger.debug(parsed)

                # Display list of open orders
                prev_orders.extend(self.print(data, 'rejected'))
            elif response_rejected.status_code == 204:
                print('None')

            # Expired orders
            print('\nExpired Orders:')
            # Handle and parse response
            if response_expired.status_code == 200:
                data = response_expired.json()
                parsed = json.dumps(data, indent=2, sort_keys=True)
                _logger.debug(parsed)

                # Display list of open orders
                prev_orders.extend(self.print(data, 'expired'))
            elif response_expired.status_code == 204:
                print('None')

            menu_items = {'1': 'Preview Order',
                          '2': 'Cancel Order',
                          '3': 'Go Back'}

            print('')
            options = menu_items.keys()
            for entry in options:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select an option: ')
            if selection == '1':
                self.preview_order_menu(
                    self.session, self.account, prev_orders)
            elif selection == '2':
                self.cancel()
            elif selection == '3':
                break
            else:
                print('Unknown Option Selected!')
