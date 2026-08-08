"""UUIDv7 生成（Python 3.11 无 stdlib uuid7）。"""

from __future__ import annotations

import os
import time
import uuid


def new_id() -> str:
    """生成小写带连字符的 UUID v7 字符串。"""
    timestamp_ms = time.time_ns() // 1_000_000
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    value = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
    value |= 0x7 << 76
    value |= rand_a << 64
    value |= 0x2 << 62
    value |= rand_b
    return str(uuid.UUID(int=value))
