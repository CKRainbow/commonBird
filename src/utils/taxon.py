import json
from pathlib import Path
from typing import List

import pandas as pd

from src.utils.location import AB_LOCATION
from src import database_path

Z3_TO_Z4 = {
    "大山雀": "欧亚大山雀",
    "远东山雀": "大山雀",
    "黑胸山鹪莺": "黑喉山鹪莺",
    "黑喉山鹪莺": "白喉山鹪莺",
    "怀氏虎鸫": "虎斑地鸫",
    "虎斑地鸫": "小虎斑地鸫",
    "理氏鹨": "田鹨",
    "田鹨": "东方田鹨",
    "喜山红眉朱雀": "红眉朱雀",
    "红眉朱雀": "中华朱雀",
    "点翅朱雀": "淡腹点翅朱雀",
    "喜山点翅朱雀": "点翅朱雀",
    "灰眉岩鹀": "淡灰眉岩鹀",
    "戈氏岩鹀": "灰眉岩鹀",
}


def process_loc(loc):
    splited = loc.split("-")
    if len(splited) >= 1:
        prov = AB_LOCATION[splited[0]]
        if len(splited) >= 2:
            return f"{prov}-{splited[1]}"
        else:
            return prov


def highlight_rows(row, idxs):
    if row.name in idxs:
        return ["color: red"] * len(row)
    else:
        return [""] * len(row)


def preview_taxon_map(map_file: Path, output_path: Path):
    taxon_map = json.load(open(map_file, "r", encoding="utf-8"))

    br_taxon_infos = json.load(
        open(database_path / "birdreport_taxon_infos.json", "r", encoding="utf-8")
    )
    br_taxon_infos = {
        id: taxon_info
        for id, taxon_info in br_taxon_infos["Z4"].items()
        if int(id) >= 4000 and int(id) < 9000
    }

    ebird_taxon_infos = json.load(
        open(database_path / "ebird_taxonomy.json", "r", encoding="utf-8")
    )

    ebird_taxon_infos = {
        taxon_info["sciName"]: taxon_info for taxon_info in ebird_taxon_infos
    }

    header = ["原学名", "原俗名", "", "现学名", "现俗名", "备注"]

    df = pd.DataFrame(columns=header)

    changed_idx = []

    for id, taxon_info in br_taxon_infos.items():
        latinname = taxon_info["latinname"].strip()
        name = taxon_info["name"]
        if latinname in taxon_map:
            converted_latinname = taxon_map[latinname]
            if isinstance(converted_latinname, List):
                for idx, convert_cond in enumerate(converted_latinname):
                    note = ""
                    if "loc" in convert_cond:
                        note = ",".join(
                            [process_loc(loc) for loc in convert_cond["loc"]]
                        )
                    else:
                        note = "其他"
                    if "time" in convert_cond:
                        note += "&" + convert_cond["time"]
                    if idx == 0:
                        df.loc[len(df)] = [
                            latinname,
                            name,
                            "->",
                            ebird_taxon_infos[convert_cond["name"]]["sciName"],
                            ebird_taxon_infos[convert_cond["name"]]["comName"],
                            note,
                        ]
                    else:
                        df.loc[len(df)] = [
                            "",
                            "",
                            "->",
                            ebird_taxon_infos[convert_cond["name"]]["sciName"],
                            ebird_taxon_infos[convert_cond["name"]]["comName"],
                            note,
                        ]
                    changed_idx.append(len(df) - 1)
            else:
                ebird_taxon_info = ebird_taxon_infos[converted_latinname]
                df.loc[len(df)] = [
                    latinname,
                    name,
                    "->",
                    ebird_taxon_info["sciName"],
                    ebird_taxon_info["comName"],
                    "",
                ]
                changed_idx.append(len(df) - 1)
        else:
            ebird_taxon_info = ebird_taxon_infos[latinname]
            df.loc[len(df)] = [
                latinname,
                name,
                "->",
                ebird_taxon_info["sciName"],
                ebird_taxon_info["comName"],
                "",
            ]

    df = df.style.apply(highlight_rows, axis=1, idxs=changed_idx)

    df.to_html(output_path, index=False)


def convert_taxon_z4_ebird(report, taxon_map):
    obs = report["obs"]
    prov = report["province_name"]
    city = report["city_name"]
    _, month, _ = report["start_time"].split(" ")[0].split("-")

    for taxon in obs:
        latin_name = taxon["latinname"].strip()
        if latin_name in taxon_map:
            converted_latinname = taxon_map[latin_name]
            if isinstance(converted_latinname, List):
                for idx, convert_cond in enumerate(converted_latinname):
                    if "loc" in convert_cond:
                        locs_cond = [process_loc(loc) for loc in convert_cond["loc"]]
                        if not ((prov in locs_cond) or (f"{prov}-{city}" in locs_cond)):
                            continue
                    if "time" in convert_cond:
                        # "time" can be "1-3,5-9"
                        time_ranges = convert_cond["time"].split(",")
                        time_range = set()
                        for tr in time_ranges:
                            if "-" in tr:
                                start, end = tr.split("-")
                                time_range.update(range(int(start), int(end) + 1))
                            else:
                                time_range.add(int(tr))
                        if int(month) not in time_range:
                            continue
                    taxon["latinname"] = convert_cond["name"]
                    break
            else:
                taxon["latinname"] = converted_latinname
