# 常见问题与失败处理

仅当正常路径出现对应问题，或 agent 犹豫、失败时读取本文件。正常归档不要读取。

## 常见问题（agent 行为纠偏）

1. **把多个 write_file 合并进一个 execute_code 脚本**。
   - 修正：note、state、registry、classification_index 各自是独立产物，优先用 `write_file` 分文件写入。为减少回合，允许在同一个 assistant turn 中连续发出多个 `write_file`，但不要每写一个文件就总结或重新规划。只有当前运行器不支持同轮多次 `write_file` 时，才可用一次 `execute_code` 仅负责机械写入已经生成好的文件内容；不得在脚本中重新分析、改写或补充笔记。

2. 把本 skill 当作原始提取流程。
   - 修正：只使用内容包中已经提取好的文本，不调用 VLM/OCR/ASR。

3. 对引用来源过度研究。
   - 修正：只提取直接相关上下文，笔记自洽后就停止。

4. 创建过窄分类或过多/过细 tags。
   - 修正：`category` 表达主检索路径；tags 只用领域+内容类型（3-6 个）；细粒度概念放 topics。

5. 把引用来源当成判重键。
   - 修正：两篇笔记可以引用同一个 GitHub 项目、论文、公告或产品，但不一定重复。

6. 把机器字段塞满 frontmatter。
   - 修正：机器追踪放 registry；来源追溯放 `来源与素材`。

7. 为了可读性丢掉细节。
   - 修正：保留具体技术名词、数字、代码、命令、指标、名称和来源标题。

## Classification Index 维护注意事项

`classification_index.md` 由 agent 在每次归档时增量追加，长期使用后容易积累格式问题。已知常见问题：

- tag 条目误插到「已有目录」区域（H3/H4 格式 vs `- tag` 列表格式混淆）
- 同一目录在不同一级分类下重复出现（如「Python」同时在「技术」和「学习」下）
- 散乱的孤立 tag 出现在「分类原则」和「已有目录」之间
- Tags 区域有未归属到一级分类的裸 tag
- 描述文字在同一行内粘贴重复

如果发现 index 文件有明显格式混乱，标记给用户手动清理——agent 自行修补容易引入新的格式问题。新增目录和 tag 时严格遵守 H3/H4 + 描述格式，不要用 `- tag` 格式追加到目录区域。

## iCloud Vault 注意事项

**目录列出**：`search_files`（ripgrep 后端）在 iCloud 路径上可能失效。列出目录时优先使用 `terminal ls "{VAULT}/Library/"` 或 `terminal find "{VAULT}/Library/" -maxdepth 2 -type d` 替代，不要依赖 `search_files(target='files')`。

**文件锁**：`execute_code` 中对 iCloud 路径的 `open().read()` 可能报 `OSError: [Errno 11] Resource deadlock avoided`（iCloud sync daemon 锁文件）。此时直接用 `write_file` 工具写入即可——它能正常处理 iCloud 路径。不要在 `execute_code` 中反复重试读取，切 `write_file` 一步到位。

## 失败恢复

### 前置检查阶段

- 无法解析 vault 路径：停止，并提示用户在 `~/.hermes/.env` 中配置 `OBSIDIAN_VAULT_PATH`。
- 必需内容包文件缺失：停止，并说明输入不是有效的已提取内容包。
- registry 读取失败或 JSON 无效：停止，不要盲目覆盖。
- 路径安全校验失败：停止并报错。

### 外部读取阶段

- 引用链接读取失败：继续使用内容包内容，不阻塞归档。
- 本地素材缺失：只列出内容包文本中提供或实际存在的素材。

### 写入与归档阶段

写入顺序：先写 note → 更新 registry → 必要时更新 classification_index。

如果 note 写入成功但 registry 写入失败：

- 不覆盖已写入的 note。
- 返回"部分归档"状态，明确说明已写入的 note 绝对路径，以及 registry 待补写。
- 下次处理同一内容包时，如果目标 note 路径已经存在，不要覆盖；可以返回已有路径或生成不冲突的新标题。

如果 registry 写入成功但 classification_index 更新失败：

- classification_index 的缺失不影响路径判重，属于可延迟修复的一致性问题。
- 返回已归档结果，同时说明 classification_index 待补写。

失败时不要覆盖旧 note 或旧 registry。

如果分类不确定：使用更宽泛目录，并减少 tags。
如果文件名冲突：追加短 ID，例如 `-a1b2c3`。
