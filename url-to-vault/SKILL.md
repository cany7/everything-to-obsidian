---
name: url-to-vault
description: 接收一个 URL，按 URL pattern 匹配 extractor，调用提取后自动进入 content-to-vault 归档。当用户发送单个链接（小红书、YouTube、网页等）或明确表示"把这个链接归档到 vault"时使用。
version: 1.0.0
author: tim77
license: MIT
metadata:
  hermes:
    tags: [url-router, content-pipeline, automation]
    related_skills: [content-to-vault, xhs-extract]
---

# url-to-vault — 单链接路由到归档

## 概览

`url-to-vault` 是单链接的统一入口。它根据 URL pattern 选择对应的 extractor，调用提取，然后将产出的内容包交给 `content-to-vault` 归档。

## URL Pattern → Extractor 映射

| URL 匹配 | Extractor | 说明 |
|----------|-----------|------|
| `xhslink.com`、`xiaohongshu.com/discovery/item/`、`xiaohongshu.com/explore/`、`user/profile/` | `xhs-extract` | 小红书帖子 |

> 当前只支持小红书。新增 extractor 时在此表追加一行。

## 流程

1. 接收 URL
2. 匹配 URL pattern，确定 extractor skill 名称
3. 如果匹配不到任何 pattern：告知用户当前不支持的链接类型，停止
4. 调用 extractor skill：`skill_view(name='<extractor>')`，传入 URL。extractor 完成后会自动加载 `content-to-vault` 归档

## 注意事项

- 不要自己分析内容、不要自己分类、不要跳过 extractor 直接读链接——每个步骤由对应的 skill 负责。
- 新 extractor 接入只需在 URL 映射表追加一行，并在 repo 根目录创建对应的 skill 目录（如 `xhs-extract/`）。
