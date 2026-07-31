# tdx-mcp

**通达信（TDX）A 股行情数据 MCP 服务**

基于 [eltdx](https://github.com/eltdx/eltdx) 和 [TDXDataFetcher](https://github.com/mickey3721/TDXDataFetcher)，通过 TCP 直连通达信服务器，提供 23 个 MCP 工具，覆盖 A 股实时行情、历史 K 线、财务数据等场景。**无需 API Key，免费使用。**

---

## 工具列表（23 个）

### eltdx 原生工具（18 个）

| 工具名 | 说明 |
|--------|------|
| `tdx_get_quote` | 实时行情快照（五档盘口） |
| `tdx_get_kline` | K 线（分页，最近 N 根） |
| `tdx_get_kline_all` | K 线（全量历史） |
| `tdx_get_minute` | 分时数据（今日 / 历史） |
| `tdx_get_trades` | 逐笔成交（单页） |
| `tdx_get_trades_all` | 逐笔成交（全量） |
| `tdx_get_trade_minute_kline` | 逐笔聚合分钟 K（精度更高） |
| `tdx_get_auction_0925` | 历史 09:25 竞价定价 |
| `tdx_get_call_auction` | 实时集合竞价序列 |
| `tdx_get_count` | 交易所代码总数 |
| `tdx_get_codes` | 交易所代码列表（分页） |
| `tdx_get_code_list` | 过滤后代码列表（A股/ETF/指数） |
| `tdx_get_xdxr` | 除权除息历史 |
| `tdx_get_gbbq` | 股本变化原始记录 |
| `tdx_get_equity` | 指定日期股本 |
| `tdx_get_equity_changes` | 股本变化历史 |
| `tdx_get_factors` | 前/后复权因子序列 |
| `tdx_get_turnover` | 换手率计算 |

### TDX 协议补充工具（5 个）

> 这 5 个工具由内置的 TDX 协议实现（源自 TDXDataFetcher）驱动，位于
> `tdx_mcp/_tdxapi/`。**它不占用顶层包名 `tdxapi`**——PyPI 上已有一个完全无关的
> 同名包（TeamDynamix API wrapper），早期版本 vendored 成顶层 `tdxapi` 会与之互相
> 遮蔽，导致这 5 个工具在调用时抛 `missing 1 required positional argument:
> 'organization'`（而 18 个 eltdx 工具一切正常，极易误判）。现已改为私有子包。


| 工具名 | 说明 |
|--------|------|
| `tdx_get_finance` | 基础财务数据（股本、净资产、利润、现金流等） |
| `tdx_get_index_quote` | 指数实时行情（沪深 300、上证 50 等） |
| `tdx_get_futures_quote` | 期货实时行情（股指、商品期货） |
| `tdx_get_block_info` | 板块成分信息（概念/行业/风格/指数） |
| `tdx_get_company_info_categories` | 公司 F10 历史期间目录 |

---

## 快速开始

### 1. 安装

```bash
pip install git+https://github.com/Neoooo0909/tdx-mcp.git
```

或者克隆后本地安装：

```bash
git clone https://github.com/Neoooo0909/tdx-mcp.git
cd tdx-mcp
pip install -e .
```

### 2. 在 Claude Desktop 中配置

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）：

```json
{
  "mcpServers": {
    "tdx": {
      "command": "tdx-mcp"
    }
  }
}
```

或者使用完整路径：

```json
{
  "mcpServers": {
    "tdx": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["-m", "tdx_mcp.server"]
    }
  }
}
```

### 3. 在 Claude Code 中配置

```bash
claude mcp add tdx-mcp tdx-mcp
```

### 4. 安装 Skill（可选）

Skill 文件让 AI Agent 知道何时自动调用 TDX 工具及每个工具的参数含义。

```bash
mkdir -p ~/.claude/skills/tdx
curl -o ~/.claude/skills/tdx/SKILL.md \
  https://raw.githubusercontent.com/Neoooo0909/tdx-mcp/main/skill/SKILL.md
```

安装后，Agent 在遇到 A 股行情、K 线、财务等请求时会自动选择正确的 MCP 工具。

---

## 代码格式

所有工具均支持以下代码格式（自动识别）：

| 格式 | 示例 |
|------|------|
| eltdx 格式（推荐） | `sz000001` / `sh600519` |
| iFinD 格式 | `000001.SZ` / `600519.SH` |
| 裸六码 | `000001`（按首位自动推断市场） |

---

## 使用示例

```
# 获取贵州茅台实时行情
tdx_get_quote(codes="sh600519")

# 获取平安银行前复权日 K 线（最近 250 根）
tdx_get_kline(code="sz000001", period="day", adjust="qfq", count=250)

# 获取上证指数行情
tdx_get_index_quote(code="000001")

# 获取贵州茅台基础财务数据
tdx_get_finance(code="sh600519")

# 获取概念板块成分
tdx_get_block_info(blockfile="block.dat", size=20)

# 获取 IF2506 期货行情（中金所）
tdx_get_futures_quote(code="IF2506", market=7)
```

---

## 技术说明

- **网络**：直连通达信公开行情服务器（TCP 协议），无代理，无需账号
- **实时性**：行情数据延迟约 3 秒
- **K 线周期**：`1min` / `5min` / `15min` / `30min` / `60min` / `day` / `week` / `month`
- **复权方式**：`qfq`（前复权）/ `hfq`（后复权）/ `None`（不复权）
- **依赖**：`eltdx >= 0.5.0, < 1.0`，`mcp[cli] >= 1.0.0, < 2.0`，Python >= 3.11

> **上限必须锁死**：`eltdx` 1.x 把 `eltdx.mcp_server.create_server()` 换成了
> `eltdx.mcp.create_mcp_server()`，工具集也从 18 个缩到 10 个、名称全变；
> `mcp` 2.x 则移除了 `mcp.server.fastmcp`。任一放开上限，全新安装都会拉到新版
> 而**服务根本起不来**。适配 eltdx 1.x 需按新 API 重做工具层并同步本文工具表。

---

## License

MIT
