"""
通达信协议请求体构造
基于 pytdx 源码逐命令校准

关键发现：不同功能使用不同的 magic/seq 组合
"""

import struct


def build_quote_request(stocks: list[tuple[int, str]]) -> bytes:
    """实时行情请求 (magic=0x010c, seq=0x02006320)"""
    stock_len = len(stocks)
    pkgdatalen = stock_len * 7 + 12
    values = (0x010C, 0x02006320, pkgdatalen, pkgdatalen, 0x5053E, 0, 0, stock_len)
    pkg_header = struct.pack("<HIHHIIHH", *values)
    pkg = bytearray(pkg_header)
    for market, code in stocks:
        code_bytes = code.encode("ascii") if isinstance(code, str) else code
        pkg += struct.pack("<B6s", market, code_bytes)
    return bytes(pkg)


def build_bars_request(
    category: int, market: int, code: str, start: int, count: int
) -> bytes:
    """K线请求 (magic=0x010c, seq=0x01016408)"""
    code_bytes = code.encode("ascii") if isinstance(code, str) else code
    values = (
        0x010C,
        0x01016408,
        0x1C,
        0x1C,
        0x052D,
        market,
        code_bytes,
        category,
        1,
        start,
        count,
        0,
        0,
        0,
    )
    return struct.pack("<HIHHHH6sHHHHIIH", *values)


def build_index_bars_request(
    category: int, market: int, code: str, start: int, count: int
) -> bytes:
    """指数K线请求"""
    return build_bars_request(category, market, code, start, count)


def build_stock_count_request(market: int) -> bytes:
    """股票数量请求 (magic=0x0c0c, seq=0x186c)"""
    pkg = bytearray.fromhex("0c 0c 18 6c 00 01 08 00 08 00 4e 04")
    pkg += struct.pack("<H", market)
    pkg += bytearray.fromhex("75 c7 33 01")
    return bytes(pkg)


def build_security_list_request(market: int, start: int) -> bytes:
    """股票列表请求 (magic=0x010c, seq=0x1864)"""
    pkg = bytearray.fromhex("0c 01 18 64 01 01 06 00 06 00 50 04")
    pkg += struct.pack("<HH", market, start)
    return bytes(pkg)


def build_minute_time_request(market: int, code: str) -> bytes:
    """当日分时数据请求 (magic=0x1b08)"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    pkg = bytearray.fromhex("0c 1b 08 00 01 01 0e 00 0e 00 1d 05")
    pkg += struct.pack("<H6sI", market, code_bytes, 0)
    return bytes(pkg)


def build_history_minute_request(market: int, code: str, date: int) -> bytes:
    """历史分时数据请求 (magic=0x0130)"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    date = int(date)
    pkg = bytearray.fromhex("0c 01 30 00 01 01 0d 00 0d 00 b4 0f")
    pkg += struct.pack("<IB6s", date, market, code_bytes)
    return bytes(pkg)


def build_transaction_request(market: int, code: str, start: int, count: int) -> bytes:
    """分笔成交数据请求 (magic=0x1708)"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    pkg = bytearray.fromhex("0c 17 08 01 01 01 0e 00 0e 00 c5 0f")
    pkg += struct.pack("<H6sHH", market, code_bytes, start, count)
    return bytes(pkg)


def build_history_transaction_request(
    market: int, code: str, start: int, count: int, date: int
) -> bytes:
    """历史分笔成交请求 (magic=0x0130)"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    date = int(date)
    pkg = bytearray.fromhex("0c 01 30 01 00 01 12 00 12 00 b5 0f")
    pkg += struct.pack("<IH6sHH", date, market, code_bytes, start, count)
    return bytes(pkg)


def build_xdxr_request(market: int, code: str) -> bytes:
    """除权除息数据请求 (magic=0x1f18)"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    pkg = bytearray.fromhex("0c 1f 18 76 00 01 0b 00 0b 00 0f 00 01 00")
    pkg += struct.pack("<B6s", market, code_bytes)
    return bytes(pkg)


def build_finance_request(market: int, code: str) -> bytes:
    """财务数据请求 (magic=0x1f18)"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    pkg = bytearray.fromhex("0c 1f 18 76 00 01 0b 00 0b 00 10 00 01 00")
    pkg += struct.pack("<B6s", market, code_bytes)
    return bytes(pkg)


def build_company_info_category_request(market: int, code: str) -> bytes:
    """公司信息目录请求"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    pkg = bytearray.fromhex("0c 1f 18 78 00 01 0b 00 0b 00 0f 00 01 00")
    pkg += struct.pack("<B6s", market, code_bytes)
    return bytes(pkg)


def build_company_info_content_request(
    market: int, code: str, filename: str, start: int, length: int
) -> bytes:
    """公司信息内容请求"""
    code_bytes = code.encode("utf-8") if isinstance(code, str) else code
    filename_bytes = filename.encode("utf-8") if isinstance(filename, str) else filename
    pkg = bytearray.fromhex("0c 1f 18 7a 00 01 38 00 38 00 7e 09 00 01")
    pkg += struct.pack("<H6s50sII", market, code_bytes, filename_bytes, start, length)
    return bytes(pkg)


def build_block_info_meta_request(blockfile: str) -> bytes:
    """板块信息元数据请求"""
    blockfile_bytes = (
        blockfile.encode("utf-8") if isinstance(blockfile, str) else blockfile
    )
    pkg = bytearray.fromhex("0c 1f 18 7c 00 01 36 00 36 00 7c 09")
    pkg += struct.pack("<50s", blockfile_bytes)
    return bytes(pkg)


def build_block_info_request(blockfile: str, start: int, size: int) -> bytes:
    """板块信息请求"""
    blockfile_bytes = (
        blockfile.encode("utf-8") if isinstance(blockfile, str) else blockfile
    )
    pkg = bytearray.fromhex("0c 1f 18 7e 00 01 38 00 38 00 7e 09")
    pkg += struct.pack("<50sHH", blockfile_bytes, start, size)
    return bytes(pkg)


def build_report_file_request(filename: str, offset: int) -> bytes:
    """报表文件请求"""
    filename_bytes = filename.encode("utf-8") if isinstance(filename, str) else filename
    pkg = bytearray.fromhex("0c 1f 18 80 00 01 22 00 22 00 68 09")
    pkg += struct.pack("<30sI", filename_bytes, offset)
    return bytes(pkg)


def build_heartbeat_request() -> bytes:
    """心跳请求"""
    return bytearray.fromhex("0c 1f 18 00 00 01 00 00 00 00 00 00 00 00")
