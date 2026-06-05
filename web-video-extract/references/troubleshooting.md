# 排障参考

仅在 `yt-dlp`、cookies、ffmpeg、Whisper、输出目录或下载失败时读取本文件。正常提取不要读取。

## 错误分类

`yt-dlp` cookies 路径和无 cookies 路径各最多尝试一次。仍失败时按以下分类停止：

| 类型 | 常见信号 | 处理 |
|------|----------|------|
| `needs_auth` | login required、private、members-only、age restricted、not available to anonymous users | 提示用户重新在 Chrome 登录对应站点后重试 |
| `rate_limited` | 403、412、429、bot check、Sign in to confirm、Precondition Failed | 提示冷却后重试；如已退出登录，先重新登录 Chrome |
| `unavailable` | 404、video removed、deleted、unavailable、版权/地区不可用 | 停止并报告视频不可访问 |
| `dependency_missing` | `yt-dlp: command not found`、`ffmpeg` 缺失、`whisper` 缺失 | 提示安装缺失依赖 |
| `unknown` | 无法归类的非零退出 | 停止并报告错误摘要 |

不要无限重试，不要绕过登录或风控。

## 输出目录缺失

如果 `EXTRACT_OUTPUT_DIR` 为空，停止并提示用户在 `~/.hermes/.env` 中配置：

```bash
EXTRACT_OUTPUT_DIR=/Users/yourname/Documents/extract_files
```

本 extractor 会在其下创建：

```text
$EXTRACT_OUTPUT_DIR/video/{source_type}/{title_safe}-{YYYYMMDDHHMM}/
```

## cookies 读取失败 / 登录态失效

默认使用：

```bash
--cookies-from-browser chrome
```

如果读取失败或登录态失效：

1. 无 cookies 重试一次。
2. 仍失败时停止，提示用户在 Chrome 中重新登录 YouTube / Bilibili 后重试。

如果用户使用其他浏览器，把 `chrome` 改为 `brave`、`chromium`、`edge`、`firefox`、`opera`、`safari`、`vivaldi` 或 `whale`。

不要把 cookies 导出到 repo 或内容包。

## 风控 / bot check

遇到 403、412、429、bot check、`Sign in to confirm`、`Precondition Failed`：

1. 确认 cookies 路径已经尝试过。
2. 无 cookies 重试一次。
3. 仍失败时标记 `rate_limited`，提示冷却后重试或重新登录浏览器。

不要连续快速重试同一 URL。

## 依赖缺失

缺 `yt-dlp`：

```bash
pip install -U yt-dlp
```

缺 `ffmpeg`：

```bash
brew install ffmpeg
```

缺 `whisper`：

```bash
pip install openai-whisper
```

## Whisper 转录失败

Whisper 超时或非零退出时不要阻塞内容包生成：

- `output.json.audio.transcript = null`
- `output.json.transcription = {"performed": false, "reason": "<错误摘要>"}`
- `content.md` 音频转录段写入 `> ⚠️ 音频转录失败（超时或模型未就绪）`

继续进入 `content-to-vault`。
