# 排障参考

仅在 MCP、launchd、Cookie、下载或环境检查失败时读取本文件。正常提取流程不要读取本文件。

## MCP 配置丢失（Hermes 升级后常见）

### 症状

- `hermes mcp test xiaohongshu` 返回 `✗ Server 'xiaohongshu' not found in config`
- MCP 服务正常（`curl http://localhost:18060/health` 返回 healthy）
- 子进程 session 没有 `mcp_xiaohongshu_*` 工具

### 原因

Hermes 升级后 `config.yaml` 的 `mcp_servers` 段中非标准 MCP 条目（如 xiaohongshu 的 streamable-http transport）可能被升级脚本丢弃。

### 修复

在 `~/.hermes/config.yaml` → `mcp_servers:` 下补回：

```yaml
  xiaohongshu:
    url: http://localhost:18060/mcp
    transport: streamable-http
    protocol_version: "2025-03-26"
```

`protocol_version` 必须设为 `2025-03-26`（xiaohongshu-mcp 不支持 SDK 默认的 `2025-11-25`）。配置后需重启 Hermes gateway 或 reload MCP 才能生效。

## MCP 连接被拒绝（HTTP 400 / 协议版本不兼容）

### 症状

- `hermes mcp test xiaohongshu` 返回连接失败
- MCP 日志中出现 `400 Bad Request: Unsupported protocol version`
- xiaohongshu-mcp 服务本身正常运行（`curl http://localhost:18060/health` 返回 healthy）
- `config.yaml` 中 xiaohongshu 的 MCP 配置正确且已配置 `protocol_version`

### 处理规则

**Agent 不得自行修改 Hermes 源码或 MCP 二进制。** 这是需要用户手动操作的底层兼容性问题。

检测到此错误时立即停止当前任务，向用户报告：

> ⚠️ MCP 协议版本不兼容：xiaohongshu-mcp 服务端不支持 Hermes 使用的协议版本，连接被拒绝。这不是 Hermes 的配置问题，而是 xiaohongshu-mcp 的一个已知问题。修复方法见项目文档 `docs/xhs-mcp-known-issues.md` 中的「问题 1」。

**不要尝试以下操作**：

- 不要修改 `~/.hermes/hermes-agent/tools/mcp_tool.py`
- 不要修改 xiaohongshu-mcp 的源码
- 不要尝试降级 Hermes SDK 或 MCP 客户端版本

这些修改需要用户手动完成，Agent 没有权限也不应引导用户直接在对话中执行。

## Cookie 过期 / 未登录

### 症状

- `mcp_xiaohongshu_check_login_status({})` 返回「❌ 未登录」
- `mcp_xiaohongshu_get_feed_detail` 返回鉴权失败或空数据
- MCP 工具注册正常，但调用时报错

### 原因

Cookie 可能因以下原因失效：

- MCP 进程重启后持久化的 cookie 被小红书标记为无效
- Cookie 自然过期（小红书登录态有有效期）
- `data/cookies.json` 文件损坏或丢失

MCP 重启时可能会弹出新的 headless Chromium 窗口——**不要关闭它**，这是 MCP 服务运行必需的浏览器进程，关闭会导致 502。该窗口可以最小化或放在后台。

### 处理规则

**子进程/Agent 不得自行处理 Cookie 过期。** 这是需要用户交互的操作（扫码），Agent 无法独立完成。

检测到 Cookie 过期时立即停止当前任务，向用户（或主 Agent）报告：

> ⚠️ Cookie 已过期，需要重新登录小红书。请用以下方式登录：
>
> 方式一（推荐）：让主 Agent 调用 `mcp_xiaohongshu_get_login_qrcode({})` 获取二维码，用小红书 App 扫码。
>
> 方式二：在终端运行 xiaohongshu-mcp 安装目录下的登录二进制（与 cookies.json 同目录，如 `xiaohongshu-login-darwin-arm64` 或对应平台名称），扫码登录。该二进制会直接写 `cookies.json`。
>
> 登录完成后无需重启 MCP 服务，Cookie 更新后立即生效。

**不要在未登录状态下继续执行任何提取操作。**

## 笔记不可访问（风控限流 / Chromium 连接断裂）

### 症状

- `mcp_xiaohongshu_get_feed_detail` 返回 `笔记不可访问: Sorry, This Page Isn't Available Right Now`
- `mcp_xiaohongshu_check_login_status` 返回 ✅ 已登录
- 笔记在 web 端可以正常打开，仅 MCP 请求失败

### 根因

**A. 风控限流（优先假设）**

连续快速请求可能触发小红书反爬。上游 issue [#627](https://github.com/xpzouying/xiaohongshu-mcp/issues/627) 已确认。多数情况下等待 15 秒后重试可恢复。

**B. Chromium 连接断裂（长时间运行后）**

MCP 使用 Go `rod` 驱动 Chrome 做页面渲染。长时间运行后连接可能退化，表现与限流相同。这是 xiaohongshu-mcp 官方版本的已知问题，详见项目文档 `docs/xhs-mcp-known-issues.md` 中的「问题 2」。

鉴别方法：15s 重试后仍失败 → 重启 MCP → 若恢复则是 Chrome 退化；若仍失败则可能是笔记本身不可访问或 token 失效。

### 修复流程

按以下顺序执行，任一步成功即回到正常流程。

**第一步：延迟 15 秒后重试（必做）**

```bash
sleep 15
```

用同一 `feed_id` + `xsec_token` 重新调用 `mcp_xiaohongshu_get_feed_detail`。冷却期间不要调用其他 MCP 工具，避免重置风控计时。

**第二步：重启 MCP 后重试一次**

正确的 launchd service name（通过 Hermes 标准方式安装时自动生成）是 `com.hermes.xiaohongshu-mcp`。如果你使用其他方式安装，请替换为你的实际 service name：

```bash
launchctl kickstart -k gui/$(id -u)/<你的 xiaohongshu-mcp service name>
sleep 30
curl -s http://localhost:18060/health
```

重启后 Chromium 需要 30-60s 预热；过早调用可能超时或返回假「笔记不可访问」。重启 MCP 可能导致登录丢失，如果登录丢失，按「Cookie 过期」节处理，停止操作。

重启后只重试一次。仍失败 → 报告并停止。

> ℹ️ 如果 launchd service 不存在，请参考 xiaohongshu-mcp 项目文档配置 launchd。

修复完成后，告知用户查看项目文档 `docs/xhs-mcp-known-issues.md` 中的「问题 2」，了解长期修复方案。

### 禁止行为

- **禁止**用 `browser_navigate` 验证——会被 300012 风控拦截
- **禁止**用 `web_extract` 确认笔记存在——只能拿到页脚，且会产生额外 MCP 请求、恶化风控状态
- **禁止**逐条尝试 `launchctl kickstart/list/lsof/kill/kill -9/find/load`——一条 `kickstart -k` 搞定
- **禁止**连续无冷却重试——无冷却的重试只会加长风控窗口
- **禁止**将此类错误直接归因于 Cookie 过期并尝试扫码登录
- **禁止** Agent 自行尝试编译或替换 xiaohongshu-mcp 二进制——这需要用户手动操作，Agent 没有权限

## 批量处理策略

批量跑前做 MCP 健康预检，避免第一条就撞墙：

```bash
hermes mcp test xiaohongshu
```

批量处理间隔由调度方控制。建议每条子进程之间至少 `sleep 5`，避免连续请求触发风控。

## Whisper 转录超时

Whisper 转录命令超时未产出结果时：

1. **不要阻塞后续步骤**——按主文档设置 `video.transcript: null`，在 `content.md` 视频字幕段写入 `> ⚠️ 视频转录失败`。
2. **不要**因为转录失败就放弃整个内容包——视频帖子的核心信息通常已在 `desc` 文本中，转录只是补充。

## 提取错误处理流程

当依赖服务不可用导致步骤失败时，按以下规则处理，**不得无底线重试直到超时**：

1. **错误分类**：判断错误是「可修复的外部依赖问题」「需要用户介入的问题」还是「无法处理的未知错误」。
2. **可修复问题**：MCP 工具不可用 / MCP 返回 502 / 图片下载 403 / MCP 返回「笔记不可访问」且登录正常。
   
   **「笔记不可访问」→ 必须 sleep 15s 后重试一次**（绝大多数是服务器限流，重试即通）。重试仍失败再继续执行本文件的其他排障步骤。
   
   其他问题直接执行相应修复，然后重试一次。
3. **需要用户介入**：Cookie 过期 / 未登录——Agent 无法独立完成扫码登录。立即停止操作，向用户（或主 Agent）报告 Cookie 过期，并按本文件「Cookie 过期 / 未登录」节告知用户如何重新登录。**不要在未登录状态下继续任何操作。**
4. **修复后仍失败**：停止操作，向用户报告：「⚠️ {步骤名} 失败：{错误摘要}，已尝试修复（{修复操作}）但未恢复。」
5. **无法识别的错误**：停止操作，报告：「⚠️ {步骤名} 遇到未识别错误：{错误摘要}。停止处理。」
6. **禁止行为**：
   - 禁止用原始 HTTP fallback 替代不可用的 MCP 工具
   - 禁止绕过 `vision_analyze` 工具调用底层视觉模型或 HTTP 接口。若 `vision_analyze` 不可用，重试一次；仍不可用则立即停止提取并告知用户「VLM 不可用」
   - 禁止对同一错误重试超过 1 次（修复后只重试一次）
   - 禁止在错误状态下继续后续步骤

## JSON lint 报错

`write_file` 对 `.json` 文件自动 lint。若写入 `metadata.json` / `output.json` 后出现 `JSONDecodeError`，不要直接忽略：

先用 `python3 -m json.tool <file>` 或重新读取文件确认是否真能 parse。只有确认文件可 parse、且错误来自工具层误报时才继续；如果文件不可 parse，必须重写该 JSON。

## 短链重定向 404

`expand-shortlink.py` 请求短链重定向后可能到达 `xiaohongshu.com/404?errorCode=-510001`，但 MCP `get_feed_detail` 仍可正常获取数据。

此时仍提取 `note_id` 和 `xsec_token` 继续调用 MCP，不要在第一步就放弃。`source_url` 回退使用原始输入短链——404 URL 不是可访问的内容链接，不应写入 `source_url`。

## 纯图片帖检测（跳过图片模式）

精简模式（跳过图片下载 + VLM）下，当 `desc` 仅含标签（全是 `#xxx`）而 `title` 承诺了实质内容时，说明内容全在图片中。

此时应向用户提示：「本帖正文仅含标签，实际内容在图片中，跳过图片后归档内容较薄。如需完整内容，重新带 VLM 提取即可」。不要静默输出空壳归档。
