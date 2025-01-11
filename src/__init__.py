import os
import sys
from pathlib import Path

# -*- coding: utf-8 -*- for popen for windows
from functools import partial
import subprocess

subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")

import execjs

##############################################

if getattr(sys, "frozen", False):
    inner_path = sys._MEIPASS
    application_path = os.path.dirname(sys.executable)
    # 指定 Node.js 可执行文件的具体路径
    runtime = execjs.ExternalRuntime(
        name="Node (custom)",
        command="",  # 替换为你的 Node.js 路径
        encoding="utf-8",
        runner_source=execjs._runner_sources.Node,
    )
    runtime._binary_cache = [(Path(inner_path) / "node.exe").absolute().as_posix()]
    runtime._available = True

    # 设置为默认运行时
    execjs.register("local_node", runtime)
elif __file__:
    inner_path = os.getcwd()
    application_path = inner_path
