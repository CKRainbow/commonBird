from dotenv import load_dotenv, set_key
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Grid
from textual.widgets import (
    Button,
    Label,
    Input,
)

from src import env_path

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
    def store_token(self, token_name, token) -> None:
        set_key(
            dotenv_path=env_path,
            key_to_set=token_name,
            value_to_set=token,
        )
        load_dotenv(env_path)
