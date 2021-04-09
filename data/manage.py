import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fetcher import fetcher as f
from utils import utils as u
from .history import History
from .models import Base, Exchange, Security, Company

logger = u.get_logger()

SQLITE_DATABASE_PATH = 'data/test.db'

class Manager:
    def __init__(self):
        self.engine = create_engine(f'sqlite:///{SQLITE_DATABASE_PATH}')#, echo=True)

    def build_exchanges(self):
        Session = sessionmaker(bind=self.engine)
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

    def populate_exchange(self, exchange):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        e = session.query(Exchange).filter(Exchange.acronym==exchange).first()
        if e is not None:
            h = History(e.acronym)
            self.add_securities_to_exchange(h.symbols[100:105], e.acronym)
        else:
            session.close()
            raise ValueError('Unknown exchange')

        session.close()
        logger.info(f'{__name__}: Populated exchange {exchange}')

    def add_securities_to_exchange(self, tickers, exchange):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        exc = session.query(Exchange).filter(Exchange.acronym == exchange).first()
        if exc is not None:
            for sec in tickers:
                s = Security(sec)
                exc.securities += [s]
                session.commit()

                self.add_company_to_security(sec)
                session.commit()
        else:
            session.close()
            raise ValueError('Unknown exchange')

        session.close()

    def add_company_to_security(self, ticker):
        Session = sessionmaker(bind=self.engine)
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

    def delete_security(self, ticker):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        s = session.query(Security).filter(Security.ticker == ticker).first()
        if s is not None:
            session.delete(s)
            session.commit()

        session.close()

    def delete_database(self):
        if os.path.exists(SQLITE_DATABASE_PATH):
            os.remove(SQLITE_DATABASE_PATH)
        else:
            logger.error(f'{__name__}: File does not exist: {SQLITE_DATABASE_PATH}')

    def print_securities(self, exchange):
        Session = sessionmaker(bind=self.engine)
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

    manager = Manager()

    manager.delete_database()
    Base.metadata.create_all(manager.engine)
    manager.build_exchanges()
    manager.populate_exchange('NASDAQ')
    manager.print_securities('NASDAQ')
