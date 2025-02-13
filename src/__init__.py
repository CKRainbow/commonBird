import os
import sys
import subprocess
import platform
from pathlib import Path


class MyPopen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("encoding", "utf-8")
        super().__init__(*args, **kwargs)


import execjs

if platform.system() == "Windows":
    subprocess.Popen = MyPopen
    _inner_node_name = "node.exe"
else:
    _inner_node_name = "node"

if getattr(sys, "frozen", False):
    inner_path = Path(sys._MEIPASS)
    application_path = Path(os.path.dirname(sys.executable))
    # 指定 Node.js 可执行文件的具体路径
    runtime = execjs.ExternalRuntime(
        name="Node (custom)",
        command="",  # 替换为你的 Node.js 路径
        encoding="utf-8",
        runner_source=execjs._runner_sources.Node,
    )
    runtime._binary_cache = [(inner_path / _inner_node_name).absolute().as_posix()]
    runtime._available = True

    # 设置为默认运行时
    execjs.register("local_node", runtime)
elif __file__:
    inner_path = Path(os.getcwd())
    application_path = Path(inner_path)

database_path = application_path / "database"
env_path = application_path / ".env"
cache_path = application_path / ".cache"
output_path = application_path / "output"
