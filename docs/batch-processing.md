# 链接批处理使用说明

`batch-url-to-vault` 支持通过 cron job 批量处理链接列表，将每条链接提取并归档到 Obsidian vault。

## 前置条件：网络请求白名单

批处理通过子进程 `hermes -s url-to-vault chat -q '...'` 逐条处理链接。很多社媒平台的分享链接是**短链**（如 `xhslink.com`、`youtu.be`、`t.co` 等），提取时需要先做 HTTP 重定向获取完整 URL。

这一步通过 `execute_code` 工具发起网络请求（Python `requests.get` 跟随重定向）。在 cron job 子进程模式中，Hermes 的审批系统没有交互界面，网络请求会等待审批并卡死。

**使用批处理前，必须将 `execute_code` 的网络请求加入审批白名单**（always approve），如果不配置白名单，子进程会在短链重定向这一步卡死等待审批，整个批处理无法进行。

## CSV 格式

链接列表需要以 CSV 文件形式提供，三列，第一行为表头：

```csv
序号,处理情况,链接
1,,http://xhslink.com/xxx
2,,http://xhslink.com/yyy 跳过下载图片
3,,https://xiaohongshu.com/explore/abc?xsec_token=...
```

各列说明：

| 列 | 说明 |
|----|------|
| 序号 | 整数，用于标识行。脚本以此判断是否为数据行 |
| 处理情况 | 空白表示未处理，`Done` 或 `Error` 表示已处理。脚本自动跳过有值的行 |
| 链接 | 要处理的 URL，可以附带额外文字备注（如「跳过下载图片」），整列内容原样传给 `url-to-vault` |

### 文件编码

CSV 文件建议使用 **UTF-8 with BOM**（`utf-8-sig`）编码，确保含中文内容的 CSV 在不同平台/编辑器中正常打开。

## 链接类型

第三列放入你想提取的 URL。支持：

- **短链**：`http://xhslink.com/xxx`（会自动重定向到完整链接）
- **完整链接**：`https://xiaohongshu.com/explore/abc?xsec_token=...`
- **任何 `url-to-vault` 支持的平台链接**

链接后面可以附加备注（如 `跳过下载图片`），用空格分隔即可，不影响处理。

## 取链接脚本

本 suite 中的取链接脚本位于：

```text
batch-url-to-vault/scripts/pick-next-url.py
```

它接受 CSV 路径作为命令行参数，输出下一条待处理链接。直接调试时可以运行：

```bash
python3 "$HERMES_HOME/skills/everything-to-obsidian/batch-url-to-vault/scripts/pick-next-url.py" "{CSV_PATH}"
```

`$HERMES_HOME` 是 Hermes 安装根目录（默认 `~/.hermes`），skill 安装在 `$HERMES_HOME/skills/` 下。

## Cron wrapper

Hermes cron 的 `script` 参数只接受 `~/.hermes/scripts/` 下的脚本路径，不能直接传命令行参数，也不能直接指向 suite 内的 `batch-url-to-vault/scripts/pick-next-url.py {CSV_PATH}`。

因此创建 cron job 前，应先在 `~/.hermes/scripts/` 下生成一个很薄的 wrapper，由 wrapper 调用本 suite 内的脚本并传入 CSV 路径。wrapper 示例：

```python
#!/usr/bin/env python3
import runpy
import sys

SCRIPT = "$HERMES_HOME/skills/everything-to-obsidian/batch-url-to-vault/scripts/pick-next-url.py"
CSV_PATH = "<absolute path to links.csv>"

sys.argv = [SCRIPT, CSV_PATH]
runpy.run_path(SCRIPT, run_name="__main__")
```

cron job 的 `script` 字段填写 wrapper 文件名或绝对路径，例如：

```text
everything-to-obsidian-pick-next-url.py
```

## 启动批处理

在 Hermes 对话中告诉 Agent：**你要批量处理链接**，并给出 CSV 文件的路径。Agent 会：

1. 加载 `batch-url-to-vault`。
2. 用 `batch-url-to-vault/scripts/pick-next-url.py` 读取下一条未处理链接。
3. 如需 cron job，先生成 `~/.hermes/scripts/` wrapper。
4. 创建 cron job，每次取一条链接。
5. 每条链接用独立 `hermes -s url-to-vault chat -q ...` 子进程处理，降低平台风控风险。
6. 根据结果把 CSV 行标记为 `Done` 或 `Error`。

## 中断后继续

cron job 被中断了（关机、停止 cron 等）？重新告诉 Agent 继续处理同一个 CSV 文件就行。CSV 里已经标记 `Done` / `Error` 的行会被自动跳过，不会重复处理。
