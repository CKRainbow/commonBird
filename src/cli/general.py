import logging
import os
from typing import List, Optional, Awaitable, Tuple, Type, TYPE_CHECKING
from itertools import count

from dotenv import load_dotenv, set_key
from textual import on, work
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Grid
from textual.widget import Widget
from textual.events import Click
from textual.widgets import (
    Button,
    Label,
    Input,
)

from src import env_path

if TYPE_CHECKING:
    from src.cli.app import CommonBirdApp

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

    def on_mount(self) -> None:
        self.screen.styles.align = ("center", "middle")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "token":
            user_input = event.input.value
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

class OptionScreen(ModalScreen):
    def __init__(self, message: str, options: List[Tuple[str, str]], **kwargs):
        super().__init__(kwargs)
        self.message = message
        self.options = options

    def compose(self) -> ComposeResult:
        self.grid = Grid(
            Label(self.message, id="messageText"),
            *[Button(option[0], id=option[1]) for option in self.options],
            id="dialog"
        )

        yield self.grid
    
    def on_mount(self) -> None:
        self.screen.styles.align = ("center", "middle")
        self.grid.styles.grid_size_columns = len(self.options)
        label = self.query_one("#messageText")
        label.styles.column_span = len(self.options)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        for option in self.options:
            if event.button.id == option[1]:
                self.dismiss(option[1])


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

    def on_mount(self) -> None:
        self.screen.styles.align = ("center", "middle")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss()


class DomainScreen(Screen):
    def __init__(self, temporary: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.app: CommonBirdApp

        self.temporary = temporary

    def store_token(self, token_name, token) -> None:
        set_key(
            dotenv_path=env_path,
            key_to_set=token_name,
            value_to_set=token,
        )
        load_dotenv(env_path)

    async def check_token(
        self,
        token_name: str,
        change_token_hint: str,
        cls: Type,
        attr,
        force_change: bool = False,
        input_screen: Optional[Screen] = None,
    ):
        token = os.getenv(token_name)
        for i in count(0):
            if i == 0:
                text = change_token_hint
            else:
                text = "先前输入的 token 无效或启动浏览器时出现错误\n请选择重新输入、退出后选择其他浏览器或手动获取 token。"
            try:
                if not force_change and not token:
                    raise Exception
                elif force_change and i == 0:
                    raise Exception
                if attr is None or attr.token != token:
                    attr = await cls.create(token)
                self.store_token(token_name, token)
                break
            except Exception as e:
                logging.warning(f"Invelid Token {token_name}: {e}")
                if input_screen is None:
                    input_screen = TokenInputScreen
                try:
                    token_result = await self.app.push_screen_wait(
                        input_screen(token_name, text),
                    )
                except RuntimeError as e:
                    logging.warning(f"Token Input Screen Error: {e}")
                    token_result = None
                if token_result is None:
                    input_screen = TokenInputScreen
                else:
                    token = token_result["token"]
        return attr


class DisplayScreen(ModalScreen):
    """
    A screen to display a instant widget, we can dismiss it with a click at anywhere

    Args:
        Widget: Widget to display
    """

    def __init__(self, widget: Widget, function: Optional[Awaitable] = None, **kwargs):
        super().__init__(**kwargs)
        self.widget = widget
        self.block = True

        if function:
            self.function = function
        else:
            self.function = None

    def compose(self) -> ComposeResult:
        yield self.widget

    def key_enter(self, event) -> None:
        if self.block:
            return
        self.dismiss()
        event.stop()

    @on(Click)
    def on_click(self, event: Click) -> None:
        if self.block:
            return
        self.dismiss()
        event.stop()

    @work
    async def on_mount(self) -> None:
        if self.function:
            await self.function()
            self.dismiss()
        else:
            self.block = False
