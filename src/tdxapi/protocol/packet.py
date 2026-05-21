"""
通达信协议数据包构造与解析

协议结构（基于 pytdx 源码校准）：

发送包头（行情查询类，10 字节）：
    <HIHH>
    H: magic (0x010c)
    I: seq_id (0x02006320 等)
    H: pkg_len (包体长度)
    H: pkg_len (重复)

响应包头（16 字节）：
    <IIIHH>
    I: unknown1 (0x0074cbb1 等)
    I: seq_id
    I: zip_size (压缩后包体长度)
    H: unzip_size (解压前长度)
    H: unknown2

注意：当 zip_size != unzip_size 时，body 需要 zlib 解压
"""

import struct
import zlib
from dataclasses import dataclass
from .constants import RSP_HEADER_LEN


@dataclass
class RspHeader:
    """响应包头 16 字节"""

    unknown1: int = 0
    seq_id: int = 0
    zip_size: int = 0
    unzip_size: int = 0
    unknown2: int = 0

    def pack(self) -> bytes:
        return struct.pack(
            "<IIIHH",
            self.unknown1,
            self.seq_id,
            self.zip_size,
            self.unzip_size,
            self.unknown2,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "RspHeader":
        unknown1, seq_id, zip_size, unzip_size, unknown2 = struct.unpack(
            "<IIIHH", data[:RSP_HEADER_LEN]
        )
        return cls(
            unknown1=unknown1,
            seq_id=seq_id,
            zip_size=zip_size,
            unzip_size=unzip_size,
            unknown2=unknown2,
        )


def decode_response_body(raw_body: bytes, header: RspHeader) -> bytes:
    """
    解码响应包体
    如果 zip_size != unzip_size，说明数据被 zlib 压缩过，需要解压
    """
    if header.zip_size != header.unzip_size:
        return zlib.decompress(raw_body)
    return raw_body


def recv_full_response(sock, header_len: int = RSP_HEADER_LEN) -> tuple:
    """
    从 socket 接收完整响应
    返回 (RspHeader, decoded_body_bytes)
    """
    # 1. 接收包头
    head_buf = _recv_exact(sock, header_len)
    if len(head_buf) != header_len:
        raise ConnectionError(
            f"响应包头接收失败，期望 {header_len} 字节，实际 {len(head_buf)} 字节"
        )

    header = RspHeader.unpack(head_buf)

    # 2. 接收包体
    body_buf = bytearray()
    while len(body_buf) < header.zip_size:
        chunk = sock.recv(header.zip_size - len(body_buf))
        if not chunk:
            raise ConnectionError("接收包体时连接断开")
        body_buf.extend(chunk)

    # 3. 解码（可能需要 zlib 解压）
    decoded = decode_response_body(bytes(body_buf), header)
    return header, decoded


def _recv_exact(sock, n: int) -> bytes:
    """精确接收 n 字节"""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data
