import os
from typing import Optional, Awaitable, Type, TYPE_CHECKING
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


class DomainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app: CommonBirdApp

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
    ):
        token = os.getenv(token_name)
        for i in count(0):
            if i == 0:
                text = change_token_hint
            else:
                text = "先前输入的token无效，请重新输入。"
            try:
                print(token, i)
                if not force_change and not token:
                    raise Exception
                elif force_change and i == 0:
                    raise Exception
                self.store_token(token_name, token)
                if attr is None or attr.token != token:
                    attr = await cls.create(token)
                break
            except Exception as e:
                print(e)
                token_result = await self.app.push_screen_wait(
                    TokenInputScreen(token_name, text),
                )
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

        if function:
            self.function = function
            self.block = True
        else:
            self.function = None
            self.block = False

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
