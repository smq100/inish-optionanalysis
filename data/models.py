from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Boolean, String, Integer, BigInteger, Float, Date
from sqlalchemy.orm import relationship
from sqlalchemy import Enum, UniqueConstraint

from utils import utils as u

logger = u.get_logger()
Base = declarative_base()

VALID_TYPES = ('google', 'excel')

EXCHANGES = ({'abbreviation':'NASDAQ', 'name':'National Association of Securities Dealers Automated Quotations'},
             {'abbreviation':'NYSE',   'name':'New York Stock Exchange'},
             {'abbreviation':'AMEX',   'name':'American Stock Exchange'},
             {'abbreviation':'TEST',   'name':'Test Exchange'})

INDEXES = ({'abbreviation':'SP500', 'name':'Standard & Poors 500'},
           {'abbreviation':'DOW',   'name':'DOW industrials'},
           {'abbreviation':'TEST',  'name':'Test Index'})

class Exchange(Base):
    __tablename__ = 'exchange'
    id = Column(Integer, primary_key=True, autoincrement=True)
    abbreviation = Column('abbreviation', String(20))
    name = Column('name', String(200), unique=True, nullable=False)
    securities = relationship('Security', back_populates='exchange')

    def __init__(self, abbreviation, name):
        self.abbreviation = abbreviation.upper()
        self.name = name

    def __repr__(self):
        return f'<Exchange({self.acronym})>'

class Index(Base):
    __tablename__ = 'index'
    id = Column(Integer, primary_key=True, autoincrement=True)
    abbreviation = Column('abbreviation', String(20))
    name = Column('name', String(200), unique=True, nullable=False)
    securities = relationship('Security', back_populates='index')

    def __init__(self, abbreviation, name):
        self.abbreviation = abbreviation.upper()
        self.name = name

    def __repr__(self):
        return f'<Index({self.name})>'

class Security(Base):
    __tablename__ = 'security'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column('ticker', String(12), nullable=False, unique=True)
    exchange_id = Column(Integer, ForeignKey('exchange.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    exchange = relationship('Exchange')
    index_id = Column(Integer, ForeignKey('index.id', onupdate='CASCADE', ondelete='SET NULL'))
    index = relationship('Index')
    pricing = relationship('Price', back_populates='security')
    company = relationship('Company', back_populates='security')

    def __init__(self, ticker):
        self.ticker = ticker

    def __repr__(self):
        return f'<Security({self.ticker})>'

class Company(Base):
    __tablename__ = 'company'
    id = Column(Integer, primary_key=True)
    name = Column('name', String(100), nullable=False)
    description = Column('description', String(2000))
    url = Column('url', String(100))
    sector = Column('sector', String(200))
    industry = Column('industry', String(200))
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    security = relationship('Security', back_populates='company')

    def __repr__(self):
        return f'<Company({self.name})>'

class Price(Base):
    __tablename__ = 'price'
    id = Column(Integer, primary_key=True)
    date = Column('date', Date, nullable=False)
    open = Column('open', Float)
    high = Column('high', Float)
    low = Column('low', Float)
    close = Column('close', Float)
    volume = Column('volume', BigInteger)
    adj_close = Column('adj_close', Float)
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    UniqueConstraint('date', 'security_id')
    security = relationship('Security')

    def __repr__(self):
        return f'<Price(security{self.security_id})>'

# class Adjustment(Base):
#     __tablename__ = 'adjustment'
#     id = Column(Integer, primary_key=True)
#     date = Column('date', Date, nullable=False)
#     factor = Column('factor', Float, nullable=False)
#     dividend = Column('dividend', Float)
#     split_ratio = Column('split_ratio', Float)
#     security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
#     security = relationship('Security')
