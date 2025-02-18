import os
from itertools import count
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import (
    Button,
    LoadingIndicator
)

from src.cli.general import DomainScreen, TokenInputScreen, DisplayScreen
from src.ebird.ebird import EBird

if TYPE_CHECKING:
    from src.cli.app import CommonBirdApp


class EbirdScreen(DomainScreen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.app: CommonBirdApp

        self.change_token_hint = (
            "请输入EBird的API token\n具体获取方法参加 README.md 说明文件"
        )
        self.token_name = "EBIRD_TOKEN"

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Button("更新热点信息", id="update_hotspot", tooltip="更新热点信息"),
            Button("修改 Token", id="change_token", tooltip="修改EBird的API token"),
            classes="option_container",
        )

    @on(Button.Pressed, "#update_hotspot")
    @work
    async def on_update_hotspot_pressed(self, event: Button.Pressed) -> None:
        await self.app.push_screen_wait(DisplayScreen(LoadingIndicator(),self.app.ebird.update_cn_hotspots))

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change_token":
            token_result = await self.app.push_screen_wait(
                TokenInputScreen(self.token_name, self.change_token_hint),
            )
            self.store_token(token_result)

    @work
    async def on_mount(self) -> None:
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
                    self.app.ebird is None
                    or self.app.ebird.token != token
                ):
                    self.app.ebird = EBird(token)
                break
            except Exception:
                token_result = await self.app.push_screen_wait(
                    TokenInputScreen(self.token_name, text),
                )
                token = token_result["token"]
