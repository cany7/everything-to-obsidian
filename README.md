# everything-to-obsidian

这是一个能帮你将各种信息来源，整理归档到 Obsidian 中的 skills。把看过的好内容，一键让 Hermes Agent 整理进知识库。

## 为什么需要这个 Skills？

我每天的日常：刷到一篇好文章、一条有价值的内容或一个干货视频，随手丢进收藏夹，想着“以后再看”。结果收藏越积越多，根本不会再打开。来源五花八门——网页、论坛、视频、转述——等到某天想起来要整理时，要么嫌重新看一遍太费时间，要么早已忘记当初为什么收藏它。这些信息就这样沉在那里，无法检索、无法串联，更没办法复用。

这个 Skills 解决的问题很简单：把任意来源的碎片信息，自动转换成一篇整理总结好的结构化笔记。它不只是于提取原文，而是生成带有摘要、重点提炼、事实核验的整理文档，并自动完成分类、标签和目录归位，方便后续查看和检索。

更重要的是，它内置了信息溯源机制。当内容中出现引用、转述或二手信息时，会查找并收集原始信息来源，一并加入整理，同时将链接附在笔记中。这意味着你积累的不再是一堆孤立的信息片段，而是有据可查、可追溯来源的知识资产。

## 它能做什么？

你只需要把一个链接，一个文档，一条视频交给它，剩下的全部自动完成：生成结构清晰的笔记、按内容分类、打上标签，笔记写好后直接写入你的 Vault，让每一次收藏都变成一次真正的知识整理。

同时这个 Skills 还对 [`llm-wiki`](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/research/research-llm-wiki) 做了适配，方便完成进一步的长期知识沉淀。它会自动判断当前内容是否适合加入 wiki，并为每条笔记标记处理状态。

## 安装说明

完整安装配置流程请参考 [`docs/installation.md`](docs/installation.md)。

## 大致流程

```text
输入来源
  ↓
提取内容
  ↓
生成内容包
  ↓
整理、分类、归档
  ↓
Obsidian 笔记
```

## 当前支持的内容来源

### URL

把支持的链接发给 agent，随后会按照链接类型选择对应的提取流程，然后自动归档到 Obsidian。

当前支持：

- 小红书帖子：支持图文和视频帖子。会提取帖子正文、图片内容、视频转写、热门评论，以及必要的平台信息，并补充帖子提到的原始资料来源。也可以告诉 Agent 跳过下载图片流程，只提取文字内容。
- YouTube / Bilibili 视频：使用 `yt-dlp` 下载音频并用 Whisper 转写，默认读取 Chrome 登录态；失败时可退回无 cookies 尝试，并按需要提示重新登录。

#### 批量归档链接

准备一个 CSV 文件，格式如下：

```csv
序号,处理情况,链接
1,,https://xhslink.com/...
2,,https://xhslink.com/... 跳过下载图片
```

然后告诉 agent：

```text
批量处理这个 CSV 里的链接：/你的/文件路径/links.csv
```

批量处理的详细说明见 [`docs/batch-processing.md`](docs/batch-processing.md)。

## 相关文档

- 安装与配置：[`docs/installation.md`](docs/installation.md)
- 批量处理：[`docs/batch-processing.md`](docs/batch-processing.md)
- 内容包格式：[`docs/content-package-schema.md`](docs/content-package-schema.md)
- 新增内容来源：[`docs/adding-extractor.md`](docs/adding-extractor.md)
- 小红书 MCP 已知问题：[`docs/xhs-mcp-known-issues.md`](docs/xhs-mcp-known-issues.md)

## 项目依赖

| 依赖 | 用途                                 | 必需性 | 来源 |
|------|------------------------------------|--------|------|
| Hermes Agent | 运行 skills、调用内置工具、管理 MCP 和 cron 批处理 | 必需 | [Hermes Agent 文档](https://hermes-agent.nousresearch.com/docs) |
| Obsidian | 写入并管理归档笔记                          | 必需 | [Obsidian](https://obsidian.md/) |
| xiaohongshu-mcp | 小红书帖子结构化数据提取和登录态管理                 | 小红书提取需要 | [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) |
| yt-dlp | YouTube / Bilibili 元数据提取和音频下载               | Web 视频提取需要 | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| OpenAI Whisper | 视频和音频内容转录                          | 视频转录需要 | [OpenAI Whisper](https://github.com/openai/whisper) |
| ffmpeg | 视频/音频处理，配合 Whisper 完成转录            | 视频转录需要 | [ffmpeg](https://ffmpeg.org/) |
| llm-wiki skill | 可选的长期知识沉淀适配                        | 可选 | [llm-wiki](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/research/research-llm-wiki) |
