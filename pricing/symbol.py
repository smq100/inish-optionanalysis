
import datetime

from analysis.technical import TechnicalAnalysis
from pricing.fetcher import validate_ticker, get_company
from utils import utils as u

logger = u.get_logger()

class Symbol:
    def __init__(self, ticker, history=0):
        self.company = None
        self.ticker = ticker
        self.history = history
        self.ta = None

        if validate_ticker(ticker):
            self.company = get_company(ticker)
            if history > 0:
                start = datetime.datetime.today() - datetime.timedelta(days=self.history)
                self.ta = TechnicalAnalysis(self.ticker, start)
        else:
            logger.error(f'Error initializing {__class__}')


    def __str__(self):
        output = f'{self.ticker} ({self.company.info["shortName"]}) ${self.company.info["regularMarketPrice"]:.2f}'

        return output


''' Example YFinance .info object:
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