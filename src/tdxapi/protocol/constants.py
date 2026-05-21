"""
通达信行情协议常量定义
基于 pytdx 源码逆向工程及抓包分析校准
"""

from enum import IntEnum, Enum


class Market(IntEnum):
    """市场代码"""

    SZ = 0  # 深圳
    SH = 1  # 上海
    BJ = 2  # 北京（北交所）
    # 扩展市场（用于特定数据）
    HK = 3  # 港股
    HK_FUTURE = 4  # 港股期货
    US = 5  # 美股
    SH_FUTURE = 6  # 上海期货
    ZJ_FUTURE = 7  # 中金所期货
    DL_FUTURE = 8  # 大连商品交易所
    ZZ_FUTURE = 9  # 郑州商品交易所


class MarketRegion(Enum):
    """市场区域（用于股票列表查询）"""

    SZ = 0  # 深圳主板
    SH = 1  # 上海
    BJ = 2  # 北京
    CYB = 128  # 创业板
    KCB = 101  # 科创板
    CXB = 128  # 创新层


class Category(IntEnum):
    """K线周期"""

    FENZHONG_5 = 0  # 5分钟
    FENZHONG_15 = 1  # 15分钟
    FENZHONG_30 = 2  # 30分钟
    FENZHONG_60 = 3  # 60分钟
    RI = 9  # 日线
    ZHOU = 5  # 周线
    YUE = 6  # 月线
    JI = 10  # 季线
    NIAN = 11  # 年线
    FENSHI = 7  # 分时线（1分钟）


# 默认行情服务器列表
DEFAULT_SERVERS = [
    ("119.147.212.81", 7709),
    ("180.153.39.51", 7709),
    ("119.147.212.82", 7709),
    ("218.75.126.9", 7709),
    ("115.238.90.165", 7709),
]

# 协议常量
# 发送包头: <HIHH = 2+4+2+2 = 10 bytes (行情查询类)
# 响应包头: <IIIHH = 4+4+4+2+2 = 16 bytes
RSP_HEADER_LEN = 0x10  # 16

# Setup 命令（连接后必须发送三次握手）
SETUP_CMD1 = bytearray.fromhex("0c 02 18 93 00 01 03 00 03 00 0d 00 01")
SETUP_CMD2 = bytearray.fromhex("0c 02 18 94 00 01 03 00 03 00 0d 00 02")
SETUP_CMD3 = bytearray.fromhex(
    "0c 03 18 99 00 01 20 00 20 00 db 0f d5"
    "d0 c9 cc d6 a4 a8 af 00 00 00 8f c2 25"
    "40 13 00 00 d5 00 c9 cc bd f0 d7 ea 00"
    "00 00 02"
)

# 心跳间隔（秒）
HEARTBEAT_INTERVAL = 30

# 连接超时（秒）
CONNECT_TIMEOUT = 5
