# 溯源搜索

仅当主流程已判断视频简介或音频转录文本中存在可验证外部事实引用、需要执行 `web_search` 时读取本文件。是否需要溯源的判断规则在主 `SKILL.md` 中，每次提取都要执行。

## 搜索规则

1. 为每个外部事实引用构造最小搜索词，优先包含专有名词、标题、项目名、型号、机构名、原文关键词。
2. 使用 `web_search` 找到原始 URL。不要调用 `web_extract`。
3. 只接受搜索结果 URL 和 snippet 足以确认匹配的来源。
4. 优先原始来源：官方公告、论文页面、GitHub repo、项目文档、原始文章。不要优先二手转载。
5. 无法可靠确认时不要硬填来源，在 tracing reason 里说明未确认。

## 输出格式

`output.json.sources[]` 每项：

```jsonc
{
  "url": "https://...",
  "type": "github|article|news|blog|paper|docs|product|other",
  "name": "简短标识",
  "description": "一句话说明这是什么来源、视频里怎么提到它"
}
```

`content.md` 的「溯源」段：

```markdown
## 溯源

- [来源名称](https://example.com/source) - 一句话说明
```

跳过时：

```jsonc
"tracing": {"performed": false, "reason": "skipped: no external factual references"}
```

```markdown
## 溯源

> 溯源已跳过：未识别到可验证的外部事实引用
```
