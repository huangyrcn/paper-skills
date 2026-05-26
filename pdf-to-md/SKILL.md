---
name: pdf-to-md
description: >
  PDF 转高质量 markdown，支持公式、表格、混合排版。
  当用户要求 PDF 转 markdown、提取论文文本、OCR 提取时触发。
  注意：paper-acquire 内部会调用它，不需要单独触发。
argument-hint: "<pdf_path> [-l lang]"
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
