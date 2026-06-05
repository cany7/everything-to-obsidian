# 安装与配置

## 前置条件

- **Hermes Agent** 已安装并正常运行
- **LLM provider** 已配置（`vision_analyze` 图片分析依赖）
- **Search provider** 已配置（`web_search` 溯源搜索依赖）

以上为 Hermes 基础配置，详见 [Hermes Agent 文档](https://hermes-agent.nousresearch.com/docs)。

## 1. 安装 Skills

```bash
git clone https://github.com/cany7/everything-to-obsidian.git \
  ~/.hermes/skills/everything-to-obsidian
```

Hermes 会递归发现 repo 内所有 `SKILL.md`，无需手动注册。

## 2. 配置环境变量

在 `~/.hermes/.env` 中添加：

```bash
# Obsidian vault 根目录绝对路径（含 Library/ 子目录的那一级）
OBSIDIAN_VAULT_PATH=/Users/yourname/ObsidianVault

# 提取内容的基础存储目录
# 各 extractor 自动在其下创建子目录：$EXTRACT_OUTPUT_DIR/xhs/、$EXTRACT_OUTPUT_DIR/youtube/ 等
EXTRACT_OUTPUT_DIR=/Users/yourname/Documents/extract_files
```

Skills 通过 `os.environ.get()` 在 `execute_code` 中读取这些路径，未配置时会停止并提示。

## 3. 重启

配置完 `.env` 后重启 Hermes gateway：

```bash
hermes gateway restart
```

---

## 可选：安装 xiaohongshu-mcp

小红书内容提取依赖 [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) 提供的 MCP 工具。不使用小红书提取功能可跳过。

### 安装服务

从 [Releases](https://github.com/xpzouying/xiaohongshu-mcp/releases) 下载对应平台的二进制，或 `go build` 编译。详见项目 README。

### 配置 MCP 连接

在 `~/.hermes/config.yaml` 的 `mcp_servers` 中添加：

```yaml
mcp_servers:
  xiaohongshu:
    url: http://localhost:18060/mcp
    transport: streamable-http
```

添加后重启 gateway 使配置生效。

### 登录

启动 MCP 服务后，用 `mcp_xiaohongshu_get_login_qrcode` 获取二维码，小红书 App 扫码登录。`cookies.json` 会自动写入 MCP 安装目录。

### 配置 cookies 路径

在 `~/.hermes/.env` 中添加：

```bash
# xiaohongshu-mcp 的 cookies.json 绝对路径，用于 CDN 图片/视频下载鉴权
XIAOHONGSHU_MCP_COOKIES=/Users/yourname/path/to/xiaohongshu-mcp/cookies.json
```

### 验证

```
hermes mcp test xiaohongshu
```

确认工具列表中包含 `mcp_xiaohongshu_get_feed_detail`。发送一条小红书分享链接测试完整流程。

### 已知问题

xiaohongshu-mcp 有协议版本不兼容和长时间运行后「笔记不可访问」等已知问题及修复方法，详见 [`xhs-mcp-known-issues.md`](xhs-mcp-known-issues.md)。

---

## 可选：安装 Whisper + ffmpeg

视频和音频字幕转录依赖 [OpenAI Whisper](https://github.com/openai/whisper) CLI 和 [ffmpeg](https://ffmpeg.org/)。

### 安装

```bash
pip install openai-whisper
brew install ffmpeg  # macOS
```

或使用 Hermes 的 `openai-whisper` skill 辅助安装。

Whisper 首次转录时将会自动下载模型（默认使用 `large-v3-turbo`，约 3GB）。

### 验证

```bash
whisper --help
ffmpeg -version
```

---

## 依赖总览

| 依赖 | 用途 | 必需？ |
|------|------|--------|
| Hermes Agent | Agent 运行环境 | ✅ |
| LLM provider | VLM 图片分析、笔记生成、分类 | ✅ |
| Search provider | 溯源搜索（`web_search`） | ✅ |
| xiaohongshu-mcp | 小红书帖子数据提取 | 小红书提取需要 |
| Whisper CLI + ffmpeg | 视频/音频字幕转录 | 视频转录需要 |
