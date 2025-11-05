import logging
from typing import TYPE_CHECKING

from textual import on, work
from textual.containers import VerticalScroll
from textual.widgets import Button, LoadingIndicator
from textual.worker import Worker, WorkerState

from src.cli.general import DomainScreen, DisplayScreen, MessageScreen
from src.ebird.ebird import EBird
from src.utils.api_exceptions import ApiErrorBase

if TYPE_CHECKING:
    from src.cli.app import CommonBirdApp


class EbirdScreen(DomainScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app: CommonBirdApp

        self.change_token_hint = (
            "请输入EBird的API token\n具体获取方法参加 README.md 说明文件"
        )
        self.token_name = "EBIRD_TOKEN"

        self.composition = VerticalScroll(
            Button("更新热点信息", id="update_hotspot", tooltip="更新热点信息"),
            Button("修改 Token", id="change_token", tooltip="修改EBird的API token"),
            Button(
                "返回",
                id="back",
                variant="primary",
                tooltip="返回上一层",
            ),
            classes="option_container",
        )

    def store_token(self, token_name: str, token: str) -> None:
        # the token must be 32 characters and consists of only number and letters
        if len(token) != 12 or not token.isalnum():
            raise ValueError(
                "token must be 12 characters and consists of only number and letters"
            )

        super().store_token(token_name, token)

    @on(Button.Pressed, "#update_hotspot")
    @work
    async def on_update_hotspot_pressed(self, event: Button.Pressed) -> None:
        try:
            loading_screen = DisplayScreen(LoadingIndicator())
            self.app.push_screen(loading_screen)
            await self.app.ebird.update_cn_hotspots()
            loading_screen.dismiss()
        except ApiErrorBase as e:
            await self.app.push_screen_wait(MessageScreen(f"更新eBird热点失败: {e}"))
            loading_screen.dismiss()
            return
        self.app.reload_hotspot_info()

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change_token":
            result = await self.check_token(
                self.token_name,
                self.change_token_hint,
                EBird,
                self.app.ebird,
                force_change=True,
            )
            if result is None:
                await self.app.push_screen_wait(MessageScreen("Token 未发生改变"))
                return
            self.app.ebird = result
        elif event.button.id == "back":
            self.app.pop_screen()

    @work
    async def on_mount(self) -> None:
        result = await self.check_token(
            self.token_name, self.change_token_hint, EBird, self.app.ebird
        )

        if result is None:
            await self.app.push_screen_wait(MessageScreen("未提供有效 Token"))
            if self.temporary:
                self.dismiss()
            else:
                self.app.pop_screen()
            return

        self.app.ebird = result

        if self.temporary:
            self.dismiss()

        await self.mount(self.composition)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.state is WorkerState.ERROR:
            # The exception object is in event.worker.error
            exception = event.worker.error

            # 5. Log the exception with the full traceback to the file
            # Using exc_info=exception ensures the full traceback is included.
            logging.critical(
                f"Worker '{event.worker.name}' encountered a fatal error.",
                exc_info=exception,
            )
