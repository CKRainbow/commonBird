import logging
import sys

from dotenv import load_dotenv

from src import application_path, env_path
from src.cli.app import CommonBirdApp
from textual.logging import TextualHandler

# 创建文件处理器
file_handler = logging.FileHandler(
    filename=application_path / "dump.log", mode="w", encoding="utf-8"
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[file_handler, TextualHandler()],
)

logger = logging.getLogger(__name__)


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """
    自定义的异常处理钩子，用于记录未捕获的异常。
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # 用户通过 Ctrl+C 中断程序，正常退出
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 记录严重的错误和完整的堆栈跟踪
    logger.critical("捕获到未处理的异常", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_uncaught_exception

if not env_path.exists():
    open(env_path, "a").close()
load_dotenv(env_path)


def main():
    app = CommonBirdApp()
    reply = app.run()

    if app.return_code != 0:
        logger.error(f"程序退出，退出码：{reply} {app.return_code} {app.return_value}")


if __name__ == "__main__":
    main()
