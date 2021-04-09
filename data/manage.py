from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fetcher import fetcher as f
from utils import utils as u
from .history import History
from .models import Exchange, Security, Company

def build_exchanges():
    Session = sessionmaker(bind=engine)
    session = Session()

    exc = Exchange(acronym='NASDAQ', name='National Association of Securities Dealers Automated Quotations')
    session.add(exc)
    exc = Exchange(acronym='NYSE', name='New York Stock Exchange')
    session.add(exc)
    exc = Exchange(acronym='AMEX', name='American Stock Exchange')
    session.add(exc)

    session.commit()
    session.close()

    logger.info(f'{__name__}: Built exchanges')

def populate_exchange(exchange):
    Session = sessionmaker(bind=engine)
    session = Session()

    e = session.query(Exchange).filter(Exchange.acronym==exchange).first()
    if e is not None:
        h = History(e.acronym)
        add_securities_to_exchange(h.symbols[100:105], e.acronym)
    else:
        session.close()
        raise ValueError('Unknown exchange')

    session.close()
    logger.info(f'{__name__}: Populated exchange {exchange}')

def add_securities_to_exchange(tickers, exchange):
    Session = sessionmaker(bind=engine)
    session = Session()

    exc = session.query(Exchange).filter(Exchange.acronym == exchange).first()
    if exc is not None:
        for sec in tickers:
            s = Security(sec)
            exc.securities += [s]
            session.commit()

            add_company_to_security(sec)
            session.commit()
    else:
        session.close()
        raise ValueError('Unknown exchange')

    session.close()

def add_company_to_security(ticker):
    Session = sessionmaker(bind=engine)
    session = Session()

    s = session.query(Security).filter(Security.ticker == ticker).first()
    if s is not None:
        try: # YFinance/Pandas throws a lot of exceptions for certain symbols
            company = f.get_company(ticker)
            if company is not None:
                if company.info is not None:
                    c = Company()
                    c.name = company.info['shortName']
                    c.description = company.info['longBusinessSummary']
                    c.url = company.info['website']
                    c.sector = company.info['sector']
                    c.industry = company.info['industry']

                    s.company += [c]
                    session.commit()
        except (ValueError, KeyError) as e:
            logger.warning(f'{__name__}: Company info invalid: {ticker}: {str(e)}')
            session.close()
    else:
        session.close()
        raise ValueError('Unknown exchange')

    session.close()

def delete_security(ticker):
    Session = sessionmaker(bind=engine)
    session = Session()

    s = session.query(Security).filter(Security.ticker == ticker).first()
    if s is not None:
        session.delete(s)
        session.commit()

    session.close()

def print_securities(exchange):
    Session = sessionmaker(bind=engine)
    session = Session()

    e = session.query(Exchange).filter(Exchange.acronym == exchange).first()
    if e is not None:
        for s in e.securities:
            print(s)

    session.close()


if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    f.initialize()

    engine = create_engine('sqlite:///data/test.db')#, echo=True)
    declarative_base().metadata.create_all(engine)
    build_exchanges()
    populate_exchange('NASDAQ')
