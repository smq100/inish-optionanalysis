'''
yfinance: https://github.com/ranaroussi/yfinance
'''

import datetime as dt
import configparser

import quandl as qd
import yfinance as yf
import pandas as pd
from pandas.tseries.offsets import BDay

from data import store as s
from utils import utils as u

logger = u.get_logger()

# Quandl credentials
CREDENTIALS = 'fetcher/quandl.ini'
config = configparser.ConfigParser()
config.read(CREDENTIALS)
qd.ApiConfig.api_key = config['DEFAULT']['APIKEY']


def validate_ticker(ticker, force=False):
    valid = False

    if force:
        t = yf.Ticker(ticker).history(period='1d')
        if len(t) > 0:
            valid = True
    else:
        valid = s.is_symbol_valid(ticker)

    return valid

def get_company(ticker, force=False):
    company = None

    if validate_ticker(ticker, force):
        company = yf.Ticker(ticker)

    return company

def get_history(ticker, days=-1):
    history = None

    company = get_company(ticker)
    if company is not None:
        if days < 1:
            days = 7300 # 20 years

        start = dt.datetime.today() - dt.timedelta(days=days)
        history = company.history(start=f'{start:%Y-%m-%d}')

    return history

def get_current_price(ticker):
    if validate_ticker(ticker):
        start = dt.datetime.today() - dt.timedelta(days=5)
        df = get_ranged_data(ticker, start)
        price = df.iloc[-1]['Close']
    else:
        logger.error(f'{__name__}: Ticker {ticker} not valid')
        price = -1.0

    return price

def get_ranged_data(ticker, start, end=None):
    df = pd.DataFrame()

    if end is None:
        end = dt.date.today()

    if validate_ticker(ticker):
        company = get_company(ticker)
        info = company.history(start=f'{start:%Y-%m-%d}', end=f'{end:%Y-%m-%d}')
        df = pd.DataFrame(info)

    return df

def get_treasury_rate(ticker='DTB3'):
    # DTB3: Default to 3-Month Treasury Rate
    df = pd.DataFrame()
    prev_business_date = dt.datetime.today() - BDay(1)

    df = qd.get('FRED/' + ticker)
    if df.empty:
        logger.error(f'{__name__}: Unable to get Treasury Rates from Quandl. Please check connection')
        raise IOError('Unable to get Treasury Rate from Quandl')

    return df['Value'][0] / 100.0


if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    history = get_history('AAPL', 60)
    print(history)

    # start = dt.datetime.today() - dt.timedelta(days=10)
    # df = refresh_history('AAPL', 60)
    # print(yf.download('AAPL'))
    # print(df.history(start=f'{start:%Y-%m-%d}'))
    # print(df.info)
    # print(df.actions)
    # print(df.dividends)
    # print(df.splits)
    # print(df.institutional_holders)
    # print(df.quarterly_financials)
    # print(df.quarterly_balancesheet)
    # print(df.quarterly_balance_sheet)
    # print(df.quarterly_cashflow)
    # print(df.major_holders)
    # print(df.sustainability)
    # print(df.recommendations)
    # print(df.calendar)
    # print(df.isin)
    # print(df.options)
    # print(df.option_chain)


    '''
    Retrieves a company object that may be used to gather numerous data about the company and security.

    Ticker attributes include:
        .info
        .history(start="2010-01-01",  end=”2020-07-21”)
        .actions
        .dividends
        .splits
        .quarterly_financials
        .major_holders
        .institutional_holders
        .quarterly_balance_sheet
        .quarterly_cashflow
        .quarterly_earnings
        .sustainability
        .recommendations
        .calendar
        .isin
        .options
        .option_chain

    :return: <object> YFinance Ticker object
    '''

    ''' Example .info object:
    {
        "zip":"98052-6399",
        "sector":"Technology",
        "fullTimeEmployees":163000,
        "longBusinessSummary":"Microsoft Corporation develops, licenses, ...",
        "city":"Redmond",
        "phone":"425-882-8080",
        "state":"WA",
        "country":"United States",
        "companyOfficers":[],
        "website":"http://www.microsoft.com",
        "maxAge":1,
        "address1":"One Microsoft Way",
        "industry":"Software—Infrastructure",
        "previousClose":242.2,
        "regularMarketOpen":243.15,
        "twoHundredDayAverage":215.28839,
        "trailingAnnualDividendYield":0.008835673,
        "payoutRatio":0.31149998,
        "volume24Hr":"None",
        "regularMarketDayHigh":243.68,
        "navPrice":"None",
        "averageDailyVolume10Day":28705283,
        "totalAssets":"None",
        "regularMarketPreviousClose":242.2,
        "fiftyDayAverage":225.23157,
        "trailingAnnualDividendRate":2.14,
        "open":243.15,
        "toCurrency":"None",
        "averageVolume10days":28705283,
        "expireDate":"None",
        "yield":"None",
        "algorithm":"None",
        "dividendRate":2.24,
        "exDividendDate":1613520000,
        "beta":0.816969,
        "circulatingSupply":"None",
        "startDate":"None",
        "regularMarketDayLow":240.81,
        "priceHint":2,
        "currency":"USD",
        "trailingPE":36.151783,
        "regularMarketVolume":17420109,
        "lastMarket":"None",
        "maxSupply":"None",
        "openInterest":"None",
        "marketCap":1828762025984,
        "volumeAllCurrencies":"None",
        "strikePrice":"None",
        "averageVolume":29247585,
        "priceToSalesTrailing12Months":11.930548,
        "dayLow":240.81,
        "ask":242.26,
        "ytdReturn":"None",
        "askSize":900,
        "volume":17420109,
        "fiftyTwoWeekHigh":245.09,
        "forwardPE":29.97157,
        "fromCurrency":"None",
        "fiveYearAvgDividendYield":1.71,
        "fiftyTwoWeekLow":132.52,
        "bid":242.16,
        "tradeable":false,
        "dividendYield":0.0092,
        "bidSize":1100,
        "dayHigh":243.68,
        "exchange":"NMS",
        "shortName":"Microsoft Corporation",
        "longName":"Microsoft Corporation",
        "exchangeTimezoneName":"America/New_York",
        "exchangeTimezoneShortName":"EST",
        "isEsgPopulated":false,
        "gmtOffSetMilliseconds":"-18000000",
        "quoteType":"EQUITY",
        "symbol":"MSFT",
        "messageBoardId":"finmb_21835",
        "market":"us_market",
        "annualHoldingsTurnover":"None",
        "enterpriseToRevenue":11.596,
        "beta3Year":"None",
        "profitMargins":0.33473998,
        "enterpriseToEbitda":24.796,
        "52WeekChange":0.2835188,
        "morningStarRiskRating":"None",
        "forwardEps":8.09,
        "revenueQuarterlyGrowth":"None",
        "sharesOutstanding":7560500224,
        "fundInceptionDate":"None",
        "annualReportExpenseRatio":"None",
        "bookValue":17.259,
        "sharesShort":41952779,
        "sharesPercentSharesOut":0.0056,
        "fundFamily":"None",
        "lastFiscalYearEnd":1593475200,
        "heldPercentInstitutions":0.71844,
        "netIncomeToCommon":51309998080,
        "trailingEps":6.707,
        "lastDividendValue":0.56,
        "SandP52WeekChange":0.15952432,
        "priceToBook":14.048902,
        "heldPercentInsiders":0.00059,
        "nextFiscalYearEnd":1656547200,
        "mostRecentQuarter":1609372800,
        "shortRatio":1.54,
        "sharesShortPreviousMonthDate":1607990400,
        "floatShares":7431722306,
        "enterpriseValue":1777517723648,
        "threeYearAverageReturn":"None",
        "lastSplitDate":1045526400,
        "lastSplitFactor":"2:1",
        "legalType":"None",
        "lastDividendDate":1605657600,
        "morningStarOverallRating":"None",
        "earningsQuarterlyGrowth":0.327,
        "dateShortInterest":1610668800,
        "pegRatio":1.82,
        "lastCapGain":"None",
        "shortPercentOfFloat":0.0056,
        "sharesShortPriorMonth":39913925,
        "impliedSharesOutstanding":"None",
        "category":"None",
        "fiveYearAverageReturn":"None",
        "regularMarketPrice":243.15,
        "logo_url":"https://logo.clearbit.com/microsoft.com"
    }
    '''
