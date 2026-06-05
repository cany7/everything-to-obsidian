# 批处理故障排查

## 子进程卡死：短链重定向网络请求被拦截

### 症状

cron job 子进程启动后卡死不动，日志中可以看到 `execute_code` 发起的 HTTP 请求等待审批，最终超时。

### 原因

很多社媒平台的分享链接是短链（如 `xhslink.com`、`youtu.be`、`t.co`），提取前需要 HTTP 重定向获取完整 URL。这一步通过 `execute_code` 的 `requests.get` 发起网络请求。cron job 子进程没有交互界面，审批弹窗无人处理，请求被永久阻塞。

### 处理

**直接中断任务**，提示用户阅读 [`docs/batch-processing.md`](../../docs/batch-processing.md) 中的「前置条件：网络请求白名单」章节，由用户自行在 Hermes 配置中完成白名单设置。

Agent **不得**代为修改 Hermes 配置或审批白名单。
