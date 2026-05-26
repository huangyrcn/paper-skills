---
name: pdf-to-md
description: >
  PDF 转高质量 markdown，支持公式、表格、混合排版。
  当用户要求 PDF 转 markdown、提取论文文本、OCR 提取时触发。
  注意：paper-acquire 内部会调用它，不需要单独触发。
argument-hint: "<pdf_path> [-l lang]"
---

# PDF to Markdown

## Ownership

This skill owns:

- PDF-to-Markdown conversion via MinerU API
- Output: `<pdf_stem>.md` and `<pdf_stem>_images/`

This skill does **not**:

- Download PDFs (use `paper-acquire`)
- Manage paper metadata (use `paper-search`)
- Generate reading notes (use `paper-card`)

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

Check availability:

```bash
python3 "${SKILL_DIR}/scripts/mineru-api.py" --help
```

## Usage

```bash
python3 "${SKILL_DIR}/scripts/mineru-api.py" <pdf_path> [-l lang]
```

- `pdf_path`: local PDF path
- `-l lang`: language hint, `en` or `ch`

## Backend contract

- Supported backend: MinerU API only
- Model: VLM (Vision Language Model)
- Goal: highest available parsing quality for formulas, tables, and mixed-layout academic PDFs
- No local GPU inference — all processing via remote API

## Output behavior

- Output files are written next to the PDF
- Existing Markdown and image directories for the same stem may be overwritten
- Example: `paper.pdf` → `paper.md` and `paper_images/`

## Error handling

| Condition | Behavior |
|-----------|----------|
| `MINERU_API_TOKEN` not set | Script exits with clear error message asking user to set the token |
| API returns 401/403 | Token is invalid or expired — inform user to regenerate |
| API timeout (>5min) | Large PDFs may timeout — suggest splitting or retrying |
| PDF is image-only (scanned) | VLM handles OCR; quality depends on image resolution |
| PDF > 100MB | May hit API limits — warn user and suggest splitting |
| Empty or corrupt PDF | Script exits with error; do not produce empty .md |

## Large file strategy

For PDFs over 50MB or 100+ pages:
- The MinerU API handles large files, but processing time scales with page count
- If the API returns a timeout error, the user can retry or split the PDF
- Do not attempt local fallback — the API-only contract ensures consistent quality

## Integration with paper-acquire

When called from `paper-acquire`, the script is invoked as:

```bash
python3 "${SKILL_DIR}/../pdf-to-md/scripts/mineru-api.py" paper/paper.pdf -l en
```

The output lands in `paper/paper.md` and `paper/paper_images/`.
