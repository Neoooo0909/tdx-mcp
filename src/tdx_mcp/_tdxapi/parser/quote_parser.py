"""
行情数据解析器
基于 pytdx 源码校准的真实二进制格式
"""

import struct
from datetime import datetime, timedelta
from ..models import StockQuote, Bar, Tick


def _get_price(data: bytes, pos: int) -> tuple:
    """pytdx 变长整型编码解析"""
    pos_byte = 6
    bdata = data[pos]
    intdata = bdata & 0x3F
    sign = bool(bdata & 0x40)
    if bdata & 0x80:
        while True:
            pos += 1
            bdata = data[pos]
            intdata += (bdata & 0x7F) << pos_byte
            pos_byte += 7
            if bdata & 0x80:
                pass
            else:
                break
    pos += 1
    if sign:
        intdata = -intdata
    return intdata, pos


def _get_volume(ival: int) -> float:
    """pytdx 对数体积编码解析"""
    logpoint = ival >> 24
    hheax = logpoint
    hleax = (ival >> 16) & 0xFF
    lheax = (ival >> 8) & 0xFF
    lleax = ival & 0xFF

    dwEcx = logpoint * 2 - 0x7F
    dwEdx = logpoint * 2 - 0x86
    dwEsi = logpoint * 2 - 0x8E
    dwEax = logpoint * 2 - 0x96
    if dwEcx < 0:
        tmpEax = -dwEcx
    else:
        tmpEax = dwEcx

    dbl_xmm6 = pow(2.0, tmpEax)
    if dwEcx < 0:
        dbl_xmm6 = 1.0 / dbl_xmm6

    dbl_xmm4 = 0.0
    if hleax > 0x80:
        dbl_xmm0 = 0.0
        dbl_xmm3 = 0.0
        dbl_xmm1 = 0.0
        dwtmpeax = dwEdx + 1
        dbl_xmm3 = pow(2.0, dwtmpeax)
        dbl_xmm0 = pow(2.0, dwEdx) * 128.0
        dbl_xmm0 += (hleax & 0x7F) * dbl_xmm3
        dbl_xmm4 = dbl_xmm0
    else:
        dbl_xmm0 = 0.0
        if dwEdx >= 0:
            dbl_xmm0 = pow(2.0, dwEdx) * hleax
        else:
            dbl_xmm0 = (1 / pow(2.0, dwEdx)) * hleax
        dbl_xmm4 = dbl_xmm0

    dbl_xmm3 = pow(2.0, dwEsi) * lheax
    dbl_xmm1 = pow(2.0, dwEax) * lleax
    if hleax & 0x80:
        dbl_xmm3 *= 2.0
        dbl_xmm1 *= 2.0

    dbl_ret = dbl_xmm6 + dbl_xmm4 + dbl_xmm3 + dbl_xmm1
    return dbl_ret


def _get_datetime(category: int, buffer: bytes, pos: int) -> tuple:
    """pytdx 日期时间解析"""
    year = 0
    month = 0
    day = 0
    hour = 15
    minute = 0
    if category in (9, 5, 6, 10, 11):
        (date_val,) = struct.unpack_from("<I", buffer, pos)
        year = date_val // 10000
        month = (date_val % 10000) // 100
        day = date_val % 100
        pos += 4
    elif category < 4 or category in (7, 8):
        (zipday, tminutes) = struct.unpack_from("<HH", buffer, pos)
        year = (zipday >> 11) + 2004
        month = int((zipday % 2048) / 100)
        day = (zipday % 2048) % 100
        hour = int(tminutes / 60)
        minute = tminutes % 60
        pos += 4
    else:
        minutes, hour, minute = struct.unpack_from("<IHH", buffer, pos)
        base = datetime(2000, 1, 1)
        dt = base + timedelta(days=minutes // 1440)
        year, month, day = dt.year, dt.month, dt.day
        pos += 8
    return year, month, day, hour, minute, pos


def _cal_price(base_p: int, diff: int) -> float:
    """pytdx 价格计算"""
    return float(base_p + diff) / 100.0


def _encode_price(value: int) -> bytes:
    """pytdx 变长整型编码"""
    if value == 0:
        return bytes([0])
    result = bytearray()
    sign = 0x40 if value < 0 else 0
    value = abs(value)
    chunk = value & 0x3F
    value >>= 6
    result.append(sign | 0x80 | chunk)
    bit_pos = 7
    while value:
        chunk = value & ((1 << bit_pos) - 1)
        value >>= bit_pos
        result.append(0x80 | chunk)
        bit_pos += 7
    result[-1] = result[-1] & 0x7F
    return bytes(result)


def _encode_volume(volume: float) -> int:
    """将浮点数编码为 pytdx 对数体积格式（逆运算，非常复杂，这里用简化）"""
    if volume <= 0:
        return 0
    logpoint = 0
    while volume >= pow(2.0, 127):
        volume /= 2.0
        logpoint += 1
    while volume < 1.0:
        volume *= 2.0
        logpoint -= 1
    hleax = int(volume)
    lheax = int((volume - hleax) * 256)
    lleax = int(((volume - hleax) * 256 - lheax) * 256)
    ival = (logpoint << 24) | (hleax << 16) | (lheax << 8) | lleax
    return ival


def parse_quotes(body: bytes) -> list[StockQuote]:
    """解析实时行情响应包体"""
    pos = 0
    pos += 2
    (num_stock,) = struct.unpack_from("<H", body, pos)
    pos += 2

    stocks = []
    for _ in range(num_stock):
        (market,) = struct.unpack_from("<B", body, pos)
        (code_raw,) = struct.unpack_from("<6s", body, pos + 1)
        pos += 9

        code = code_raw.decode("ascii").strip("\x00")
        price, pos = _get_price(body, pos)
        last_close_diff, pos = _get_price(body, pos)
        open_diff, pos = _get_price(body, pos)
        high_diff, pos = _get_price(body, pos)
        low_diff, pos = _get_price(body, pos)

        reversed_bytes0, pos = _get_price(body, pos)
        reversed_bytes1, pos = _get_price(body, pos)

        vol, pos = _get_price(body, pos)
        cur_vol, pos = _get_price(body, pos)

        (amount_raw,) = struct.unpack_from("<I", body, pos)
        amount = _get_volume(amount_raw)
        pos += 4

        s_vol, pos = _get_price(body, pos)
        b_vol, pos = _get_price(body, pos)

        _, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)

        bid1, pos = _get_price(body, pos)
        ask1, pos = _get_price(body, pos)
        bid_vol1, pos = _get_price(body, pos)
        ask_vol1, pos = _get_price(body, pos)

        bid2, pos = _get_price(body, pos)
        ask2, pos = _get_price(body, pos)
        bid_vol2, pos = _get_price(body, pos)
        ask_vol2, pos = _get_price(body, pos)

        bid3, pos = _get_price(body, pos)
        ask3, pos = _get_price(body, pos)
        bid_vol3, pos = _get_price(body, pos)
        ask_vol3, pos = _get_price(body, pos)

        bid4, pos = _get_price(body, pos)
        ask4, pos = _get_price(body, pos)
        bid_vol4, pos = _get_price(body, pos)
        ask_vol4, pos = _get_price(body, pos)

        bid5, pos = _get_price(body, pos)
        ask5, pos = _get_price(body, pos)
        bid_vol5, pos = _get_price(body, pos)
        ask_vol5, pos = _get_price(body, pos)

        (reversed_bytes4,) = struct.unpack_from("<H", body, pos)
        pos += 2
        _, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)
        (reversed_bytes9, active2) = struct.unpack_from("<hH", body, pos)
        pos += 4

        stocks.append(
            StockQuote(
                code=code,
                market="SH" if market == 1 else "SZ",
                name="",
                price=_cal_price(price, 0),
                last_close=_cal_price(price, last_close_diff),
                open=_cal_price(price, open_diff),
                high=_cal_price(price, high_diff),
                low=_cal_price(price, low_diff),
                volume=vol,
                amount=amount,
                bid1=_cal_price(price, bid1),
                bid1_vol=bid_vol1,
                ask1=_cal_price(price, ask1),
                ask1_vol=ask_vol1,
                bid2=_cal_price(price, bid2),
                bid2_vol=bid_vol2,
                ask2=_cal_price(price, ask2),
                ask2_vol=ask_vol2,
                bid3=_cal_price(price, bid3),
                bid3_vol=bid_vol3,
                ask3=_cal_price(price, ask3),
                ask3_vol=ask_vol3,
                bid4=_cal_price(price, bid4),
                bid4_vol=bid_vol4,
                ask4=_cal_price(price, ask4),
                ask4_vol=ask_vol4,
                bid5=_cal_price(price, bid5),
                bid5_vol=bid_vol5,
                ask5=_cal_price(price, ask5),
                ask5_vol=ask_vol5,
                datetime=datetime.now(),
            )
        )
    return stocks


def parse_bars(body: bytes, category: int) -> list[Bar]:
    """解析K线响应包体"""
    pos = 0
    (ret_count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    bars = []
    pre_diff_base = 0

    for _ in range(ret_count):
        year, month, day, hour, minute, pos = _get_datetime(category, body, pos)

        price_open_diff, pos = _get_price(body, pos)
        price_close_diff, pos = _get_price(body, pos)
        price_high_diff, pos = _get_price(body, pos)
        price_low_diff, pos = _get_price(body, pos)

        (vol_raw,) = struct.unpack_from("<I", body, pos)
        vol = _get_volume(vol_raw)
        pos += 4

        (dbvol_raw,) = struct.unpack_from("<I", body, pos)
        dbvol = _get_volume(dbvol_raw)
        pos += 4

        open_diff_total = price_open_diff + pre_diff_base
        close = (open_diff_total + price_close_diff) / 1000.0
        high = (open_diff_total + price_high_diff) / 1000.0
        low = (open_diff_total + price_low_diff) / 1000.0
        open_ = open_diff_total / 1000.0

        pre_diff_base = open_diff_total + price_close_diff

        try:
            dt = datetime(year, month, day, hour, minute)
        except ValueError:
            dt = datetime(1970, 1, 1)

        bars.append(
            Bar(
                code="",
                market="",
                datetime=dt,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=vol,
                amount=dbvol,
            )
        )
    return bars


def parse_minute_time(body: bytes) -> list[dict]:
    """解析分时数据（基于 pytdx get_minute_time_data）

    注意：分时数据解析存在字节边界问题，部分价格可能不正确
    """
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 6

    results = []
    last_price = 0
    for _ in range(count):
        price_raw, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)
        vol, pos = _get_price(body, pos)
        last_price += price_raw
        results.append(
            {
                "price": last_price / 100.0,
                "volume": vol,
            }
        )
    return results


def parse_history_minute_time(body: bytes) -> list[dict]:
    """解析历史分时数据"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    results = []
    for _ in range(count):
        (hour,) = struct.unpack_from("<B", body, pos)
        pos += 1
        (minute,) = struct.unpack_from("<B", body, pos)
        pos += 1
        (sec,) = struct.unpack_from("<H", body, pos)
        pos += 2
        (price,) = struct.unpack_from("<I", body, pos)
        pos += 4
        (vol,) = struct.unpack_from("<I", body, pos)
        pos += 4
        (amount,) = struct.unpack_from("<I", body, pos)
        pos += 4

        results.append(
            {
                "hour": hour,
                "minute": minute,
                "sec": sec,
                "price": price / 100.0,
                "volume": vol,
                "amount": amount,
            }
        )
    return results


def parse_transactions(body: bytes, market: int, code: str) -> list[Tick]:
    """解析分笔成交数据"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    ticks = []
    market_str = "SH" if market == 1 else "SZ"

    for _ in range(count):
        (hour,) = struct.unpack_from("<B", body, pos)
        pos += 1
        (minute,) = struct.unpack_from("<B", body, pos)
        pos += 1
        (sec,) = struct.unpack_from("<H", body, pos)
        pos += 2
        price_raw, pos = _get_price(body, pos)
        vol, pos = _get_price(body, pos)
        (amount_raw,) = struct.unpack_from("<I", body, pos)
        pos += 4
        (direction,) = struct.unpack_from("<B", body, pos)
        pos += 1

        ticks.append(
            Tick(
                code=code,
                market=market_str,
                time=f"{hour:02d}:{minute:02d}:{sec:02d}",
                price=price_raw / 100.0,
                volume=vol,
                amount=amount_raw,
                direction=direction,
            )
        )
    return ticks


def parse_security_list(body: bytes, market: int) -> list[dict]:
    """解析股票列表"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    results = []
    for _ in range(count):
        code_raw = body[pos : pos + 6].decode("ascii").strip("\x00")
        pos += 6
        name_raw = body[pos : pos + 8].decode("gbk").strip("\x00")
        pos += 8
        pos += 12
        (decimal,) = struct.unpack_from("<B", body, pos)
        pos += 1
        (pre_close,) = struct.unpack_from("<H", body, pos)
        pos += 2

        results.append(
            {
                "code": code_raw,
                "name": name_raw,
                "decimal_point": decimal,
                "pre_close": pre_close / 100.0,
            }
        )
    return results


def parse_stock_count(body: bytes) -> int:
    """解析股票数量"""
    (count,) = struct.unpack_from("<H", body, 0)
    return count


def parse_xdxr_info(body: bytes) -> list[dict]:
    """解析除权除息数据"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    results = []
    for _ in range(count):
        (date,) = struct.unpack_from("<I", body, pos)
        pos += 4
        (add_count,) = struct.unpack_from("<I", body, pos)
        pos += 4
        (add_price,) = struct.unpack_from("<I", body, pos)
        pos += 4
        results.append(
            {
                "date": str(date),
                "add_count": add_count,
                "add_price": add_price / 1000.0,
            }
        )
    return results


def parse_finance_info(body: bytes) -> dict:
    """解析财务数据

    响应头 9 字节: count(2B) + market(1B) + code(6B)
    响应体 136 字节: <fHHII + 30×f，格式与 pytdx 完全一致
    股本字段单位: 万股 (×10000 得实际股数)
    财务字段单位: 万元 (×10000 得实际元数)，gudongrenshu 除外
    """
    if len(body) < 9 + 136:
        return {}

    pos = 9  # skip count(2) + market(1) + code(6)
    fmt = "<fHHIIffffffffffffffffffffffffffffff"

    (
        liutongguben,    # 流通股本 (万股)
        province,        # 所属省份代码
        industry,        # 所属行业代码
        updated_date,    # 财务更新日期 YYYYMMDD
        ipo_date,        # 上市日期 YYYYMMDD
        zongguben,       # 总股本 (万股)
        guojiagu,        # 国家股 (万股)
        faqirenfarengu,  # 发起人法人股 (万股)
        farengu,         # 法人股 (万股)
        bgu,             # B股 (万股)
        hgu,             # H股 (万股)
        zhigonggu,       # 职工股 (万股)
        zongzichan,      # 总资产 (万元)
        liudongzichan,   # 流动资产 (万元)
        gudingzichan,    # 固定资产 (万元)
        wuxingzichan,    # 无形资产 (万元)
        gudongrenshu,    # 股东人数 (人，不乘万)
        liudongfuzhai,   # 流动负债 (万元)
        changqifuzhai,   # 长期负债 (万元)
        zibengongjijin,  # 资本公积金 (万元)
        jingzichan,      # 净资产 (万元)
        zhuyingshouru,   # 主营收入 (万元)
        zhuyinglirun,    # 主营利润 (万元)
        yingshouzhangkuan,  # 应收账款 (万元)
        yingyelirun,     # 营业利润 (万元)
        touzishouyu,     # 投资收益 (万元)
        jingyingxianjinliu,  # 经营现金流 (万元)
        zongxianjinliu,  # 总现金流 (万元)
        cunhuo,          # 存货 (万元)
        lirunzonghe,     # 利润总额 (万元)
        shuihoulirun,    # 税后利润 (万元)
        jinglirun,       # 净利润 (万元)
        weifenlirun,     # 未分配利润 (万元)
        meigujingzichan, # 每股净资产 (元/股)
        baoliu2,         # 保留字段
    ) = struct.unpack_from(fmt, body, pos)

    return {
        "float_shares": liutongguben * 10000,
        "province": province,
        "industry": industry,
        "updated_date": updated_date,
        "ipo_date": ipo_date,
        "total_shares": zongguben * 10000,
        "state_shares": guojiagu * 10000,
        "founder_shares": faqirenfarengu * 10000,
        "corp_shares": farengu * 10000,
        "b_shares": bgu * 10000,
        "h_shares": hgu * 10000,
        "employee_shares": zhigonggu * 10000,
        "total_assets": zongzichan * 10000,
        "current_assets": liudongzichan * 10000,
        "fixed_assets": gudingzichan * 10000,
        "intangible_assets": wuxingzichan * 10000,
        "shareholder_count": gudongrenshu,
        "current_liabilities": liudongfuzhai * 10000,
        "long_term_liabilities": changqifuzhai * 10000,
        "capital_reserve": zibengongjijin * 10000,
        "net_assets": jingzichan * 10000,
        "main_revenue": zhuyingshouru * 10000,
        "main_profit": zhuyinglirun * 10000,
        "receivables": yingshouzhangkuan * 10000,
        "operating_profit": yingyelirun * 10000,
        "investment_income": touzishouyu * 10000,
        "operating_cash_flow": jingyingxianjinliu * 10000,
        "total_cash_flow": zongxianjinliu * 10000,
        "inventory": cunhuo * 10000,
        "total_profit": lirunzonghe * 10000,
        "after_tax_profit": shuihoulirun * 10000,
        "net_profit": jinglirun * 10000,
        "retained_earnings": weifenlirun * 10000,
        "bvps": meigujingzichan,
        "_reserved": baoliu2,
    }


def parse_ticks(body: bytes, market: int, code: str) -> list[Tick]:
    """解析分笔成交数据"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    ticks = []
    market_str = "SH" if market == 1 else "SZ"
    last_price = 0

    for _ in range(count):
        (tminutes,) = struct.unpack_from("<H", body, pos)
        hour = int(tminutes / 60)
        minute = tminutes % 60
        pos += 2

        price_raw, pos = _get_price(body, pos)
        vol, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)
        direction, pos = _get_price(body, pos)
        _, pos = _get_price(body, pos)

        last_price += price_raw

        ticks.append(
            Tick(
                code=code,
                market=market_str,
                time=f"{hour:02d}:{minute:02d}:00",
                price=last_price / 100.0,
                volume=vol,
                amount=0,
                direction=direction,
            )
        )
    return ticks


def parse_company_info_category(body: bytes) -> list[dict]:
    """解析公司信息目录

    旧协议 (pytdx 0x109b): count(2B) + N×[name(64B)+filename(80B)+start(4B)+length(4B)]
    新协议 (0x1878): outer_count(2B) + N×[market(1B)+code(6B)+cat_count(2B) + cat_count×29B]
      每条 29B 记录: market(1)+code(6)+sep(1)+date_uint32(4)+type(1)+f1(4)+f2(4)+f3(4)+f4(4)
    """
    if len(body) < 4:
        return []

    pos = 0
    (outer_count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    # 判断是否为新协议: 检查是否紧跟 market(0或1) + ASCII 数字代码
    # 新协议 outer_count 通常为 1，且 body[2] 为 0x00 或 0x01
    is_new_format = outer_count <= 10 and len(body) >= 11 and body[pos] in (0, 1)
    if is_new_format:
        # 尝试验证: 检查 code 为 6 位 ASCII 数字
        try:
            body[pos + 1 : pos + 7].decode("ascii")
            is_new_format = True
        except Exception:
            is_new_format = False

    if is_new_format:
        results = []
        for _ in range(outer_count):
            if pos + 9 > len(body):
                break
            market = body[pos]; pos += 1
            code = body[pos : pos + 6].decode("ascii", errors="replace"); pos += 6
            (cat_count,) = struct.unpack_from("<H", body, pos); pos += 2
            rec_size = 29  # market(1)+code(6)+sep(1)+date(4)+type(1)+4×float(16)
            for i in range(cat_count):
                if pos + rec_size > len(body):
                    break
                rec = body[pos : pos + rec_size]; pos += rec_size
                r_market = rec[0]
                r_code = rec[1:7].decode("ascii", errors="replace")
                (r_date,) = struct.unpack_from("<I", rec, 8)
                r_type = rec[12]
                f1, f2, f3, f4 = struct.unpack_from("<ffff", rec, 13)
                results.append({
                    "market": r_market,
                    "code": r_code,
                    "date": r_date,
                    "type": r_type,
                    "values": [f1, f2, f3, f4],
                })
        return results

    # 旧协议: count(2B) + N×[name(64B)+filename(80B)+start(4B)+length(4B)]
    results = []
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    def _decode_gbk(b: bytes) -> str:
        null = b.find(b"\x00")
        if null != -1:
            b = b[:null]
        return b.decode("gbk", errors="ignore")

    for _ in range(count):
        if pos + 152 > len(body):
            break
        name = _decode_gbk(body[pos : pos + 64]); pos += 64
        filename = _decode_gbk(body[pos : pos + 80]); pos += 80
        (start,) = struct.unpack_from("<I", body, pos); pos += 4
        (length,) = struct.unpack_from("<I", body, pos); pos += 4
        results.append({"name": name, "filename": filename, "start": start, "length": length})
    return results


def parse_company_info_content(body: bytes) -> bytes:
    """解析公司信息内容（返回原始数据）"""
    return body


def parse_block_info_meta(body: bytes) -> dict:
    """解析板块信息元数据"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    blocks = []
    for _ in range(count):
        blockname = body[pos : pos + 9].decode("gbk").rstrip("\x00")
        pos += 9
        (code_count,) = struct.unpack_from("<H", body, pos)
        pos += 2
        blocks.append({"name": blockname, "code_count": code_count})
    return {"count": count, "blocks": blocks}


def parse_block_info(body: bytes) -> list[dict]:
    """解析板块信息内容"""
    pos = 0
    (count,) = struct.unpack_from("<H", body, pos)
    pos += 2

    results = []
    for _ in range(count):
        code_raw = body[pos : pos + 6].decode("ascii").rstrip("\x00")
        pos += 6
        (market,) = struct.unpack_from("<B", body, pos)
        pos += 1
        results.append({"code": code_raw, "market": market})
    return results
