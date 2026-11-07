"""Token 的清理与基本合法性校验。

这里刻意不做长度/字符集的硬性限制：eBird 的 API key 已经从 12 位短串换成了
8-4-4-4-12 的 UUID 形式，写死格式会导致服务方更换格式后 token 无法使用。
token 是否有效最终由服务器判定。
"""

from typing import Optional


def normalize_token(token: Optional[str]) -> str:
    """去掉复制粘贴时可能带入的空白字符（token 本身不含空白）。"""
    if token is None:
        return ""
    return "".join(token.split())


def validate_token(token: Optional[str]) -> str:
    """返回规范化后的 token，明显不可能合法的输入抛出 ValueError。"""
    token = normalize_token(token)
    if not token:
        raise ValueError("Token 不能为空")
    if not token.isascii() or not token.isprintable():
        raise ValueError("Token 包含非法字符，请检查是否复制了多余的内容")
    return token
