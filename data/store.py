import datetime as dt

from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker
import pandas as pd

from fetcher.google import Google
from fetcher.excel import Excel
from utils import utils as u
import data as d
from data import models as o
from fetcher import fetcher as f

logger = u.get_logger()
_master_exchanges = {
    d.EXCHANGES[0]['abbreviation']: set(),
    d.EXCHANGES[1]['abbreviation']: set(),
    d.EXCHANGES[2]['abbreviation']: set()
    }

_master_indexes = {
    d.INDEXES[0]['abbreviation']: set(),
    d.INDEXES[1]['abbreviation']: set(),
    d.INDEXES[2]['abbreviation']: set()
    }

def is_symbol_valid(symbol):
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        e = session.query(o.Security).filter(o.Security.ticker==symbol.upper()).one_or_none()

    return (e is not None)

def is_exchange(exchange):
    ret = False
    for e in d.EXCHANGES:
        if exchange == e['abbreviation']:
            ret = True
            break
    return ret

def is_index(index):
    ret = False
    for i in d.INDEXES:
        if index == i['abbreviation']:
            ret = True
            break
    return ret

def get_tickers(exchange=''):
    tickers = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        if exchange:
            e = session.query(o.Exchange.id, o.Exchange.abbreviation).filter(o.Exchange.abbreviation==exchange).one()
            t = session.query(o.Security.ticker).filter(o.Security.exchange_id==e.id).order_by(o.Security.ticker)
        else:
            t = session.query(o.Security.ticker).order_by(o.Security.ticker)

    tickers = list(map(lambda x: x[0], t.all()))
    return tickers

def get_history(ticker, days, live=False):
    if live:
        results = f.get_history(ticker, days)
    else:
        results = pd.DataFrame
        engine = create_engine(d.ACTIVE_URI, echo=False)
        session = sessionmaker(bind=engine)
        with session() as session:
            t = session.query(o.Security.id).filter(o.Security.ticker==ticker.upper()).one()
            if t is not None:
                if days < 0:
                    p = session.query(o.Price).filter(o.Price.security_id==t.id).order_by(o.Price.date)
                    results = pd.read_sql(p.statement, engine)
                    logger.info(f'{__name__}: Fetched max price history for {ticker}')
                elif days > 1:
                    start = dt.datetime.today() - dt.timedelta(days=days)
                    p = session.query(o.Price).filter(and_(o.Price.security_id==t.id, o.Price.date >= start)).order_by(o.Price.date)
                    results = pd.read_sql(p.statement, engine)
                    logger.info(f'{__name__}: Fetched {days} days of price history for {ticker}')
                else:
                    start = dt.datetime.today() - dt.timedelta(days=100)
                    p = session.query(o.Price).filter(and_(o.Price.security_id==t.id, o.Price.date >= start)).order_by(o.Price.date)
                    results = pd.read_sql(p.statement, engine)
                    if not results.empty:
                        results = results.iloc[-1]
                        logger.info(f'{__name__}: Fetched latest price history for {ticker}')
                    else:
                        logger.warning(f'{__name__}: No price history for {ticker}')
            else:
                logger.warning(f'{__name__}: No history found for {ticker}')

    return results

def get_company(ticker, live=False):
    results = {}
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    if live:
        c = f.get_company(ticker)
        if c is not None:
            try:
                results['name'] = c.info['shortName']
                results['description'] = c.info['longBusinessSummary']
                results['url'] = c.info['website']
                results['sector'] = c.info['sector']
                results['industry'] = c.info['industry']
                results['indexes'] = ''
                results['precords'] = 0
            except KeyError:
                results = {}
    else:
        results['name'] = ''
        results['description'] = ''
        results['url'] = ''
        results['sector'] = ''
        results['industry'] = ''
        results['indexes'] = ''
        results['precords'] = 0

        with session() as session:
            t = session.query(o.Security).filter(o.Security.ticker==ticker.upper()).one_or_none()
            if t is not None:
                c = session.query(o.Company).filter(o.Company.security_id==t.id).one_or_none()
                if c is not None:
                    results['name'] = c.name
                    results['description'] = c.description
                    results['url'] = c.url
                    results['sector'] = c.sector
                    results['industry'] = c.industry

                results['indexes'] = 'None'
                if t.index1_id is not None:
                    index = session.query(o.Index).filter(o.Index.id==t.index1_id).one().abbreviation
                    results['indexes'] = index

                    if t.index2_id is not None:
                        index = session.query(o.Index).filter(o.Index.id==t.index2_id).one().abbreviation
                        results['indexes'] += f', {index}'

                p = session.query(o.Price).filter(o.Price.security_id==t.id).count()
                results['precords'] = p

    return results

def get_exchanges():
    results = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        exc = session.query(o.Exchange.abbreviation).all()
        for e in exc:
            results += [e.abbreviation]

    return results

def get_exchange(exchange):
    results = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        exc = session.query(o.Exchange.id).filter(o.Exchange.abbreviation==exchange.upper()).first()
        if exc is not None:
            t = session.query(o.Security).filter(o.Security.exchange_id==exc.id).all()
            for symbol in t:
                results += [symbol.ticker]
        else:
            raise ValueError(f'Invalid exchange: {exchange}')

    return results

def get_indexes():
    results = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        ind = session.query(o.Index.abbreviation).all()
        for i in ind:
            results += [i.abbreviation]

    return results

def get_index(index):
    results = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        i = session.query(o.Index.id).filter(o.Index.abbreviation==index.upper()).first()
        if i is not None:
            t = session.query(o.Security).filter(or_(o.Security.index1_id==i.id, o.Security.index2_id==i.id)).all()
            for symbol in t:
                results += [symbol.ticker]
        else:
            raise ValueError(f'Invalid index: {index}')

    return results

def get_exchange_symbols_master(exchange, type='google'):
    global _master_exchanges
    symbols = []
    table = None

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
                logger.warning(f'{__name__}: Unable to open index spreadsheet {exchange}')
    else:
        raise ValueError(f'Invalid exchange name: {exchange}')

    return symbols

def get_index_symbols_master(index, type='google'):
    global _master_indexes
    table = None
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
                symbols = table.get_column(1)
                _master_indexes[index] = set(symbols)
            else:
                logger.warning(f'{__name__}: Unable to open exchange spreadsheet {index}')
    else:
        raise ValueError(f'Invalid index name: {index}')

    return symbols


if __name__ == '__main__':
    # from logging import DEBUG
    # logger = u.get_logger(DEBUG)

    t = get_tickers()
    print(t)
