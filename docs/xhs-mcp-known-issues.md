# xiaohongshu-mcp 已知问题

本文档说明 xiaohongshu-mcp 的两个已知问题及修复方法。先按 README 安装官方版 MCP，遇到对应症状时再来查看。

---

## 问题 1：MCP 协议版本不兼容 → 完全无法连接

**影响**：所有使用 MCP SDK ≥ 1.24.0 的客户端（Hermes Agent、Claude Code、Cursor 等），连接 xiaohongshu-mcp 时直接返回 HTTP 400，无法使用。

**症状**：

- `hermes mcp test xiaohongshu` 报错 `Failed to connect`
- MCP 日志或客户端日志中出现 `400 Bad Request: Unsupported protocol version`
- xiaohongshu-mcp 服务本身正常运行（`curl http://localhost:18060/health` 返回 healthy）

**原因**：

Hermes Agent 使用的 MCP SDK 在建立连接时发送协议版本 `2025-11-25`，但 xiaohongshu-mcp 服务端只白名单了旧版协议（`2025-06-18`、`2025-03-26`、`2024-11-05`）。服务端在 HTTP 层直接拒绝，没有进入 MCP 协议协商流程。

**上游 Issue**：[xpzouying/xiaohongshu-mcp#697](https://github.com/xpzouying/xiaohongshu-mcp/issues/697)

### 修复方法

> ⚠️ 以下改动涉及修改 Hermes Agent 源码。Hermes 升级（`git pull`）后会覆盖修改，需重新 apply。

**1. 编辑 `~/.hermes/hermes-agent/tools/mcp_tool.py`**

在文件头部的 import 区域添加 `contextlib`：

```python
import contextlib
```

在 MCP import/fallback 块之后（约 line 207），插入以下 context manager：

```python
@contextlib.contextmanager
def _override_protocol_version(version: Optional[str]):
    """Temporarily override mcp.types.LATEST_PROTOCOL_VERSION.

    The mcp SDK hardcodes types.LATEST_PROTOCOL_VERSION in
    ClientSession.initialize() with no per-call override. Some
    MCP servers (e.g. xiaohongshu-mcp) only support older protocol
    versions and reject 2025-11-25 with HTTP 400. This context
    manager provides a per-connection escape hatch.
    """
    if version is None:
        yield
        return
    import mcp.types
    saved = mcp.types.LATEST_PROTOCOL_VERSION
    mcp.types.LATEST_PROTOCOL_VERSION = version
    try:
        yield
    finally:
        mcp.types.LATEST_PROTOCOL_VERSION = saved
```

在 `_run_http()` 方法中，找到 `headers = dict(...)` 之后，添加：

```python
protocol_version: Optional[str] = config.get("protocol_version")
headers["mcp-protocol-version"] = protocol_version or LATEST_PROTOCOL_VERSION
```

找到 `session.initialize()` 调用（两处 HTTP code path），用 context manager 包裹：

```python
async with ClientSession(...) as session:
    with _override_protocol_version(protocol_version):
        self.initialize_result = await session.initialize()
```

**2. 编辑 `~/.hermes/config.yaml`**，在 `mcp_servers` 下为 xiaohongshu 添加 `protocol_version`：

```yaml
mcp_servers:
  xiaohongshu:
    url: http://localhost:18060/mcp
    transport: streamable-http
    protocol_version: "2025-03-26"
```

**3. 重启 Hermes gateway** 使配置生效。

---

## 问题 2：长时间运行后出现「笔记不可访问」

**影响**：偶尔出现，不影响正常使用。

**症状**：

- `mcp_xiaohongshu_get_feed_detail` 返回「笔记不可访问」
- `mcp_xiaohongshu_check_login_status` 显示已登录
- 同一笔记在浏览器中可正常打开

**原因**：

xiaohongshu-mcp 的官方版本每次 MCP 请求都会创建一个新的无头 Chromium 进程，请求结束后 `defer b.Close()` 不保证执行。长时间运行后出现进程泄漏和 WebSocket 连接断裂，同时连续请求可能触发小红书风控限流。

### 方案 A：快速修复（sleep + 重启 MCP）

无需改动任何文件，遇到问题时按以下顺序执行，任一步成功即恢复正常。

**第一步：延迟 15 秒后重试**

```bash
sleep 15
```

用同一参数重新调用 `mcp_xiaohongshu_get_feed_detail`。

**第二步：重启 MCP 服务**

```bash
launchctl kickstart -k gui/$(id -u)/com.hermes.xiaohongshu-mcp
sleep 30
```

重启后等待 30-60 秒预热，然后重试。

**⚠️ 代价**：`kickstart -k` 会强制杀死 MCP 进程和其中的 Chromium 实例。浏览器 session 丢失后，小红书服务端可能判定 session 异常中断，导致 `cookies.json` 中的 Cookie 被标记为无效，需要重新扫码登录。这是重启方式的主要缺点——可能修好一个问题但引入另一个。

**禁止行为**：

- 不要用 `browser_navigate` 验证——会触发风控
- 不要用 `web_extract` 确认笔记存在——增加无用 MCP 请求
- 不要连续无冷却重试——加长风控窗口

### 方案 B：长期修复（编译 PR #488 版本）

从根本上解决：将 xiaohongshu-mcp 的「每次请求创建新 Chromium 进程」改为「所有请求共享一个 browser 实例」，彻底消除进程泄漏和连接断裂。

**优点**：正常使用频率下基本不再出现「笔记不可访问」问题。出现 page 级错误时内部 auto-reconnect 只重建 page，不动 browser 进程和 session，**不会丢 Cookie**。

**缺点**：需要自行编译替换二进制。该 PR 已被上游维护者拒绝合入（截至 2026-05-23 仍未入 main），不再是官方维护的代码路径。

**上游 PR**：[xpzouying/xiaohongshu-mcp#488](https://github.com/xpzouying/xiaohongshu-mcp/pull/488)

是否使用由你自行决定。如果选择使用：

**1. 获取源码并切换分支**

```bash
git clone https://github.com/xpzouying/xiaohongshu-mcp.git /tmp/xhs-build
cd /tmp/xhs-build
git fetch origin pull/488/head:pr-488
git checkout pr-488
```

**2. 编译**

```bash
GOPROXY=https://goproxy.cn,direct go build -o xiaohongshu-mcp-darwin-arm64 .
```

**3. 替换现有二进制**

先停掉 MCP 服务，备份旧二进制后替换。将 `XHS_MCP_BIN` 改成你实际安装的 xiaohongshu-mcp 二进制路径：

```bash
XHS_MCP_BIN="/path/to/xiaohongshu-mcp-darwin-arm64"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.hermes.xiaohongshu-mcp.plist"

launchctl bootout gui/$(id -u)/com.hermes.xiaohongshu-mcp 2>/dev/null
cp "$XHS_MCP_BIN" "$XHS_MCP_BIN.bak"
cp /tmp/xhs-build/xiaohongshu-mcp-darwin-arm64 "$XHS_MCP_BIN"
chmod +x "$XHS_MCP_BIN"
launchctl bootstrap gui/$(id -u) "$LAUNCH_AGENT"
```

如果你的服务名或 launchd plist 路径不同，请按自己的安装方式调整。官方发布新版后可以替换回官方二进制。
