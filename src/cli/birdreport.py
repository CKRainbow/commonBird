import json
import os
import asyncio
import csv
import time
import pytz
import platform
from typing import Dict, Optional, Union, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

import selenium
from textual import on, work
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import VerticalScroll, HorizontalGroup, Grid
from textual.widgets import (
    Header,
    Button,
    Label,
    Input,
    LoadingIndicator,
    Select,
    SelectionList,
    MaskedInput,
    ListView,
    ListItem,
)
from fuzzywuzzy.fuzz import partial_ratio
from selenium import webdriver

from src import application_path
from src.birdreport.birdreport import Birdreport
from src.utils.location import EBIRD_REGION_CODE_TO_NAME, NAME_TO_EBIRD_REGION_CODE
from src.utils.taxon import convert_taxon_z4_ebird
from src.cli.general import ConfirmScreen, MessageScreen, DomainScreen, DisplayScreen
from src.cli.ebird import EbirdScreen

if TYPE_CHECKING:
    from src.cli.app import CommonBirdApp


def get_report_eb_region_code(province, city):
    if province == "台湾省":
        return NAME_TO_EBIRD_REGION_CODE[city]
    else:
        return NAME_TO_EBIRD_REGION_CODE[province]


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
    def __init__(self, point_name, province, **kwargs):
        super().__init__(kwargs)

        self.province = province
        self.point_name = point_name
        self.target_cn_hotspot = {
            name: hotspot
            for name, hotspot in self.app.ebird_cn_hotspots.items()
            if hotspot["subnational1Code"] == self.province
        }
        self.target_other_hotspot = {
            name: hotspot
            for name, hotspot in self.app.ebird_other_hotspots.items()
            if hotspot["subnational1Code"] == self.province
        }

    def compose(self) -> ComposeResult:
        yield Grid(
            Input(self.point_name, id="hotspot_name"),
            Button(
                "查询",
                id="query",
                variant="primary",
            ),
            ListView(id="hotspot_listview"),
            classes="search_container",
        )

    async def on_mount(self) -> None:
        query_button = self.query_one("#query")
        query_button.post_message(Button.Pressed(query_button))

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
            self.target_cn_hotspot.values(),
        )
        hotspot_infos_other = filter(
            lambda x: partial_ratio(hotspot_name, x["locName"]) > 80,
            self.target_other_hotspot.values(),
        )

        hotspot_infos = list(hotspot_infos_cn) + list(hotspot_infos_other)

        if len(hotspot_infos) == 0:
            hotspot_listview.append(
                ListItem(
                    Label("无搜索结果，点此不做修改"),
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


class BirdreportToEbirdLocationAssignScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.app: CommonBirdApp

        self.location_assign = {}
        for report in self.app.cur_birdreport_data:
            point_name = report["point_name"]
            if point_name not in self.location_assign:
                self.location_assign[point_name] = {
                    "point_id": report["point_id"] if "point_id" in report else "",
                    "province": (
                        report["province_name"] if "province_name" in report else ""
                    ),
                    "city": report["city_name"] if "city_name" in report else "",
                    "district": (
                        report["district_name"] if "district_name" in report else ""
                    ),
                    "longitude": report["longitude"] if "longitude" in report else "",
                    "latitude": report["latitude"] if "latitude" in report else "",
                    "reports": [],
                }
            self.location_assign[point_name]["reports"].append(report)

        for point_name, value in self.app.location_assign.items():
            if point_name not in self.location_assign:
                continue
            if isinstance(value, dict):
                converted_hotspot_name = point_name
                custom_info = value
            else:
                converted_hotspot_name = value
                custom_info = None

            self.modify_converted_hotspot(
                point_name,
                converted_hotspot_name,
                custom_info=custom_info,
                modify_cache=False,
            )

        self.temp_assign_cache: Dict[str, Union[str, Dict]] = {}

    @work
    async def on_mount(self) -> None:
        last_update_date = self.app.ebird_hotspots_update_date
        is_update = await self.app.push_screen_wait(
            ConfirmScreen(
                f"是否更新eBird的地点信息？\n这可能有助于地点分配的准确性\n最后更新时间：{last_update_date}\n（需要拥有eBird API Token）"
            )
        )
        if is_update:
            if self.app.ebird is None:
                await self.app.push_screen_wait(EbirdScreen(temporary=True))
            await self.app.push_screen_wait(
                DisplayScreen(LoadingIndicator(), self.app.ebird.update_cn_hotspots)
            )
            self.app.reload_hotspot_info()

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
                "不做修改，请点此修改"
                if "converted_hotspot" not in info or info["converted_hotspot"] is None
                else info["converted_hotspot"],
                name=point_name,
                id="converted_hotspot_" + str(point_id),
                classes="converted_hotspot",
                variant="default",
            )

            set_as_personal = Button(
                "保留为个人地点",
                name=point_name,
                id="set_as_personal_" + str(point_id),
                classes="set_as_personal",
                variant="primary",
            )

            assign_row = HorizontalGroup(
                original_location_name,
                converted_hotspot,
                set_as_personal,
                classes="assign_row",
            )
            horizonal_groups.append(assign_row)
        await vertical_scroll.mount(*horizonal_groups)

    @on(Button.Pressed, "#confirm")
    def on_button_confirm_pressed(self, event: Button.Pressed) -> None:
        for info in self.location_assign.values():
            if info.get("converted_hotspot") is not None:
                for report in info["reports"]:
                    # override or add new record?
                    report["point_name"] = info["converted_hotspot"]
                    report["lat"] = info["lat"] if info["lat"] is not None else ""
                    report["lng"] = info["lng"] if info["lng"] is not None else ""
        self.app.save_location_assign_cache(self.temp_assign_cache)
        self.dismiss()

    @on(Button.Pressed, ".converted_hotspot")
    @work
    async def on_button_converted_hotspot_pressed(self, event: Button.Pressed) -> None:
        point_name = event.button.name

        birdreport_point_info = self.location_assign[point_name]
        province_code = get_report_eb_region_code(
            birdreport_point_info["province"],
            birdreport_point_info["city"],
        )
        hotspot_name = await self.app.push_screen_wait(
            SearchEbirdHotspotScreen(point_name, province_code)
        )
        button = event.button

        if hotspot_name is None:
            button.label = "不做修改"
        else:
            button.label = hotspot_name

        self.modify_converted_hotspot(event.button.name, hotspot_name)

    @on(Button.Pressed, ".set_as_personal")
    @work
    async def on_button_set_as_personal_pressed(self, event: Button.Pressed) -> None:
        point_name = event.button.name
        point_index = event.button.id.split("_")[-1]
        display_button: Button = self.app.query_one("#converted_hotspot_" + point_index)
        report = self.location_assign[point_name]
        # if there is no point_id, it is a casual report
        if "point_id" not in report or not report["point_id"]:
            custom_info = {
                "lng": report["longitude"],
                "lat": report["latitude"],
            }
            self.modify_converted_hotspot(
                point_name, point_name, custom_info=custom_info
            )
        # if there is point_id, it is a point report
        else:
            point_id = report["point_id"]
            point_info = await self.app.birdreport.member_get_point(point_id)
            custom_info = {
                "lng": point_info["longitude"],
                "lat": point_info["latitude"],
            }
            self.modify_converted_hotspot(
                point_name, point_name, custom_info=custom_info
            )
        display_button.label = point_name

    def modify_converted_hotspot(
        self,
        point_name: str,
        converted_hotspot_name: str,
        custom_info: Dict = None,
        modify_cache: bool = True,
    ) -> None:
        # conveted_hotspot is None means remaining

        if modify_cache:
            if custom_info is not None:
                self.temp_assign_cache[point_name] = custom_info
            else:
                self.temp_assign_cache[point_name] = converted_hotspot_name

            # set 10 as a threshold to save cache
            if len(self.temp_assign_cache) >= 10:
                self.app.save_location_assign_cache(self.temp_assign_cache)
                self.temp_assign_cache = {}

        if converted_hotspot_name is None:
            self.location_assign[point_name]["lat"] = None
            self.location_assign[point_name]["lng"] = None
        else:
            if custom_info is not None:
                location_info = custom_info
            elif converted_hotspot_name in self.app.ebird_cn_hotspots:
                location_info = self.app.ebird_cn_hotspots[converted_hotspot_name]
            elif converted_hotspot_name in self.app.ebird_other_hotspots:
                location_info = self.app.ebird_other_hotspots[converted_hotspot_name]
            else:
                return

            self.location_assign[point_name]["lat"] = location_info["lat"]
            self.location_assign[point_name]["lng"] = location_info["lng"]

        self.location_assign[point_name]["converted_hotspot"] = converted_hotspot_name


class BirdreportFilterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.title = "选择需要导出的记录"

    def compose(self):
        yield Header()
        yield Grid(
            HorizontalGroup(
                Label("日期范围："),
                MaskedInput(template="0000-00-00;0", id="start_date"),
                Label("至"),
                MaskedInput(template="0000-00-00;0", id="end_date"),
                id="date_range",
            ),
            HorizontalGroup(
                Label("记录版本："),
                Select(
                    id="version",
                    options=[("郑三", "G3"), ("郑四", "CH4")],
                    disabled=True,
                    value="CH4",
                    prompt="全部",
                ),  # CH4 pnly for now
                classes="select",
            ),
            HorizontalGroup(
                Label("记录类型："),
                Select(
                    id="type", options=[("定点记", 0), ("随手记", 1)], prompt="全部"
                ),
                classes="select",
            ),
            *[Label("") for _ in range(6)],
            Button("搜索", id="search", variant="primary"),
            Button("全选", id="select_all", variant="primary"),
            Button("确认", id="confirm", variant="primary"),
            SelectionList[int](),
            id="filter_container",
        )

    @on(Button.Pressed, "#search")
    def on_button_search_pressed(self, event: Button.Pressed) -> None:
        def process_date(date):
            if date == "":
                return ""
            splited_date = date.split("-")
            if len(splited_date) < 3 or splited_date[1] == "":
                return f"{splited_date[0]}-01-01"
            elif splited_date[2] == "":
                return f"{splited_date[0]}-{splited_date[1]}-01"
            else:
                return date

        selectible_reports = []

        query_start_date = process_date(self.query_one("#start_date").value)
        if query_start_date != "":
            query_start_date = time.strptime(query_start_date, "%Y-%m-%d")
        query_end_date = process_date(self.query_one("#end_date").value)
        if query_end_date != "":
            query_end_date = time.strptime(query_end_date, "%Y-%m-%d")

        query_version = self.query_one("#version").value
        query_type = self.query_one("#type").value
        for report in self.app.cur_birdreport_data:
            version = report["version"]
            is_handy = "latitude" in report
            start_date = time.strptime(report["start_time"].split(" ")[0], "%Y-%m-%d")
            # filter reports of G3 which have been converted
            if query_version != Select.BLANK:
                if version != query_version:
                    continue
            if query_type != Select.BLANK:
                if is_handy != (query_type == 1):
                    continue
            if query_start_date != "":
                if start_date < query_start_date:
                    continue
            if query_end_date != "":
                if start_date > query_end_date:
                    continue
            selectible_reports.append(
                (
                    f"{report['serial_id']}: {report['start_time']} - {report['point_name']}",
                    report["id"],
                )
            )

        selection_list = self.query_one(SelectionList)
        selection_list.clear_options()
        selection_list.add_options(selectible_reports)

    @on(Button.Pressed, "#select_all")
    def on_button_select_all_pressed(self, event: Button.Pressed) -> None:
        selection_list = self.query_one(SelectionList)
        selection_list.select_all()

    @on(Button.Pressed, "#confirm")
    def on_button_confirm_pressed(self, event: Button.Pressed) -> None:
        selection_list = self.query_one(SelectionList)
        new_list = list(
            filter(
                lambda x: x["id"] in selection_list.selected,
                self.app.cur_birdreport_data,
            )
        )
        if len(new_list) == 0:
            return
        self.app.cur_birdreport_data = new_list
        self.dismiss()

    def on_mount(self) -> None:
        search_button = self.query_one("#search")
        search_button.post_message(Button.Pressed(search_button))


class BirdreportToEbirdScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.app: CommonBirdApp

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

        await self.app.push_screen_wait(BirdreportFilterScreen())

        if (
            self.app.ebird_cn_hotspots is not None
            and self.app.ebird_other_hotspots is not None
        ):
            await self.app.push_screen_wait(BirdreportToEbirdLocationAssignScreen())

        await self.app.push_screen_wait(
            MessageScreen(
                "请注意：\n请勿使用Excel或WPS打开编辑生成的csv文件\n而应使用记事本或类似工具\n否则可能导致乱码问题"
            )
        )

        await self.dump_as_ebird_csv(
            self.cur_date,
        )
        self.dismiss()

    async def dump_as_ebird_csv(self, update_date):
        reports = self.app.cur_birdreport_data
        ch4_to_eb_taxon_map = self.app.ch4_to_eb_taxon_map
        username = self.app.birdreport.user_info["username"]
        ebird_taxon_info_dict: Optional[Dict] = None
        if self.app.ebird_taxon_info is not None:
            ebird_taxon_info_dict = {
                taxon_info["sciName"]: taxon_info
                for taxon_info in self.app.ebird_taxon_info
            }

        csvs = [[]]
        for report in reports:
            version = report["version"]
            obs = report["obs"]

            start_time = time.strptime(report["start_time"], "%Y-%m-%d %H:%M:%S")
            end_time = time.strptime(report["end_time"], "%Y-%m-%d %H:%M:%S")
            duration = (time.mktime(end_time) - time.mktime(start_time)) // 60

            # FIXME: need alert
            duration = max(min(duration, 24 * 60), 1)

            if "eye_all_birds" in report:
                all_observations_reported = (
                    "Y" if report["eye_all_birds"] != "" else "N"
                )
            else:
                all_observations_reported = "Y"

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
            region_code = get_report_eb_region_code(
                report["province_name"],
                report["city_name"] if "city_name" in report else "",
            )
            if region_code.endswith("-"):
                state = region_code
                country = region_code[:-1]
            else:
                country, state = region_code.split("-")
            location_name = report["point_name"]
            lat = report["lat"] if "lat" in report else ""
            lng = report["lng"] if "lng" in report else ""
            protocol = "historical"  # historical
            num_observers = 1

            if "real_quantity" in report:
                real_quantity = report["real_quantity"] == 1
            elif all([o["taxon_count"] == 1 for o in obs]):
                real_quantity = False
            else:
                real_quantity = True

            if version == "G3":
                pass
            else:
                if ch4_to_eb_taxon_map is not None:
                    convert_taxon_z4_ebird(report, ch4_to_eb_taxon_map)
                else:
                    pass

            for entry in obs:
                # common_name = entry["taxon_name"]

                common_name = ""
                genus = ""
                species = ""
                if ebird_taxon_info_dict is not None:
                    common_name = ebird_taxon_info_dict[entry["latinname"]]["comName"]
                    if common_name == "鹗":
                        common_name = "鹗鹗"
                else:
                    splited_latinname = entry["latinname"].split(" ")
                    genus = splited_latinname[0]
                    species = " ".join(splited_latinname[1:])

                species_count = entry["taxon_count"] if real_quantity else "X"

                note = entry["note"].replace("\n", "\\n") if "note" in entry else ""

                species_comments = note
                # only for detail taxon
                # if entry["type"] == 2:
                #     species_comments += "\\nHeard."
                # if entry["outside_type"] != 0:
                #     species_comments += "\nOut of scope or not confirmed."
                csv_line = (
                    common_name,
                    genus,
                    species,
                    species_count,
                    species_comments,
                    location_name,
                    lat,
                    lng,
                    observation_date,
                    start_time,
                    state,
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


class BirdreportScreen(DomainScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app: CommonBirdApp

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
            self.app.birdreport = await self.check_token(
                self.token_name,
                self.change_token_hint,
                Birdreport,
                self.app.birdreport,
                force_change=True,
                input_screen=BirdreportTokenFetchScreen,
            )
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

        self.app.birdreport = await self.check_token(
            self.token_name,
            self.change_token_hint,
            Birdreport,
            self.app.birdreport,
            input_screen=BirdreportTokenFetchScreen,
        )

        if self.temporary:
            self.dismiss()

        await self.mount(self.composition)

class BirdreportTokenFetchScreen(ModalScreen):
    def __init__(self, token_name: str, hint_text: str, **kwargs):
        super().__init__(kwargs)
        self.token_name = token_name
        self.hint_text = hint_text

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("请在弹出的浏览器界面登陆账号，随后点击“继续”\n选择取消则进入 Token 输入界面", id="hintText"),
            Button(
                "继续",
                id="get_token",
                variant="primary",
            ),
            Button(
                "取消",
                id="cancel",
            ),
            id="dialog",
        )
        
    def on_mount(self) -> None:
        self.driver = webdriver.Chrome()
        self.driver.get("https://www.birdreport.cn/member/login.html")
    
    def select_driver(self) -> webdriver.remote.webdriver.BaseWebDriver:
        plat = platform.system().lower()
        if plat == "darwin":
            supported_list = [webdriver.Safari, webdriver.Chrome, webdriver.Firefox, webdriver.Edge]
        else:
            supported_list = [webdriver.Chrome, webdriver.Firefox, webdriver.Edge, webdriver.Safari]
        
        for driver in supported_list:
            try:
                return driver()
            except selenium.common.exceptions.NoSuchDriverException:
                pass

        raise RuntimeError("No supported driver found")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "get_token":
            local_storage = self.driver.execute_script("""
                var items = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            """)
            self.driver.quit()
            token = ""
            if "$user" in local_storage:
                user = json.loads(local_storage["$user"])
                token = user["token"]
                self.dismiss({"token": token, "token_name": self.token_name})
            else:
                self.dismiss(None)
        elif event.button.id == "cancel":
            self.driver.quit()
            self.dismiss(None)