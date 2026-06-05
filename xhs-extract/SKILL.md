---
name: xhs-extract
description: 小红书内容提取器：从分享链接提取笔记内容、下载图片/视频、溯源原始来源，输出结构化内容包。由 url-to-vault 根据 URL pattern 自动路由调用，不应被用户直接触发。
version: 1.0.0
author: tim77
license: MIT
metadata:
  hermes:
    tags: [xiaohongshu, content-extraction, social-media, image-download, tracing]
    related_skills: [content-to-vault]
---

# xhs-extract — 小红书内容提取 + 溯源

## 任务目标

接收一个小红书分享链接，完成以下全部工作后输出一个**结构化内容包**（JSON + Markdown + 媒体文件）：

1. 从链接解析帖子元数据（标题、正文、作者、互动数据等）
2. 下载帖子中的图片和视频到本地
3. 用 VLM 提取每张图片中的文字和内容描述
4. 对视频笔记，转录视频字幕
5. 识别帖子中引用的外部信息来源，通过 web_search 找到原始 URL 并记录到 output.json 和 content.md
6. 将所有结果打包为结构化输出，供下游分析流程消费

**本 skill 只做提取和记录，不做分析、不做归档、不做总结。** 输出的内容包是原始素材，分析和整理由下游 `content-to-vault` 负责。本 skill 完成后应**自动串联** `content-to-vault` 继续归档，不要等用户指令。

## 依赖

执行本 skill 需要以下工具可用。不要为了确认正常路径而逐项检查；只有对应步骤失败或内容类型触发时才检查。

| 工具 | 用途 |
|------|------|
| `mcp_xiaohongshu_get_feed_detail` | 获取帖子结构化数据（含评论） |
| `vision_analyze` | 图片 VLM 分析（Hermes 内置） |
| `curl` + Cookie | 下载 CDN 图片/视频 |
| `web_search` | 溯源时搜索原始来源 URL |
| `whisper` + `ffmpeg` | 视频字幕转录（仅视频帖需要） |

## 执行纪律：快速主路径

默认按快速主路径连续执行，不停止、不汇报、不等确认：解析链接 → 获取帖子数据 → 创建输出目录 → 下载媒体 → VLM/ASR → 按规则判断溯源 → 打包输出 → 自动进入 `content-to-vault`。

子进程不需要 `--yolo`（网络请求通过 `execute_code` 白名单处理，见 README 和 `docs/batch-processing.md`）。

- 不要在每个步骤后向用户汇报、总结或等待确认。
- 不要做无条件前置检查；仅在对应步骤失败或内容类型需要时检查。
- 不要读取 `references/`，除非当前内容触发视频/溯源分支，或当前步骤失败且主文档无法解决。
- 图文帖不执行任何视频、Whisper 或视频 HTML 抓取检查；只有 `note.type == "video"` 才进入视频分支。
- 溯源规则保持不变，但只在完成 `desc`、VLM 描述和视频转录文本收集后判断一次。
- 生成文件内容后，在同一个 assistant turn 内批量写入所有输出文件。
- 完成提取后自动进入 `content-to-vault`，不向用户确认。

### 工具调用合并规则

以下规则强制减少回合数，是快速主路径的核心。**违反任一条将导致提取时间翻倍。**

**1. 输出文件必须一次批写入**

`metadata.json`、`output.json`、`content.md` 三个文件，必须在**同一个 tool_calls 数组中一次发出**，不得拆成多轮。

```
✅ 正确（一轮完成）：
   tool_calls: [write_file(metadata.json), write_file(output.json), write_file(content.md)]

❌ 错误（拆成多轮，每个文件单独一轮）：
   Turn A: write_file(metadata.json)
   Turn B: write_file(content.md)  
   Turn C: write_file(output.json)
```

**2. 非视频操作一律用 `execute_code`**（强制规则——不留给模型选择）

除视频转录外，以下操作**必须**在 `execute_code` 中完成，**禁止**使用 `terminal`：

- 创建输出目录
- 读取 Cookie
- 下载图片（用 Python `requests` 库，不是 `curl`）
- 时间戳计算
- 目录名清理

`execute_code` 不经过审批系统。视频转录仍用 `terminal`。

> ⚠️ **JSON 组装除外**：`metadata.json`、`output.json`、`content.md` 的内容由 Agent 在脑中组装后，直接通过 `write_file` 写入。**禁止用 `execute_code` 组装 JSON**——嵌入巨型 MCP 原始数据时转义极容易出错（实测频繁 Traceback）。

图片下载的 execute_code 模式（`XIAOHONGSHU_MCP_COOKIES` 和 `EXTRACT_OUTPUT_DIR` 通过 `os.environ.get()` 直接读取——Hermes `.env` 注入的变量在 `execute_code` 沙盒中可用）：

```python
import requests, json, os

cookie_path = os.environ["XIAOHONGSHU_MCP_COOKIES"]
extract_output_dir = os.environ["EXTRACT_OUTPUT_DIR"]

with open(cookie_path) as f:
    cookies = json.load(f)
cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('name') and c.get('value'))

# 创建目录
os.makedirs(os.path.join(extract_output_dir, "xhs", f"{title_safe}-{ts_str}", "images"), exist_ok=True)

# 下载图片
headers = {"Referer": "https://www.xiaohongshu.com/",
           "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
           "Cookie": cookie_str}
for i, img in enumerate(image_list):
    r = requests.get(img["urlDefault"], headers=headers, timeout=30)
    r.raise_for_status()
    with open(f"images/{i+1:02d}.webp", "wb") as f:
        f.write(r.content)
```

### 错误处理

提取过程中遇到错误时，读取 `references/troubleshooting.md` 按排障流程处理。正常提取不要读取该文件。

## 前置检查

默认不做无条件前置检查，先沿快速主路径执行。只有出现对应触发条件时才检查：

1. **MCP/Cookie 检查**：直接调用 `mcp_xiaohongshu_get_feed_detail`。只有返回未登录、鉴权失败、Cookie 失效或工具不可用时，才调用 `mcp_xiaohongshu_check_login_status({})` 或检查工具注册状态。
2. **输出目录检查**：首次创建输出目录前，用 `os.environ.get("EXTRACT_OUTPUT_DIR")` 检查基础提取目录。为空则停止并提示用户配置。
3. **Whisper 检查**：只有确认帖子类型为视频（`type: "video"`）并需要转录时，才检查 `ls ~/.cache/whisper/large-v3-turbo.pt`。
4. **参考文档检查**：仅当内容触发视频/溯源分支，或主流程失败且本文件无法解决时，才读取 `references/`。

## 输入

一个或多个小红书分享链接。支持三种格式：

- 短链：`xhslink.com/m/xxx` 或 `xhslink.com/a/xxx`
- 完整分享链接：`xiaohongshu.com/discovery/item/{note_id}?xsec_token=xxx`
- 赞过/收藏页链接：`user/profile/{user_id}/{note_id}?xsec_token=xxx&xsec_source=pc_like`

> ⚠️ **user/profile 格式**来自 PC 端赞过/收藏页面。此格式下 agent 可能误判为"用户主页"——不要转换页面类型、不要调用 `mcp_xiaohongshu_user_profile`，只需要从 URL 路径中提取 user_id 之后的十六进制串作为 `note_id`，并从查询参数提取 `xsec_token`。

## 输出

在 `$EXTRACT_OUTPUT_DIR/xhs/{标题}-{YYYYMMDDHHMM}/` 目录下生成（`EXTRACT_OUTPUT_DIR` 见「环境变量」说明）：

```
{output_dir}/
├── output.json       # 最终打包的结构化 JSON
├── metadata.json     # 归一化元数据（见下方 schema）
├── content.md        # 可读 Markdown
├── images/           # 图片文件
│   ├── 01.webp
│   ├── 02.webp
│   └── ...
└── video.mp4         # 仅视频笔记
```

`output.json` 的结构：

```jsonc
{
  "source_type": "xhs",
  "source_url": "原始输入链接或短链重定向后的最终 URL",
  "post": {
    "title": "...",
    "desc": "...",
    "author": {"userId": "...", "nickname": "...", "avatar": "..."},
    "type": "图文|视频",
    "tags": ["标签1", "标签2"],
    "stats": {"likedCount": "32", "commentCount": "14", "collectedCount": "14"},
    "time": 1779284005000,
    "ipLocation": "广东"
  },
  "images": [
    {"path": "/abs/path/to/01.webp", "description": "VLM 的描述"},
    ...
  ],
  "video": {"path": "/abs/path/to/video.mp4", "transcript": "Whisper 字幕"},
  "sources": [
    {
      "url": "https://...",
      "type": "github|article|x_post|news|blog|paper|docs|other",
      "name": "简短标识（repo 名、文章标题等）",
      "description": "一句话说明这是什么来源、帖子里怎么提的（纯事实，不做分析）"
    }
  ],
  "tracing": {
    "performed": true,
    "reason": "completed"
  },
  "output_dir": "/absolute/path/to/output_dir"
}
```

`metadata.json` 的结构（归一化 schema，字段固定）：

```jsonc
{
  "note_id": "6a0c1c3d000000000803ddeb",       // 归一化 note_id（固定字段名）
  "source_url": "https://www.xiaohongshu.com/...",  // 原始输入链接或短链重定向后的最终 URL（不强制转换格式）
  "extracted_at": "2026-05-24T12:00:00+08:00",  // ISO 时间戳
  "raw": { ... }                                  // 完整原始 MCP 数据（如有）
}
```

> ⚠️ **note_id 归一化**：MCP 原始返回中 note_id 字段名不固定（可能是 `feed_id`、`note_id`、`data.note.noteId`、顶层 `noteId` 或 `mcp_raw.noteId`）。写入 metadata.json 前按此顺序提取，统一存到顶层 `note_id`。`xsec_token` 同样需要提取（`xsec_token` > `xsecToken` > `data.note.xsecToken` > `mcp_raw.xsecToken`）。`source_url` 直接使用原始输入链接；如果输入是短链，则使用重定向后的最终 URL。不要为了记录而强制转换成 explore 格式。

---

## 提取模式

默认执行完整提取（图片下载 + VLM 分析 + 溯源判断）。用户可通过以下指令触发精简模式：

- **跳过图片下载 + VLM**：用户说"跳过下载图片和 VLM"等类似表述时，不下载图片、不调用 `vision_analyze`。`output.json` 的 `images[]` 中每张图的 `path` 设为 `null`、`description` 设为 `"[跳过] 按用户指示跳过图片下载和 VLM 提取"`。`content.md` 的「图片分析」段写入同一行说明。
- 精简模式下，溯源判断仍按正常规则执行（通常纯个人经验帖会跳过）。
- 仍需创建 `images/` 子目录（保持目录结构一致）。
- 仍需完成下游 `content-to-vault` 归档。

---

## 完整流程

### 第一步：解析链接

**输入为短链**（`xhslink.com/...`）时，用 `terminal` 调用本 skill 目录下的 `scripts/expand-shortlink.py` 获取重定向后的完整 URL：

```bash
python3 <xhs-extract skill_dir>/scripts/expand-shortlink.py "https://xhslink.com/m/xxx"
# 输出：https://www.xiaohongshu.com/discovery/item/6a1fd292...?xsec_token=...
```

**输入为完整链接**时直接解析。

从最终 URL 中提取两个关键参数。MCP `get_feed_detail` 只需要这两个参数，不需要页面 URL 格式转换：

- `note_id`：正则 `/explore/([a-f0-9]+)` 或 `/discovery/item/([a-f0-9]+)` 或 `/user/profile/[a-f0-9]+/([a-f0-9]+)`
- `xsec_token`：查询参数 `xsec_token=` 的值

两个参数缺一不可——`get_feed_detail` 同时需要两者。直接粘贴浏览器地址栏的 URL 通常不含 `xsec_token`，必须从分享链接获取。`user/profile` 链接仍按上面的正则取 `note_id` 和 `xsec_token`，不要调用用户主页工具。

### 第二步：获取帖子数据

调用 MCP 工具：

```
mcp_xiaohongshu_get_feed_detail(
    feed_id="<note_id>",
    xsec_token="<xsec_token>"
)
```

返回结构的关键路径：

- `data.note` — 帖子核心数据
  - `title`、`desc` — 标题和正文
  - `type` — `"normal"`（图文）或 `"video"`（视频）
  - `time` — 毫秒时间戳
  - `ipLocation` — IP 属地
  - `user` — `{userId, nickname, avatar}`
  - `interactInfo` — `{likedCount, commentCount, collectedCount}`（均为**字符串**，需 `int()` 转换）
  - `imageList` — 图片数组，每项含 `urlDefault`（原图 CDN URL）
  - `tagList` — 标签数组
  - `data.comments` — 评论数据，小红书默认按热度排序（点赞+回复多的在前），非时间序

> ⚠️ **视频笔记没有 `videoUrl`**：MCP `get_feed_detail` 不返回 `videoUrl`。视频 URL 需要单独从页面 HTML 提取，见第四步。

### 第三步：创建输出目录

**必须使用 `execute_code`**（禁止 `terminal`）。

**路径规则：**

```
$EXTRACT_OUTPUT_DIR/xhs/{title_safe}-{YYYYMMDDHHMM}/
```

- `EXTRACT_OUTPUT_DIR` = 用户配置的基础提取目录（通过 `os.environ.get("EXTRACT_OUTPUT_DIR")` 在 `execute_code` 中直接读取）
- `title_safe` = `re.sub(r'[^\w\u4e00-\u9fff -]', '', title).strip()[:40]`
- `YYYYMMDDHHMM` = 从 `note.time`（毫秒时间戳）转换为北京时间

用 `execute_code` 计算目录名并创建 `images/` 子目录。代码模式见「非视频操作一律用 `execute_code`」。

### 第四步：下载媒体

Cookie 从环境变量 `XIAOHONGSHU_MCP_COOKIES` 指定的 `cookies.json` 路径读取。CDN 需要 Cookie 鉴权——裸 URL 返回 403。

**图文笔记**（`type: "normal"`）：**必须使用 `execute_code`**（禁止 `terminal` + `curl`）。

用 Python `requests` 库下载。代码模式见「非视频操作一律用 `execute_code`」。

**视频笔记**（`type: "video"`）：

仅当帖子类型为视频时执行。MCP `get_feed_detail` **不返回** `videoUrl`，需要按 `references/video-download.md` 从页面 HTML 提取视频 URL、下载 `video.mp4`，并在第六步转录。图文帖不要读取该 reference。

### 第五步：VLM 图片分析

对每张下载的图片调用 `vision_analyze`。每张图一个 `vision_analyze` 调用，但默认在**同一个 assistant turn 的 tool_calls 数组中一次性发出全部图片请求**；不要预先按 5 张一批拆分。若工具层返回并发、超时或单图失败，只重试失败图片一次。

默认 prompt：

```
详细描述这张图片的内容，并提取图中所有可见文字。
如果是截图、长图、信息图、表格、图表、流程图、代码、聊天记录或照片，请按实际内容保留结构和关键信息。

补充要求：
- 逐行提取可见文字，保留原文、换行、编号、项目符号、价格、参数、链接、代码和标点等内容，不改写、不总结、不翻译。
- 看不清的内容标记为 [无法识别]，不要根据上下文补全。
- 表格用 Markdown 表格还原行列结构，不合并为散文。
- 图表（柱状/折线/饼图）提取数据点、坐标轴标签、具体数值和比例。
- 流程图/架构图按节点和箭头关系描述，用 "A → B → C" 格式。
- 代码截图标注编程语言，保留代码格式和缩进。
- 聊天记录区分发言人和消息内容，保持对话顺序。
- 步骤教程/长图按步骤顺序输出，标注序号。
- 纯照片/插画描述画面关键元素和视觉特征。
- 无可见文字的图片明确写"文字：无"，只保留图片描述。

返回格式：[内容类型]: 描述 + 文字（如有）
```

允许根据帖子标题、正文、图片序号或任务语境在 prompt 末尾追加一句提取重点，例如「结合帖子主题，优先保留可复用的信息、步骤、参数、结论和原文表述」。但不得替换或删除默认 prompt 中的两条不变量：**提取所有可见文字**、**保留返回格式**。

结果存入 `images[].description`。

### 第六步：视频转录

仅当帖子类型为视频（`type: "video"`）时执行。

按 `references/video-download.md` 的"视频转录"执行。转录失败不阻塞后续步骤：在 `output.json` 中设置 `video.transcript: null`，在 `content.md` 视频字幕段写入失败说明。

### 第七步：生成 content.md

生成可读的 Markdown 文件，包含帖子正文和所有提取结果：

```markdown
# {title}

**作者**: {nickname} | **时间**: {YYYY-MM-DD HH:MM} | **地点**: {ipLocation}
**互动**: {likedCount} 赞 · {commentCount} 评 · {collectedCount} 收藏

{desc}

## 标签
{tag1} {tag2} ...

## 图片分析
{每张图的 VLM 描述，格式：[类型]: 描述}

## 视频字幕
{视频帖：完整的 Whisper 转录文本。图文帖：此段不出现}

## 评论
{每条评论：[nickname]：content（时间）}

## 溯源
{每个来源：- [来源名称](https://example.com/source) — 一句话说明（帖子里怎么提的）}

{tracing_status_line}
```

### 第八步：溯源

找到帖子中引用的外部信息来源的原始 URL。VLM（第五步）只负责每张图的看图说话，不参与溯源。本步骤完全由 Agent 执行。

> ⚠️ **本步骤不是每条帖子都必须执行的。** 见 8.0 的判断标准。

#### 8.0 判断是否需要溯源

溯源的目标是**可验证的外部事实引用**。以下情况**需要**溯源：

- 帖子引用了具体产品/工具（提及型号、参数、价格等，如「799 元、212g」）
- 帖子引用了研究/论文/报告（「Nature 一篇论文说…」「XX 研究显示…」）
- 帖子引用了新闻/公告/事件（「XX 刚发布的…」「XX 官宣…」）
- 帖子引用了 GitHub 项目/开源工具/代码
- 帖子引用了可定位的文章/blog/教程
- 帖子中包含显式 URL（github.com、arxiv.org 等）

以下情况**不需要**溯源：

- 纯个人体验/感受/观点（无外部事实引用）
- 日常分享/生活记录（自拍、美食、旅行 vlog 等）
- 纯教程/方法帖（作者自己的方法，未引用外部来源）
- 开箱帖中提到产品名但仅为主观感受（「这个风扇挺好看」）——但如果提到了具体参数/价格，仍需溯源

**判断流程：** 通读帖子全文（desc + VLM 描述 + transcript）→ 识别所有外部事实引用 → 有就溯源，没有就跳过。

该判断只做一次。没有识别到外部事实引用时，直接跳过溯源，不要为了确认"是否存在来源"而调用 `web_search`。

**跳过时：** 在 `output.json` 中写入 `"tracing": {"performed": false, "reason": "skipped: <原因>"}`，在 `content.md` 末尾添加 `> ℹ️ 溯源已跳过：<原因>`。完成第九步打包后，在结果总结中明确告知用户溯源已跳过，并提示「如需追加溯源，告诉我即可」。然后**自动继续下游流程**，不在此处阻塞。

#### 8.1 执行溯源

8.0 判断需要溯源时，读取 `references/tracing-search.md` 并按其中完整流程执行：收集文本 → 识别来源 → 搜索原始 URL → 记录到 output.json 和 content.md。

不需要溯源时，按 8.0 中的跳过规则处理，不要读取该 reference。

### 第九步：打包输出

将所有结果写入输出目录。必须在同一个 turn 内连续调用多个 `write_file` 写入 `metadata.json`、`output.json`、`content.md`，禁止拆成多个 turn。只有 `write_file` 返回错误时才进入修复流程。

1. **`metadata.json`**：归一化格式。从 MCP 原始返回中提取 `note_id`（优先级：`feed_id` > `note_id` > `data.note.noteId` > 顶层 `noteId` > `mcp_raw.noteId`），存入顶层 `note_id`；`xsec_token`（优先级：`xsec_token` > `xsecToken` > `data.note.xsecToken` > `mcp_raw.xsecToken`）；`source_url` 直接使用原始输入链接，短链则使用重定向后的最终 URL，不强制转换成 explore 格式；`extracted_at` 用当前 ISO 时间；原始 MCP 数据放入 `raw`。schema 见「输出」章节。
2. **`output.json`**：组装后的结构化内容包（格式见上方「输出」章节）。顶层必须包含 `source_url`，作为下游 `content-to-vault` 的唯一原始内容链接字段；不要另写同义字段。另包含所有提取和处理结果，以及 `tracing` 字段标明溯源执行状态。下游只读取其需要的字段，多出字段不阻塞归档。
3. **`content.md`**：可读 Markdown（第七步生成的内容），末尾包含 `tracing_status_line`：溯源完成时显示来源列表，跳过时显示 `> ℹ️ 溯源已跳过：<原因>`
4. 媒体文件已在 `images/` 和 `video.mp4` 中

---

## 完成后：自动进入下游归档

本 skill 是 pipeline 的第一阶段。完成后，**不要就此结束**——必须自动加载 `content-to-vault` skill 并传入 `output_dir`，让归档流程继续。

具体操作：

1. 记下最终 `output_dir` 的绝对路径
2. 加载 `content-to-vault` skill（`skill_view(name='content-to-vault')`）
3. 将 `output_dir` 作为输入，同时传递已提取字段（标题、`source_url`、`source_type`）
4. 按 `content-to-vault` 的工作流程执行归档（判重 → 分类 → 生成笔记 → 写入 vault）
5. 最终向用户返回完整的「提取 → 归档」结果摘要

如果 `content-to-vault` skill 不存在，只返回提取结果摘要，并告知用户可以安装该 skill 进行自动归档。不要尝试自己分析或总结内容包——那是 `content-to-vault` 的工作。

---

## 注意事项

- `xsec_token` 必须从分享链接获取——直接粘贴浏览器地址栏 URL 不含 token
- 溯源由 8.0 判断是否需要——不是每条帖子都必须执行。需要时按 8.3 读取 `references/tracing-search.md`
- `get_feed_detail` 只需要 `feed_id`/`note_id` 与 `xsec_token`——不要为了调用 MCP 或记录 `source_url` 强制转换 URL 格式
- 批量处理见 `batch-url-to-vault` skill
- 媒体文件不自动删除，由用户手动管理
- **禁止开启 `load_all_comments`**——使用默认的 10 条评论即可
- Cookie、MCP、下载失败等排障见 `references/troubleshooting.md`
