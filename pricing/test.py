''' TODO '''
import datetime
import pandas as pd
from european import EuropeanPricing

if __name__ == '__main__':
    pricer = EuropeanPricing('AAPL', datetime.datetime(2021, 2, 12), 145)
    call_price, put_price = pricer.calculate_prices()
    value = pricer.generate_value_table('call')
    profit = pricer.generate_profit_table(call_price, value)

    pd.options.display.float_format = '${:,.2f}'.format

    print(value)
    print(profit)
