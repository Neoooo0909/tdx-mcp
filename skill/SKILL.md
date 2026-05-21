---
name: tdx
description: |
  A-share market data via TDX (通达信) — realtime quotes, K-lines, minute data,
  tick trades, finance info, equity, factors, index/futures quotes, block sectors.
  No API key required. Use whenever the user asks about Chinese A-share market data.
  Triggers on: stock price, K-line, quote, 行情, K线, 分时, 逐笔, 财务, 股本, 板块.
version: 1.0.0
---

# TDX 通达信行情数据 Skill

通过 MCP 工具直连通达信服务器，获取 A 股实时/历史行情、财务、板块等数据。**无需 API Key。**

## 触发条件

以下请求自动使用本 Skill：

- 查询股票实时行情、价格、涨跌（`tdx_get_quote`）
- 获取 K 线、历史行情（`tdx_get_kline` / `tdx_get_kline_all`）
- 查看分时走势（`tdx_get_minute`）
- 查看逐笔成交、大单（`tdx_get_trades` / `tdx_get_trades_all`）
- 查询财务数据、净资产、利润（`tdx_get_finance`）
- 查询股本、流通盘（`tdx_get_equity`）
- 查询指数行情（`tdx_get_index_quote`）
- 查询期货行情（`tdx_get_futures_quote`）
- 查询板块成分（`tdx_get_block_info`）

## 代码格式（自动识别，任意格式均可）

| 格式 | 示例 |
|------|------|
| eltdx 格式（推荐） | `sz000001` / `sh600519` |
| iFinD 格式 | `000001.SZ` / `600519.SH` |
| 裸六码 | `000001`（首位=6 → SH，其余 → SZ） |

---

## 工具速查

### 实时行情 — `tdx_get_quote`

获取实时报价及五档盘口。

```
tdx_get_quote(codes="sh600519")                     # 单只
tdx_get_quote(codes="sz000001,sh600519,sh000300")   # 多只（逗号分隔）
```

返回字段：`last_price` / `open` / `high` / `low` / `last_close` /
`total_hand`（成交量，手）/ `amount`（成交额）/
`buy1~buy5` / `sell1~sell5`（价格） /
`buy1_n~buy5_n` / `sell1_n~sell5_n`（挂单量，手）

---

### K 线 — `tdx_get_kline` / `tdx_get_kline_all`

```
# 最近 N 根
tdx_get_kline(code="sh600519", period="day", adjust="qfq", count=250)
tdx_get_kline(code="sz000001", period="5min", adjust=None, count=100)

# 全量历史
tdx_get_kline_all(code="sh600519", period="day", adjust="qfq")
```

`period`：`1min` / `5min` / `15min` / `30min` / `60min` / `day` / `week` / `month`
`adjust`：`None`=不复权 / `qfq`=前复权 / `hfq`=后复权

返回字段：`time` / `open` / `high` / `low` / `close` / `volume`（手）/ `amount`（元）

---

### 分时数据 — `tdx_get_minute`

```
tdx_get_minute(code="sh600519")                   # 今日实时
tdx_get_minute(code="sh600519", date="2026-05-20") # 历史某天
```

返回字段：`time` / `price` / `volume`（手）

---

### 逐笔成交 — `tdx_get_trades` / `tdx_get_trades_all`

```
tdx_get_trades(code="sh600519", count=200)                          # 最新 200 笔
tdx_get_trades(code="sh600519", date="2026-05-20", count=200)       # 历史某天
tdx_get_trades_all(code="sh600519", date="2026-05-20")              # 历史全部
```

返回字段：`time` / `price` / `volume`（手）/ `side`（买/卖）

---

### 逐笔聚合分钟 K — `tdx_get_trade_minute_kline`

精度高于普通 1 分钟 K（由逐笔成交聚合）。

```
tdx_get_trade_minute_kline(code="sh600519")                    # 今日
tdx_get_trade_minute_kline(code="sh600519", date="2026-05-20") # 历史某天
```

返回字段同 K 线：`time` / `open` / `high` / `low` / `close` / `volume` / `amount`

---

### 集合竞价 — `tdx_get_call_auction` / `tdx_get_auction_0925`

```
tdx_get_call_auction(code="sh600519")                           # 实时竞价序列
tdx_get_auction_0925(code="sh600519", date="2026-05-20")        # 历史 09:25 定价
```

`call_auction` 返回：`time` / `price` / `match`（可成交量）/ `unmatched`（未成交量）/ `flag`
`auction_0925` 返回：`has_auction_0925` / `price` / `volume` / `amount` / `trading_date`

---

### 财务数据 — `tdx_get_finance`

最近一期财务报告的关键指标（tdxapi 后端）。

```
tdx_get_finance(code="sh600519")
tdx_get_finance(code="000001", market="SZ")
```

返回字段（部分）：
`float_shares`（流通股） / `total_shares`（总股本） / `bvps`（每股净资产） /
`total_assets` / `net_assets` / `main_revenue`（主营收入） /
`net_profit`（净利润） / `operating_cash_flow` /
`ipo_date` / `updated_date` / `province` / `industry` / `shareholder_count`

---

### 指数行情 — `tdx_get_index_quote`

```
tdx_get_index_quote(code="000001")   # 上证指数
tdx_get_index_quote(code="399001")   # 深成指
tdx_get_index_quote(code="000300")   # 沪深 300
tdx_get_index_quote(code="000016")   # 上证 50
tdx_get_index_quote(code="000905")   # 中证 500
tdx_get_index_quote(code="399006")   # 创业板指
```

返回原始字段：`price` / `open` / `high` / `low` / `volume` / `amount` 等

---

### 期货行情 — `tdx_get_futures_quote`

```
tdx_get_futures_quote(code="IF2506", market=7)   # 沪深300股指期货（中金所）
tdx_get_futures_quote(code="RB2510", market=6)   # 螺纹钢（上海期货）
tdx_get_futures_quote(code="I2509",  market=8)   # 铁矿石（大连）
tdx_get_futures_quote(code="SR509",  market=9)   # 白糖（郑州）
```

`market`：6=上海期货 / 7=中金所 / 8=大连 / 9=郑州

---

### 板块信息 — `tdx_get_block_info`

```
tdx_get_block_info(blockfile="block.dat",     size=50)   # 概念板块
tdx_get_block_info(blockfile="block_gn.dat",  size=50)   # 行业板块
tdx_get_block_info(blockfile="block_fg.dat",  size=50)   # 风格板块
tdx_get_block_info(blockfile="block_zs.dat",  size=50)   # 指数板块
```

返回：`items[].name`（板块名）/ `items[].stocks`（成分股代码列表）

---

### 股本 / 复权 / 除权 — `tdx_get_equity` / `tdx_get_equity_changes` / `tdx_get_xdxr` / `tdx_get_factors`

```
tdx_get_equity(code="sh600519")                      # 最新股本
tdx_get_equity(code="sh600519", on="2020-01-01")     # 历史股本
tdx_get_equity_changes(code="sh600519")              # 股本变化历史
tdx_get_xdxr(code="sh600519")                        # 除权除息历史
tdx_get_factors(code="sh600519")                     # 前/后复权因子序列
```

---

### 换手率 — `tdx_get_turnover`

```
tdx_get_turnover(code="sh600519", volume=19430)                  # 最新股本换手
tdx_get_turnover(code="sh600519", volume=19430, on="2024-01-01") # 历史股本换手
tdx_get_turnover(code="sh600519", volume=1943000, unit="share")  # 以股为单位
```

返回：`turnover`（换手率，%）

---

### 代码列表 — `tdx_get_code_list` / `tdx_get_codes`

```
tdx_get_code_list(kind="a_share", limit=100)   # A 股（默认）
tdx_get_code_list(kind="etf",     limit=100)   # ETF
tdx_get_code_list(kind="index",   limit=100)   # 指数
tdx_get_codes(exchange="sh",      limit=200)   # 上交所完整代码表
tdx_get_codes(exchange="sz",      limit=200)   # 深交所完整代码表
```

---

## 安装说明

### 1. 安装 MCP 服务

```bash
pip install git+https://github.com/Neoooo0909/tdx-mcp.git
```

### 2. 配置 MCP 服务器

**Claude Desktop**（`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "tdx": {
      "command": "tdx-mcp"
    }
  }
}
```

**Claude Code**：

```bash
claude mcp add tdx-mcp tdx-mcp
```

### 3. 安装本 Skill

```bash
mkdir -p ~/.claude/skills/tdx
curl -o ~/.claude/skills/tdx/SKILL.md \
  https://raw.githubusercontent.com/Neoooo0909/tdx-mcp/main/skill/SKILL.md
```

---

## 注意事项

- 数据来自通达信公开服务器，延迟约 3 秒
- 非交易时间行情字段返回盘后最后值
- 财务数据为最近一期报告期，非实时更新
- 期货代码需指定对应交易所 market 参数
