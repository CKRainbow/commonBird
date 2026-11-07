import json
from pathlib import Path
from typing import List

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
        # 未知省份代码不应让整个转换过程崩溃，原样保留
        prov = AB_LOCATION.get(splited[0], splited[0])
        if len(splited) >= 2:
            return f"{prov}-{splited[1]}"
        else:
            return prov


def highlight_rows(row, changed_idx, questionalble_idx):
    if row.name in changed_idx:
        return ["color: green"] * len(row)
    elif row.name in questionalble_idx:
        return ["color: red"] * len(row)
    else:
        return [""] * len(row)


def preview_taxon_map(map_file: Path, output_path: Path):
    import pandas as pd

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
    questionalble_idx = []

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
            ebird_com_name = ebird_taxon_info["comName"]
            df.loc[len(df)] = [
                latinname,
                name,
                "->",
                ebird_taxon_info["sciName"],
                ebird_com_name,
                "",
            ]
            if name != ebird_com_name:
                questionalble_idx.append(len(df) - 1)

    df = df.style.apply(
        highlight_rows,
        axis=1,
        changed_idx=changed_idx,
        questionalble_idx=questionalble_idx,
    )

    df.to_html(output_path, index=False)


def convert_taxon_z4_ebird(report, taxon_map):
    obs = report.get("obs") or []
    prov = report.get("province_name", "")
    city = report.get("city_name", "")
    # start_time 形如 "2025-11-08 08:25:00"；格式异常时不做“按月份筛选”的转换
    month = None
    date_part = (report.get("start_time") or "").split(" ")[0]
    date_parts = date_part.split("-")
    if len(date_parts) >= 2 and date_parts[1].isdigit():
        month = int(date_parts[1])

    for taxon in obs:
        latin_name = (taxon.get("latinname") or "").strip()
        if not latin_name:
            continue
        if latin_name in taxon_map:
            converted_latinname = taxon_map[latin_name]
            if isinstance(converted_latinname, List):
                for idx, convert_cond in enumerate(converted_latinname):
                    new_name = convert_cond.get("name")
                    if not isinstance(new_name, str):
                        continue
                    if "loc" in convert_cond:
                        locs_cond = [process_loc(loc) for loc in convert_cond["loc"]]
                        if not ((prov in locs_cond) or (f"{prov}-{city}" in locs_cond)):
                            continue
                    if "time" in convert_cond:
                        if month is None:
                            # 无法判断月份，跳过带月份条件的转换，避免错误替换
                            continue
                        # "time" can be "1-3,5-9"
                        time_ranges = str(convert_cond["time"]).split(",")
                        time_range = set()
                        for tr in time_ranges:
                            if "-" in tr:
                                start, end = tr.split("-")
                                time_range.update(range(int(start), int(end) + 1))
                            else:
                                time_range.add(int(tr))
                        if month not in time_range:
                            continue
                    taxon["latinname"] = new_name
                    break
            else:
                taxon["latinname"] = converted_latinname
