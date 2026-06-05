# Content Package Schema

本文档定义 extractor（上游）产出的内容包格式，以及 content-to-vault（下游归档器）的读取契约。所有 extractor skill 产出的内容包应满足本契约中下游可读的部分。

## 必需文件

```
{output_dir}/
├── output.json
└── content.md
```

## output.json

`output.json` 是上游 extractor 产出的结构化数据文件。不同 extractor 可能产出不同字段——这是允许的。下游 content-to-vault **只读取以下字段**：

| 字段 | 必需 | 说明 |
|------|------|------|
| `source_type` | 是 | 上游来源或 extractor 类型。示例：`xhs`、`youtube`、`web`、`pdf`。 |
| `source_url` | 是 | 原始内容链接。下游原样保存于 registry，不 normalize，不用于判重。 |
| `sources[]` | 否 | 上游已通过 `web_search` 确认的溯源 URL 列表。存在时下游直接 `web_extract`；不存在时下游从 `content.md` 的溯源段提取。 |
| `images[]` | 否 | 上游下载的图片路径列表。每项含 `path`（绝对路径）和 `description`（VLM 描述）。存在时下游在笔记末尾插入 `file://` 图片链接。 |

`output.json` 中其他字段（如 `post.*`、`video`、`tracing`、`output_dir`、`schema_version` 等）是上游 extractor 的内部格式。下游 content-to-vault 不读取、不依赖这些字段——它们的存废由上游自行决定。

### xhs-extract 的 output.json 示例

```jsonc
{
  "source_type": "xhs",
  "source_url": "https://www.xiaohongshu.com/explore/...",
  "post": {
    "title": "...",
    "desc": "...",
    "author": {"userId": "...", "nickname": "...", "avatar": "..."},
    "type": "图文|视频",
    "tags": ["标签1"],
    "stats": {"likedCount": "32", "..." },
    "time": 1779284005000,
    "ipLocation": "广东"
  },
  "images": [{"path": "...", "description": "..."}],
  "video": {"path": "...", "transcript": "..."},
  "sources": [{"url": "...", "type": "github", "name": "...", "description": "..."}],
  "tracing": {"performed": true, "reason": "completed"},
  "output_dir": "/abs/path/..."
}
```

以上是 xhs-extract 的完整 output.json。content-to-vault 只取其中的 `source_type`、`source_url` 和 `sources[]`，其余全部忽略。其他 extractor 的 output.json 可能只有三个字段——两种形式都合法。

## content.md

`content.md` 是下游生成 Obsidian 笔记的**主材料**。extractor 必须把可供归档使用的内容整理为可读 Markdown。

### 最低要求

- 原始内容标题（作为 H1 或文档开头）
- 原始正文或主要内容
- 图片 OCR / VLM 描述
- 视频或音频转写文本
- 评论/讨论中有信息增量的内容
- 上游已提取到的、对理解内容有用的平台上下文（作者、时间、互动数据等）

### 溯源信息

extractor 应将溯源结果写入 `content.md` 的「溯源」或「引用来源」小节。当 `output.json` 中没有 `sources[]` 时，下游从此处提取 URL。

extractor 的溯源职责：通过 `web_search` 找到帖子引用的外部信息的**原始 URL**，从搜索结果 snippet 确认匹配，将 URL 写入 content.md。**不做 web_extract**——内容提取留给下游。

### 不要求

- 不要求固定小节名或模板结构。下游不依赖 content.md 的标题层级。
- 不要求 extractor 对内容做分析、总结或归档判断——这些是 content-to-vault 的工作。

## 下游读取方式

| 输入 | 用途 |
|------|------|
| `output_dir` | registry `input_dir`、路径判重、笔记「原始内容包」路径 |
| `output.json.source_url` | registry `source_url`、笔记「原始链接」 |
| `output.json.source_type` | registry `source_type`、来源类型记录 |
| `output.json.sources[]` | （优先）溯源 URL，下游 `web_extract` 补充内容 |
| `content.md` | 笔记正文主材料 |
| `content.md` 溯源段 | （回退）当 `sources[]` 不存在时提取 URL |

## 判重

判重使用**路径匹配**，不使用 URL 或内容 hash：

1. `os.path.realpath(output_dir)` 匹配 registry 的 `input_dir`——命中则跳过
2. 目标 note_path 已存在——返回已有路径，不覆盖旧笔记

不同内容包引用同一个外部 URL 不视为重复。同一内容包路径重复提交才判重。

## 可选文件

以下文件不影响下游行为，可作为 extractor 内部调试产物保留：

- `metadata.json`：extractor 的平台原始元数据（API 返回的全量 JSON 等）
- `images/`：下载的图片文件
- `video.mp4`、`video.txt`：视频文件及转录文本
- 其他 extractor 专用文件

这些文件不进入 content-to-vault 的读取范围，不阻塞归档。
