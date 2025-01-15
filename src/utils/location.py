import json
import os
import re
import multiprocessing
import asyncio
from typing import Dict, List

from dotenv import load_dotenv
from tqdm import tqdm

from src.birdreport.birdreport import Birdreport
from src import database_path

WITH_TRANS = r"(\S*)\s*\(.*\)"
GET_GROUPING = r"(\S*)\s*\[.*\]"

EBIRD_REGION_CODE_TO_NAME = {
    "CN-34": "Anhui",
    "CN-11": "Beijing",
    "CN-50": "Chongqing",
    "CN-35": "Fujian",
    "CN-62": "Gansu",
    "CN-44": "Guangdong",
    "CN-45": "Guangxi",
    "CN-52": "Guizhou",
    "CN-46": "Hainan",
    "CN-13": "Hebei",
    "CN-23": "Heilongjiang",
    "CN-41": "Henan",
    "CN-42": "Hubei",
    "CN-43": "Hunan",
    "CN-32": "Jiangsu",
    "CN-36": "Jiangxi",
    "CN-22": "Jilin",
    "CN-21": "Liaoning",
    "CN-15": "Nei Mongol",
    "CN-64": "Ningxia",
    "CN-63": "Qinghai",
    "CN-61": "Shaanxi",
    "CN-37": "Shandong",
    "CN-31": "Shanghai",
    "CN-14": "Shanxi",
    "CN-51": "Sichuan",
    "CN-12": "Tianjin",
    "CN-65": "Xinjiang",
    "CN-54": "Xizang",
    "CN-53": "Yunnan",
    "CN-33": "Zhejiang",
    "MO-": "Macau",
    "HK-": "Hong Kong",
    "TW-CHA": "Changhua County",
    "TW-CYI": "Chiayi City",
    "TW-CYQ": "Chiayi County",
    "TW-HSZ": "Hsinchu City",
    "TW-HSQ": "Hsinchu County",
    "TW-HUA": "Hualien County",
    "TW-KHH": "Kaohsiung City",
    "TW-KEE": "Keelung City",
    "TW-KIN": "Kinmen County",
    "TW-LIE": "Lienchiang County",
    "TW-MIA": "Miaoli County",
    "TW-NAN": "Nantou County",
    "TW-TPQ": "New Taipei City",
    "TW-PEN": "Penghu County",
    "TW-PIF": "Pingtung County",
    "TW-TXG": "Taichung City",
    "TW-TNN": "Tainan City",
    "TW-TPE": "Taipei City",
    "TW-TTT": "Taitung County",
    "TW-TAO": "Taoyuan City",
    "TW-ILA": "Yilan County",
    "TW-YUN": "Yunlin County",
}


def process_name(name):
    matches = re.match(WITH_TRANS, name)
    if matches:
        name = matches.group(1)

    matches = re.match(GET_GROUPING, name)
    if matches:
        group_name = matches.group(1)
    elif name.find("--") != -1:
        group_name = name.split("--")[0]
    else:
        group_name = name

    return (name, group_name)


async def extract_group_locations(
    client: Birdreport, ebird_hotspots: List, old_group_locs: Dict = None
) -> Dict:
    if old_group_locs is None:
        old_group_locs = []

    tasks = []
    group_names = []
    for hotspot in ebird_hotspots:
        name, group_name = process_name(hotspot["locName"])
        if group_name in old_group_locs:
            continue

        if group_name not in group_names:
            tasks.append(client.member_search_hotspots_by_name(group_name))
            group_names.append(group_name)

        if (
            len(tasks) % (multiprocessing.cpu_count() // 2) == 0
            or hotspot == ebird_hotspots[-1]
        ):
            result = await asyncio.gather(*tasks)
            for idx, locs in enumerate(result):
                group_name = group_names[idx]
                old_group_locs[group_name] = locs
            tasks = []
            group_names = []
    return old_group_locs


async def get_location_map(
    client: Birdreport,
    ebird_hotspots: List,
    old_location_map: Dict = None,
    group_locs: Dict = None,
) -> Dict:
    if old_location_map is None:
        old_location_map = []

    tasks = []
    group_names = []
    names = []
    for hotspot in tqdm(ebird_hotspots):
        name = hotspot["locName"]
        _, group_name = process_name(hotspot["locName"])
        lat, lng = hotspot["lat"], hotspot["lng"]
        if name in old_location_map:
            continue

        tasks.append(client.member_search_hotspots_nearby(5, lat, lng))
        group_names.append(group_name)
        names.append(name)

        if (
            len(tasks) % (multiprocessing.cpu_count() // 2) == 0
            or hotspot == ebird_hotspots[-1]
        ):
            result = await asyncio.gather(*tasks)
            for idx, locs in enumerate(result):
                group_name = group_names[idx]
                name = names[idx]
                if group_locs is not None:
                    group_loc = group_locs[group_name]
                    locs.extend(group_loc)
                locs = list(set([loc["point_name"] for loc in locs]))
                old_location_map[name] = locs
            tasks = []
            group_names = []
            names = []
    return old_location_map


if __name__ == "__main__":
    load_dotenv()
    br = Birdreport(os.getenv("BIRDREPORT_TOKEN"))

    async def inner(**kwargs):
        result = await get_location_map(br, **kwargs)
        return result

    with open(database_path / "group_locations.json", "r", encoding="utf-8") as f:
        group_locs = json.load(f)
    with open(database_path / "ebird_other_hotspots.json", "r", encoding="utf-8") as f:
        ebird_hotspots = json.load(f)
    with open(database_path / "location_map.json", "r", encoding="utf-8") as f:
        old_location_map = json.load(f)

    result = asyncio.run(
        inner(
            group_locs=None,
            ebird_hotspots=ebird_hotspots,
            old_location_map=old_location_map,
        )
    )

    with open(database_path / "location_map_.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
