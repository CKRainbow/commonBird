import json
import os
import webbrowser
import platform
from typing import Dict, List, Optional, TYPE_CHECKING
from packaging import version

import httpx
from textual import work, on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, HorizontalGroup
from textual.widgets import Footer, Header, Button, Markdown

from src import application_path, database_path, inner_path, cache_path
from src.utils.consts import GITHUB_API_TOKEN, APP_VERSION, DOWNLOAD_URL
from src.cli.birdreport import BirdreportScreen
from src.cli.ebird import EbirdScreen
from src.cli.general import ConfirmScreen, MessageScreen, DisplayScreen

if TYPE_CHECKING:
    from src.ebird.ebird import EBird
    from src.birdreport.birdreport import Birdreport


class CommonBirdApp(App):
    CSS_PATH = inner_path / "common_bird_app.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ebird: EBird = None
        self.birdreport: Birdreport = None

        self.ebird_cn_hotspots = None
        self.ebird_other_hotspots = None
        self.ebird_hotspots_update_date = None
        self.ch4_to_eb_taxon_map = None
        self.ebird_taxon_info = None

        self.location_assign = {}

        self.first_open = True
        if APP_VERSION == "beta":
            self.version = APP_VERSION
        else:
            self.version = version.parse(APP_VERSION)
        
        self.reload_hotspot_info()

        # all exists or all not exists
        assert all(
            (
                self.ebird_cn_hotspots,
                self.ebird_other_hotspots,
            )
        ) or all(
            (
                not self.ebird_cn_hotspots,
                not self.ebird_other_hotspots,
            )
        )

        if (database_path / "ch4_to_eb_taxon_map.json").exists():
            with open(
                database_path / "ch4_to_eb_taxon_map.json", "r", encoding="utf-8"
            ) as f:
                self.ch4_to_eb_taxon_map = json.load(f)

        if (database_path / "ebird_taxonomy.json").exists():
            with open(
                database_path / "ebird_taxonomy.json", "r", encoding="utf-8"
            ) as f:
                self.ebird_taxon_info: Optional[List] = json.load(f)

        if (cache_path / "location_assign.json").exists():
            with open(cache_path / "location_assign.json", "r", encoding="utf-8") as f:
                self.location_assign: Dict = json.load(f)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield VerticalScroll(
            HorizontalGroup(
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
            ),
            HorizontalGroup(
                Button(
                    "更新日志",
                    id="changelog",
                    tooltip="查看更新日志",
                ),
                Button(
                    "使用说明",
                    id="help",
                    tooltip="查看使用说明",
                ),
            ),
            HorizontalGroup(
                Button(
                    "关于本软件",
                    id="about",
                    tooltip="关于本软件",
                ),
                Button(
                    "退出",
                    id="exit",
                    tooltip="退出应用",
                    variant="warning",
                ),
            ),
            classes="option_container",
        )

    @on(Button.Pressed, "#changelog")
    @work
    async def on_changelog_pressed(self, event: Button.Pressed) -> None:
        await self.push_screen_wait(
            DisplayScreen(
                Markdown(
                    open(
                        application_path / "changelog.md", "r", encoding="utf-8"
                    ).read()
                )
            )
        )

    @on(Button.Pressed, "#help")
    @work
    async def on_help_pressed(self, event: Button.Pressed) -> None:
        await self.push_screen_wait(
            DisplayScreen(
                Markdown(
                    open(application_path / "README.md", "r", encoding="utf-8").read()
                )
            )
        )

    ABOUT_MARKDOWN = f"""
## 当前版本
{APP_VERSION}

## 联系作者
- [GitHub](https://github.com/CKRainbow)
- 微信号：gandptriyx
- QQ： 417266948
    """

    @on(Button.Pressed, "#about")
    @work
    async def on_about_pressed(self, event: Button.Pressed) -> None:
        await self.push_screen_wait(DisplayScreen(Markdown(self.ABOUT_MARKDOWN)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "birdreport":
            self.push_screen(BirdreportScreen())
        elif event.button.id == "ebird":
            self.push_screen(EbirdScreen())
        elif event.button.id == "exit":
            self.exit()

    @work
    async def on_mount(self) -> None:
        github_api_token = os.getenv("GITHUB_API_TOKEN") or GITHUB_API_TOKEN

        if self.version == "beta":
            self.sub_title = "当前版本为beta测试版本"
        elif self.first_open:
            self.first_open = False

            if self.ch4_to_eb_taxon_map is None:
                await self.push_screen_wait(
                    MessageScreen(
                        "没有找到ch4_to_eb_taxon_map.json文件\n数据迁移可能出现错误\n请检查数据文件是否存在"
                    )
                )

            GITHUB_API_URL = (
                "https://api.github.com/repos/CKRainbow/commonBird/releases/latest"
            )
            HEADERS = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {github_api_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(GITHUB_API_URL, headers=HEADERS)
                    response.raise_for_status()
                    latest_release = response.json()
                    latest_version = version.parse(latest_release["tag_name"])

                    if latest_version > self.version:
                        is_update = await self.push_screen_wait(
                            ConfirmScreen(
                                f"当前版本为{self.version.base_version},最新版本为{latest_version.base_version}\n"
                                + "选择是将打开下载链接。\n"
                                + "更新日志：https://github.com/CKRainbow/commonBird/blob/main/changelog.md"
                            )
                        )

                        if is_update:
                            download_url = DOWNLOAD_URL.get(
                                f"{platform.system().lower()}_{platform.machine().lower()}"
                            )
                            if download_url:
                                webbrowser.open(download_url)
                            else:
                                await self.push_screen_wait(
                                    MessageScreen(
                                        f"未识别平台{platform.system()}，当前平台不支持下载。"
                                    )
                                )
                        else:
                            self.sub_title = (
                                f"当前版本为旧版本：{self.version.base_version}"
                            )
                    else:
                        self.sub_title = (
                            f"当前版本为最新版本：{self.version.base_version}"
                        )
                except httpx.HTTPError as e:
                    await self.push_screen_wait(
                        MessageScreen(f"获取最新版本信息失败：{e}")
                    )

    def save_location_assign_cache(self, location_assign_cache: dict) -> None:
        self.location_assign.update(location_assign_cache)
        self.location_assign = {
            k: v for k, v in self.location_assign.items() if v is not None
        }

        with open(cache_path / "location_assign.json", "w", encoding="utf-8") as f:
            json.dump(self.location_assign, f, ensure_ascii=False, indent=4)

    def reload_hotspot_info(self) -> None:
        if (database_path / "ebird_cn_hotspots.json").exists():
            with open(
                database_path / "ebird_cn_hotspots.json", "r", encoding="utf-8"
            ) as f:
                data = json.load(f)
                self.ebird_cn_hotspots: Dict = data["data"]
                self.ebird_hotspots_update_date = data["last_update_date"]
        if (database_path / "ebird_other_hotspots.json").exists():
            with open(
                database_path / "ebird_other_hotspots.json", "r", encoding="utf-8"
            ) as f:
                data = json.load(f)
                self.ebird_other_hotspots: Dict = data["data"]
                self.ebird_hotspots_update_date = data["last_update_date"]