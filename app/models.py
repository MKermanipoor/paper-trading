from datetime import datetime
from typing import List

from sqlalchemy.orm import relationship, Mapped
import enum

from app import db
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, JSON, Enum, Float


class Position(enum.Enum):
    buy = 'buy'
    sell = 'sell'


class Account(db.Model):
    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    api_key = Column(Text)
    secret_key = Column(Text)

    class AccountDTO:
        def __init__(self, identifier, title, api_key, secret_key):
            self.id = identifier
            self.title = title
            self.api_key = api_key
            self.secret_key = secret_key

    def get_DTO(self):
        return Account.AccountDTO(self.id, self.title, self.api_key, self.secret_key)


class Asset(db.Model):
    __tablename__ = 'assets'
    id = Column(Integer, primary_key=True)
    symbol = Column(Text)

    class AssetDTO:
        def __init__(self, identifier, symbol):
            self.id = identifier
            self.symbol = symbol

    def get_DTO(self):
        return Asset.AssetDTO(self.id, self.symbol)


class Rule(db.Model):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True)

    asset_id = Column(ForeignKey(Asset.id))
    asset: Mapped[Asset] = relationship(Asset)

    position: Mapped[Position] = Column(Enum(Position))

    test_info_id = Column('test_id', Integer, ForeignKey('test_info.id'))
    test_info = relationship('TestInfo', backref='parent')

    setting = Column('setting', JSON)

    class RuleDTO:
        def __init__(self, identifier, asset_id, position, test_info_id, setting):
            self.id = identifier
            self.asset_id = asset_id
            self.position = position
            self.test_info_id = test_info_id
            self.setting = setting

    def get_DTO(self):
        return Rule.RuleDTO(self.id, self.asset_id, self.position, self.test_info_id, self.setting)


class TestInfo(db.Model):
    INTERVAL_SETTING_KEY = 'interval'
    CHANNEL_ID_SETTING_KEY = 'channel_id'

    __tablename__ = 'test_info'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    account_id = Column(ForeignKey(Account.id))
    account: Mapped[Account] = relationship(Account)

    sell_interval: Mapped[JSON] = Column(JSON)
    buy_interval: Mapped[JSON] = Column(JSON)
    setting: Mapped[JSON] = Column(JSON)

    rules: Mapped[List['Rule']] = relationship(Rule)

    class TestInfoDTO:
        def __init__(self, identity, name, start_time, end_time, account_id, sell_interval, buy_interval, setting):
            self.id = identity
            self.name = name
            self.start_time = start_time
            self.end_time = end_time

            self.account_id = account_id

            self.sell_interval = sell_interval
            self.buy_interval = buy_interval
            self.setting = setting

    def get_DTO(self):
        return TestInfo.TestInfoDTO(self.id, self.name, self.start_time, self.end_time, self.account_id,
                                    self.sell_interval, self.buy_interval, self.setting)


class Order(db.Model):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)

    shares = Column(Float)
    average_price = Column(Float)
    type = Column(Enum(Position))
    alpaca_id = Column(Text)

    rule_id = Column(ForeignKey(Rule.id))
    rule = relationship(Rule)

    action_time = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)


class AssetBudget(db.Model):
    __tablename__ = 'assets_budget'

    id = Column(Integer, primary_key=True)
    budget = Column(Float)
    asset_id = Column(Integer)
    test_id = Column(Integer)
