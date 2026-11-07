import logging
import os
import webbrowser
import platform
from typing import Dict, Optional, Union, TYPE_CHECKING
from packaging import version

import httpx
from textual import work, on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, HorizontalGroup
from textual.widgets import Footer, Header, Button, Markdown
from textual.worker import Worker, WorkerState

from src import application_path, database_path, inner_path, cache_path
from src.utils.api_exceptions import DataFileError
from src.utils.consts import GITHUB_API_TOKEN, APP_VERSION, DOWNLOAD_URL
from src.utils.files import read_json, write_json
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

        self.location_assign: Dict[str, Union[str, Dict]] = {}

        self.first_open = True
        if APP_VERSION == "beta":
            self.version = APP_VERSION
        else:
            self.version = version.parse(APP_VERSION)

        self.reload_hotspot_info()

        # 热点数据应同时存在或同时缺失，缺一个时只记录日志，不再 assert 让程序崩溃
        if bool(self.ebird_cn_hotspots) != bool(self.ebird_other_hotspots):
            logging.warning(
                "热点数据不完整：ebird_cn_hotspots.json 与 ebird_other_hotspots.json 应同时存在"
            )

        # 数据文件缺失或损坏时返回 None，由后续逻辑给出提示（如 on_mount 中的检查），
        # 而不是在启动阶段抛出 JSONDecodeError/KeyError 直接退出
        self.ch4_to_eb_taxon_map = read_json(database_path / "ch4_to_eb_taxon_map.json")
        self.ebird_taxon_info = read_json(database_path / "ebird_taxonomy.json")

        cache_data = read_json(cache_path / "location_assign.json")
        if isinstance(cache_data, dict):
            if "version" in cache_data and "data" in cache_data:
                self.location_assign = cache_data["data"] or {}
            else:
                # Old format, needs migration
                self.location_assign = cache_data
                self.migrate_legacy_location_assign()

    def migrate_legacy_location_assign(self) -> None:
        """把只存 locName 的旧版地点缓存迁移为 locId。"""
        if not self.ebird_cn_hotspots and not self.ebird_other_hotspots:
            # 没有热点数据时无法迁移，保留旧数据，等更新热点后再迁移
            logging.warning("缺少热点数据，跳过旧版地点缓存迁移")
            return

        name_to_id = {}
        for loc_id, v in (self.ebird_cn_hotspots or {}).items():
            name_to_id[v.get("locName", loc_id)] = loc_id
        for loc_id, v in (self.ebird_other_hotspots or {}).items():
            name_to_id[v.get("locName", loc_id)] = loc_id

        result = {}
        for k, v in self.location_assign.items():
            if isinstance(v, dict):
                result[k] = v
            elif v in name_to_id:
                result[k] = name_to_id[v]
            else:
                result[k] = v
        self.location_assign = result
        self.save_location_assign_cache({})

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
        content = self._read_text("changelog.md")
        if content is None:
            await self.push_screen_wait(
                MessageScreen("无法读取 changelog.md，请检查程序文件是否完整")
            )
            return
        await self.push_screen_wait(DisplayScreen(Markdown(content)))

    @on(Button.Pressed, "#help")
    @work
    async def on_help_pressed(self, event: Button.Pressed) -> None:
        content = self._read_text("README.md")
        if content is None:
            await self.push_screen_wait(
                MessageScreen("无法读取 README.md，请检查程序文件是否完整")
            )
            return
        await self.push_screen_wait(DisplayScreen(Markdown(content)))

    def _read_text(self, name: str) -> Optional[str]:
        """读取程序目录下的文本文件，缺失或不可读时返回 None。"""
        try:
            return (application_path / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logging.error(f"读取 {name} 失败：{e}")
            return None

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
                except (httpx.HTTPError, KeyError, ValueError) as e:
                    # 网络异常、返回体缺字段（KeyError）、版本号无法解析（ValueError）都不能崩
                    logging.error(f"检查更新失败：{e}")
                    await self.push_screen_wait(
                        MessageScreen(f"获取最新版本信息失败：{e}")
                    )

    def save_location_assign_cache(self, location_assign_cache: dict) -> None:
        self.location_assign.update(location_assign_cache)
        self.location_assign = {
            k: v for k, v in self.location_assign.items() if v is not None
        }

        cache_data = {"version": APP_VERSION, "data": self.location_assign}

        try:
            write_json(cache_path / "location_assign.json", cache_data, indent=4)
        except DataFileError as e:
            # 缓存目录不可写时不能崩，提示后继续（本次会话的地点分配仍然可用）
            logging.critical(f"保存地点分配缓存失败：{e}")
            try:
                self.notify(f"{e}\n本次的地点分配结果不会被保存", severity="error")
            except Exception:  # notify 在 app 尚未运行时不可用
                pass

    def reload_hotspot_info(self) -> None:
        data = read_json(database_path / "ebird_cn_hotspots.json")
        if isinstance(data, dict) and "data" in data:
            self.ebird_cn_hotspots = data["data"] or {}
            self.ebird_hotspots_update_date = data.get("last_update_date")

            # Migrate old format to new format
            if self.ebird_cn_hotspots and any(
                "|" in k for k in self.ebird_cn_hotspots.keys()
            ):
                self.ebird_cn_hotspots = {
                    v["locId"]: v for v in self.ebird_cn_hotspots.values()
                }
                data["data"] = self.ebird_cn_hotspots
                self._rewrite_hotspot_file("ebird_cn_hotspots.json", data)

        data = read_json(database_path / "ebird_other_hotspots.json")
        if isinstance(data, dict) and "data" in data:
            self.ebird_other_hotspots = data["data"] or {}
            self.ebird_hotspots_update_date = data.get("last_update_date")

            # Migrate old format to new format
            if self.ebird_other_hotspots and any(
                "|" in k for k in self.ebird_other_hotspots.keys()
            ):
                self.ebird_other_hotspots = {
                    v["locId"]: v for v in self.ebird_other_hotspots.values()
                }
                data["data"] = self.ebird_other_hotspots
                self._rewrite_hotspot_file("ebird_other_hotspots.json", data)

    def _rewrite_hotspot_file(self, name: str, data: dict) -> None:
        """把迁移后的热点数据写回文件；失败只记录日志，不影响启动。"""
        try:
            write_json(database_path / name, data)
        except DataFileError as e:
            logging.error(f"迁移热点数据失败：{e}")

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
            # 把失败原因显示给用户，避免操作静默失败、界面像卡住一样
            try:
                self.notify(
                    f"操作失败：{exception or '未知错误'}", severity="error", timeout=10
                )
            except Exception:
                pass
