import json
import os
import re
import multiprocessing
import asyncio
from typing import Dict, List

from dotenv import load_dotenv

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
        print(group_name)
        if group_name in old_group_locs:
            continue

        if group_name in group_names:
            continue

        tasks.append(client.search_hotspots_by_name(hotspot["locName"]))
        group_names.append(group_name)

        if (
            len(tasks) % (multiprocessing.cpu_count() // 2) == 0
            or hotspot == ebird_hotspots[-1]
        ):
            result = await asyncio.gather(*tasks)
            result = [r["data"] for r in result]
            for idx, locs in enumerate(result):
                group_name = group_names[idx]
                old_group_locs[group_name] = locs
            tasks = []
            group_names = []
            print(result)
    return old_group_locs


if __name__ == "__main__":
    load_dotenv()
    br = Birdreport(os.getenv("BIRDREPORT_TOKEN"))

    async def inner(**kwargs):
        result = await extract_group_locations(br, **kwargs)
        return result

    with open(database_path / "group_locations.json", "r", encoding="utf-8") as f:
        old_group_locs = json.load(f)
    with open(database_path / "ebird_cn_hotspots.json", "r", encoding="utf-8") as f:
        ebird_hotspots = json.load(f)

    result = asyncio.run(
        inner(old_group_locs=old_group_locs, ebird_hotspots=ebird_hotspots)
    )

    with open(database_path / "group_locations_.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
