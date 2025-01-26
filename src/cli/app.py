import json
import os
import webbrowser
import platform
from typing import Dict, List, Optional
from click import HelpOption
from packaging import version

import httpx
from textual import work, on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, HorizontalGroup
from textual.widgets import Footer, Header, Button, Markdown

from src import application_path, database_path
from src.utils.consts import GITHUB_API_TOKEN, APP_VERSION, DOWNLOAD_URL
from src.cli.birdreport import BirdreportScreen
from src.cli.ebird import EbirdScreen
from src.cli.general import ConfirmScreen, MessageScreen, DisplayScreen


class CommonBirdApp(App):
    CSS_PATH = application_path / "common_bird_app.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.first_open = True
        self.version = version.parse(APP_VERSION)

        if (database_path / "ebird_cn_hotspots.json").exists():
            with open(
                database_path / "ebird_cn_hotspots.json", "r", encoding="utf-8"
            ) as f:
                self.ebird_cn_hotspots: Dict = json.load(f)
        else:
            self.ebird_cn_hotspots = None
        if (database_path / "ebird_other_hotspots.json").exists():
            with open(
                database_path / "ebird_other_hotspots.json", "r", encoding="utf-8"
            ) as f:
                self.ebird_other_hotspots: Dict = json.load(f)
        else:
            self.ebird_other_hotspots = None
        if (database_path / "location_map.json").exists():
            with open(database_path / "location_map.json", "r", encoding="utf-8") as f:
                self.ebird_to_br_location_map: Dict = json.load(f)
            self.br_to_ebird_location_map = {}
            for eb_loc_name, locs in self.ebird_to_br_location_map.items():
                for loc in locs:
                    if loc not in self.br_to_ebird_location_map:
                        self.br_to_ebird_location_map[loc] = []
                    self.br_to_ebird_location_map[loc].append(eb_loc_name)
        else:
            self.ebird_to_br_location_map = None
            self.br_to_ebird_location_map = None

        # all exists or all not exists
        assert all(
            (
                self.ebird_cn_hotspots,
                self.ebird_other_hotspots,
                self.ebird_to_br_location_map,
                self.br_to_ebird_location_map,
            )
        ) or all(
            (
                not self.ebird_cn_hotspots,
                not self.ebird_other_hotspots,
                not self.ebird_to_br_location_map,
                not self.br_to_ebird_location_map,
            )
        )

        if (database_path / "ch4_to_eb_taxon_map.json").exists():
            with open(
                database_path / "ch4_to_eb_taxon_map.json", "r", encoding="utf-8"
            ) as f:
                self.ch4_to_eb_taxon_map = json.load(f)
        else:
            self.ch4_to_eb_taxon_map = None

        if (database_path / "ebird_taxonomy.json").exists():
            with open(
                database_path / "ebird_taxonomy.json", "r", encoding="utf-8"
            ) as f:
                self.ebird_taxon_info: Optional[List] = json.load(f)
        else:
            self.ebird_taxon_info: Optional[List] = None

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
                    disabled=True,
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
- 微信号：grandptriyx
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
        if not os.getenv("GITHUB_API_TOKEN"):
            github_api_token = GITHUB_API_TOKEN
        else:
            github_api_token = os.getenv("GITHUB_API_TOKEN")

        if self.first_open:
            self.first_open = False

            if self.ch4_to_eb_taxon_map is None:
                await self.push_screen_wait(
                    MessageScreen(
                        "没有找到ch4_to_eb_taxon_map.json文件\n数据迁移可能出现错误\n请检查数据文件是否存在"
                    )
                )

            get_latest_repo_url = (
                "https://api.github.com/repos/CKRainbow/commonBird/releases/latest"
            )

            header = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {github_api_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(get_latest_repo_url, headers=header)
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_version = version.parse(latest_release["tag_name"])
                    if latest_version > self.version:
                        # is_update = await self.push_screen(
                        #     ConfirmScreen(
                        #         f"当前版本为{self.version.base_version},最新版本为{latest_version.base_version}\n"
                        #         + "是否要更新到新版本？\n"
                        #         + "更新日志：https://github.com/CKRainbow/commonBird/blob/main/changelog.md",  # FIXME: 不够长？
                        #     )
                        # )

                        # if is_update:
                        #     pass
                        # else:
                        #     self.sub_title = (
                        #         f"当前版本为旧版本：{self.version.base_version}"
                        #     )
                        is_update = await self.push_screen_wait(
                            ConfirmScreen(
                                f"当前版本为{self.version.base_version},最新版本为{latest_version.base_version}\n"
                                + "选择是将打开下载链接。\n"
                                + "更新日志：https://github.com/CKRainbow/commonBird/blob/main/changelog.md",  # FIXME: 不够长？
                            )
                        )

                        if is_update:
                            download_url = DOWNLOAD_URL.get(platform.system().lower())
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
