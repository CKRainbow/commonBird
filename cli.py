import json
import os
import asyncio
import csv
import time
import pytz
import logging
from datetime import datetime
from pathlib import Path
from itertools import count

from dotenv import load_dotenv, set_key
from textual import work
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import VerticalScroll, HorizontalGroup, Grid
from textual.widgets import Footer, Header, Button, Label, Input, LoadingIndicator

from src.birdreport.birdreport import Birdreport
from src import application_path

logging.basicConfig(
    filename=Path(application_path) / "log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

env_path = Path(application_path) / ".env"
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


def process_reports(retrieved_reports, cur_reports):
    # TODO: set location
    pass


async def dump_as_ebird_csv(reports, username, update_date):
    # FIXME: single csv file should be less than 1MB
    values = []
    for report in reports:
        start_time = time.strptime(report["start_time"], "%Y-%m-%d %H:%M:%S")
        end_time = time.strptime(report["end_time"], "%Y-%m-%d %H:%M:%S")
        duration = (time.mktime(end_time) - time.mktime(start_time)) // 60

        if "eye_all_birds" in report:
            all_observations_reported = "Y" if report["eye_all_birds"] == "1" else "N"
        else:
            all_observations_reported = ""

        # TODO: add checklist comments
        checklist_comment = report["note"] if "note" in report else ""
        if checklist_comment != "":
            checklist_comment += "\\n"
        # TODO: 可选是否添加
        checklist_comment += (
            f"Converted from BirdReport CN, report ID: {report['serial_id']}"
        )

        start_time = time.strftime("%-m/%-d/%Y %H:%M", start_time)
        observation_date, start_time = start_time.split(" ")
        country = "CN"
        location_name = report["point_name"]
        protocol = "historical"  # historical

        real_quality = report["real_quality"] if "real_quality" in report else None

        for entry in report["obs"]:
            common_name = entry["taxon_name"]
            species = entry["latinname"]
            species_count = (
                entry["taxon_count"]
                if real_quality is None or real_quality == 1
                else "X"
            )

            note = entry["note"] if "note" in entry else ""

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
                "",
                "",
                observation_date,
                start_time,
                "",
                country,
                protocol,
                "",
                duration,
                all_observations_reported,
                "",
                "",
                checklist_comment,
            )
            values.append(csv_line)

    with open(
        Path(application_path) / f"{username}_{update_date}_checklists.csv",
        "w",
        newline="",
    ) as f:
        writer = csv.writer(f)
        writer.writerows(values)


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


class BirdreportToEbirdScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)

    def compose(self) -> ComposeResult:
        yield VerticalScroll(LoadingIndicator())

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
                Path(application_path) / f"{username}_{self.cur_date}_checklists.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(self.app.cur_birdreport_data, f, ensure_ascii=False, indent=2)

            grid = self.query_one(VerticalScroll)
            loading_label = self.query_one(LoadingIndicator)
            await loading_label.remove()
            new_button = Button(
                "导出为EBird格式", id="export_to_ebird", variant="primary"
            )
            grid.mount(new_button)

        checklist_files = list(Path(".").glob(f"{username}_*_checklists.json"))
        use_existing = False

        if len(checklist_files) >= 1:
            checklist_file = checklist_files[0]
            use_existing = await self.app.push_screen_wait(
                ConfirmScreen(f"文件{checklist_file.name}已经存在，是否使用已有数据？"),
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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "export_to_ebird":

            async def inner(data, username, cur_date):
                await dump_as_ebird_csv(data, username, cur_date)
                self.dismiss()

            username = self.app.birdreport.user_info["username"]
            asyncio.create_task(
                inner(self.app.cur_birdreport_data, username, self.cur_date)
            )


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

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
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
        print(token)
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
