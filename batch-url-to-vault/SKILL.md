---
name: batch-url-to-vault
description: 按链接列表批量处理：cron job 定时触发，每条链接通过 url-to-vault 路由到对应的 extractor 提取+归档。当用户提供 CSV 链接列表文件路径并明确要求批量处理多个链接时使用。
version: 1.0.0
author: tim77
license: MIT
metadata:
  hermes:
    tags: [batch-processing, cron, url-router, automation]
---

# batch-url-to-vault — 批量链接处理

## 流程

1. **脚本取链接** — 扫描 CSV，取第一条未处理行，输出 `LINE=row` 和 `CONTENT=url`
2. **Cron 定时触发** — 每 2 分钟触发，注入脚本输出到 agent prompt
3. **子 agent 处理** — `hermes -s url-to-vault chat -q 'CONTENT'`（timeout 600s），由 url-to-vault 根据 URL pattern 选择 extractor 并完成提取+归档
4. **标记结果** — 在 CSV 处理情况列写 `Done`（成功）或 `Error`（失败）

## 链接列表

用户指定 CSV 文件路径。格式：三列，第一行表头。

```
序号,处理情况,链接
1,,http://xhslink.com/xxx
2,,http://xhslink.com/yyy 跳过下载图片
3,,https://xiaohongshu.com/discovery/item/abc?xsec_token=...
```

第三列为链接，可能会带有其他文字备注，整列内容原样传给 `url-to-vault`。

## 取链接脚本

本 skill 目录下的 `scripts/pick-next-url.py`，接受 CSV 路径作为命令行参数。加载本 skill 后，Hermes 会注入 `[Skill directory: .../batch-url-to-vault]`；运行脚本时用该目录解析出绝对路径：

```bash
python3 <batch-url-to-vault skill_dir>/scripts/pick-next-url.py "{CSV_PATH}"
```

## Cron job 配置

创建 cron job 时，用用户提供的 CSV 路径替换 `{CSV_PATH}`。

| 参数 | 值 |
|------|-----|
| schedule | `every 2m` |
| repeat | 链接总数 |
| script | `~/.hermes/scripts/<generated-wrapper>.py` |
| deliver | `local` |
| enabled_toolsets | `["terminal", "file", "skills"]` |

Hermes cron 的 `script` 参数只接受 `~/.hermes/scripts/` 下的脚本路径，不能直接带命令行参数。因此创建 cron 前，先在 `~/.hermes/scripts/` 生成一个很薄的 wrapper，把 CSV 路径传给本 skill 的 `scripts/pick-next-url.py`。

Wrapper 内容模板：

```python
import runpy, sys

SCRIPT = "<batch-url-to-vault skill_dir>/scripts/pick-next-url.py"
CSV = "{CSV_PATH}"

sys.argv = [SCRIPT, CSV]
runpy.run_path(SCRIPT, run_name="__main__")
```

**Prompt 模板（`{CSV_PATH}` 替换为实际路径）：**

```
The script output above contains a LINE number and CONTENT to process.

If the output is EMPTY (no LINE= line), respond with "[SILENT]" and stop.

Steps:
1. Run url-to-vault via terminal (replace <CONTENT> with the actual link from script output):
   hermes -s url-to-vault chat -q '<CONTENT>' (timeout 600)
2. Check exit code.
3. Mark CSV (replace LINE and STATUS):
   python3 -c "
   import csv
   csv_path = '{CSV_PATH}'
   rows = list(csv.reader(open(csv_path, encoding='utf-8-sig')))
   for i, row in enumerate(rows):
       if i == 0: continue
       if len(row) >= 2 and row[0].strip() == 'LINE':
           row[1] = 'STATUS'
   writer = csv.writer(open(csv_path, 'w', encoding='utf-8', newline=''))
   writer.writerows(rows)
   "
   STATUS = Done on success, Error on failure.
4. Final response: brief summary including CONTENT, result, note title.
```

> `script` 参数传生成后的 wrapper 文件名或绝对路径，例如 `everything-to-obsidian-pick-next-url.py`。不要把 `<batch-url-to-vault skill_dir>/scripts/pick-next-url.py {CSV_PATH}` 直接传给 cron 的 `script` 参数；cron 不会解析参数，且只允许运行 `~/.hermes/scripts/` 下的脚本。

## 断点续传

中断后重新创建 cron job 即可。脚本自动跳过已有处理结果的行。

## 注意事项

- 每条链接独立处理，单条失败不阻塞后续。
- 不要跳过 `url-to-vault` 直接调 extractor 或 `content-to-vault`——不同链接类型由 `url-to-vault` 的 URL pattern 路由。
- batch 不做类型判断，URL pattern 匹配完全交给 `url-to-vault`。
