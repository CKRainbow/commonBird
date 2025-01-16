import json
import os
import asyncio
import csv
import time
from typing import Dict, List
import pytz
import logging
from datetime import datetime
from pathlib import Path
from itertools import count

from dotenv import load_dotenv, set_key
from textual import on, work
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import VerticalScroll, HorizontalGroup, Grid
from textual.widgets import (
    Footer,
    Header,
    Button,
    Label,
    Input,
    LoadingIndicator,
    Select,
    ListView,
    ListItem,
)
from fuzzywuzzy.fuzz import partial_ratio

from src.birdreport.birdreport import Birdreport
from src.utils.location import EBIRD_REGION_CODE_TO_NAME
from src import application_path, database_path

logging.basicConfig(
    filename=application_path / "log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

env_path = application_path / ".env"
if not env_path.exists():
    open(env_path, "a").close()
load_dotenv(env_path)

EBIRD_RECORD_HEADER = [
    "Common Name",  # Required or Species
    "Genus",
    "Species",  # Required or Common Name
    "Species Count",
    "Species Comments",
    "Location name",  # Required
    "Latitude",
    "Longitude",
    "Observation date",  # Required MM/dd/yyyy
    "Start time",  # Required for non-casual HH:mm
    "State",
    "Country",
    "Protocol",
    "Number of observers",
    "Duration",
    "All observations reported?",
    "Distance covered",
    "Area covered",
    "Checklist Comments",
]

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

# TODO: Or use scientific name?
Z4_TO_EBIRD = {
    "淡腹点翅朱雀": "点翅朱雀",
    "点翅朱雀": "喜山点翅朱雀",
    "东方田鹨": "田鹨",
    "田鹨": "理氏鹨",
    "斑林鸽": "点斑林鸽",
    "毛腿夜鹰": "毛腿耳夜鹰",
    "库氏白腰雨燕": "印支白腰雨燕",
    "红脚斑秧鸡": "红腿斑秧鸡",
    "西秧鸡": "西方秧鸡",
    "白眉苦恶鸟": "白胸苦恶鸟",
    "黄斑苇鳽": "黄苇鳽",
    "黑苇鳽": "黑鳽",
    "栗头鳽": "栗鳽",
    "绿背鸬鹚": "暗绿背鸬鹚",
    "金鸻": "金斑鸻",
    "灰鸻": "灰斑鸻",
    "西滨鹬": "西方滨鹬",
    "小黑背银鸥": "小黑背鸥",
    "灰翅浮鸥": "须浮鸥",
    "绿拟啄木鸟": "斑头绿拟啄木鸟",
    "金背啄木鸟": "金背三趾啄木鸟",
    "纹喉绿啄木鸟": "鳞喉绿啄木鸟",
    "纹腹啄木鸟": "纹胸啄木鸟",
    "鹊鹂": "鹊色鹂",
    "西灰伯劳": "西方灰伯劳",
    "四川褐头山雀": "川褐头山雀",
    "中华短趾百灵": "蒙古短趾百灵",
    "短趾百灵": "亚洲短趾百灵",
    "白喉山鹪莺": "黑喉山鹪莺",
    "黑喉山鹪莺": "黑胸山鹪莺",
    "噪苇莺": "噪大苇莺",
    "蒲苇莺": "水蒲苇莺",
    "芦莺": "芦苇莺",
    "淡色崖沙燕": "淡色沙燕",
    "中亚叽喳柳莺": "东方叽喳柳莺",
    "漠白喉林莺": "沙白喉林莺",
    "细嘴钩嘴鹛": "剑嘴鹛",
    "台湾噪鹛": "玉山噪鹛",
    "红顶噪鹛": "金翅噪鹛",
    "栗额斑翅鹛": "锈额斑翅鹛",
    "白腹暗蓝鹟": "琉璃蓝鹟",
    "喜山蓝短翅鸫": "喜山短翅鸫",
    "台湾蓝短翅鸫": "台湾短翅鸫",
    "蓝额地鸲": "蓝额长脚地鸲",
    "紫颊太阳鸟": "紫颊直嘴太阳鸟",
    "红额金翅雀": "欧红额金翅雀/红额金翅雀",
    "橙腹叶鹎": "橙腹叶鹎 (灰冠蓝喉)",
    "丛林鸦": "丛林鸦 (levaillantii)",
    "日本云雀": "云雀 (东北亚)",
    "西南橙腹叶鹎": "橙腹叶鹎 (黄冠黑喉)",
    "日本冕柳莺": "饭岛柳莺",
    "紫花蜜鸟": "紫色花蜜鸟",
    # "斑头秋沙鸭": "",
    # "黄喉雉鹑": "",
    # "雉鸡": "",
    # "黑胸鹌鹑": "",
    # "信使圆尾鹱": "",
    # "灰胸秧鸡": "",
    # "白骨顶": "",
    # "红脚田鸡": "",
    # "石鸻": "",
    # "长嘴半蹼鹬": "",
    # "拉氏沙锥": "",
    # "黄胸滨鹬": "",
    # "中华凤头燕鸥": "",
    # "里海银鸥": "",
    "西伯利亚银鸥": "织女银鸥/蒙古银鸥 (西伯利亚银鸥)",
    "鹗": "鹗鹗",
    # "北棕腹鹰鹃": "",
    # "棕腹鹰鹃": "",
    # "东方中杜鹃": "",
    # "琉球角鸮": "",
    # "北领角鸮": "",
    # "毛腿雕鸮": "",
    # "凤头雨燕": "",
    # "普通雨燕": "",
    # "华西白腰雨燕": "",
    # "红脚隼": "",
    # "蓝腰鹦鹉": "",
    # "印度寿带": "",
    # "北星鸦": "",
    # "星鸦": "",
    # "白翅云雀": "",
    # "双斑百灵": "",
    # "灰喉沙燕": "",
    # "洋燕": "",
    # "喜山黄腹树莺": "",
    # "东亚蝗莺": "",
    # "纹胸鹛": "",
    # "红额穗鹛": "",
    # "灰腹鹩鹛": "",
    # "黑胸楔嘴穗鹛": "",
    # "楔嘴穗鹛": "",
    # "中华草鹛": "",
    # "棕胸雅鹛": "",
    # "灰头薮鹛": "",
    # "中华雀鹛": "",
    # "中南雀鹛": "",
    # "黑颏凤鹛": "",
    # "淡背地鸫": "",
    # "喜山淡背地鸫": "",
    # "四川淡背地鸫": "",
    # "虎斑地鸫": "",
    # "蒂氏鸫": "",
    # "黑喉鸫": "",
    # "旅鸫": "",
    # "侏蓝姬鹟": "",
    # "台湾林鸲": "",
    # "麻雀": "",
    # "红眉朱雀": "",
    # "中华朱雀": "",
    # "褐头朱雀": "",
    # "硫黄鹀": "",
}


async def dump_as_ebird_csv(reports, username, update_date):
    # FIXME: single csv file should be less than 1MB
    csvs = [[]]
    for report in reports:
        version = report["version"]

        start_time = time.strptime(report["start_time"], "%Y-%m-%d %H:%M:%S")
        end_time = time.strptime(report["end_time"], "%Y-%m-%d %H:%M:%S")
        duration = (time.mktime(end_time) - time.mktime(start_time)) // 60

        # FIXME: need alert
        duration = min(duration, 24 * 60)

        if "eye_all_birds" in report:
            all_observations_reported = "Y" if report["eye_all_birds"] != "" else "N"
        else:
            all_observations_reported = ""

        # TODO: add checklist comments
        checklist_comment = (
            report["note"].replace("\n", "\\n") if "note" in report else ""
        )
        if checklist_comment != "":
            checklist_comment += "\\n"
        # TODO: 可选是否添加
        checklist_comment += (
            f"Converted from BirdReport CN, report ID: {report['serial_id']}"
        )

        start_time = time.strftime("%m/%d/%Y %H:%M", start_time)
        observation_date, start_time = start_time.split(" ")
        country = "CN"
        location_name = report["point_name"]
        lat = report["lat"] if "lat" in report else ""
        lng = report["lng"] if "lng" in report else ""
        protocol = "stationary"  # historical
        num_observers = 1

        real_quality = report["real_quality"] if "real_quality" in report else None

        for entry in report["obs"]:
            if version == "G3":
                if entry["taxon_name"] in Z3_TO_Z4:
                    entry["taxon_name"] = Z3_TO_Z4[entry["taxon_name"]]
            if entry["taxon_name"] in Z4_TO_EBIRD:
                entry["taxon_name"] = Z4_TO_EBIRD[entry["taxon_name"]]
            common_name = entry["taxon_name"]

            species = entry["latinname"]
            species_count = (
                entry["taxon_count"]
                if real_quality is None or real_quality == 1
                else "X"
            )

            note = entry["note"].replace("\n", "\\n") if "note" in entry else ""

            species_comments = note
            # only for detail taxon
            # if entry["type"] == 2:
            #     species_comments += "\\nHeard."
            # if entry["outside_type"] != 0:
            #     species_comments += "\nOut of scope or not confirmed."
            csv_line = (
                common_name,
                "",
                species,
                species_count,
                species_comments,
                location_name,
                lat,
                lng,
                observation_date,
                start_time,
                "",
                country,
                protocol,
                num_observers,
                duration,
                all_observations_reported,
                "",
                "",
                checklist_comment,
            )
            csvs[-1].append(csv_line)
        if len(csvs[-1]) >= 4000:
            csvs.append([])

    for i in range(len(csvs)):
        with open(
            application_path / f"{username}_{update_date}_checklists_{i}.csv",
            "w",
            encoding="utf-8",
            newline="",
        ) as f:
            writer = csv.writer(f)
            writer.writerows(csvs[i])


class TokenInputScreen(ModalScreen):
    def __init__(self, token_name: str, hint_text: str, **kwargs):
        super().__init__(kwargs)
        self.token_name = token_name
        self.hint_text = hint_text

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.hint_text, id="hintText"),
            Input(id="token"),
            id="dialog",
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "token":
            user_input = event.input.value
            # TODO: validation
            self.dismiss({"token": user_input, "token_name": self.token_name})


class ConfirmScreen(ModalScreen):
    def __init__(self, message: str, **kwargs):
        super().__init__(kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.message, id="messageText"),
            Button("是", id="confirm", variant="primary"),
            Button("否", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        elif event.button.id == "cancel":
            self.dismiss(False)


class MessageScreen(ModalScreen):
    def __init__(self, message: str, **kwargs):
        super().__init__(kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.message, id="messageText"),
            Button("确定", id="confirm", variant="primary"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss()


class BirdreportSearchReportScreen(Screen):
    def __init__(self, birdreport: Birdreport, **kwargs):
        super().__init__(kwargs)
        self.birdreport = birdreport

    def compose(self) -> ComposeResult:
        yield Grid(
            HorizontalGroup(
                Label("用户名："), Input(id="username"), classes="text-group"
            ),
            HorizontalGroup(
                Label("地点："),
                Input(id="pointname"),
                classes="text-group",
            ),
            Button(
                "查询",
                id="query",
                variant="primary",
            ),
            classes="query_container",
        )

    # TODO; async running
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        async def background_sleep() -> None:
            await asyncio.sleep(3)
            self.dismiss()

        if event.button.id == "query":
            query_button = self.query_one("#query")
            query_button.disabled = True

            username = self.query_one("#username").value
            pointname = self.query_one("#pointname").value
            print(username, pointname)
            asyncio.create_task(background_sleep())


class SearchEbirdHotspotScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Grid(
            Input(id="hotspot_name"),
            Button(
                "查询",
                id="query",
                variant="primary",
            ),
            ListView(id="hotspot_listview"),
            classes="search_container",
        )

    @on(Button.Pressed, "#query")
    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        hotspot_name = self.query_one("#hotspot_name").value
        if hotspot_name == "":
            return

        hotspot_listview = self.query_one(ListView)
        await hotspot_listview.clear()

        # 繁体简体（或许可以都转为简体后搜索）
        hotspot_infos_cn = filter(
            lambda x: partial_ratio(hotspot_name, x["locName"]) > 80,
            self.app.ebird_cn_hotspots.values(),
        )
        hotspot_infos_other = filter(
            lambda x: partial_ratio(hotspot_name, x["locName"]) > 80,
            self.app.ebird_other_hotspots.values(),
        )

        hotspot_infos = list(hotspot_infos_cn) + list(hotspot_infos_other)

        if len(hotspot_infos) == 0:
            hotspot_listview.append(
                ListItem(
                    Label("无搜索结果，请尝试其他关键词"),
                    name=None,
                    classes="hotspot_item",
                )
            )
            return

        hotspot_listview.append(
            ListItem(Label("不做修改"), name=None, classes="hotspot_item")
        )
        for hotspot_info in hotspot_infos:
            hotspot_listview.append(
                ListItem(
                    Label(
                        hotspot_info["locName"]
                        + "\n"
                        + EBIRD_REGION_CODE_TO_NAME[hotspot_info["subnational1Code"]],
                    ),
                    name=hotspot_info["locName"],
                    classes="hotspot_item",
                )
            )

    @on(ListView.Selected)
    async def on_listview_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.name)


class SelectEbirdHotspotScreen(ModalScreen):
    def __init__(self, point_name: str, hotspots: List[str], **kwargs):
        super().__init__(kwargs)
        self.point_name = point_name
        self.hotspots = hotspots

    @work
    async def on_mount(self) -> None:
        if len(self.hotspots) == 0:
            self.dismiss()

        hotspot_listview = ListView(
            classes="hotspot_listview",
        )
        await self.mount(hotspot_listview)
        hotspot_items = []
        hotspot_items.append(
            ListItem(Label("不做修改", id="no_change"), classes="hotspot_item")
        )
        for hotspot_name in self.hotspots:
            hotspot_info = self.app.ebird_cn_hotspots.get(hotspot_name)
            if hotspot_info is None:
                hotspot_info = self.app.ebird_other_hotspots.get(hotspot_name)
            if hotspot_info is None:
                continue
            hotspot_item = ListItem(
                Label(
                    hotspot_name
                    + "\n"
                    + EBIRD_REGION_CODE_TO_NAME[hotspot_info["subnational1Code"]],
                    name=hotspot_name,
                ),
                classes="hotspot_item",
            )
            hotspot_items.append(hotspot_item)
        await hotspot_listview.mount(*hotspot_items)

    @on(ListView.Selected)
    def on_listview_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.children[0].name)


class BirdreportToEbirdLocationAssignScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.location_assign = {}
        for report in self.app.cur_birdreport_data:
            point_name = report["point_name"]
            if point_name not in self.location_assign:
                self.location_assign[point_name] = {
                    "province": (
                        report["province_name"] if "province_name" in report else ""
                    ),
                    "city": report["city_name"] if "city_name" in report else "",
                    "district": (
                        report["district_name"] if "district_name" in report else ""
                    ),
                    "reports": [],
                }
            self.location_assign[point_name]["reports"].append(report)

    @work
    async def on_mount(self) -> None:
        vertical_scroll = VerticalScroll(id="location_assign_scroll")
        await self.mount(vertical_scroll)
        await vertical_scroll.mount(
            HorizontalGroup(
                Label("观鸟记录中心地点", classes="assign_title"),
                Label("EBird地点", classes="assign_title"),
                Button("确认", id="confirm", variant="success"),
            )
        )
        horizonal_groups = []
        for point_id, (point_name, info) in enumerate(self.location_assign.items()):
            original_location_name = Label(
                point_name + "\n" + info["province"] + info["city"] + info["district"],
                classes="original_location_name",
            )

            converted_hotspot = Button(
                "不做修改",
                name=point_name,
                id="converted_hotspot_" + str(point_id),
                classes="converted_hotspot",
                variant="default",
            )

            search_button = Button(
                "搜索热点",
                name=point_name,
                id="search_button_" + str(point_id),
                classes="search_button",
                variant="primary",
            )

            # if point_name in self.app.br_to_ebird_location_map:
            #     options = [
            #         (name, name)
            #         for idx, name in enumerate(
            #             self.app.br_to_ebird_location_map[point_name]
            #         )
            #     ]
            # else:
            #     options = []
            # selection = Select(
            #     options=options,
            #     prompt="不做修改",
            #     name=point_name,
            #     id=f"select_{point_id}",
            # )

            assign_row = HorizontalGroup(
                original_location_name,
                converted_hotspot,
                search_button,
                classes="assign_row",
            )
            horizonal_groups.append(assign_row)
        await vertical_scroll.mount(*horizonal_groups)

    @on(Button.Pressed, "#confirm")
    def on_button_confirm_presses(self, event: Button.Pressed) -> None:
        for info in self.location_assign.values():
            if info.get("converted_hotspot") is not None:
                for report in info["reports"]:
                    # override or add new record?
                    report["point_name"] = info["converted_hotspot"]
                    report["lat"] = info["lat"] if info["lat"] is not None else ""
                    report["lng"] = info["lng"] if info["lng"] is not None else ""
        self.dismiss()

    @on(Button.Pressed, ".converted_hotspot")
    @work
    async def on_button_converted_hotspot_presses(self, event: Button.Pressed) -> None:
        hotspots = self.app.br_to_ebird_location_map.get(event.button.name)
        if hotspots is None:
            event.button.label = "无可选项，请尝试搜索"
            return
        hotspot_name = await self.app.push_screen_wait(
            SelectEbirdHotspotScreen(
                event.button.name,
                hotspots,
            )
        )

        if hotspot_name is None:
            event.button.label = "不做修改"
        else:
            event.button.label = hotspot_name

        self.modify_converted_hotspot(event.button.name, hotspot_name)

    @on(Button.Pressed, ".search_button")
    @work
    async def on_button_search_location_presses(self, event: Button.Pressed) -> None:
        hotspot_name = await self.app.push_screen_wait(SearchEbirdHotspotScreen())
        point_id = event.button.id.split("_")[-1]

        button: Button = self.query_one(f"#converted_hotspot_{point_id}")

        if hotspot_name is None:
            button.label = "不做修改"
        else:
            button.label = hotspot_name

        self.modify_converted_hotspot(event.button.name, hotspot_name)

    def modify_converted_hotspot(
        self, point_name: str, converted_hotspot_name: str
    ) -> None:
        # conveted_hotspot is None means remaining
        self.location_assign[point_name]["converted_hotspot"] = converted_hotspot_name

        if converted_hotspot_name is None:
            self.location_assign[point_name]["lat"] = None
            self.location_assign[point_name]["lng"] = None
        else:
            if converted_hotspot_name in self.app.ebird_cn_hotspots:
                location_info = self.app.ebird_cn_hotspots[converted_hotspot_name]
            elif converted_hotspot_name in self.app.ebird_hotspots:
                location_info = self.app.ebird_hotspots[converted_hotspot_name]
            else:
                return

            self.location_assign[point_name]["lat"] = location_info["lat"]
            self.location_assign[point_name]["lng"] = location_info["lng"]


class BirdreportToEbirdScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()

    @work
    async def on_mount(self) -> None:
        username = self.app.birdreport.user_info["username"]

        async def load_report(start_date: str = ""):
            checklists = await self.app.birdreport.member_get_reports(
                start_date=start_date
            )
            candi_dup_checklists = list(
                filter(
                    lambda x: x["start_time"].split(" ")[0] == start_date, checklists
                )
            )
            candi_dup_old_checklists = list(
                filter(
                    lambda x: x["start_time"].split(" ")[0] == start_date,
                    self.app.cur_birdreport_data,
                )
            )
            for candi_dup in candi_dup_checklists:
                for candi_dup_old in candi_dup_old_checklists:
                    if candi_dup["id"] == candi_dup_old["id"]:
                        checklists.remove(candi_dup)

            self.app.cur_birdreport_data += checklists

            self.cur_date = datetime.now(pytz.timezone("Asia/Shanghai")).strftime(
                "%Y-%m-%d"
            )

            with open(
                application_path / f"{username}_{self.cur_date}_checklists.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(self.app.cur_birdreport_data, f, ensure_ascii=False, indent=2)

            loading_label = self.query_one(LoadingIndicator)
            await loading_label.remove()
            # new_button = Button(
            #     "导出为EBird格式", id="export_to_ebird", variant="primary"
            # )
            # grid.mount(new_button)

        checklist_files = list(Path(".").glob(f"{username}_*_checklists.json"))
        use_existing = False

        # TODO: 记录时长太长应有提示跳出，终止任务
        if len(checklist_files) >= 1:
            checklist_file = checklist_files[0]
            use_existing = await self.app.push_screen_wait(
                ConfirmScreen(f"文件{checklist_file.name}已经存在\n是否使用已有数据？"),
            )
        if use_existing:
            with open(checklist_file, "r", encoding="utf-8") as f:
                self.app.cur_birdreport_data = json.load(f)
                update_date = checklist_file.stem.split("_")[-2]
            os.remove(checklist_file)
            await load_report(update_date)
        else:
            self.app.cur_birdreport_data = []
            await load_report()

        if self.app.br_to_ebird_location_map is not None:
            await self.app.push_screen_wait(BirdreportToEbirdLocationAssignScreen())

        new_button = Button("导出为EBird格式", id="export_to_ebird", variant="primary")
        await self.mount(new_button)

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "export_to_ebird":
            if any(
                map(
                    lambda x: x["version"] == "CH3",
                    self.app.cur_birdreport_data,
                )
            ):
                await self.app.push_screen_wait(
                    MessageScreen(
                        "检测到郑三版本数据，此类数据暂时不支持导出\n请手动迁移至郑四后重新导出。"
                    )
                )

            username = self.app.birdreport.user_info["username"]
            await dump_as_ebird_csv(
                self.app.cur_birdreport_data, username, self.cur_date
            )
            self.dismiss()


class DomainScreen(Screen):
    def store_token(self, token_name, token) -> None:
        set_key(
            dotenv_path=env_path,
            key_to_set=token_name,
            value_to_set=token,
        )
        load_dotenv(env_path)


class BirdreportScreen(DomainScreen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.change_token_hint = (
            "请输入观鸟记录中心的认证token\n具体获取方法参加 README.md 说明文件"
        )
        self.token_name = "BIRDREPORT_TOKEN"

        self.composition = VerticalScroll(
            Header(),
            Button(
                "获取记录",
                id="retrieve_report",
                tooltip="根据查询条件获取记录",
                disabled=True,
            ),
            Button(
                "记录迁移至EBird",
                id="convert_ebird",
                tooltip="将某用户的所有记录迁移至EBird",
            ),
            Button(
                "修改 Token", id="change_token", tooltip="修改观鸟记录中心的认证token"
            ),
            Button(
                "返回",
                id="back",
                variant="primary",
                tooltip="返回上一层",
            ),
            classes="option_container",
        )

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change_token":
            token = os.getenv(self.token_name)
            for i in count(0):
                if i == 0:
                    text = self.change_token_hint
                else:
                    text = "先前输入的token无效，请重新输入。"
                try:
                    if i == 0:
                        raise Exception
                    self.store_token(self.token_name, token)
                    token = os.getenv(self.token_name)
                    if (
                        not hasattr(self.app, "birdreport")
                        or self.app.birdreport.token != token
                    ):
                        self.app.birdreport = await Birdreport.create(token)
                    break
                except Exception:
                    token_result = await self.app.push_screen_wait(
                        TokenInputScreen(self.token_name, text),
                    )
                    token = token_result["token"]
        elif event.button.id == "retrieve_report":
            self.app.push_screen(
                BirdreportSearchReportScreen(self.app.birdreport),
            )
        elif event.button.id == "convert_ebird":
            self.app.push_screen(BirdreportToEbirdScreen())
        elif event.button.id == "back":
            self.app.pop_screen()

    def store_token(self, token_name: str, token: str) -> None:
        # the token must be 32 characters and consists of only number and letters
        if len(token) != 32 or not token.isalnum():
            raise ValueError(
                "token must be 32 characters and consists of only number and letters"
            )

        super().store_token(token_name, token)

    @work
    async def on_mount(self) -> None:
        self.title = "中国观鸟记录中心"
        self.sub_title = "可能会对记录中心服务器带来压力，酌情使用"
        token = os.getenv(self.token_name)
        for i in count(0):
            if i == 0:
                text = self.change_token_hint
            else:
                text = "先前输入的token无效，请重新输入。"
            try:
                if not token:
                    raise Exception
                self.store_token(self.token_name, token)
                token = os.getenv(self.token_name)
                if (
                    not hasattr(self.app, "birdreport")
                    or self.app.birdreport.token != token
                ):
                    self.app.birdreport = await Birdreport.create(token)
                break
            except Exception:
                token_result = await self.app.push_screen_wait(
                    TokenInputScreen(self.token_name, text),
                )
                token = token_result["token"]

        await self.mount(self.composition)


class EbirdScreen(DomainScreen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.change_token_hint = (
            "请输入EBird的API token\n具体获取方法参加 README.md 说明文件"
        )
        self.token_name = "EBIRD_TOKEN"

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Button("修改 Token", id="change_token", tooltip="修改EBird的API token"),
            classes="option_container",
        )

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change_token":
            token_result = await self.app.push_screen_wait(
                TokenInputScreen(self.token_name, self.change_token_hint),
            )
            self.store_token(token_result)

    @work
    async def on_mount(self) -> None:
        if not os.getenv(self.token_name):
            token_result = await self.app.push_screen_wait(
                TokenInputScreen(self.token_name, self.change_token_hint),
            )
            self.store_token(token_result)


class CommonBirdApp(App):
    CSS_PATH = "common_bird_app.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if (database_path / "ebird_cn_hotspots.json").exists():
            with open(
                database_path / "ebird_cn_hotspots.json", "r", encoding="utf-8"
            ) as f:
                self.ebird_cn_hotspots: Dict = json.load(f)
        else:
            self.ebird_cn_hotspots = None
        if (database_path / "ebird_other_hotspots.json").exists():
            with open(
                database_path / "ebird_other_hotspots.json", "r", encoding="utf-8"
            ) as f:
                self.ebird_other_hotspots: Dict = json.load(f)
        else:
            self.ebird_other_hotspots = None
        if (database_path / "location_map.json").exists():
            with open(database_path / "location_map.json", "r", encoding="utf-8") as f:
                self.ebird_to_br_location_map: Dict = json.load(f)
            self.br_to_ebird_location_map = {}
            for eb_loc_name, locs in self.ebird_to_br_location_map.items():
                for loc in locs:
                    if loc not in self.br_to_ebird_location_map:
                        self.br_to_ebird_location_map[loc] = []
                    self.br_to_ebird_location_map[loc].append(eb_loc_name)
        else:
            self.ebird_to_br_location_map = None
            self.br_to_ebird_location_map = None

        # all exists or all not exists
        assert all(
            (
                self.ebird_cn_hotspots,
                self.ebird_other_hotspots,
                self.ebird_to_br_location_map,
                self.br_to_ebird_location_map,
            )
        ) or all(
            (
                not self.ebird_cn_hotspots,
                not self.ebird_other_hotspots,
                not self.ebird_to_br_location_map,
                not self.br_to_ebird_location_map,
            )
        )

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield VerticalScroll(
            Button(
                "观鸟记录中心",
                id="birdreport",
                tooltip="观鸟记录中心相关的功能，包括将报告迁移至EBird",
            ),
            Button(
                "EBird",
                id="ebird",
                tooltip="EBird相关的功能，包括将报告迁移至观鸟记录中心",
                disabled=True,
            ),
            Button(
                "退出",
                id="exit",
                tooltip="退出应用",
                variant="warning",
            ),
            classes="option_container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "birdreport":
            self.push_screen(BirdreportScreen())
        elif event.button.id == "ebird":
            self.push_screen(EbirdScreen())
        elif event.button.id == "exit":
            self.exit()


def main():
    app = CommonBirdApp()
    app.run()


if __name__ == "__main__":
    main()
