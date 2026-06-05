# 溯源搜索细则

仅当主 `SKILL.md` 的 8.0 判断需要溯源时读取本文件。没有识别到外部事实引用时，不要读取本文件，不要调用 `web_search`。

## 1. 收集文本

汇总以下全部文本作为溯源的原材料：

- `desc`（帖子正文）
- 每张图的 VLM `description`（第五步结果——图中文字和画面描述）
- 视频 `transcript`（第六步结果，如有）

## 2. 识别来源

通读以上全部文本，从中识别作者引用的外部信息。来源形式多样，包括但不限于：

- **显式 URL**：任何直接出现的链接（github.com、arxiv.org、zhuanlan.zhihu.com、新闻报道 URL、公众号文章链接等）
- **明确的项目/工具名**：GitHub `org/repo` 格式、知名产品名（如 "spaCy"、"Stable Diffusion"、"M5Paper"）
- **可定位的引用线索**：文中提到「XX 时报最新发布了一篇文章…」「XX 公司的一篇 blog 提到…」「据 XX 研究…」「XX 论文指出…」——这些是**线索**而不是直接 URL，需要下一步推断搜索词去找到原始来源

## 3. 搜索原始 URL

**只使用 `web_search`，不调用 `web_extract`。** 从搜索结果 snippet 和 URL 确认匹配即可——内容提取留给下游 content-to-vault。

找到原始来源 URL 后直接进入第 4 步记录。找不到的，跳过该来源。

### 搜索原则

1. **双语搜索**：每个来源至少搜索两次，一次中文关键词、一次英文关键词。英文搜索信息质量通常更高，尤其对产品、论文、开源项目。
2. **优先一手来源**：搜索结果中按权威性排序：官方页面 > 原始论文/仓库 > 权威媒体报道 > 博客/论坛。对于产品类引用，优先找品牌官网产品页；对于研究类引用，优先找 arxiv/期刊原文；对于工具/项目，优先找 GitHub 仓库 README。
3. **不限制数量**：当帖子涉及多个不同的外部来源时，每个都单独记录。没有数量上限。
4. **第三方来源作为备选**：仅当无法找到官方/一手来源时（404、需要付费墙、内容已被删除），才使用可靠的第三方来源（如 IT之家、The Verge 等知名科技媒体）。在 `description` 中标注「（一手来源无法获取，此为第三方报道）」。

### 显式 URL 的来源

帖子中直接出现了 URL 或 GitHub `org/repo` 时，用 `web_search` 快速验证该 URL/项目确实存在——搜索结果中应能匹配到该域名或项目名。确认后直接记录 URL。如果该 URL 是第三方页面，按上面的搜索原则搜索官方一手来源。

### 无可直接访问 URL 的线索

1. 根据上下文推断关键信息，构造**中英文两组搜索词**。
2. 用 `web_search` 分别搜索，从结果 snippet 和 URL 判断最匹配的官方/原始来源。
3. 记录确认后的 URL。

搜索词构造示例：

| 帖子上下文 | 中文搜索 | 英文搜索 |
|-----------|---------|---------|
| 戴森手持风扇开箱，799 元 | `"戴森 HushJet Mini Cool" 官方 参数` | `"Dyson HushJet Mini Cool" official specs site:dyson.com` |
| 「苹果 M4 MacBook Air 评测…」 | `"M4 MacBook Air" 官方 技术规格 site:apple.com.cn` | `"M4 MacBook Air" tech specs site:apple.com` |
| 「Nature 最新 AlphaFold 3 论文…」 | `"AlphaFold 3" site:nature.com` | 同上（论文名通常仅英文） |
| 「Redis 8.0 新特性…」 | `"Redis 8.0" 新特性 site:redis.io` | `"Redis 8.0" release notes site:redis.io` |
| 「GitHub 上一个本地 agent 项目…」 | 用帖子中的功能关键词 + `github.com` | 用英文功能关键词 + `github.com` |
| 「XX 时报报道了…」 | `"标题关键词" site:原媒体域名` | 同上，英文媒体用英文关键词 |

## 4. 记录来源

将找到的每个原始来源写入 `output.json` 的 `sources[]` 和 `content.md` 的「溯源」段：

`sources[]` 每条包含：

- `url`：原始来源的 URL
- `type`：来源类型（`github` / `article` / `x_post` / `news` / `blog` / `paper` / `docs` / `other`）
- `name`：简短标识（repo 名、文章标题、媒体名称等）
- `description`：**一句话纯事实**——这是什么来源、帖子里怎么提的。如果使用的是一手来源，直接描述事实；如果使用的是第三方来源（官方找不到），标注「（一手来源无法获取，此为第三方报道）」

**禁止在 description 中做任何分析**——不评价帖子描述是否准确、不对比原始内容、不总结全文、不发表观点。只记录"帖子里引用了 X，原始来源 URL 是 Y"这一事实。

`content.md` 的「溯源」段格式：

```markdown
## 溯源

- [来源名称](https://example.com/source) — 一句话说明（帖子里怎么提的）
```

溯源完成后，在 `output.json` 中设置 `"tracing": {"performed": true, "reason": "completed"}`，记录搜索结果到 `sources[]`。找不到任何来源的，`sources` 为空数组，`reason` 设为 `"completed: 未找到外部来源"`。

> ⚠️ 本步骤只做**找到并记录**原始来源的 URL 和基本事实。分析、对比、概括帖子观点与原始来源之间的关系——这些不属于本 skill 的范围，由下游流程负责。
