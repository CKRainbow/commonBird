import os
from typing import Optional, Type
from dotenv import load_dotenv, set_key

from src import env_path
from src.birdreport.birdreport import Birdreport
from src.ebird.ebird import EBird
from src.utils.api_exceptions import ApiErrorBase


def store_token(token_name, token) -> None:
    set_key(
        dotenv_path=env_path,
        key_to_set=token_name,
        value_to_set=token,
    )
    load_dotenv(env_path)


async def check_token(
    token_name: str,
    cls: Type,
) -> Optional[Birdreport | EBird]:
    token = os.getenv(token_name)
    try:
        client = await cls.create(token)
        store_token(token_name, token)
        return client
    except ApiErrorBase:
        return
