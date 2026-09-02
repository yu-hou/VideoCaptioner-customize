# Cookie 配置指南

配置 Cookie 以下载需要登录的视频。抖音和视频号可在软件内直接读取 Chrome Cookie，其他平台可导出 `cookies.txt`。

## 何时需要配置 Cookie？

在以下情况下需要配置 Cookie：

1. 下载抖音或微信视频号视频
2. 下载视频网站需要登录信息
3. 只能下载较低分辨率的视频
4. 网络条件较差时需要验证

## 获取 Cookie

### 抖音 / 视频号（推荐）

打开 **设置 → 抖音 Cookie** 或 **设置 → 视频号 Cookie（腾讯元宝）**：

1. 选择已经登录对应网站的 Chrome 用户
2. 点击“打开抖音”或“打开腾讯元宝”完成登录
3. 点击“读取 Cookie”
4. 粘贴测试链接并点击“测试 Cookie”

视频号需要先登录腾讯元宝，详见 [视频号下载](/guide/wechat-channels-download)。

### 其他平台

1. 使用浏览器扩展导出 Netscape 格式的 `cookies.txt`
2. 放到 NovaCaption 的 `AppData/` 目录
3. 与软件内读取的抖音、元宝 Cookie 可以共存于同一文件

完整步骤见 [Cookie 配置指南](/guide/cookies-config)。

## 配置方法

1. 抖音、视频号：在设置页读取 Chrome Cookie
2. 其他网站：将 `cookies.txt` 放到 `AppData/` 目录
3. Cookie 失效后重新登录并再次读取或导出

---

相关文档：
- [快速开始](/guide/getting-started)
- [视频号下载](/guide/wechat-channels-download)
- [Cookie 配置指南](/guide/cookies-config)
