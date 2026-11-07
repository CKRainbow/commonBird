"""检查依赖清单是否与源码导入一致（仅在标准库下运行）。

用途：在全新环境（干净 venv、别人的机器、打包机）里先跑一遍，避免
"本机能跑、别人一装就 ModuleNotFoundError"。

区分两类导入：
  * 模块级导入 —— 程序启动就会执行，缺失 = 直接起不来（必须进 requirements.txt）
  * 函数内 / TYPE_CHECKING 内的延迟导入 —— 缺失只影响对应功能（可放 requirements-dev.txt）

用法：
    python tools/check_imports.py          # 检查 src/ 与 cli.py
    python tools/check_imports.py --tests  # 连 tests/ 一起检查
    python tools/check_imports.py --strict # 延迟导入缺失也算失败

退出码：0 = 运行时依赖齐全；1 = 有模块级依赖缺失（--strict 时含延迟导入）。
"""

import ast
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 导入名 -> 发行包名（与导入名不一致的几个）
DIST_NAMES = {
    "PIL": "pillow",
    "Crypto": "pycryptodome",
    "dotenv": "python-dotenv",
    "Levenshtein": "python-Levenshtein",
    "textual_image": "textual-image",
}


class _Collector(ast.NodeVisitor):
    """把模块级导入和函数内（延迟）导入分开收集。"""

    def __init__(self):
        self.runtime = {}
        self.lazy = {}
        self._in_function = 0
        self._in_type_checking = 0

    # 函数体内的导入是延迟执行；类体在导入期执行，不算延迟
    def visit_FunctionDef(self, node):
        self._in_function += 1
        self.generic_visit(node)
        self._in_function -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node):
        is_type_checking = (
            isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
        )
        if is_type_checking:
            self._in_type_checking += 1
            self.generic_visit(node)
            self._in_type_checking -= 1
        else:
            self.generic_visit(node)

    def _record(self, name):
        delayed = self._in_function or self._in_type_checking
        target = self.lazy if delayed else self.runtime
        target.setdefault(name, None)

    def visit_Import(self, node):
        for alias in node.names:
            self._record(alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module:  # 相对导入属于本仓库
            self._record(node.module.split(".")[0])
        self.generic_visit(node)


def local_modules(root: pathlib.Path = ROOT) -> set:
    """仓库自身的顶层模块名（src / tools / tests 等），不算第三方依赖。"""
    names = {"src"}
    for child in root.iterdir():
        if child.is_dir() and (child / "__init__.py").exists():
            names.add(child.name)
    return names


def audit(paths, root: pathlib.Path = ROOT):
    """返回 (模块级缺失, 延迟导入缺失)，元素为 (模块名, 使用位置列表)。"""
    skip = set(sys.stdlib_module_names) | local_modules(root)
    runtime = {}
    lazy = {}

    for path in paths:
        try:
            tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as e:
            print(f"跳过 {path}: {e}")
            continue
        collector = _Collector()
        collector.visit(tree)
        for name in collector.runtime:
            runtime.setdefault(name, set()).add(str(path))
        for name in collector.lazy:
            lazy.setdefault(name, set()).add(str(path))

    def missing(mapping):
        return [
            (name, sorted(users))
            for name, users in sorted(mapping.items())
            if name not in skip and importlib.util.find_spec(name) is None
        ]

    return missing(runtime), missing(lazy)


def default_paths(with_tests: bool):
    paths = list((ROOT / "src").rglob("*.py")) + [ROOT / "cli.py"]
    if with_tests:
        paths += list((ROOT / "tests").rglob("*.py"))
    return paths


def main() -> int:
    args = sys.argv[1:]
    with_tests = "--tests" in args
    strict = "--strict" in args

    paths = default_paths(with_tests)
    runtime_missing, lazy_missing = audit(paths)

    for name, users in lazy_missing:
        print(
            f"  · 延迟导入缺失 {name}（发行包名 {DIST_NAMES.get(name, name)}，"
            f"不影响启动）：{', '.join(users[:2])}"
        )

    if not runtime_missing and not (strict and lazy_missing):
        print(f"依赖检查通过（扫描 {len(paths)} 个文件）")
        return 0

    if runtime_missing:
        print("以下模块在启动路径上被导入，但当前环境没有安装：")
        for name, users in runtime_missing:
            print(f"  ✗ {name:<16} 应加入 requirements.txt：{', '.join(users[:3])}")
    if strict and lazy_missing:
        print("--strict：以下延迟导入也需要安装（应加入 requirements-dev.txt）：")
        for name, users in lazy_missing:
            print(f"  ✗ {name:<16} {', '.join(users[:3])}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
