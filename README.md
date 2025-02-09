# commonBird
`commonBird`是一款旨在互通[中国观鸟记录中心](https://www.birdreport.cn/)和[eBird](https://ebird.org)两款国内鸟人常用软件的小工具，在[qBird](https://github.com/TaQini/qBird)的基础之上改进而来，部分灵感来源于 https://github.com/sun-jiao/birdreportcn-to-ebird。

## 预计支持的功能
 - [x] 观鸟记录中心记录一键转换eBird导入文件
    - [x] 本地调整地点
    - [x] 转换随手记（希望能）
    - [x] 支持部分报告导出
    - [ ] 增加缓存（主要是地点分配），避免中断后需要重新分配
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

- 如何获取观鸟记录中心的认证 Token
    - 打开观鸟记录中心[用户中心](birdreport.cn/member)
    - 按下 `f12` 键打开开发工具 `DevTools`
    - 点击上方选项卡`网络`(`Network`)并刷新页面
    - 搜索 `msg` 并点击其中一个搜索结果
    - 点击选项卡`标头`(`Header`)，一般来说默认就是这个选项卡
    - 复制 `X-Auth-Token` 的内容填入即可
    - **请注意在网页上重新登陆会导致 Token 发生变化，届时请重新获取**
    - ![image](./res/bird_report_token.png)

- 如何使用迁移后的 eBird 数据
    - 打开 eBird 官网，点击`提交记录`(`Submit`)
    - 选择`导入数据`(`Import Data`)
    - `格式`(`Format`)选择`eBird记录格式（扩展）`(`eBird Record Format (Extended)`)并上传文件
        - 文件包括所有生成的 csv 文件，文件名以 `_数字` 结尾
    - 跟随网站指引完成导入

## 目前存在的问题
* eBird的导入要求文件大小不超过1MB，当前不排除会出现过大的文件
* 部分鸟种俗名在两个平台存在差异，尤其是记录中心的郑三记录，若发现鸟种转换出现问题，请提交 issue 或联系作者
* MacOS 启动时会受到安全限制，目前不清楚解决方法
* 即使学名与eBird上的学名完全相同，eBird依旧会将其标注为未知，其实在修正时直接复制学名选择相应选项即可


## 欢迎鸟友们一起开发
 - 快来 Fork + Star！

 - My ebird profile URL: https://ebird.org/profile/NDcyMjc0Ng

 - 观鸟中心 ID: ckrainbow

