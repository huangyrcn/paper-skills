---
name: pdf-to-md
description: >
  When: 有一个 PDF 文件需要转成 markdown。
  How: 调用 MinerU API VLM 管线，处理公式、表格、混合排版。
  Output: 与 PDF 同目录的 `.md` 文件和 `_images/` 文件夹。
argument-hint: "<pdf_path> [-l lang]"
allowed-tools: Bash
---

# PDF to Markdown

Converts a PDF to:

```text
<pdf_stem>.md
<pdf_stem>_images/
```

## Prerequisite

Set the MinerU API token:

```bash
export MINERU_API_TOKEN="your_token_here"
```

## Usage

```bash
python3 "${SKILL_DIR}/scripts/mineru-api.py" <pdf_path> [-l lang]
```

- `pdf_path`: local PDF path
- `-l lang`: language hint, `en` or `ch`

## Backend contract

- Supported backend: MinerU API only
- Model: VLM
- Goal: highest available parsing quality for formulas, tables, and mixed-layout academic PDFs

## Output behavior

- Output files are written next to the PDF
- Existing Markdown and image directories for the same stem may be overwritten
- Example: `paper.pdf` -> `paper.md` and `paper_images/`
