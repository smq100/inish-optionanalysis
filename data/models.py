from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Boolean, String, Integer, BigInteger, Float, Date
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import Enum, UniqueConstraint

engine = create_engine('sqlite:///data/test.db')#, echo=True)
Base = declarative_base()

class Exchange(Base):
    __tablename__ = 'exchange'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(200), unique=True, nullable=False)
    acronym = Column('acronym', String(20))
    securities = relationship('Security', back_populates='exchange')

    def __init__(self, acronym, name):
        self.acronym = acronym
        self.name = name

    def __repr__(self):
        return f'<Exchange({self.acronym})>'

class Security(Base):
    __tablename__ = 'security'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column('ticker', String(12), nullable=False, unique=True)
    name = Column('name', String(200), nullable=False)
    index = Column('index', String(12), default='')
    exchange_id = Column(Integer, ForeignKey('exchange.id', onupdate='CASCADE', ondelete='SET NULL'), nullable=False)
    exchange = relationship('Exchange')
    # company = relationship('Company', back_populates='security')

    def __init__(self, ticker, name):
        self.ticker = ticker
        self.name = name

    def __repr__(self):
        return f'<Security({self.ticker})>'

# class Company(Base):
#     __tablename__ = 'company'
#     id = Column(Integer, primary_key=True)
#     name = Column('name', String(100), nullable=False)
#     description = Column('description', String(2000))
#     company_url = Column('company_url', String(100))
#     sic = Column('sic', String(4))
#     employees = Column('employees', Integer)
#     sector = Column('sector', String(200))
#     industry_category = Column('industry_category', String(200))
#     industry_group = Column('industry_group', String(200))
#     security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
#     security = relationship('Security', back_populates='company')

# class History(Base):
#     __tablename__ = 'history'
#     id = Column(Integer, primary_key=True)
#     date = Column('date', Date, nullable=False)
#     open = Column('open', Float)
#     high = Column('high', Float)
#     low = Column('low', Float)
#     close = Column('close', Float)
#     volume = Column('volume', BigInteger)
#     adj_close = Column('adj_close', Float)
#     security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
#     UniqueConstraint('date', 'security_id')
#     security = relationship('Security')

# class Adjustment(Base):
#     __tablename__ = 'adjustment'
#     id = Column(Integer, primary_key=True)
#     date = Column('date', Date, nullable=False)
#     factor = Column('factor', Float, nullable=False)
#     dividend = Column('dividend', Float)
#     split_ratio = Column('split_ratio', Float)
#     security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
#     security = relationship('Security')

def add_security_to_exchange(ticker, name, exchange):
    Session = sessionmaker(bind=engine)
    session = Session()

    e = session.query(Exchange).filter(Exchange.acronym == exchange).first()
    if e is not None:
        sec = Security(ticker, name)
        e.securities += [sec]
        session.commit()
    else:
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

def _build_exchanges():
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


if __name__ == '__main__':
    # Base.metadata.create_all(engine)
    # _build_exchanges()

    # add_security_to_exchange('TSLA', 'Tesla', 'NASDAQ')
    # delete_security('TSLA')
    print_securities('NASDAQ')
