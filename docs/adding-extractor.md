# Adding a New Extractor

本文档说明如何给 everything-to-obsidian 新增一个上游 extractor。

## 放置位置

新增 extractor 直接放在 repo 根目录下，与现有 skills 同级：

```text
everything-to-obsidian/
├── url-to-vault/
├── content-to-vault/
├── xhs-extract/
└── <new-extractor>/
    ├── SKILL.md
    ├── references/      # 可选；排障、长规则、条件加载材料
    └── scripts/         # 可选；该 extractor 自己调用的脚本
```

Hermes 会递归发现 repo 内的 `SKILL.md`；保持每个 skill 自包含即可。

## 步骤

### 1. 创建 skill 目录

```text
<new-extractor>/
├── SKILL.md
├── references/
└── scripts/
```

### 2. 实现 SKILL.md

extractor 必须按 [`content-package-schema.md`](content-package-schema.md) 产出内容包。最小可用的 SKILL.md 结构：

- **输入**：该 extractor 接受的链接格式
- **依赖**：需要的工具（Hermes tools / MCP / 外部 CLI）
- **流程**：提取 → 下载媒体（如有）→ 搜索溯源 → 生成 `content.md` → 打包
- **输出**：`output_dir/` 目录，内含 `output.json` + `content.md`（+ 媒体文件）

### 3. 产出 output.json

至少写入这些下游读取字段：

```json
{
  "source_type": "<your_type>",
  "source_url": "<原始链接>",
  "sources": [],
  "images": []
}
```

`source_type`、`source_url` 必需；`sources[]` 和 `images[]` 可选——没有时可写空数组或省略。extractor 可以额外写入平台专用字段，下游会忽略不认识的字段。

### 4. 产出 content.md

把所有可读内容整理进 `content.md`：原始正文、图片 OCR/VLM 描述、转写文本、评论、平台元数据（作者、时间等）。溯源结果也写入 `content.md` 的「溯源」段。

### 5. 注册到 url-to-vault

在 [`../url-to-vault/SKILL.md`](../url-to-vault/SKILL.md) 的 URL Pattern → Extractor 映射表中追加一行：

```markdown
| `<你的 URL pattern>` | `<new-extractor>` | <说明> |
```

`<new-extractor>` 应与新 skill 的 frontmatter `name` 一致，确保 `skill_view(name='<new-extractor>')` 能加载到它。

### 6. 更新架构文档

在 [`architecture.md`](architecture.md) 的 pipeline 图和 repository layout 中加上新 extractor。

### 7. 验证

- 新目录下存在 `SKILL.md`，且 frontmatter 有 `name` 和 `description`。
- 运行 `/reload-skills` 后，Hermes 能加载新 skill。
- 对一条真实 URL 运行 extractor，确认输出目录包含 `output.json` 和 `content.md`。
- 将该输出目录交给 `content-to-vault`，确认能成功归档。
- 通过 `url-to-vault` 输入同一类 URL，确认路由到新 extractor。

## 溯源：上游只 web_search

extractor 的溯源职责是**找到原始 URL**——通过 `web_search` 从搜索结果 snippet 和 URL 确认匹配。**不要调用 `web_extract`**——内容提取留给 `content-to-vault`。找到的 URL 写入 `output.json.sources[]` 和 `content.md` 的「溯源」段。

## 提取后自动归档

extractor 完成提取后应自动加载 `content-to-vault` 进行归档，无论是由用户直接触发还是被 `url-to-vault` 调用。路径判重保证了重复提交不会产生重复笔记。

## 参考

- 内容包 schema：[`content-package-schema.md`](content-package-schema.md)
- 架构文档：[`architecture.md`](architecture.md)
- 安装说明：[`installation.md`](installation.md)
- 已有 extractor 示例：[`../xhs-extract/SKILL.md`](../xhs-extract/SKILL.md)
