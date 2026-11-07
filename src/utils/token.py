import os
from typing import Optional, Type
from dotenv import load_dotenv, set_key

from src import env_path
from src.birdreport.birdreport import Birdreport
from src.ebird.ebird import EBird
from src.utils.api_exceptions import ApiErrorBase
from src.utils.token_format import normalize_token, validate_token

__all__ = [
    "normalize_token",
    "validate_token",
    "store_token",
    "check_token",
]


def store_token(token_name, token) -> None:
    set_key(
        dotenv_path=env_path,
        key_to_set=token_name,
        value_to_set=validate_token(token),
    )
    load_dotenv(env_path)


async def check_token(
    token_name: str,
    cls: Type,
) -> Optional[Birdreport | EBird]:
    try:
        token = validate_token(os.getenv(token_name))
        client = await cls.create(token)
        store_token(token_name, token)
        return client
    except (ApiErrorBase, ValueError):
        return
