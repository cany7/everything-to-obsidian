# Architecture

## Repository Layout

`everything-to-obsidian` 是一个多 skill suite。repo 根目录下每个子目录都是一个可被 Hermes 递归发现的 skill：

```text
everything-to-obsidian/
├── url-to-vault/          # 链接路由入口
├── batch-url-to-vault/    # 批量入口 / cron job 编排
├── content-to-vault/      # 内容包 → Obsidian 归档
├── xhs-extract/           # 小红书 extractor
├── web-video-extract/     # YouTube / Bilibili 视频音频 extractor
└── docs/                  # 项目文档
```

目录约定：

- 每个 skill 自带自己的 `SKILL.md`、`references/`、`scripts/`。
- 运行时脚本放在调用它的 skill 目录内。

## Pipeline

```text
                  ┌──────────────────┐
                  │  url-to-vault    │  ← 链接入口，URL pattern 路由
                  │  (router)        │
                  └──────┬───────────┘
                         │ 匹配 pattern → 选 extractor
          ┌──────────────┼─────────────────┐
          ▼              ▼                 ▼
   ┌────────────┐ ┌─────────────────┐ ┌────────────┐
   │ xhs-extract│ │web-video-extract│ │ (future)   │  ← 上游提取器
   │ 小红书      │ │YouTube/Bilibili │ │ web/pdf    │
   └─────┬──────┘ └────────┬────────┘ └─────┬──────┘
         │                 │                │
         └─────────────────┼────────────────┘
                        │ output_dir (output.json + content.md)
                        ▼
               ┌──────────────────┐
               │ content-to-vault │  ← 下游归档器
               │ (archiver)       │
               └──────┬───────────┘
                      │
                      ▼
               ┌──────────────────┐
               │  Obsidian Vault  │
               └──────────────────┘
```

```text
                  ┌──────────────────┐
                  │ batch-url-to-vault│ ← 批量链接入口
                  │ (batch)           │
                  └──────┬───────────┘
                         │ 逐条调用
                         ▼
                  ┌──────────────────┐
                  │  url-to-vault    │
                  └──────────────────┘
```

当前所有入口都通过 URL 触发。后续会加入接受文件、音频等非 URL 输入的入口和 extractor，同样产出标准化内容包交由 `content-to-vault` 归档。

## 入口

| 入口 | 用途 | 触发方式 |
|------|------|----------|
| `url-to-vault` | 单个链接 | 直接对话 |
| `batch-url-to-vault` | 链接列表 | 直接对话 / cron job |
| `content-to-vault` | 已有内容包目录，只需归档 | 直接传入 `output_dir` |

## 数据流

```text
extractor 产出                      content-to-vault 读取
─────────────────                   ──────────────────
output.json:
  source_type                        → registry
  source_url                         → registry，笔记「原始链接」
  sources[]                          → web_extract 补充内容
  images[]                           → 插入笔记末尾（file:// 图片链接）
  (post.*, video, tracing 等)        → 忽略

content.md                           → 笔记正文主材料
  (溯源段)                            → sources[] 不存在时的回退 URL 来源
```
