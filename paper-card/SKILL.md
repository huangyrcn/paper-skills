---
name: paper-card
description: >
  把一篇论文拆解成结构化研究卡片。
  当用户说"做个卡片"、"写阅读笔记"、"总结这篇论文"、
  "帮我读一下"、"结构化分析"、"拆解论文"时触发。
  输出 card.md（快速概览）和 card-deep.md（深度分析）。
argument-hint: "<folder_slug>"
---

# Paper Card

Generate structured research cards from an acquired paper.

## Ownership

This skill owns:

- `$PAPERS_DIR/{folder_slug}/card.md` — quick card
- `$PAPERS_DIR/{folder_slug}/card-deep.md` — deep card

This skill does **not**:

- Download PDF or normalize paper (use `paper-acquire`)
- Resolve paper identity (use `paper-resolve`)
- Discover code repositories (use `paper-repo`)
- Modify `metadata.yaml`

## Prerequisites

Before running paper-card, the paper must have:

- `$PAPERS_DIR/{folder_slug}/metadata.yaml` (from `paper-resolve`)
- `$PAPERS_DIR/{folder_slug}/paper/paper.md` (from `paper-acquire`)

If these are missing, run the upstream skills first.

## Workflow

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

## Templates

- [Quick card template](../templates/paper-card-quick.md)
- [Deep card template](../templates/paper-card-deep.md)

Read the templates before filling them. Preserve all section headers and structure exactly.

## Subagent Reference Files

- [Structure Extractor schema](references/subagent-structure.md)
- [Evaluation Extractor schema](references/subagent-evaluation.md)

Read these before dispatching subagents.

## Integration

This skill runs after `paper-acquire` (which runs after `paper-resolve`).

Use `paper-pipeline` for end-to-end workflow including card generation.
