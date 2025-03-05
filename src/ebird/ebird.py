import json
import os
import asyncio
import datetime
from typing import Dict
from enum import Enum

import httpx
from dotenv import load_dotenv
from ebird.api.validation import (
    clean_back,
    clean_dist,
    clean_lat,
    clean_lng,
    clean_location,
    clean_region,
)
from ebird.api.hotspots import REGION_HOTSPOTS_URL
from ebird.api.regions import REGION_LIST_URL

from src import database_path


class RegionType(Enum):
    COUNTRY = "country"
    SUBNATIONAL1 = "subnational1"
    SUBNATIONAL2 = "subnational2"


async def call(url: str, params: Dict, headers: Dict) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        res = response.json()
    return res


class EBird:
    def __init__(self, token, locale="zh_SIM"):
        self.token = token
        self.locale = locale

    @classmethod
    async def create(cls, token: str):
        instance = cls(token)
        res = await instance.get_regions(RegionType.SUBNATIONAL1, "MO")
        print(res)
        return instance

    async def get_hotspots(self, region: str, back: int = None):
        url = REGION_HOTSPOTS_URL % clean_region(region)
        params = {
            "fmt": "json",
        }
        if back is not None:
            params["back"] = clean_back(back)
        headers = {"X-eBirdApiToken": self.token}

        res = await call(url, params, headers)
        return res

    async def update_cn_hotspots(self):
        res = await self.get_hotspots("CN")
        res = {hotspot["locName"]: hotspot for hotspot in res}
        res = {
            "last_update_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "data": res,
        }
        old_cn_hotspots = database_path / "ebird_cn_hotspots.json"
        old_cn_hotspots_bak = old_cn_hotspots.with_suffix(".json.bak")
        if old_cn_hotspots_bak.exists():
            os.remove(old_cn_hotspots_bak)
        os.rename(old_cn_hotspots, old_cn_hotspots.with_suffix(".json.bak"))
        with open(old_cn_hotspots, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        tw_res = await self.get_hotspots("TW")
        hk_res = await self.get_hotspots("HK")
        mo_res = await self.get_hotspots("MO")
        res = tw_res + hk_res + mo_res
        res = {hotspot["locName"]: hotspot for hotspot in res}
        res = {
            "last_update_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "data": res,
        }
        old_other_hotspots = database_path / "ebird_other_hotspots.json"
        old_other_hotspots_bak = old_other_hotspots.with_suffix(".json.bak")
        if old_other_hotspots_bak.exists():
            os.remove(old_other_hotspots_bak)
        os.rename(old_other_hotspots, old_other_hotspots.with_suffix(".json.bak"))
        with open(old_other_hotspots, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    async def get_regions(self, region_type: RegionType, region: str):
        url = REGION_LIST_URL % (region_type.value, clean_region(region))

        params = {"fmt": "json", "locale": self.locale}

        headers = {
            "X-eBirdApiToken": self.token,
        }

        res = await call(url, params, headers)
        return res


if __name__ == "__main__":
    load_dotenv()
    ebird = EBird(os.getenv("EBIRD_TOKEN"))

    async def inner():
        result = []
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "CN"))
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "MO"))
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "HK"))
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "TW"))
        return result

    result = asyncio.run(inner())

    with open("regions.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
