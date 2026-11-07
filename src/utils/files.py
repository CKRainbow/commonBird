"""本地数据文件读写的小工具。

数据库目录可能不可写（例如安装在 Program Files 下），文件也可能缺失或被改坏。
这里把这类问题统一处理掉：读取失败返回默认值并记日志，写入失败抛出
DataFileError，让调用方能够弹出提示而不是让程序直接崩溃。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.utils.api_exceptions import DataFileError


def read_json(path: Path, default: Any = None, *, what: str = "") -> Any:
    """读取 JSON 文件；文件缺失或内容损坏时返回 default 并记录日志。"""
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logging.error(f"读取 {what or path.name} 失败：{e}")
        return default


def write_json(
    path: Path, data: Any, *, indent: int = 2, backup: bool = False
) -> None:
    """写入 JSON 文件。

    Args:
        backup: 写入前把已有文件改名为 .bak（旧文件缺失时忽略）。

    Raises:
        DataFileError: 目录不可写、磁盘满等本地文件错误。
    """
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if backup and path.exists():
            bak = path.with_suffix(path.suffix + ".bak")
            if bak.exists():
                bak.unlink()
            os.replace(path, bak)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp, path)
    except OSError as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise DataFileError(f"无法写入 {path.name}：{e}") from e
