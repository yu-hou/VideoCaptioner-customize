# Cookie 配置指南

本指南将帮助你配置浏览器 Cookie，以便下载需要登录才能访问的视频。

## 软件内一键读取（抖音 / 视频号）

抖音和微信视频号不需要手动导出 Cookie 文件。和首次启动向导一样：

1. 打开 **设置 → 抖音 Cookie** 或 **设置 → 视频号 Cookie（腾讯元宝）**。
2. 选择平时使用的 Chrome 用户。
3. 点击 **打开抖音** 或 **打开腾讯元宝**，完成登录（抖音还需确认视频能播放）。
4. 回到 NovaCaption，点击 **读取 Cookie**。
5. 粘贴测试链接，点击 **测试 Cookie**。

两次读取都只保存对应网站的 Cookie，并写入同一份 `AppData/cookies.txt`，不会互相覆盖。视频号解析依赖腾讯元宝登录状态，详细步骤见 [视频号下载](./wechat-channels-download.md)。

YouTube、B 站等其他平台仍可按下面的扩展导出方式补充 Cookie。

## 为什么需要配置 Cookie？

在使用 NovaCaption 下载视频时，你可能会遇到以下错误：

![Cookie 错误提示](https://h1.appinn.me/file/1731487405884_cookies_error.png)

这通常是因为：

1. **某些视频平台**（如 B 站、YouTube）需要用户登录才能获取高质量视频
2. **网络条件较差**时，部分网站需要验证用户身份才能下载
3. **地区限制**的内容需要特定账号权限

:::tip 何时需要配置
抖音、视频号必须先在软件内读取 Cookie。YouTube、B 站等平台通常可直接下载，只有出现登录或清晰度错误时才需要按下面步骤导出 `cookies.txt`。
:::

---

## 其他平台：导出 cookies.txt

### 1. 安装浏览器扩展

根据你使用的浏览器选择对应的扩展：

| 浏览器      | 扩展名称              | 下载链接                                                                                                                |
| ----------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Chrome**  | Get CookieTxt Locally | [Chrome 应用店](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)       |
| **Edge**    | Export Cookies File   | [Edge 插件商店](https://microsoftedge.microsoft.com/addons/detail/export-cookies-file/hbglikhfdcfhdfikmocdflffaecbnedo) |
| **Firefox** | cookies.txt           | [Firefox 附加组件](https://addons.mozilla.org/zh-CN/firefox/addon/cookies-txt/)                                         |

:::info 其他浏览器
如果你使用其他浏览器（如 Safari、Opera），可以搜索类似的 "Export Cookies" 扩展。
:::

### 2. 导出 Cookie 文件

安装扩展后，按以下步骤操作：

#### 步骤一：登录目标网站

打开需要下载视频的网站（如 B 站、YouTube），**确保你已登录账号**。

#### 步骤二：导出 Cookie

1. 在该网站页面点击浏览器扩展图标
2. 选择 **"Export Cookies"** 或类似选项
3. 扩展会自动下载一个 `cookies.txt` 文件

![导出 Cookie 示例](https://h1.appinn.me/file/1731487405884_cookies_export.png)

:::warning 注意事项

- 确保在**目标网站的页面**上导出 Cookie（不是在其他网站）
- 某些扩展可能默认导出为 `cookies.json`，请重命名为 `cookies.txt`
  :::

### 3. 放置 Cookie 文件

将导出的 `cookies.txt` 文件移动到 NovaCaption 的 **AppData** 目录下。

#### AppData 目录位置

NovaCaption 的 AppData 目录通常位于：

```
NovaCaption/
├─ app/
├─ resource/
├─ AppData/          # Cookie 文件放这里
│  ├─ cache/
│  ├─ logs/
│  ├─ models/
│  ├─ cookies.txt    # ← 将文件放在这里
│  └─ settings.json
└─ work-dir/
```

:::tip 快速定位
在 NovaCaption 中点击 **设置 → 打开日志文件夹**，然后返回上一级目录即可看到 `AppData` 文件夹。
:::

### 4. 验证配置

配置完成后：

1. 重启 NovaCaption
2. 再次尝试下载视频
3. 如果仍然失败，请检查 Cookie 文件是否正确放置

---

## 常见问题

### Cookie 文件格式不正确

**问题**：提示 "Cookie 文件格式错误"

**解决方法**：

- 确保文件名为 `cookies.txt`（不是 `cookies.json` 或其他）
- 使用文本编辑器打开文件，检查是否为 Netscape Cookie 格式
- 重新导出 Cookie，确保选择正确的格式

### 下载仍然失败

**问题**：配置 Cookie 后仍然无法下载

**可能原因**：

1. **Cookie 已过期** - 重新登录网站并导出新的 Cookie
2. **账号权限不足** - 确认你的账号能否在浏览器中正常观看该视频
3. **地区限制** - 视频可能仅限特定地区访问

### 需要为每个网站单独配置吗？

**答案**：不需要。

- 一个 `cookies.txt` 文件可以包含多个网站的 Cookie
- 浏览器扩展通常会导出**所有已登录网站**的 Cookie
- 建议在常用的视频网站（B 站、YouTube 等）都登录后再导出

### Cookie 安全吗？

**安全建议**：

- Cookie 文件包含你的登录信息，**不要分享给他人**
- 定期更新 Cookie（每月导出一次）
- 如果担心安全，可以使用**小号**登录并导出 Cookie

### 支持哪些视频网站？

NovaCaption 使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 作为下载引擎，支持 1000+ 个视频网站，包括：

- 🎬 YouTube、Bilibili、抖音、快手、微信视频号
- 📺 爱奇艺、腾讯视频、优酷
- 🎓 Coursera、Udemy、Khan Academy
- 🐦 Twitter、Facebook、Instagram
- ...以及更多

完整列表请查看 [yt-dlp 支持列表](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 下一步

配置完成后，你可以：

- 查看 [快速开始指南](./getting-started.md) 下载并处理视频
- 了解 [批量处理功能](./batch-processing.md) 处理多个视频
- 探索 [视频下载技巧](./video-download.md)
