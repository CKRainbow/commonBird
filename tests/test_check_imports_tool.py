import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_imports.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("check_imports_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return load_tool()


@pytest.fixture
def write(tmp_path):
    def _write(name: str, source: str) -> Path:
        path = tmp_path / name
        path.write_text(source, encoding="utf-8")
        return path

    return _write


def test_missing_module_level_import_is_reported(tool, write, tmp_path):
    path = write("a.py", "import definitely_not_installed_pkg\n")
    runtime, lazy = tool.audit([path], root=tmp_path)
    names = [n for n, _ in runtime]
    assert "definitely_not_installed_pkg" in names
    assert lazy == []


def test_function_level_import_counts_as_lazy(tool, write, tmp_path):
    path = write(
        "b.py",
        "def f():\n"
        "    import another_missing_pkg\n"
        "    return another_missing_pkg\n",
    )
    runtime, lazy = tool.audit([path], root=tmp_path)
    assert runtime == []
    assert [n for n, _ in lazy] == ["another_missing_pkg"]


def test_type_checking_import_counts_as_lazy(tool, write, tmp_path):
    path = write(
        "c.py",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import yet_another_missing_pkg\n",
    )
    runtime, lazy = tool.audit([path], root=tmp_path)
    assert runtime == []
    assert [n for n, _ in lazy] == ["yet_another_missing_pkg"]


def test_class_body_import_is_runtime(tool, write, tmp_path):
    # 类体在导入期执行，缺包会直接崩在 import 上
    path = write("d.py", "class C:\n    import class_body_missing_pkg\n")
    runtime, _ = tool.audit([path], root=tmp_path)
    assert [n for n, _ in runtime] == ["class_body_missing_pkg"]


def test_stdlib_and_local_modules_are_ignored(tool, write, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    path = write(
        "e.py",
        "import json\n"
        "import os.path\n"
        "from src.utils import something\n",
    )
    runtime, lazy = tool.audit([path], root=tmp_path)
    assert runtime == []
    assert lazy == []


def test_relative_import_is_ignored(tool, write, tmp_path):
    path = write("f.py", "from . import sibling\nfrom .module import thing\n")
    runtime, lazy = tool.audit([path], root=tmp_path)
    assert runtime == []
    assert lazy == []


def test_installed_module_is_not_reported(tool, write, tmp_path):
    path = write("g.py", "import json\nimport pathlib\n")
    runtime, lazy = tool.audit([path], root=tmp_path)
    assert runtime == [] and lazy == []
