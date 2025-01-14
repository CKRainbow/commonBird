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

    # TODO: cn 也需要重新跑一次

    with open(database_path / "location_map_.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
