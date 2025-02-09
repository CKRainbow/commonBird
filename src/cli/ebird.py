import os

from textual import on, work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import (
    Button,
)

from src.cli.general import DomainScreen, TokenInputScreen
from src.ebird.ebird import EBird


class EbirdScreen(DomainScreen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
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
    async def on_update_hotspot_pressed(self, event: Button.Pressed) -> None:
        pass

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
