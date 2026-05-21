"""代码格式标准化工具"""
from __future__ import annotations

import re


def normalize_code_market(code: str, market: str | None) -> tuple[str, str]:
    """
    将各种格式的代码统一为 (六位代码, 市场) 格式。

    支持：sz000001 / sh600519 / 000001.SZ / 600519.SH / 000001
    """
    code = code.strip()
    prefix = code[:2].lower()

    if prefix in ("sz", "sh", "bj"):
        c = code[2:]
        m = prefix.upper()
    elif "." in code:
        parts = code.rsplit(".", 1)
        c = parts[0]
        m = parts[1].upper()[:2]
        if m not in ("SZ", "SH", "BJ"):
            m = "SH"
    else:
        c = re.sub(r"\D", "", code)
        if c.startswith("6"):
            m = "SH"
        elif c.startswith(("4", "8", "9")):
            m = "BJ"
        else:
            m = "SZ"

    if market:
        m = market.upper()

    return c, m
