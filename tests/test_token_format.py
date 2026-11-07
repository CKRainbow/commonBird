import pytest

from src.utils.token_format import normalize_token, validate_token

# eBird 旧版（12 位短串）与新版（8-4-4-4-12 的 UUID）两种 token 形态
OLD_STYLE_TOKEN = "jfekrij2sdc"
NEW_STYLE_TOKEN = "6f9a1c3e-8b21-4d7a-9f0c-1b2d3e4f5a6b"


@pytest.mark.parametrize("token", [OLD_STYLE_TOKEN, NEW_STYLE_TOKEN])
def test_validate_token_accepts_both_ebird_formats(token):
    assert validate_token(token) == token


@pytest.mark.parametrize(
    "raw",
    [
        f"  {NEW_STYLE_TOKEN}\n",
        f"\t{NEW_STYLE_TOKEN} ",
        f"{NEW_STYLE_TOKEN}\r\n",
    ],
)
def test_validate_token_strips_pasted_whitespace(raw):
    assert validate_token(raw) == NEW_STYLE_TOKEN


@pytest.mark.parametrize("raw", [None, "", "   ", "\n\t "])
def test_validate_token_rejects_empty(raw):
    with pytest.raises(ValueError):
        validate_token(raw)


def test_validate_token_rejects_non_ascii():
    with pytest.raises(ValueError):
        validate_token("6f9a1c3e-8b21-4d7a-密钥")


def test_normalize_token_never_returns_none():
    assert normalize_token(None) == ""
