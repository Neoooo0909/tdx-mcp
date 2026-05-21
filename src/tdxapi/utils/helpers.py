"""
工具函数
"""


def code_to_market(code: str) -> int:
    """
    根据股票代码自动判断市场
    6xxxxx -> SH (1)
    0xxxxx, 3xxxxx -> SZ (0)
    8xxxxx, 4xxxxx -> BJ (0, 走深圳通道)
    """
    if code.startswith("6"):
        return 1  # SH
    return 0  # SZ / BJ


def market_to_str(market: int) -> str:
    """市场代码转字符串"""
    return "SH" if market == 1 else "SZ"


def format_volume(vol: int) -> str:
    """格式化成交量显示"""
    if vol >= 100000000:
        return f"{vol / 100000000:.2f}亿"
    elif vol >= 10000:
        return f"{vol / 10000:.2f}万"
    return str(vol)


def format_amount(amt: float) -> str:
    """格式化成交额显示"""
    if amt >= 100000000:
        return f"{amt / 100000000:.2f}亿"
    elif amt >= 10000:
        return f"{amt / 10000:.2f}万"
    return f"{amt:.2f}"
