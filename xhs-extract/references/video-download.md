# 视频下载与转录

仅当 `note.type == "video"` 时读取并执行本文件。图文帖不要读取本文件。

## 下载视频

MCP `get_feed_detail` **不返回** `videoUrl`。视频 URL 需要从页面 HTML 的 `__INITIAL_STATE__` 提取。

1. 用 curl + Cookie 访问帖子页面 HTML：

```bash
curl -sL --max-time 15 \
  -H "Cookie: <从 $XIAOHONGSHU_MCP_COOKIES 文件拼出的 cookie 串>" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -H "Referer: https://www.xiaohongshu.com/" \
  "https://www.xiaohongshu.com/explore/<note_id>?xsec_token=<token>"
```

不能用 Hermes 内置的 `browser_navigate`：浏览器走云端代理 IP，小红书可能返回 `error_code=300012`。必须从本地 curl 走本地网络。

2. 从 `__INITIAL_STATE__` 提取视频 URL。

页面 HTML 约 500KB+，视频 URL 嵌在 `<script>window.__INITIAL_STATE__={...}</script>` 里。Python 提取代码：

```python
import json, re

# html = curl 输出
idx = html.find('window.__INITIAL_STATE__=')
json_start = idx + len('window.__INITIAL_STATE__=')
script_end = html.find('</script>', json_start)
json_str = html[json_start:script_end]

# JSON 中可能混入 JavaScript undefined，必须清洗
json_str = re.sub(r':\s*undefined\b', ': null', json_str)

state = json.loads(json_str)

note_detail = state["note"]["noteDetailMap"][note_id]
video = note_detail["note"]["video"]
h264_streams = video["media"]["stream"]["h264"]

# 优先取 masterUrl，fallback 到 backupUrls[0]
stream = h264_streams[0]  # HD 质量
video_url = stream.get("masterUrl") or stream["backupUrls"][0]
```

3. 用 curl + Cookie 下载视频：

```bash
curl -sL --max-time 120 -o "video.mp4" \
  -H "Cookie: <cookie_str>" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Referer: https://www.xiaohongshu.com/" \
  "<video_url>"
```

`masterUrl` 带签名参数 `?sign=xxx&t=xxx`，有时效性，拿到后尽快下载。`backupUrls` 不带签名，但可能也需要 Cookie 鉴权。图片 CDN URL 同样有时效性，获取帖子数据后尽快下载所有媒体。

Cookie 串格式：从环境变量 `XIAOHONGSHU_MCP_COOKIES` 指定的 `cookies.json` 读取，拼成 `name1=value1; name2=value2; ...`。

此 HTML 抓取也可复用获取评论区更多数据：`__INITIAL_STATE__` 包含完整评论列表，不一定需要 MCP 的 `load_all_comments`。

## 视频转录

对下载的 `video.mp4` 调用 Whisper 转录字幕。必须在输出目录内执行，确保 `video.txt` 写入正确位置：

```bash
cd "{output_dir}" && whisper "video.mp4" --model large-v3-turbo --output_format txt --output_dir .
```

超时处理：Whisper 命令设置 `timeout=1800`（30 分钟）。超时或非零退出码时跳过转录，在 `output.json` 中设置 `video.transcript: null`，在 `content.md` 视频字幕段写入 `> ⚠️ 视频转录失败（超时或模型未就绪）`。不阻塞后续步骤。
