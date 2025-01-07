import json
import os
import asyncio

from dotenv import load_dotenv, find_dotenv, set_key
from textual import events
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen, ScreenResultType
from textual.widget import Widget
from textual.containers import VerticalScroll, HorizontalGroup, Grid
from textual.widgets import Footer, Header, Button, Label, Input

import ebird
from birdreport import Birdreport

if not find_dotenv():
    open(".env", "a").close()
load_dotenv(".env")


def store_token(tokenInputResult: dict) -> None:
    set_key(
        dotenv_path=".env",
        key_to_set=tokenInputResult["token_name"],
        value_to_set=tokenInputResult["token"],
    )


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
            # checklists = self.birdreport.search(
            #     username=username,
            #     pointname=pointname,
            # )

            # print(checklists)
            asyncio.create_task(background_sleep())


class BirdreportToEbirdScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)


class BirdreportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.change_token_hint = (
            "请输入观鸟记录中心的认证token\n具体获取方法参加 README.md 说明文件"
        )
        self.token_name = "BIRDREPORT_TOKEN"
        self.birdreport = None

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Header(),
            Button("获取记录", id="retrieve_report", tooltip="根据查询条件获取记录"),
            Button(
                "记录迁移至EBird",
                id="convert_ebird",
                tooltip="将某用户的所有记录迁移至EBird",
            ),
            Button(
                "修改 Token", id="change_token", tooltip="修改观鸟记录中心的认证token"
            ),
            classes="option_container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change_token":
            self.app.push_screen(
                TokenInputScreen(self.token_name, self.change_token_hint),
                store_token,
            )
            self.birdreport = Birdreport(os.getenv(self.token_name))
        elif event.button.id == "retrieve_report":
            self.app.push_screen(
                BirdreportSearchReportScreen(self.birdreport),
            )
        elif event.button.id == "convert_ebird":
            self.app.push_screen(BirdreportToEbirdScreen())

    def on_mount(self) -> None:
        self.title = "中国观鸟记录中心"
        self.sub_title = "可能会对记录中心服务器带来压力，酌情使用"
        if not os.getenv(self.token_name):
            self.app.push_screen(
                TokenInputScreen(self.change_token_hint),
                store_token,
            )
        self.birdreport = Birdreport(os.getenv(self.token_name))


class EbirdScreen(Screen):
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change_token":
            self.app.push_screen(
                TokenInputScreen(self.token_name, self.change_token_hint),
                store_token,
            )

    def on_mount(self) -> None:
        if not os.getenv(self.token_name):
            self.app.push_screen(
                TokenInputScreen(self.token_name, self.change_token_hint),
                store_token,
            )


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
            ),
            classes="option_container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "birdreport":
            self.push_screen(BirdreportScreen())
        elif event.button.id == "ebird":
            self.push_screen(EbirdScreen())


if __name__ == "__main__":
    app = CommonBirdApp()
    app.run()


# x = ebird.ebird(config.token)
# checklists = x.search(startTime=x.get_back_date(3),endTime=x.get_back_date(0))
# # x.show(checklists)
# info = x.spp_info(checklists)
# # print(info)

# y = birdreport.birdreport()
# print(y.search_hotspots_by_name("上海"))
# province = "山东省"
# checklists2 = y.search(
#     startTime=y.get_back_date(0), province=province, pointname="莱西"
# )
# with open("result.json", "w") as f:
#     json.dump(checklists2, f, indent=2, ensure_ascii=False)
# # y.show(checklists)
# info2 = y.spp_info(checklists2)
# print(info2)

# # 整合观测数据
# merge = info2
# for i in info:
#     if i not in merge:
#         merge[i] = info[i]
#     else:
#         merge[i] += info[i]

# f = open('./test.db','w+')
# f.write(str(merge))
# f.close()
# print(merge)

# sp = 'lewduc1'
# sciName = x.get_sciName_from_speciesCode(sp)
# comName = x.get_comName_from_speciesCode(sp)
# print(sciName,comName)
# sp1 = x.get_speciesCode_from_sciName(sciName)
# comName1 = x.get_comName_from_sciName(sciName)
# print(sp1,comName1)
