---
name: paper-card
description: >
  把一篇论文拆解成结构化研究卡片。
  当用户说"做个卡片"、"写阅读笔记"、"总结这篇论文"、
  "帮我读一下"、"结构化分析"、"拆解论文"时触发。
  输出 card.md（快速概览）和 card-deep.md（深度分析）。
argument-hint: "<论文引用 | folder_slug | PDF路径> [--lang zh|en]"
---

# Paper Card

Generate structured research cards from an acquired paper.

## Ownership

This skill owns:

- `$PAPERS_DIR/{folder_slug}/card.md` — quick card
- `$PAPERS_DIR/{folder_slug}/card-deep.md` — deep card

This skill does **not**:

- Download PDF or normalize paper (use `paper-acquire`)
- Resolve paper identity (use `paper-search`)
- Discover code repositories (use `paper-repo`)
- Modify `metadata.yaml`

## Input Handling

### 输入类型检测

按以下优先级检测输入类型：

1. **已导入论文**（folder_slug）：检查 `$PAPERS_DIR/{input}/metadata.yaml` 是否存在。
   存在 → 检查 `paper/paper.md` → 生成卡片。
   **输入看起来像 folder_slug（无 `.pdf` 后缀、无 URL scheme、无 DOI/arXiv 前缀）但目录不存在时**，告知用户该论文未导入，询问是否需要导入。
2. **本地 PDF**：输入是本地 `.pdf` 文件路径（`Path(input).suffix == '.pdf' and Path(input).is_file()`）。
   → 调 `pdf-to-md` 转 markdown → 调 `paper-search` 解析身份 → 复制 PDF 和 markdown 到 `$PAPERS_DIR/{folder_slug}/paper/` → 生成卡片。
3. **论文引用**（标题/DOI/arXiv ID/URL）：其他所有输入。
   → 委托 `paper-import` 完成 search+acquire → 用生成的 folder_slug → 生成卡片。

### 本地 PDF 处理细节

用户给本地 PDF（如 `~/Downloads/paper.pdf`）时：

1. 调 `pdf-to-md` 把 PDF 转成 markdown，输出到 PDF 同目录
2. 从 PDF 文件名推断论文身份（如 `2301.13688.pdf` → arXiv ID，`attention_is_all_you_need.pdf` → 标题关键词）
3. 如果文件名无法推断，询问用户补充信息（标题/DOI/arXiv ID）
4. 调 `paper-search` 生成 `metadata.yaml`
5. 在 `$PAPERS_DIR/{folder_slug}/paper/` 下创建标准目录结构，**复制**（不移动）PDF 和 markdown
6. 生成卡片

### 委托 paper-import

非 folder_slug、非本地 PDF 的输入，agent 应：

1. 调用 `paper-import` skill，传入用户的论文引用
2. paper-import 完成 search → acquire 后，获得 folder_slug
3. 用该 folder_slug 继续生成卡片

### Windows 兼容性注意事项

在 Windows 上执行 paper-acquire / pdf-to-md 的 bash 命令时：
- 设置 `PYTHONIOENCODING=utf-8` 环境变量避免 GBK 编码错误
- 确保 `MINERU_API_TOKEN` 在当前 shell session 中可用（检查 `$env:MINERU_API_TOKEN` 或 `os.environ`）
- Windows 上 `python3` 可能不存在，使用 `python` 替代

## Workflow

### Step 0: Input Resolution

检测输入类型并确保前置条件满足（详见 Input Handling）。

完成后，以下文件必须存在：
- `$PAPERS_DIR/{folder_slug}/metadata.yaml`
- `$PAPERS_DIR/{folder_slug}/paper/paper.md`

### Step 1: Load paper content and metadata

Read both files:

- `$PAPERS_DIR/{folder_slug}/metadata.yaml` — for frontmatter (title, authors, year, venue, url, code, tags)
- `$PAPERS_DIR/{folder_slug}/paper/paper.md` — full paper text

### Step 2: Dispatch two subagents in parallel

Launch both subagents simultaneously. Each reads the full `paper.md` independently.

**Subagent 1 — Structure Extractor** (`references/subagent-structure.md`):
Extracts factual, verifiable content: problem definition, method pipeline, experimental setup, results, datasets, baselines.

**Subagent 2 — Evaluation Extractor** (`references/subagent-evaluation.md`):
Extracts judgmental content: claim verification, evidence quality, limitations, novelty assessment, soundness, reproducibility concerns.

Each subagent outputs a structured JSON object. Read their reference files for the exact schemas.

### Step 3: Synthesize and fill templates

The main agent combines both subagent outputs:

1. **Frontmatter**: Fill from `metadata.yaml` + subagent-derived fields (tags, builds_on, contrasts_with, ratings)
2. **Quick card**: Fill `templates/paper-card-quick.md` using synthesis
3. **Deep card**: Fill `templates/paper-card-deep.md` using synthesis

**Synthesis rules**:

- For factual claims (method, results): if both subagents agree → high confidence; if they disagree → use the more conservative/verifiable version
- For judgments (novelty, soundness): average the two assessments, round to nearest integer star rating
- For limitations: merge both lists, deduplicate
- For tags: combine both subagents' tag suggestions, deduplicate

### Step 4: Write output files

Write to:

- `$PAPERS_DIR/{folder_slug}/card.md`
- `$PAPERS_DIR/{folder_slug}/card-deep.md`

Both files should be self-contained Markdown with YAML frontmatter.

### Language

卡片输出语言由 `--lang` 参数决定。未指定时跟随用户对话语言（用户用中文提问则输出中文，用英文则输出英文）。

语言规则：
- **保持原文**（不翻译）：frontmatter 的 title / authors / venue / url / code
- **跟随 --lang**：section headers、分析正文（TL;DR、Problem、Method、Result、Limitation、Takeaway、Verdict）、tags / builds_on / contrasts_with / verdict
- **技术术语保持英文**：方法名（Transformer、BERT、GAT）、数据集（CIFAR-10、ImageNet）、指标（mAP、BLEU、F1）、架构组件（attention head、MLP、GNN layer）

模板文件保持英文不变。agent 在生成卡片时根据语言指令翻译 section headers 和正文内容。

## Templates

- [Quick card template](templates/paper-card-quick.md)
- [Deep card template](templates/paper-card-deep.md)

Read the templates before filling them. Preserve all section headers and structure exactly.

## Subagent Reference Files

- [Structure Extractor schema](references/subagent-structure.md)
- [Evaluation Extractor schema](references/subagent-evaluation.md)

Read these before dispatching subagents.

## Integration

This skill runs after `paper-acquire` (which runs after `paper-search`).

Use `paper-import` for end-to-end workflow including card generation.
