import datetime as dt

import pandas as pd
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker

import data as d
from fetcher import fetcher as fetcher
from fetcher.google import Google
from fetcher.excel import Excel
from data import models as models
from utils import ui, logger


_logger = logger.get_logger()


_master_exchanges: dict = {
    d.EXCHANGES[0]['abbreviation']: set(),
    d.EXCHANGES[1]['abbreviation']: set(),
    d.EXCHANGES[2]['abbreviation']: set()
}

_master_indexes: dict = {
    d.INDEXES[0]['abbreviation']: set(),
    d.INDEXES[1]['abbreviation']: set()
    # d.INDEXES[2]['abbreviation']: set()
}

if d.ACTIVE_DB == 'Postgres':
    _engine = create_engine(d.ACTIVE_URI, echo=False, pool_size=10, max_overflow=20)
    _session = sessionmaker(bind=_engine)
elif d.ACTIVE_DB == 'SQLite':
    _engine = create_engine(d.ACTIVE_URI)
    _session = sessionmaker(bind=_engine)

UNAVAILABLE = 'unavailable'


def is_database_connected() -> bool:
    return bool(d.ACTIVE_URI)


def is_live_connection() -> bool:
    return fetcher.is_connected()


def is_ticker(ticker: str, inactive: bool = False) -> bool:
    ticker = ticker.upper()

    if _session is not None:
        with _session() as session:
            if inactive:
                t = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()
            else:
                t = session.query(models.Security).filter(and_(models.Security.ticker == ticker, models.Security.active)).one_or_none()

            valid = t is not None
    else:
        valid = fetcher.validate_ticker(ticker)

    return valid


def is_exchange(exchange: str) -> bool:
    exchange = exchange.upper()

    if _session is not None:
        with _session() as session:
            e = session.query(models.Exchange).filter(models.Exchange.abbreviation == exchange).one_or_none()

        valid = e is not None
    else:
        e = [e['abbreviation'] for e in d.EXCHANGES]
        valid = exchange in e

    return valid


def is_index(index: str) -> bool:
    index = index.upper()

    if _session is not None:
        with _session() as session:
            i = session.query(models.Index).filter(models.Index.abbreviation == index).one_or_none()
            valid = i is not None
    else:
        i = [i['abbreviation'] for i in d.INDEXES]
        valid = index in i

    return valid


def is_list(list: str) -> bool:
    exist = False
    if is_exchange(list):
        exist = True
    elif is_index(list):
        exist = True

    return exist


def get_tickers(list: str, inactive: bool = False) -> list[str]:
    tickers = []

    if list.lower() == 'all':
        with _session() as session:
            if inactive:
                symbols = session.query(models.Security.ticker).order_by(models.Security.ticker).all()
            else:
                symbols = session.query(models.Security.ticker).filter(models.Security.active).order_by(models.Security.ticker).all()
        tickers = [x[0] for x in symbols]
    elif is_exchange(list):
        tickers = get_exchange_tickers(list, inactive=inactive)
    elif is_index(list):
        tickers = get_index_tickers(list, inactive=inactive)

    return tickers


def get_exchanges() -> list[str]:
    results = []

    with _session() as session:
        exchange = session.query(models.Exchange.abbreviation).order_by(models.Exchange.abbreviation).all()
        results = [exc.abbreviation for exc in exchange]

    return results


def get_indexes() -> list[str]:
    results = []

    with _session() as session:
        index = session.query(models.Index.abbreviation).all()
        results = [ind.abbreviation for ind in index]

    return results


def get_exchange_tickers(exchange: str, inactive: bool = False) -> list[str]:
    results = []

    if _session is not None:
        if is_exchange(exchange):
            with _session() as session:
                exc = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange.upper()).one()
                if exc is not None:
                    if inactive:
                        symbols = session.query(models.Security).filter(models.Security.exchange_id == exc.id).all()
                    else:
                        symbols = session.query(models.Security).filter(and_(models.Security.exchange_id == exc.id, models.Security.active)).all()

                    results = [symbol.ticker for symbol in symbols]
        else:
            raise ValueError(f'Invalid exchange: {exchange}')
    else:
        results = get_exchange_tickers_master(exchange)

    return results


def get_index_tickers(index: str, inactive: bool = False) -> list[str]:
    results = []

    if _session is not None:
        if is_index(index):
            with _session() as session:
                ind = session.query(models.Index.id).filter(models.Index.abbreviation == index.upper()).first()
                if ind is not None:
                    if inactive:
                        symbols = session.query(models.Security).filter(
                            or_(models.Security.index1_id == ind.id, models.Security.index2_id == ind.id, models.Security.index3_id == ind.id)).all()
                    else:
                        symbols = session.query(models.Security).filter(
                            and_(models.Security.active, or_(models.Security.index1_id == ind.id, models.Security.index2_id == ind.id, models.Security.index3_id == ind.id))).all()

                    results = [symbol.ticker for symbol in symbols]
        else:
            raise ValueError(f'Invalid index: {index}')
    else:
        results = get_index_tickers_master(index)

    return results


def get_ticker_exchange(ticker: str) -> str:
    if ticker.upper() in get_exchange_tickers_master('NASDAQ'):
        exchange = 'NASDAQ'
    elif ticker.upper() in get_exchange_tickers_master('NYSE'):
        exchange = 'NYSE'
    elif ticker.upper() in get_exchange_tickers_master('AMEX'):
        exchange = 'AMEX'
    else:
        exchange = ''

    return exchange


def get_ticker_index(ticker: str) -> str:
    index = ''

    if ticker.upper() in get_index_tickers_master('SP500'):
        index = 'NASDAQ'

    if ticker.upper() in get_index_tickers_master('DOW'):
        if index:
            index += ', '
        index += 'DOW'

    # if ticker.upper() in get_index_tickers_master('CUSTOM'):
    #     if index: index += ', '
    #     index += 'CUSTOM'

    if not index:
        index = 'None'

    return index


def get_current_price(ticker: str) -> float:
    price = 0.0
    history = get_history(ticker, 5, live=True)
    if history is not None:
        price = history.iloc[-1]['close']

    return price


def get_last_price(ticker: str) -> float:
    price = 0.0
    live = True if _session is None else False

    history = get_history(ticker, 30, live=live)
    if history is not None:
        price = history.iloc[-1]['close']

    return price


def get_history(ticker: str, days: int = -1, end: int = 0, use_last: bool = False, live: bool = False) -> pd.DataFrame:
    ticker = ticker.upper()
    history = pd.DataFrame()
    live = True if _session is None else live

    if end < 0:
        ValueError('Invalid value for "end"')
    elif live:
        history = fetcher.get_history_live(ticker, days)
        if history is not None:
            _logger.info(f'{__name__}: Fetched {len(history)} days of live price history for {ticker}')
        else:
            _logger.info(f'{__name__}: Unable to fetch live price history for {ticker} from {d.ACTIVE_CLOUDDATASOURCE}')

        if end > 0:
            _logger.info(f'{__name__}: "end" value ignored for live queries')
    else:
        _logger.info(f'{__name__}: Fetching {len(history)} days of price history for {ticker}...')
        with _session() as session:
            symbols = session.query(models.Security.id).filter(and_(models.Security.ticker == ticker, models.Security.active)).one_or_none()
            if symbols is not None:
                q = None
                if days < 0:
                    q = session.query(models.Price).filter(models.Price.security_id == symbols.id).order_by(models.Price.date)
                elif days > 1:
                    start = dt.datetime.today() - dt.timedelta(days=days) - dt.timedelta(days=end)
                    if use_last:
                        q = session.query(models.Price).filter(models.Price.security_id == symbols.id).order_by(models.Price.date).limit(days)
                    else:
                        q = session.query(models.Price).filter(and_(models.Price.security_id == symbols.id, models.Price.date >= start)).order_by(models.Price.date)
                else:
                    _logger.warning(f'{__name__}: Must specify history days > 1')

                if q is not None:
                    history = pd.read_sql(q.statement, _engine)
                    if not history.empty:
                        history.drop(['id', 'security_id'], axis=1, inplace=True)
                        if end > 0:
                            history = history[:-end]

                        _logger.info(f'{__name__}: Fetched {len(history)} days of price history for {ticker} from {d.ACTIVE_DB} ({end} days prior)')
            else:
                _logger.info(f'{__name__}: No history found for {ticker}')

    return history


def get_company(ticker: str, live: bool = False, extra: bool = False, uselast: bool = False, test: bool = False) -> dict:
    ticker = ticker.upper()
    live = True if _session is None else live
    results = {}

    if live:
        company = fetcher.get_company_live(ticker, uselast)
        if company is not None:
            if company.info is not None and not test:
                try:
                    results['name'] = company.info.get('shortName')[:95] if company.info.get('shortName') is not None else UNAVAILABLE
                    results['description'] = company.info.get('longBusinessSummary')[:4995] if company.info.get('longBusinessSummary') is not None else UNAVAILABLE
                    results['url'] = company.info.get('website')[:195] if company.info.get('website') is not None else UNAVAILABLE
                    results['sector'] = company.info.get('sector')[:195] if company.info.get('sector') is not None else UNAVAILABLE
                    results['industry'] = company.info.get('industry')[:195] if company.info.get('industry') is not None else UNAVAILABLE
                    results['marketcap'] = company.info.get('marketCap') if company.info.get('marketCap') is not None else 0
                    results['beta'] = company.info.get('beta') if company.info.get('beta') is not None else 3.0
                    results['indexes'] = ''
                    results['active'] = '?'
                    results['precords'] = 0

                    ratings = fetcher.get_ratings(ticker)
                    results['rating'] = sum(ratings) / float(len(ratings)) if len(ratings) > 0 else 3.0
                    results['exchange'] = '?'
                except Exception as e:
                    results = {}
                    _logger.error(f'{__name__}: Exception for ticker {ticker}: {str(e)}')
    else:
        with _session() as session:
            symbol = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()
            if symbol is not None:
                company = session.query(models.Company).filter(models.Company.security_id == symbol.id).one_or_none()
                if company is not None:
                    results['name'] = company.name
                    results['description'] = company.description
                    results['url'] = company.url
                    results['sector'] = company.sector
                    results['industry'] = company.industry
                    results['marketcap'] = company.marketcap
                    results['beta'] = company.beta
                    results['rating'] = company.rating
                    results['indexes'] = 'None'
                    results['active'] = str(symbol.active)
                    results['precords'] = 0

                    # Exchange
                    exc = session.query(models.Exchange.abbreviation).filter(models.Exchange.id == symbol.exchange_id).one_or_none()
                    if exc is not None:
                        results['exchange'] = exc.abbreviation

                    # Indexes
                    if symbol.index1_id is not None:
                        index = session.query(models.Index).filter(models.Index.id == symbol.index1_id).one().abbreviation
                        results['indexes'] = index

                        if symbol.index2_id is not None:
                            index = session.query(models.Index).filter(models.Index.id == symbol.index2_id).one().abbreviation
                            results['indexes'] += f', {index}'

                            if symbol.index3_id is not None:
                                index = session.query(models.Index).filter(models.Index.id == symbol.index3_id).one().abbreviation
                                results['indexes'] += f', {index}'

                    # Number of price records
                    if extra:
                        results['precords'] = session.query(models.Price.security_id).filter(models.Price.security_id == symbol.id).count()
                else:
                    _logger.warning(f'{__name__}: No company information for {ticker}')
            else:
                _logger.warning(f'{__name__}: No ticker located for {ticker}')

    return results


def get_exchange_tickers_master(exchange: str, type: str = 'google') -> list[str]:
    global _master_exchanges
    symbols = []

    if is_exchange(exchange):
        if len(_master_exchanges[exchange]) > 0:
            symbols = _master_exchanges[exchange]
        else:
            if type == 'google':
                table = Google(d.GOOGLE_SHEETNAME_EXCHANGES)
            elif type == 'excel':
                table = Excel(d.EXCEL_SHEETNAME_EXCHANGES)
            else:
                raise ValueError(f'Invalid table type: {type}')

            if table.open(exchange):
                symbols = table.get_column(1)
                _master_exchanges[exchange] = set(symbols)
            else:
                _logger.warning(f'{__name__}: Unable to open exchange spreadsheet {exchange}')
    else:
        raise ValueError(f'Invalid exchange name: {exchange}')

    return symbols


def get_index_tickers_master(index: str, type: str = 'google') -> list[str]:
    global _master_indexes
    symbols = []

    if is_index(index):
        if len(_master_indexes[index]) > 0:
            symbols = _master_indexes[index]
        else:
            if type == 'google':
                table = Google(d.GOOGLE_SHEETNAME_INDEXES)
            elif type == 'excel':
                table = Excel(d.EXCEL_SHEETNAME_INDEXES)
            else:
                raise ValueError(f'Invalid spreadsheet type: {type}')

            if table.open(index):
                symbols = set(table.get_column('1'))
                _master_indexes[index] = symbols
            else:
                _logger.warning(f'{__name__}: Unable to open index spreadsheet {index}')
    else:
        raise ValueError(f'Invalid index name: {index}')

    return symbols


def get_option_expiry(ticker: str, uselast: bool = False) -> tuple[str]:
    return fetcher.get_option_expiry(ticker, uselast)


def get_option_chain(ticker: str, uselast: bool = False) -> dict:
    return fetcher.get_option_chain(ticker, uselast)


def get_treasury_rate(ticker: str = 'DTB3') -> float:
    # DTB3: Default to 3-Month Treasury Rate
    return fetcher.get_treasury_rate(ticker)


if __name__ == '__main__':
    import sys
    from logging import DEBUG
    logger = ui.get_logger(DEBUG)

    if len(sys.argv) > 1:
        t = get_history(sys.argv[1], days=100, live=True)
    else:
        t = get_history('AAPL', live=True)

    print(t)
