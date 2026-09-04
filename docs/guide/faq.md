# 常见问题

常见问题解答。

## 安装问题

### Q: 如何安装依赖？

A: 参考[快速开始](/guide/getting-started)中的安装步骤。

## 使用问题

### Q: 转录时出现幻觉或重复怎么办？

A: 
- 启用 VAD 过滤
- 更换更大的模型
- 尝试 Large-v2 而不是 Large-v3
- 在嘈杂环境中启用音频分离

### Q: LLM 请求失败怎么办？

A:
- 检查 API Key 是否正确
- 检查 Base URL 是否正确
- 降低线程数
- 检查网络连接
- 查看日志文件获取详细错误信息

### Q: 抖音或视频号下载失败怎么办？

A:
- 打开 **设置 → 抖音 Cookie** 或 **设置 → 视频号 Cookie（腾讯元宝）**
- 选择刚才登录时使用的 Chrome 用户
- 重新打开对应网页完成登录，再点击“读取 Cookie”和“测试 Cookie”
- 视频号不需要安装证书或开启系统代理，但需要腾讯元宝处于登录状态
- 详细步骤见 [Cookie 配置](/guide/cookies-config) 和 [视频号下载](/guide/wechat-channels-download)

更多问题，请访问 [GitHub Issues](https://github.com/yu-hou/VideoCaptioner-customize/issues)。
