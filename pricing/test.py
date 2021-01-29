''' TODO '''
import datetime

from european import EuropeanPricing

if __name__ == '__main__':
    pricer = EuropeanPricing('AAPL', datetime.datetime(2021, 2, 12), 145)
    call_price, put_price = pricer.calculate_prices()
    df = pricer.generate_value_table('call', call_price)
    print(df)
