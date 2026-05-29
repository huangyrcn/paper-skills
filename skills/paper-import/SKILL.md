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
  ① paper-search（始终执行）
       │
       ▼ 确定论文身份，生成 metadata.yaml
       │
       ├── 用户传了 --no-acquire? ──→ 跳到 ③
       │
       ▼
  ② paper-acquire（默认执行）
       │
       ▼ 下载 PDF，转成 paper.md
       │
       ├── 用户传了 --no-repo? ──→ 结束
       │
       ▼
  ③ paper-repo（默认执行）
       │
       ▼ 搜索并 clone 代码仓库
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

### Step 1: paper-search（始终执行）

调用 `paper-search` skill。

- 输入：用户的论文引用
- 输出：`$PAPERS_DIR/{folder_slug}/metadata.yaml`
- 失败处理：如果无法确定论文，停止并告知用户

**解析出标题后，用 Grep tool 搜索 `$PAPERS_DIR` 下所有 `*/metadata.yaml`，匹配标题关键词。**
如果匹配到已有论文，获取其 folder_slug，跳过后续步骤中已存在的产出（见 Step 2/3）。

### Step 2: paper-acquire（默认执行）

除非用户传了 `--no-acquire`，否则调用 `paper-acquire` skill。

**先检查本地是否已存在**：如果 `$PAPERS_DIR/{folder_slug}/paper/paper.pdf` 已存在（文件 >1KB），跳过下载；如果 `paper.md` 也已存在，跳过整个 acquire 步骤并告知用户。

- 输入：`$PAPERS_DIR/{folder_slug}/metadata.yaml`
- 输出：`$PAPERS_DIR/{folder_slug}/paper/paper.pdf` + `paper.md`
- 失败处理：记录警告，继续下一步（如果 repo 搜索开启）

### Step 3: paper-repo（默认执行）

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
