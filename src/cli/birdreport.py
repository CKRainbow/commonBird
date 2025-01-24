import json
import os
import asyncio
import csv
import time
import pytz
from typing import List
from datetime import datetime
from pathlib import Path
from itertools import count

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

from src import application_path
from src.birdreport.birdreport import Birdreport
from src.utils.location import EBIRD_REGION_CODE_TO_NAME, NAME_TO_EBIRD_REGION_CODE
from src.utils.taxon import convert_taxon_z4_ebird
from src.cli.general import ConfirmScreen, MessageScreen, DomainScreen, TokenInputScreen


async def dump_as_ebird_csv(reports, username, update_date, ch4_to_eb_taxon_map):
    # FIXME: single csv file should be less than 1MB
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
            all_observations_reported = "Y" if report["eye_all_birds"] != "" else "N"
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
        country = "CN"
        location_name = report["point_name"]
        lat = report["lat"] if "lat" in report else ""
        lng = report["lng"] if "lng" in report else ""
        protocol = "stationary"  # historical
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
                # common_name,
                "",
                genus,
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
    def __init__(self, province, **kwargs):
        super().__init__(kwargs)

        self.province = NAME_TO_EBIRD_REGION_CODE[province]
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
        await self.app.push_screen_wait(
            MessageScreen(
                "注意！由于eBird记录上传的逻辑，在该软件中分配的地点"
                + "\n最终只会生成一个与热点同名且坐标一样的个人地点，"
                + "\n报告并没有真正的存在热点里，请酌情使用。"
                + "\n若希望将此类报告分配到热点，请尝试在个人主页的地点界面"
                + "\n将自动生成的个人地点合并至相应热点。",
            )
        )

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
        point_name = event.button.name

        birdreport_point_info = self.location_assign[point_name]
        province = birdreport_point_info["province"]
        if province == "台湾省":
            province = birdreport_point_info["city"]

        hotspot_name = await self.app.push_screen_wait(
            SearchEbirdHotspotScreen(province)
        )
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
                id="version_select",
            ),
            Button("搜索", id="search", variant="primary"),
            Button("全选", id="select_all", variant="primary"),
            Button("确认", id="confirm", variant="primary"),
            SelectionList[int](),
            id="filter_container",
        )

    @on(Button.Pressed, "#search")
    def on_button_search_presses(self, event: Button.Pressed) -> None:
        def process_date(date):
            if date == "":
                return ""
            splited_date = date.split("-")
            if len(splited_date) == 1:
                return f"{splited_date[0]}-01-01"
            elif len(splited_date) == 2:
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
        for report in self.app.cur_birdreport_data:
            version = report["version"]
            start_date = time.strptime(report["start_time"].split(" ")[0], "%Y-%m-%d")
            # filter reports of G3 which have been converted
            if query_version != Select.BLANK:
                if version != query_version:
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
    def on_button_select_all_presses(self, event: Button.Pressed) -> None:
        selection_list = self.query_one(SelectionList)
        selection_list.select_all()

    @on(Button.Pressed, "#confirm")
    def on_button_confirm_presses(self, event: Button.Pressed) -> None:
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

        await self.app.push_screen_wait(BirdreportFilterScreen())

        if self.app.br_to_ebird_location_map is not None:
            await self.app.push_screen_wait(BirdreportToEbirdLocationAssignScreen())

        await self.app.push_screen_wait(
            MessageScreen(
                "请注意：\n请勿使用Excel或WPS打开编辑生成的csv文件\n而应使用记事本或类似工具\n否则可能导致乱码问题"
            )
        )

        username = self.app.birdreport.user_info["username"]
        await dump_as_ebird_csv(
            self.app.cur_birdreport_data,
            username,
            self.cur_date,
            self.app.ch4_to_eb_taxon_map,
        )
        self.dismiss()


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
