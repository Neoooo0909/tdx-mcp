"""
数据模型定义
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class StockQuote:
    """实时行情数据"""

    code: str
    market: str
    name: str
    price: float
    last_close: float
    open: float
    high: float
    low: float
    volume: int
    amount: float
    bid1: float
    bid1_vol: int
    ask1: float
    ask1_vol: int
    datetime: datetime

    bid2: float = 0.0
    bid2_vol: int = 0
    bid3: float = 0.0
    bid3_vol: int = 0
    bid4: float = 0.0
    bid4_vol: int = 0
    bid5: float = 0.0
    bid5_vol: int = 0
    ask2: float = 0.0
    ask2_vol: int = 0
    ask3: float = 0.0
    ask3_vol: int = 0
    ask4: float = 0.0
    ask4_vol: int = 0
    ask5: float = 0.0
    ask5_vol: int = 0

    def __repr__(self):
        return f"StockQuote({self.code} {self.price} {self.volume}手)"


@dataclass
class Bar:
    """K线数据"""

    code: str
    market: str
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float

    def __repr__(self):
        return f"Bar({self.code} {self.datetime.date()} O:{self.open} C:{self.close})"


@dataclass
class Tick:
    """分笔成交数据"""

    code: str
    market: str
    time: str
    price: float
    volume: int
    amount: float
    direction: int

    def __repr__(self):
        return f"Tick({self.code} {self.time} {self.price} vol:{self.volume})"
