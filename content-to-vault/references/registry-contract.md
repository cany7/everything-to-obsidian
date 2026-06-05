# Registry 契约

## 用途

`content_registry.json` 是轻量地址簿和基于路径的判重索引，供已归档内容包使用。

不是内容身份数据库、URL 规范化层或恢复日志。

## 位置

```text
{VAULT}/Library/_system/content_registry.json
```

## Schema

```json
{
  "items": [
    {
      "input_dir": "/absolute/path/to/output_dir",
      "note_path": "Library/<category_l1>/<category_l2>/<filename>.md",
      "created_at": "2026-05-22T10:30:00+08:00",
      "source_url": "https://...",
      "source_type": "xhs"
    }
  ]
}
```

必填字段：

- `input_dir`：本次运行中内容包的 `os.path.realpath(output_dir)`。
- `note_path`：相对于 vault 根目录的路径。
- `created_at`：归档时间戳。

可选元数据字段：

- `source_url`：从顶层 `output.json.source_url` 原样复制；不要 normalize 或 canonicalize。
- `source_type`：从 extractor 输出复制（如有）。

## 判重

判重有意保守，仅基于路径：

1. 将 `os.path.realpath(output_dir)` 与 registry 的 `input_dir` 比较。
2. 生成目标笔记路径后，检查 registry 是否已有相同 `note_path` 或目标 `.md` 文件已存在。

不要用 `source_url` 判重。不同内容包可能引用或讨论同一个外部 URL，不应视为重复。
