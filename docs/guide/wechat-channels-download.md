# 视频号下载

NovaCaption 支持 `https://weixin.qq.com/sph/...` 视频号分享链接。解析使用本机
Chrome 中的腾讯元宝登录 Cookie，不需要安装根证书、修改系统代理、启动伴侣服务，
也不要求打开微信电脑端。

## 首次配置

首次启动向导里也有同样的步骤，之后可以随时在设置中重新配置：

1. 打开 NovaCaption 的 **设置 → 视频号 Cookie（腾讯元宝）**。
2. 选择平时使用的 Chrome 用户。
3. 点击 **打开腾讯元宝**，完成登录并确认元宝首页可以正常打开。
4. 回到 NovaCaption，点击 **读取 Cookie**。
5. 使用默认测试链接或粘贴其他视频号链接，点击 **测试 Cookie**。

读取时只保存 `.tencent.com` 和 `yuanbao.tencent.com` 下、腾讯元宝解析所需的
Cookie，并与现有 `AppData/cookies.txt` 合并，不会覆盖已保存的抖音等平台 Cookie。

配置成功后，像其他平台一样把视频号链接粘贴到主页即可下载。命令行也使用同一个
`AppData/cookies.txt`：

```bash
videocaptioner download "https://weixin.qq.com/sph/AtBrYj8dQb" -o ./downloads
```

## 工作流程

NovaCaption 会把分享链接和元宝 Cookie 发送到腾讯元宝的 HTTPS 解析接口，使用返回的
临时凭据读取视频号详情，再从腾讯视频 CDN 直接下载媒体。元宝 Cookie 不会发送给
视频 CDN，也不会写入日志或错误信息。

## 常见问题

- **没有有效的腾讯元宝 Cookie**：确认选择的是刚才登录元宝时使用的 Chrome 用户，
  然后重新点击“读取 Cookie”。
- **Cookie 已失效**：在同一 Chrome 用户中重新登录元宝，再读取一次 Cookie。
- **内容暂时无法播放**：视频可能已删除、仅特定用户可见、为图集或直播回放；当前仅
  支持能够通过分享页播放的普通视频。
- **Chrome 正在运行时读取失败**：先完全退出 Chrome 后重试；读取完成后可以重新打开。

## 安全说明

Cookie 相当于网页登录凭据，请勿上传、截图或分享 `cookies.txt`。建议使用权限较少的
账号，并在不再使用时退出腾讯元宝。该方案依赖腾讯未公开的网页接口，接口调整后可能
需要更新 NovaCaption。
