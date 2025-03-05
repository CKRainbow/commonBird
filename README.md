# commonBird
`commonBird`是一款旨在互通[中国观鸟记录中心](https://www.birdreport.cn/)和[eBird](https://ebird.org)两款国内鸟人常用软件的小工具，在[qBird](https://github.com/TaQini/qBird)的基础之上改进而来，部分灵感来源于 https://github.com/sun-jiao/birdreportcn-to-ebird。

## 预计支持的功能
 - [x] 观鸟记录中心记录一键转换eBird导入文件
    - [x] 本地调整地点
    - [x] 转换随手记（希望能）
    - [x] 支持部分报告导出
    - [x] 增加缓存（主要是地点分配），避免中断后需要重新分配
 - [ ] eBird记录转换观鸟记录中心记录
 - [x] 打包成为exe
 - [ ] 在每个页面添加帮助
 - [x] 自动检查更新并下载
 - [ ] 性能优化
    - [ ] 批量调用Js
 - [ ] 还没想好
 
## 如何使用
- 若使用该仓库，执行 `python cli.py` 即可运行
- 若使用打包后的软件，解压后双击 `commonBird(.exe)` 即可运行
 
## FAQ
- 环境要求(仅运行代码需要)
    - 需要具备 `node` 和 `python` 环境
    - 执行 `npm i` 安装 javascript 依赖项
    - 执行 `pip install -r requirements.txt` 安装 python 依赖项

- 如何获取观鸟记录中心的认证 Token (适用于 Chromium 内核浏览器，如 Chrome/Edge/360 等，对于 Firefox Safari 等浏览器暂时没有教程，欢迎提交 issue)
    - 打开观鸟记录中心[用户中心](birdreport.cn/member)
    - 按下 `f12` 键打开开发工具 `DevTools`
    - 点击上方选项卡`网络`(`Network`)并刷新页面
    - 搜索 `msg` 并点击其中一个搜索结果
    - 点击选项卡`标头`(`Header`)，一般来说默认就是这个选项卡
    - 复制 `X-Auth-Token` 的内容填入即可
    - **请注意在网页上重新登陆会导致 Token 发生变化，届时请重新获取**
    - ![image](./res/bird_report_token.png)

- 如何获取 eBird API Token
    - 填写[eBird API Token 申请表](https://ebird.org/api/keygen)，随后便可获取 API Token

- 地点分配的缓存数据保存在哪里？
    - 保存在 `./.cache/` 文件夹中，文件名为 `location.json`
    - 若下载了新版本，请将该文件夹复制到新版本中，避免重新分配地点

- 如何使用迁移后的 eBird 数据
    - 请注意需要先将 `偏好`(`Preferences`)中的 `俗名`(`Common Name`)设置为 `中文 (SIM)`，否则无法识别鸟名
    - 打开 eBird 官网，点击`提交记录`(`Submit`)
    - 选择`导入数据`(`Import Data`)
    - `格式`(`Format`)选择`eBird记录格式（扩展）`(`eBird Record Format (Extended)`)并上传文件
        - 文件包括所有生成的 csv 文件，文件名以 `_数字` 结尾
    - 跟随网站指引完成导入

- MacOS 提示有安全问题，如何解决
    - 强制打开即可

## 目前存在的问题
* eBird的导入要求文件大小不超过1MB，当前不排除会出现过大的文件
* 部分鸟种俗名在两个平台存在差异，尤其是记录中心的郑三记录，若发现鸟种转换出现问题，请提交 issue 或联系作者

## 鸣谢
* 感谢绿之源的乌桕老师对于名录转换提供的指导
* 感谢九歌、小火鸡、白头鹎等鸟友对于软件的测试与建议

## 欢迎鸟友们一起开发
 - 快来 Fork + Star！

 - My ebird profile URL: https://ebird.org/profile/NDcyMjc0Ng

 - 观鸟中心 ID: ckrainbow

