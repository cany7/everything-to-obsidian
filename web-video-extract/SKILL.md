---
name: web-video-extract
description: Web 视频音频提取器：用 yt-dlp 从 YouTube 和 Bilibili 链接提取元数据、下载音频、转录文字，并输出标准内容包。由 url-to-vault 根据 URL pattern 自动路由调用，不应被用户直接触发。
version: 1.0.0
author: tim77
license: MIT
metadata:
  hermes:
    tags: [video, youtube, bilibili, audio-download, transcription, content-extraction]
    related_skills: [content-to-vault]
---

# web-video-extract - Web 视频音频提取

## 任务目标

接收一个 YouTube 或 Bilibili 视频链接，完成以下工作后输出标准内容包：

1. 解析链接和短链，识别来源类型
2. 用 `yt-dlp` 提取视频元数据并下载最佳可用音频
3. 用 Whisper 将音频转录为文本
4. 按内容判断是否需要溯源，并记录原始来源 URL
5. 生成 `metadata.json`、`output.json`、`content.md`
6. 自动串联 `content-to-vault` 继续归档

本 skill 只做提取和记录，不做分析、不做归档、不做总结。下游整理由 `content-to-vault` 负责。

## 依赖

| 工具 | 用途 |
|------|------|
| `yt-dlp` | 视频元数据提取、音频下载、浏览器 cookies 读取 |
| `ffmpeg` | `yt-dlp` 音频抽取/封装、Whisper 解码 |
| `whisper` | 音频转录 |
| `web_search` | 溯源时搜索原始来源 URL |

## 认证前置条件

默认假设用户已在 Chrome 中登录 YouTube / Bilibili。主路径使用 `yt-dlp --cookies-from-browser chrome`。

如用户使用其他浏览器，手动把命令中的 `chrome` 改为以下值之一：`brave`、`chrome`、`chromium`、`edge`、`firefox`、`opera`、`safari`、`vivaldi`、`whale`。

不要把 cookies 写入内容包、repo、日志或 `output.json`。不要要求用户预先配置 cookies 文件。

## 输入

| URL pattern | source_type |
|-------------|-------------|
| `youtube.com/watch`、`youtube.com/shorts`、`youtu.be` | `youtube` |
| `bilibili.com/video/`、`b23.tv` | `bilibili` |

短链（`youtu.be`、`b23.tv`）先用本 skill 的 `scripts/expand-shortlink.py` 展开。展开失败但原始 URL 已可明确匹配时，允许继续把原始 URL 交给 `yt-dlp`。

## 输出

在 `$EXTRACT_OUTPUT_DIR/video/{source_type}/{title_safe}-{YYYYMMDDHHMM}/` 下生成：

```text
{output_dir}/
├── output.json
├── metadata.json
├── content.md
├── audio.m4a
├── audio.txt
└── audio.info.json
```

如果 Whisper 失败，`audio.txt` 可能不存在；仍需生成 `output.json` 和 `content.md`。

`output.json` 至少包含下游读取字段：

```jsonc
{
  "source_type": "youtube",
  "source_url": "https://...",
  "sources": [],
  "images": []
}
```

允许额外写入本 extractor 自用字段，例如 `audio`、`video`、`transcription`、`tracing`、`output_dir`。下游只读取 `source_type`、`source_url`、`sources[]`、`images[]` 和 `content.md`。

## 执行纪律

默认按快速主路径执行：解析链接 → 检查输出目录 → 提取元数据 → 创建 `output_dir` → 下载音频 → Whisper 转录 → 判断溯源 → 打包输出 → 自动进入 `content-to-vault`。

- 不要做无条件前置检查；只有步骤失败或内容触发时才读取 reference。
- `references/tracing-search.md`：只有已判断需要溯源、准备执行 `web_search` 时读取。
- `references/troubleshooting.md`：只有 `yt-dlp`、cookies、ffmpeg、Whisper、输出目录或下载失败时读取。
- 音频转录失败不阻塞归档。

## 完整流程

### 第一步：解析链接

如果输入为短链，运行：

```bash
python3 <web-video-extract skill_dir>/scripts/expand-shortlink.py "<url>"
```

用最终 URL 判断 `source_type`。无法展开时，用原始 URL 判断。

### 第二步：检查基础输出目录

读取 `EXTRACT_OUTPUT_DIR`。为空时停止并提示用户配置。

最终目录规则：

```text
$EXTRACT_OUTPUT_DIR/video/{source_type}/{title_safe}-{YYYYMMDDHHMM}/
```

此时只检查基础目录配置，不创建最终目录。`title_safe` 和时间戳来自下一步的 `yt-dlp` 元数据；若元数据没有上传时间，使用当前本地时间。

### 第三步：提取元数据并创建 output_dir

先用 Chrome cookies 获取 JSON 元数据：

```bash
yt-dlp --ignore-config --no-playlist --cookies-from-browser chrome -J "<url>"
```

如果失败原因像 cookies 读取失败、登录态失效、风控、年龄限制、会员限制或 bot check，先不要停止，进入无 cookies 重试：

```bash
yt-dlp --ignore-config --no-playlist -J "<url>"
```

如果无 cookies 也失败，读取 `references/troubleshooting.md` 分类处理。

元数据成功后，按第二步规则创建最终 `output_dir`。`source_url` 优先使用 `yt-dlp` 元数据里的 `webpage_url`；没有时使用展开后的 URL；再没有时使用原始输入 URL。

### 第四步：下载音频

主路径使用 Chrome cookies 直接下载最佳音频。只下载音频，不 fallback 下载完整视频：

```bash
yt-dlp \
  --ignore-config \
  --no-playlist \
  --cookies-from-browser chrome \
  --sleep-interval 2 \
  --max-sleep-interval 8 \
  --retries 3 \
  --fragment-retries 3 \
  -f "ba/bestaudio" \
  -x --audio-format m4a \
  --write-info-json \
  -o "{output_dir}/audio.%(ext)s" \
  "<url>"
```

如果 cookies 路径失败，用无 cookies 重试一次：

```bash
yt-dlp \
  --ignore-config \
  --no-playlist \
  --sleep-interval 2 \
  --max-sleep-interval 8 \
  --retries 3 \
  --fragment-retries 3 \
  -f "ba/bestaudio" \
  -x --audio-format m4a \
  --write-info-json \
  -o "{output_dir}/audio.%(ext)s" \
  "<url>"
```

若站点没有可用音频格式，或 cookies 与无 cookies 路径都失败，按下载失败处理并读取 `references/troubleshooting.md`。

下载成功后确认输出目录中存在 `audio.m4a` 或其他 `audio.*` 音频文件。若实际扩展名不是 `.m4a`，后续 Whisper 使用实际文件路径。

### 第五步：音频转录

在输出目录中执行：

```bash
cd "{output_dir}" && whisper "<audio_file>" --model large-v3-turbo --output_format txt --output_dir .
```

超时设置 1800 秒。超时或非零退出码时，不阻塞后续步骤：

- `output.json` 写入 `"audio": {"path": "...", "transcript": null}`
- `content.md` 的「音频转录」段写入 `> ⚠️ 音频转录失败（超时或模型未就绪）`
- 仍继续生成内容包并交给下游归档

### 第六步：判断是否需要溯源

通读视频简介和转录文本，识别是否存在可验证的外部事实引用。

以下情况需要溯源：

- 提到具体论文、报告、新闻、公告或事件
- 提到 GitHub 项目、开源工具、软件发布
- 提到可定位的文章、教程、博客、产品参数或价格
- 包含显式 URL
- 引用了外部人物、机构或产品发布的具体说法

以下情况不需要溯源：

- 纯观点、闲聊、个人经验或娱乐内容
- 教程内容但未引用外部来源
- 创作者自己的展示、讲解、评测，但没有可验证的外部事实引用

没有识别到外部事实引用时，跳过溯源，不读取 reference，在 `output.json.tracing` 写入跳过原因，并在 `content.md` 的「溯源」段写入跳过说明。

需要溯源时，读取 `references/tracing-search.md`，用 `web_search` 找到原始 URL。只记录 URL 和简短说明，不调用 `web_extract`。

### 第七步：生成内容包文件

生成 `metadata.json`、`output.json` 和 `content.md`。`content.md` 是下游主材料；不要加入分析、总结或归档分类结论。

`metadata.json` 写入：

```jsonc
{
  "source_type": "youtube",
  "source_url": "https://...",
  "extracted_at": "2026-05-24T12:00:00+08:00",
  "raw": { "yt_dlp_info": "完整 JSON 元数据" }
}
```

`output.json` 写入标准下游字段和本 extractor 自用字段：

```jsonc
{
  "source_type": "youtube",
  "source_url": "https://...",
  "sources": [],
  "images": [],
  "audio": {"path": "/abs/path/audio.m4a", "transcript": "..."},
  "video": {
    "title": "...",
    "uploader": "...",
    "upload_date": "20260524",
    "duration": 123,
    "webpage_url": "https://..."
  },
  "transcription": {"performed": true, "reason": "completed"},
  "tracing": {"performed": false, "reason": "skipped: no external factual references"},
  "output_dir": "/abs/path/..."
}
```

`source_url` 优先使用 `yt-dlp` 元数据里的 `webpage_url`；没有时使用展开后的 URL；再没有时使用原始输入 URL。

`content.md` 必须包含：

```markdown
# {title}

**来源**: {source_type}
**作者/频道**: {uploader}
**发布时间**: {upload_date}
**时长**: {duration}
**原链接**: {source_url}

## 简介

{description}

## 音频转录

{transcript 或失败说明}

## 溯源

{来源列表或跳过说明}
```

### 第八步：自动进入 content-to-vault

完成内容包后，必须自动加载 `content-to-vault` 并传入 `output_dir`。不要等待用户确认。

## 注意事项

- 不抓取评论，第一版只保留元数据、简介和音频转录。
- 不分析缩略图或视频画面。
- 不保存 cookies。
- 批量处理时由上游 batch 入口控制间隔；本 skill 内部只设置 `yt-dlp` 的请求间隔和重试。
