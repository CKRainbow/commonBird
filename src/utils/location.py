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
    "CN-34": "安徽省",
    "CN-11": "北京市",
    "CN-50": "重庆市",
    "CN-35": "福建省",
    "CN-62": "甘肃省",
    "CN-44": "广东省",
    "CN-45": "广西壮族自治区",
    "CN-52": "贵州省",
    "CN-46": "海南省",
    "CN-13": "河北省",
    "CN-23": "黑龙江省",
    "CN-41": "河南省",
    "CN-42": "湖北省",
    "CN-43": "湖南省",
    "CN-32": "江苏省",
    "CN-36": "江西省",
    "CN-22": "吉林省",
    "CN-21": "辽宁省",
    "CN-15": "内蒙古自治区",
    "CN-64": "宁夏回族自治区",
    "CN-63": "青海省",
    "CN-61": "陕西省",
    "CN-37": "山东省",
    "CN-31": "上海市",
    "CN-14": "山西省",
    "CN-51": "四川省",
    "CN-12": "天津市",
    "CN-65": "新疆维吾尔自治区",
    "CN-54": "西藏自治区",
    "CN-53": "云南省",
    "CN-33": "浙江省",
    "MO-": "澳门特别行政区",
    "HK-": "香港特别行政区",
    "TW-CHA": "彰化县",
    "TW-CYI": "嘉义市",
    "TW-CYQ": "嘉义县",
    "TW-HSZ": "新竹市",
    "TW-HSQ": "新竹县",
    "TW-HUA": "花莲县",
    "TW-KHH": "高雄市",
    "TW-KEE": "基隆市",
    "TW-KIN": "金门县",
    "TW-LIE": "连江县",
    "TW-MIA": "苗栗县",
    "TW-NAN": "南投县",
    "TW-TPQ": "新北市",
    "TW-PEN": "澎湖县",
    "TW-PIF": "屏东县",
    "TW-TXG": "台中市",
    "TW-TNN": "台南市",
    "TW-TPE": "台北市",
    "TW-TTT": "台东县",
    "TW-TAO": "桃园市",
    "TW-ILA": "宜兰县",
    "TW-YUN": "云林县",
}
NAME_TO_EBIRD_REGION_CODE = {
    value: key for key, value in EBIRD_REGION_CODE_TO_NAME.items()
}

AB_LOCATION = {
    "BJ": "北京市",
    "TJ": "天津市",
    "SH": "上海市",
    "AH": "安徽省",
    "JS": "江苏省",
    "JX": "江西省",
    "ZJ": "浙江省",
    "FJ": "福建省",
    "GD": "广东省",
    "GX": "广西壮族自治区",
    "GZ": "贵州省",
    "HAN": "海南省",
    "HEB": "河北省",
    "HEN": "河南省",
    "SHX": "陕西省",
    "SD": "山东省",
    "SX": "山西省",
    "HUN": "湖南省",
    "HUB": "湖北省",
    "HLJ": "黑龙江省",
    "JL": "吉林省",
    "LN": "辽宁省",
    "GS": "甘肃省",
    "NMG": "内蒙古自治区",
    "NX": "宁夏回族自治区",
    "QH": "青海省",
    "SC": "四川省",
    "CQ": "重庆市",
    "XJ": "新疆维吾尔自治区",
    "XZ": "西藏自治区",
    "YN": "云南省",
    "TW": "台湾省",
    "HK": "香港特别行政区",
    "MO": "澳门",
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
