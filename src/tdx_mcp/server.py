"""
tdx-mcp MCP 服务入口

包含两个后端的完整工具集：
  - eltdx 原生 18 个工具（行情、K线、分时、逐笔、股本、复权等）
  - _tdxapi 补充 5 个工具（财务数据、指数行情、期货行情、板块、公司信息）

TDX 协议实现（源自 TDXDataFetcher）内置在 ``tdx_mcp._tdxapi``，**不占用顶层
包名**。曾经它被 vendored 成顶层 ``tdxapi``，而 PyPI 上已有一个完全无关的同名包
（TeamDynamix API wrapper，构造函数为 ``TdxClient(organization, ...)``），
两者互相遮蔽：装了那个包的用户，这里 5 个工具会在**调用时**抛
``missing 1 required positional argument: 'organization'``（import 阶段毫无征兆，
而 18 个 eltdx 工具一切正常，极易误判成"某几个接口坏了"）；反过来本包也会
盖掉别人真正需要的 TeamDynamix 包。改为私有子包后该冲突从根上不存在。
"""
from __future__ import annotations

from typing import Any


def _tdxapi_client():
    """创建并连接一个 TDX 协议客户端（调用方负责 close）"""
    from ._tdxapi import TdxClient

    client = TdxClient()
    client.connect()
    return client


def create_server():
    """创建完整 TDX MCP 服务（eltdx 18 工具 + tdxapi 5 工具）"""
    try:
        from eltdx.mcp_server import create_server as _eltdx_server
    except ImportError as exc:
        raise RuntimeError("请先安装 eltdx：pip install eltdx") from exc

    # 继承 eltdx 的 18 个工具
    server = _eltdx_server()

    # ─────────────────────────────────────────────────────────────────────
    # tdxapi 补充工具 1：基础财务数据
    # ─────────────────────────────────────────────────────────────────────

    @server.tool(name="tdx_get_finance")
    def tdx_get_finance(code: str, market: str | None = None) -> dict[str, Any]:
        """
        基础财务数据（tdxapi 后端）

        返回最近一期财务报告的关键财务指标，包括股本结构、资产负债、利润表等。

        Args:
            code:   股票代码，支持多种格式（sz000001 / 000001.SZ / 000001）
            market: 交易所代码 'SH' 或 'SZ'；为 None 时自动推断

        Returns:
            dict 包含以下字段（均为最近报告期数据）：
              float_shares        — 流通股本（股）
              total_shares        — 总股本（股）
              ipo_date            — 上市日期（YYYYMMDD int）
              updated_date        — 财务数据更新日期（YYYYMMDD int）
              province            — 所属省份代码
              industry            — 所属行业代码
              shareholder_count   — 股东人数
              bvps                — 每股净资产（元/股）
              total_assets        — 总资产（元）
              current_assets      — 流动资产（元）
              fixed_assets        — 固定资产（元）
              intangible_assets   — 无形资产（元）
              net_assets          — 净资产（元）
              current_liabilities — 流动负债（元）
              long_term_liabilities — 长期负债（元）
              capital_reserve     — 资本公积金（元）
              retained_earnings   — 未分配利润（元）
              main_revenue        — 主营收入（元）
              main_profit         — 主营利润（元）
              operating_profit    — 营业利润（元）
              net_profit          — 净利润（元）
              after_tax_profit    — 税后利润（元）
              investment_income   — 投资收益（元）
              operating_cash_flow — 经营现金流（元）
              total_cash_flow     — 总现金流（元）
              inventory           — 存货（元）
              receivables         — 应收账款（元）
              state_shares        — 国家股（股）
              b_shares            — B股（股）
              h_shares            — H股（股）
        """
        from ._helpers import normalize_code_market
        c, m = normalize_code_market(code, market)
        client = _tdxapi_client()
        try:
            result = client.get_finance_info(c, m)
        finally:
            client.close()
        return result or {}

    # ─────────────────────────────────────────────────────────────────────
    # tdxapi 补充工具 2：指数实时行情
    # ─────────────────────────────────────────────────────────────────────

    @server.tool(name="tdx_get_index_quote")
    def tdx_get_index_quote(code: str) -> dict[str, Any]:
        """
        指数实时行情（tdxapi 后端）

        适用于沪深主要指数，返回价格、涨跌、成交量等。

        Args:
            code: 六位指数代码
                  常用：000001（上证指数）、399001（深成指）、399006（创业板指）
                        000300（沪深300）、000016（上证50）、000905（中证500）

        Returns:
            dict 包含 price / open / high / low / volume / amount 等原始字段
        """
        from ._helpers import normalize_code_market
        c, _ = normalize_code_market(code, None)
        client = _tdxapi_client()
        try:
            q = client.get_index_quote(c)
        finally:
            client.close()
        if q is None:
            return {}
        return vars(q) if hasattr(q, "__dict__") else dict(q)

    # ─────────────────────────────────────────────────────────────────────
    # tdxapi 补充工具 3：期货实时行情
    # ─────────────────────────────────────────────────────────────────────

    @server.tool(name="tdx_get_futures_quote")
    def tdx_get_futures_quote(code: str, market: int = 6) -> dict[str, Any]:
        """
        期货实时行情（tdxapi 后端）

        Args:
            code:   期货合约代码，如 'IF2506'（沪深300股指期货主力）
            market: 交易所代码
                    6 = 上海期货交易所（螺纹钢、铜等）
                    7 = 中国金融期货交易所（IF/IH/IC/IM 等）
                    8 = 大连商品交易所（铁矿石、豆粕等）
                    9 = 郑州商品交易所（白糖、棉花等）

        Returns:
            dict 包含 price / open / high / low / volume / amount 等原始字段
        """
        client = _tdxapi_client()
        try:
            q = client.get_futures_quote(code, market=market)
        finally:
            client.close()
        if q is None:
            return {}
        return vars(q) if hasattr(q, "__dict__") else dict(q)

    # ─────────────────────────────────────────────────────────────────────
    # tdxapi 补充工具 4：板块信息
    # ─────────────────────────────────────────────────────────────────────

    @server.tool(name="tdx_get_block_info")
    def tdx_get_block_info(
        blockfile: str = "block.dat",
        start: int = 0,
        size: int = 100,
    ) -> dict[str, Any]:
        """
        板块成分信息（tdxapi 后端）

        从通达信服务器读取板块文件，返回板块名称及成分股列表。

        Args:
            blockfile: 板块文件名
                       block.dat      — 概念板块
                       block_zs.dat   — 指数板块
                       block_fg.dat   — 风格板块
                       block_gn.dat   — 行业板块
            start: 分页起始位置（默认 0）
            size:  最多返回条数（默认 100）

        Returns:
            dict:
              blockfile — 请求的文件名
              start     — 起始位置
              count     — 本次返回条数
              items     — list[dict]，每条包含板块名称及成分股代码列表
        """
        client = _tdxapi_client()
        try:
            items = client.get_block_info(blockfile, start, size)
        finally:
            client.close()
        return {"blockfile": blockfile, "start": start, "count": len(items), "items": items}

    # ─────────────────────────────────────────────────────────────────────
    # tdxapi 补充工具 5：公司信息历史期间目录
    # ─────────────────────────────────────────────────────────────────────

    @server.tool(name="tdx_get_company_info_categories")
    def tdx_get_company_info_categories(
        code: str,
        market: str | None = None,
    ) -> dict[str, Any]:
        """
        公司信息历史期间目录（通达信 F10，tdxapi 后端）

        返回个股的历史信息期间列表（含财务/价格关联数据），通常为 43 条记录。

        Args:
            code:   股票代码，支持多种格式（sz000001 / 000001.SZ / 000001）
            market: 'SH' 或 'SZ'；为 None 时自动推断

        Returns:
            dict:
              code    — 六位代码
              market  — 交易所（SH/SZ）
              count   — 记录条数
              items   — list[dict]，每条包含：
                          market  — 市场代码（0=SZ, 1=SH）
                          code    — 六位代码
                          date    — 报告期日期（YYYYMMDD int）
                          type    — 记录类型（1=期间边界, 2=期间区间数据）
                          values  — 4个浮点值（关联财务/价格数据）
        """
        from ._helpers import normalize_code_market
        c, m = normalize_code_market(code, market)
        client = _tdxapi_client()
        try:
            items = client.get_company_info_category(c, m)
        finally:
            client.close()
        return {"code": c, "market": m, "count": len(items or []), "items": items or []}

    return server


def main() -> None:
    """MCP 服务入口（由 pyproject.toml 脚本调用）"""
    create_server().run()


if __name__ == "__main__":
    main()
