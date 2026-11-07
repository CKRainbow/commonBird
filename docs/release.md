# 发版流程

版本号与打包全部由 **GitHub Actions** 驱动：推一个 `v*` 的 tag，CI 编译四个平台并直接发布
Release。本地只在需要应急/离线时手工打包。

---

## 1. 发版模型

`.github/workflows/build.yml`

| 触发方式 | 得到的 tag | 产物去向 |
|---|---|---|
| push tag `v*` | 该 tag 名 | 正式 Release（`draft: false`、`prerelease: false`、`make_latest: true`） |
| 手动 `workflow_dispatch` | `beta` | 先删旧的 `beta` tag 再重建，发布 **Prerelease**（`Draft <sha>`） |

四个构建作业：`build-linux`（ubuntu-22.04）、`build-win`（windows-latest）、
`build-mac-x64`（macos-15）、`build-mac-arm`（macos-latest），全部用
**Python 3.10 + Node 22**，装完 `requirements-dev.txt` 后调用对应平台的 `build_*` 脚本。

版本号不写在源码里：`get-tag` 作业把 tag 名作为参数传给构建脚本，脚本把它追加成
`src/utils/consts.py` 的 `APP_VERSION`。所以**tag 名就是版本号**，必须形如 `v0.11.1`
（应用内用 `packaging.version.parse` 解析，带 `v` 前缀没问题）。

## 2. 产物命名契约（改名会导致下载链接 404）

`src/utils/consts.py` 的 `DOWNLOAD_URL` 指向 `releases/latest/download/<固定文件名>`：

| 平台键（`platform.system()_platform.machine()`） | 必须存在的资产名 | CI 里怎么来的 |
|---|---|---|
| `windows_amd64` | `commonBird_win_x64.zip` | `build_win.ps1` 直接产出 |
| `linux_x86_64` | `commonBird_linux_x64.tar.gz` | `build_linux.sh` 直接产出 |
| `darwin_x86_64` | `commonBird_mac_x64.tar.gz` | `build_mac.sh` 产出 `commonBird_mac.tar.gz`，CI 里 `mv` 改名 |
| `darwin_arm64` | `commonBird_mac_arm64.tar.gz` | 同上，CI 里 `mv` 改名 |

**本地手工打包 mac 版时别忘了这一步改名**，否则自动更新会打开 404。
四个资产名任何一个缺失，对应平台的"检查更新 → 打开下载链接"就会失效。

## 3. 标准发版流程

### 第 1 步：冻结代码
```bash
git status --short          # 确认没有遗忘的改动（尤其 database/ 下的数据文件）
git log --oneline -5
```

### 第 2 步：写 changelog（先看有没有被发过）
```bash
git tag --sort=-creatordate | head -3
```
- 顶部版本块 **已经打过 tag** → 新建一个版本块，历史块不要再动；
- 还没发过 → 追加到当前块即可。

条目用简体中文、`*` 开头，一条一个修复/特性，和现有风格保持一致。发版后不建议再改这一段
（用户可以拿它对照已下载的版本）。

### 第 3 步：本地自检（干净 venv，别用天天在用的那个）

```bash
# 运行时依赖（模拟用户只装 requirements.txt）
VENV="$TMPDIR/qbird-rt"; uv venv "$VENV" --python 3.12
uv pip install --python "$VENV/Scripts/python.exe" -r requirements.txt
PYTHONPATH= "$VENV/Scripts/python.exe" tools/check_imports.py
PYTHONPATH= "$VENV/Scripts/python.exe" -c "from src.cli.app import CommonBirdApp; CommonBirdApp(); print('启动 OK')"

# 开发依赖 + 测试（CI 用的也是 requirements-dev.txt）
VENV="$TMPDIR/qbird-dev"; uv venv "$VENV" --python 3.12
uv pip install --python "$VENV/Scripts/python.exe" -r requirements-dev.txt
PYTHONPATH= "$VENV/Scripts/python.exe" tools/check_imports.py --tests --strict
PYTHONPATH= "$VENV/Scripts/python.exe" -m pytest -q -p no:cacheprovider
```

`PYTHONPATH=` 必须带：本机全局值指向另一个 venv，会把 `pydantic_core` 之类装成错误版本。
至少要过：依赖自检（含 `--strict`）+ 全部测试 + `CommonBirdApp()` 构造冒烟。

涉及数据/打包的改动，再打一次包并在**空目录**里启动（产物放临时目录，别覆盖 `dist/`）：

```bash
DIST="$TMPDIR/qbird-dist"; WORK="$TMPDIR/qbird-build"
PYTHONPATH= "E:/tmp/qbird-dev/Scripts/python.exe" -m PyInstaller --noconfirm --name commonBird \
  --distpath "$DIST" --workpath "$WORK" --specpath "$WORK" \
  --add-data "E:/Projects/bird/qBird/common_bird_app.tcss:." \
  --add-data "E:/Projects/bird/qBird/public_key.pem:." \
  --exclude-module pandas --exclude-module numpy --exclude-module textual-dev \
  --exclude-module pyinstaller --exclude-module pytest --exclude-module pytest-asyncio \
  --exclude-module respx cli.py

mkdir -p "$TMPDIR/fresh/commonBird"
cp -r "$DIST/commonBird/." "$TMPDIR/fresh/commonBird/"
cp -r database res README.md changelog.md "$TMPDIR/fresh/commonBird/"
cd "$TMPDIR/fresh/commonBird" && ./commonBird.exe
```

> 坑：用了 `--specpath` 之后，相对路径的 `--add-data` 会相对 spec 目录解析并报
> `Unable to find ... common_bird_app.tcss`；所以要给绝对路径。

检查点：界面能起、`关于` 版本号正确、程序目录自动生成 `.env`/`.cache/`/`dump.log`、
日志里没有 `CRITICAL`。没有 tag 时版本号是 `beta`（会跳过更新检查），这正是打包必须传
`-latest_tag` 的原因。

### 第 4 步：提交并推送
```bash
git add -A
git commit -m "chore: 发布 v0.11.1"
git push origin main
```

### 第 5 步：打 tag 并推送（这一步 = 立刻对外发布）
```bash
git tag v0.11.1
git push origin v0.11.1
```
现有 tag 都是轻量 tag（`git cat-file -t v0.11.0` → `commit`），保持一致，不要用
`-a`/`-s` 另起风格。

### 第 6 步：盯 Actions
四个 build 全部绿 → `release` 作业创建 Release。检查：
```bash
gh release view v0.11.1          # 或网页看
```
确认 4 个资产都在：`commonBird_win_x64.zip`、`commonBird_linux_x64.tar.gz`、
`commonBird_mac_x64.tar.gz`、`commonBird_mac_arm64.tar.gz`，且该 Release 被标为 Latest。

### 第 7 步：发布后自检（用旧版本客户端视角）
1. 用**上一版**的程序启动，应弹出"有新版本 v0.11.1"并能打开下载链接（走的是
   `gh-proxy.com` 代理 + `releases/latest`，代理挂了会打开失败，属已知外部依赖）；
2. 下载新包，解压后双击运行，`关于` 里版本号正确（不是 `beta`、不是旧号）；
3. `dump.log` 里没有 `CRITICAL`；
4. 抽一个真实用户路径跑通（`eBird → 修改 Token`、`记录中心 → 迁移到 eBird` 并导入 eBird 网站）。

## 4. Beta 通道

Actions 页面手动 `Run workflow`（`workflow_dispatch`）即可：tag 固定为 `beta`，
发布的是 **Prerelease**，不会被当作 Latest，所以正式用户不会收到更新提示。
另外 `APP_VERSION == "beta"` 时代码会直接跳过更新检查，双保险。

beta 的 `git push -d origin beta` + 重建会让旧 beta 包失去 tag 引用，需要复现问题请自己留档。

## 5. 应急：本地手工打包

```powershell
# Windows（PowerShell，仓库根目录）
powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -latest_tag v0.11.1 -github_api_token <token>
```
```bash
# Linux / macOS
bash build_linux.sh v0.11.1 "<token>"
bash build_mac.sh  v0.11.1 "<token>" && mv commonBird_mac.tar.gz commonBird_mac_x64.tar.gz
```

三个注意点：

1. 脚本用 `>>` 往 `src/utils/consts.py` **追加** `APP_VERSION` / `GITHUB_API_TOKEN`，
   打完包必须还原，否则会把版本号、token 提交进仓库：
   ```bash
   git checkout src/utils/consts.py
   ```
2. 脚本会复制 `database/`、`res/`、`README.md`、`changelog.md` 到 `dist/commonBird/`，
   发布压缩包必须包含这些（缺 `database/` 时程序能开但热点/名录为空、转换会报错）。
3. mac 版是 `--onefile`，产物是单个可执行文件；`taxon_map_preview.py` 会把
   `ch4_to_eb_taxon_map.json` 渲染成 `taxon_map_preview.html`，需要构建机上有 pandas。

手工打包生成的文件需要自己上传到对应 Release（`gh release upload v0.11.1 <文件>`）。

## 6. 常见坑

| 坑 | 说明 |
|---|---|
| tag 一推就正式发布 | `draft: false` + `make_latest: true`，没有"先存草稿确认"的机会。tag 之前把 changelog 和代码定好；发现错了只能发下一个 patch 版本（不要复用/强推 tag，客户端按 tag 比较版本） |
| CI 是 Python 3.10，本地可能用 3.12 | 只在 CI 暴雷的依赖问题（某个包要求 ≥3.11）本地测不出来；改依赖后留意 Actions 日志 |
| `database/` 只有 5 个文件纳入版本库 | 新增运行时数据文件必须 `git add`，否则 CI 包缺文件（`ch3_to_ch4_taxon_map.json` 只给 `dev/` 用，不需要入库） |
| `GITHUB_API_TOKEN` 会被编译进二进制 | 来源是 `secrets.CONTENT_RETRIEVE_TOKEN`，用于更新检查避开限流。等于公开，权限请给只读最小范围 |
| 更新检查依赖外部代理 | `DOWNLOAD_URL` 走 `gh-proxy.com`，该代理不可用时"打开下载链接"会失败，但程序本身正常（已做异常兜底） |
| 打包脚本改过 `.spec` 也没用 | 构建脚本用的是 PyInstaller 命令行参数；仓库里的 `commonBird.spec` 是历史遗留（且被 `.gitignore` 忽略） |
| 发版前忘记更新数据库 | 热点/名录由 `database/` 决定，用户端"更新热点"也能刷新；如要随版本更新数据，发版前用新数据覆盖 `database/` 再提交 |

## 7. 一页清单

```text
[ ] 代码冻结，git status 干净
[ ] changelog 顶部块未被 tag 过；本次条目已写
[ ] 干净环境：tools/check_imports.py --tests + pytest 全绿
[ ] 涉及打包/数据的改动：空目录跑过一次打包产物
[ ] 提交并推送 main
[ ] git tag vX.Y.Z && git push origin vX.Y.Z
[ ] Actions 4 个 build 绿，Release 里 4 个资产齐全且为 Latest
[ ] 旧版本客户端能看到更新提示；新包空目录可启动、版本号正确
[ ] 手工打包的话：git checkout src/utils/consts.py，且资产已上传
```
