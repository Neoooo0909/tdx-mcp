"""
通达信行情客户端
支持：实时行情、K线、分时、分笔、股票列表、财务数据等
基于 pytdx 源码校准协议
"""

import socket
import time
import struct
import threading
from typing import Optional

from ..protocol.constants import (
    DEFAULT_SERVERS,
    RSP_HEADER_LEN,
    Category,
    SETUP_CMD1,
    SETUP_CMD2,
    SETUP_CMD3,
    CONNECT_TIMEOUT,
    HEARTBEAT_INTERVAL,
)
from ..protocol.requests import (
    build_quote_request,
    build_bars_request,
    build_stock_count_request,
    build_security_list_request,
    build_minute_time_request,
    build_transaction_request,
    build_history_minute_request,
    build_history_transaction_request,
    build_xdxr_request,
    build_finance_request,
)
from ..protocol.packet import RspHeader, _recv_exact
from ..parser import parse_quotes, parse_bars, parse_ticks
from ..parser.quote_parser import (
    parse_minute_time,
    parse_history_minute_time,
    parse_security_list,
    parse_stock_count,
    parse_xdxr_info,
    parse_finance_info,
)
from ..models import StockQuote, Bar, Tick


class TdxClient:
    """通达信行情客户端（不依赖任何通达信软件）"""

    def __init__(
        self,
        ip: str = None,
        port: int = 7709,
        timeout: float = CONNECT_TIMEOUT,
        auto_reconnect: bool = True,
        max_retries: int = 3,
        thread_safe: bool = True,
        heartbeat: bool = True,
    ):
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self._auto_reconnect = auto_reconnect
        self._max_retries = max_retries
        self._sock: Optional[socket.socket] = None
        self._seq = 0
        self._lock = threading.RLock() if thread_safe else None
        self._heartbeat_enabled = heartbeat
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop = threading.Event()

    def connect(self, ip: str = None, port: int = None) -> "TdxClient":
        """
        连接行情服务器并完成三次握手
        握手命令固定，不需要知道内容
        """
        target_ip = ip or self._ip
        target_port = port or self._port

        if not target_ip:
            target_ip, target_port = self._find_best_server()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self._timeout)
        self._sock.connect((target_ip, target_port))
        self._ip = target_ip
        self._port = target_port
        self._seq = 0

        # 三次握手
        for cmd in [SETUP_CMD1, SETUP_CMD2, SETUP_CMD3]:
            self._send_raw(cmd)
            self._recv_response()

        if self._heartbeat_enabled:
            self._start_heartbeat()

        return self

    def close(self):
        """断开连接"""
        self._stop_heartbeat()
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()
            self._sock = None

    def _start_heartbeat(self):
        """启动心跳线程"""
        self._stop_heartbeat()
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self):
        """停止心跳线程"""
        if self._heartbeat_thread:
            self._heartbeat_stop.set()
            self._heartbeat_thread.join(timeout=2)
            self._heartbeat_thread = None

    def _heartbeat_loop(self):
        """心跳循环"""
        from ..protocol.requests import build_heartbeat_request

        while not self._heartbeat_stop.wait(HEARTBEAT_INTERVAL):
            try:
                with self._lock:
                    if self._sock:
                        self._send_raw(build_heartbeat_request())
            except Exception:
                pass

    def _ensure_connected(self):
        """确保已连接，未连接时自动重连"""
        if self._sock is None:
            self.connect()

    def _send_raw(self, data: bytes):
        if not self._sock:
            raise ConnectionError("未连接服务器")
        self._sock.sendall(data)

    def _reconnect(self):
        """重新连接"""
        self._stop_heartbeat()
        self.close()
        self.connect(self._ip, self._port)

    def _recv_response(self) -> tuple:
        head_buf = _recv_exact(self._sock, RSP_HEADER_LEN)
        header = RspHeader.unpack(head_buf)

        if header.zip_size >= header.unzip_size:
            actual_size = header.unzip_size
        else:
            actual_size = header.zip_size

        # body 必须收满 actual_size 才算完整。
        #
        # 旧写法在 `len(chunk) < remaining` 时直接 `actual_size = len(body_buf); break`
        # ——把 **TCP 的短读当成了响应结束**。短读在数据跨包时完全正常，后果有二：
        # ① body 被截断；② 响应剩余字节留在 socket 缓冲区，污染之后每一次读取
        # （协议流失步）。小响应总在一个 TCP 段里，所以这个 bug 长期不暴露；
        # 一旦响应变大（多股批量、长 K 线、板块文件）就变成"第一次对、后续全乱"，
        # 而且重连也不稳定修复——分包与否取决于当时的网络状况。
        # 同一文件里 header 本来就用 _recv_exact 收满，body 却没有。
        body = _recv_exact(self._sock, actual_size)
        if len(body) < actual_size:
            raise ConnectionError(
                f"响应不完整: 期望 {actual_size} 字节，实收 {len(body)}")
        needs_decompress = header.zip_size < header.unzip_size
        if not needs_decompress and len(body) >= 2 and body[:2] == b"x\x9c":
            needs_decompress = True
        if needs_decompress:
            import zlib

            try:
                body = zlib.decompress(body)
            except zlib.error:
                pass

        return header, body

    def _send_recv(self, body: bytes, retries: int = None) -> bytes:
        if self._lock:
            with self._lock:
                return self._send_recv_unlocked(body, retries)
        return self._send_recv_unlocked(body, retries)

    def _send_recv_unlocked(self, body: bytes, retries: int = None) -> bytes:
        self._ensure_connected()
        retries = retries if retries is not None else self._max_retries

        for attempt in range(retries):
            try:
                self._send_raw(body)
                _, body = self._recv_response()
                return body
            except (ConnectionError, OSError) as e:
                if attempt < retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    self._reconnect_unlocked()
                else:
                    raise ConnectionError(f"请求失败（已重试 {retries} 次）: {e}")

    def _reconnect(self):
        """重新连接（带锁）"""
        if self._lock:
            with self._lock:
                self._reconnect_unlocked()
        else:
            self._reconnect_unlocked()

    def _reconnect_unlocked(self):
        """重新连接（无锁）"""
        self._stop_heartbeat()
        self.close()
        self.connect(self._ip, self._port)

    def _find_best_server(self) -> tuple[str, int]:
        """测速选择最优服务器"""
        best = None
        best_time = float("inf")
        for ip, port in DEFAULT_SERVERS:
            t = self._ping_server(ip, port)
            if t is not None and t < best_time:
                best_time = t
                best = (ip, port)
        if best is None:
            raise ConnectionError("所有服务器均不可用")
        return best

    def _ping_server(self, ip: str, port: int) -> Optional[float]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            start = time.time()
            sock.connect((ip, port))
            elapsed = (time.time() - start) * 1000
            sock.close()
            return elapsed
        except (socket.timeout, OSError):
            return None

    # === 行情数据 ===

    @staticmethod
    def _parse_market(market) -> int:
        """解析市场代码"""
        if isinstance(market, int):
            return market
        return 1 if market.upper() == "SH" else 0

    def get_quote(self, code: str, market: str = "SH") -> StockQuote:
        """获取单只股票实时行情"""
        m = self._parse_market(market)
        results = self.get_quotes([(m, code)])
        return results[0] if results else None

    def get_quotes(self, stocks: list[tuple[int, str]]) -> list[StockQuote]:
        """批量获取实时行情"""
        body = build_quote_request(stocks)
        resp = self._send_recv(body)
        return parse_quotes(resp)

    def get_index_quote(self, code: str) -> StockQuote:
        """获取指数实时行情（如 000001 上证指数）"""
        m = self._parse_market("SH")
        results = self.get_quotes([(m, code)])
        return results[0] if results else None

    def get_futures_quote(self, code: str, market: int = 6) -> StockQuote:
        """获取期货实时行情（market: 6=上海期货, 7=中金所, 8=大连, 9=郑州）"""
        results = self.get_quotes([(market, code)])
        return results[0] if results else None

    # === K线数据 ===

    def get_bars(
        self,
        code: str,
        market: str = "SH",
        period: str = "1d",
        count: int = 100,
        start: int = 0,
    ) -> list[Bar]:
        """
        获取K线数据
        period: 1d/1w/1m/5m/15m/30m/60m/1min
        """
        m = 1 if market.upper() == "SH" else 0
        period_map = {
            "1d": 9,
            "1w": 5,
            "1m": 6,
            "1min": 7,
            "5m": 0,
            "15m": 1,
            "30m": 2,
            "60m": 3,
        }
        category = period_map.get(period, 9)
        body = build_bars_request(category, m, code, start, count)
        resp = self._send_recv(body)
        bars = parse_bars(resp, category)
        for bar in bars:
            bar.code = code
            bar.market = market.upper()
        return bars

    def get_index_bars(
        self,
        code: str,
        market: str = "SH",
        period: str = "1d",
        count: int = 100,
        start: int = 0,
    ) -> list[Bar]:
        """获取指数K线"""
        from ..protocol.requests import build_index_bars_request

        m = 1 if market.upper() == "SH" else 0
        period_map = {"1d": 9, "5m": 0, "15m": 1, "30m": 2, "60m": 3}
        category = period_map.get(period, 9)
        body = build_index_bars_request(category, m, code, start, count)
        resp = self._send_recv(body)
        bars = parse_bars(resp, category)
        for bar in bars:
            bar.code = code
            bar.market = market.upper()
        return bars

    # === 分时数据 ===

    def get_minute_time(
        self, code: str, market: str = "SH", use_bars: bool = True
    ) -> list[dict]:
        """获取当日分时数据

        Args:
            code: 股票代码
            market: 市场 (SH/SZ)
            use_bars: 是否使用1分钟K线代替（更可靠）

        Returns:
            分时数据列表，每项包含 price 和 volume
        """
        if use_bars:
            bars = self.get_bars(code, market, "1min", 240)
            return [{"price": b.close, "volume": b.volume} for b in bars]

        m = 1 if market.upper() == "SH" else 0
        body = build_minute_time_request(m, code)
        resp = self._send_recv(body)
        return parse_minute_time(resp)

    def get_history_minute_time(
        self, code: str, market: str = "SH", date: int = None
    ) -> list[dict]:
        """获取历史分时数据"""
        m = 1 if market.upper() == "SH" else 0
        import datetime

        date = date or int(datetime.datetime.now().strftime("%Y%m%d"))
        body = build_history_minute_request(m, code, date)
        resp = self._send_recv(body)
        return parse_history_minute_time(resp)

    # === 分笔成交 ===

    def get_transactions(
        self, code: str, market: str = "SH", start: int = 0, count: int = 100
    ) -> list[Tick]:
        """获取分笔成交数据"""
        m = 1 if market.upper() == "SH" else 0
        body = build_transaction_request(m, code, start, count)
        resp = self._send_recv(body)
        return parse_ticks(resp, m, code)

    def get_history_transactions(
        self,
        code: str,
        market: str = "SH",
        date: int = None,
        start: int = 0,
        count: int = 100,
    ) -> list[Tick]:
        """获取历史分笔成交"""
        from ..protocol.requests import build_history_transaction_request

        m = 1 if market.upper() == "SH" else 0
        import datetime

        date = date or int(datetime.datetime.now().strftime("%Y%m%d"))
        body = build_history_transaction_request(m, code, start, count, date)
        resp = self._send_recv(body)
        return parse_ticks(resp, m, code)

    # === 股票列表 ===

    def get_stock_count(self, market: str = "SH") -> int:
        """获取市场股票总数"""
        m = self._parse_market(market)
        body = build_stock_count_request(m)
        resp = self._send_recv(body)
        return parse_stock_count(resp)

    def get_security_list(
        self, market: str = "SH", start: int = 0, count: int = None
    ) -> list[dict]:
        """获取股票列表（分页）"""
        m = self._parse_market(market)
        if count is None:
            count = self.get_stock_count(market)
        results = []
        pos = start
        while pos < count:
            body = build_security_list_request(m, pos)
            resp = self._send_recv(body)
            page = parse_security_list(resp, m)
            if not page:
                break
            results.extend(page)
            pos += len(page)
        return results

    def get_security_list_by_region(
        self, region: int, start: int = 0, count: int = 100
    ) -> list[dict]:
        """按板块获取股票列表"""
        from ..protocol.requests import build_security_list_request

        results = []
        pos = start
        while len(results) < count:
            body = build_security_list_request(region, pos)
            resp = self._send_recv(body)
            page = parse_security_list(resp, region)
            if not page:
                break
            results.extend(page)
            pos += len(page)
        return results[:count]

    # === 财务数据 ===

    def get_xdxr_info(self, code: str, market: str = "SH") -> list[dict]:
        """获取除权除息数据"""
        m = self._parse_market(market)
        body = build_xdxr_request(m, code)
        resp = self._send_recv(body)
        return parse_xdxr_info(resp)

    def get_finance_info(self, code: str, market: str = "SH") -> dict:
        """获取财务数据"""
        m = self._parse_market(market)
        body = build_finance_request(m, code)
        resp = self._send_recv(body)
        return parse_finance_info(resp)

    # === 公司信息/板块信息 ===

    def get_company_info_category(self, code: str, market: str = "SH") -> list[dict]:
        """获取公司信息目录"""
        from ..protocol.requests import build_company_info_category_request
        from ..parser import parse_company_info_category

        m = self._parse_market(market)
        body = build_company_info_category_request(m, code)
        resp = self._send_recv(body)
        return parse_company_info_category(resp)

    def get_company_info_content(
        self,
        code: str,
        market: str = "SH",
        filename: str = "",
        start: int = 0,
        length: int = 6000,
    ) -> bytes:
        """获取公司信息内容"""
        from ..protocol.requests import build_company_info_content_request
        from ..parser import parse_company_info_content

        m = self._parse_market(market)
        body = build_company_info_content_request(m, code, filename, start, length)
        resp = self._send_recv(body)
        return parse_company_info_content(resp)

    def get_block_info_meta(self, blockfile: str = "block.dat") -> dict:
        """获取板块信息元数据"""
        from ..protocol.requests import build_block_info_meta_request
        from ..parser import parse_block_info_meta

        body = build_block_info_meta_request(blockfile)
        resp = self._send_recv(body)
        return parse_block_info_meta(resp)

    def get_block_info(
        self, blockfile: str = "block.dat", start: int = 0, size: int = 100
    ) -> list[dict]:
        """获取板块信息内容"""
        from ..protocol.requests import build_block_info_request
        from ..parser import parse_block_info

        body = build_block_info_request(blockfile, start, size)
        resp = self._send_recv(body)
        return parse_block_info(resp)

    # === 上下文管理 ===

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
