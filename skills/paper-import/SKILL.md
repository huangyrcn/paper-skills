---
name: paper-import
description: >
  一键导入论文：从标题/DOI/链接/模糊描述开始，自动走完 resolve → acquire → repo 管线。
  当用户说"导入这篇论文"、"帮我把这篇论文弄下来"、"下载这篇论文"、
  "把这篇论文弄到本地"、"帮我搞定这篇论文"时触发。
  覆盖从搜索到下载到找代码的全流程。如果用户只需要搜索/确认论文身份，
  不需要下载，应使用 paper-search skill。
  三步默认全部执行：确定论文 → 获取 PDF+markdown → 找代码仓库。
  用 --no-acquire 跳过下载，--no-repo 跳过代码搜索。
argument-hint: "<论文引用> [--no-acquire] [--no-repo]"
---

# Paper Import

一键导入论文。编排 resolve → acquire → repo 管线。

## Ownership

This skill is an orchestrator. It owns:

- Pipeline control flow (which steps to run, error handling between steps)
- Output folder structure under `$PAPERS_DIR/{folder_slug}/`

This skill does **not** own any artifacts directly. All work is delegated:

- Identity resolution → `paper-search`
- PDF download + normalization → `paper-acquire`
- Repository discovery → `paper-repo`

## 流程

```
用户输入（标题/DOI/链接/模糊描述）
       │
       ▼
  Step 0: 解析 PAPERS_DIR（环境变量 → 实际路径）
       │
       ▼
  Step 1: 快速去重（目录名匹配 → 身份验证 → 产出验证 → 结构修复）
       │
       ├── 身份匹配 + 产出完整？──→ 报告"已导入"，结束
       ├── 身份匹配 + 部分缺失？──→ 只执行缺失的步骤
       │
       ▼
  Step 2: paper-search（确定论文身份）
       │
       ▼ 生成 metadata.yaml
       │
       ├── 用户传了 --no-acquire? ──→ 跳到 Step 4
       │
       ▼
  Step 3: paper-acquire（下载 PDF + 转 markdown）
       │
       ├── 用户传了 --no-repo? ──→ 结束
       │
       ▼
  Step 4: paper-repo（搜索并 clone 代码仓库）
```

## 用法

```bash
# 全套：确定 + 下载 + 找代码（默认行为）
paper-import "Attention Is All You Need"

# 只确定论文身份，不下载
paper-import "GAT" --no-acquire

# 确定 + 下载，不找代码
paper-import "10.48550/arxiv.2002.05287" --no-repo
```

## 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| 第一个参数 | 论文引用（标题/DOI/arXiv/URL/模糊描述） | 必填 |
| `--no-acquire` | 跳过 PDF 下载和 markdown 转换 | 不跳过 |
| `--no-repo` | 跳过代码仓库搜索 | 不跳过（默认执行） |

## 各步骤职责

### Step 0: 解析 $PAPERS_DIR

`$PAPERS_DIR` 是环境变量（plugin settings 或系统环境变量），需要先解析为实际路径。解析方式不限，拿到路径即可。

拿到结果后（如 `Y:\papers`），后续步骤直接用这个路径，不要再重复解析。

### Step 1: 快速去重（必须在 paper-search 之前执行）

拿到 `$PAPERS_DIR` 实际路径后，**立即**检查已导入的论文：

**1a — 目录名匹配（快速粗筛）：**

列出 `$PAPERS_DIR` 下所有文件夹名，查找包含论文关键词的 folder_slug（如 `iclr2026-mf-gia-zhuo` 包含 `mf-gia`）。
如果目录名没匹配到，用 Grep tool 搜 `*/metadata.yaml` 的 title 字段兜底。

**1b — 身份验证（确认是同一篇论文）：**

读取匹配到的 `metadata.yaml`，验证：
- `identity.aliases` 中的 arXiv ID / DOI 与用户输入一致（如有）
- `bibliography.title` 与用户查询的论文标题匹配

如果身份不匹配（同名不同论文），视为未找到，继续 Step 2。

**1c — 产出验证（确认文件确实属于这篇论文）：**

身份确认后，验证实际产出：
- `paper/paper.pdf`：存在且 >1KB。如果 `hydrate_raw.py` 的 `_verify_pdf_identity()` 可用，用它验证 PDF 第一页标题与 metadata 一致
- `paper/paper.md`：存在且 >500 字符
- `repo/`：存在且非空。检查 `repo_search.selected.url` 与实际 clone 的 remote 一致

**1d — 结构修复（metadata 损坏时修复，不重跑）：**

如果 metadata.yaml 有结构问题（如 legacy 字段嵌套在错误的层级、schema 外的字段），直接修复 YAML 结构，而不是重新跑 paper-search 管线。论文数据已经存在，只是元数据格式有误。

**判断结果：**
- 身份验证通过 + 产出全部正确 → 报告"论文已导入"，结束
- 身份验证通过 + 部分产出缺失/损坏 → 只执行缺失的步骤（跳过已完成的）
- 身份验证失败 → 继续 Step 2（完整管线）

### Step 2: paper-search（仅当 Step 1 未找到匹配时执行）

调用 `paper-search` skill。

- 输入：用户的论文引用
- 输出：`$PAPERS_DIR/{folder_slug}/metadata.yaml`
- 失败处理：如果无法确定论文，停止并告知用户

### Step 3: paper-acquire（默认执行）

除非用户传了 `--no-acquire`，否则调用 `paper-acquire` skill。

**先检查本地是否已存在**：如果 `$PAPERS_DIR/{folder_slug}/paper/paper.pdf` 已存在（文件 >1KB），跳过下载；如果 `paper.md` 也已存在，跳过整个 acquire 步骤并告知用户。

- 输入：`$PAPERS_DIR/{folder_slug}/metadata.yaml`
- 输出：`$PAPERS_DIR/{folder_slug}/paper/paper.pdf` + `paper.md`
- 失败处理：记录警告，继续下一步（如果 repo 搜索开启）

### Step 4: paper-repo（默认执行）

除非用户传了 `--no-repo`，否则调用 `paper-repo` skill。

**先检查本地是否已存在**：如果 `$PAPERS_DIR/{folder_slug}/repo/` 已存在（目录非空），跳过整个 repo 步骤并告知用户。

- 输入：`$PAPERS_DIR/{folder_slug}/metadata.yaml`
- 输出：代码仓库 clone 到 `repo/`，搜索结果写入 metadata.yaml

## 输出结构

完成后，`$PAPERS_DIR/{folder_slug}/` 下应有：

```
{folder_slug}/
  metadata.yaml          ← resolve 产出（始终有）
  paper/
    paper.pdf            ← acquire 产出（除非 --no-acquire）
    paper.md             ← acquire 产出（除非 --no-acquire）
    paper_images/        ← acquire 产出（如果 PDF 含图片）
  repo/                  ← repo 产出（除非 --no-repo）
```
