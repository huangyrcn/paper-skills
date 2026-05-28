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

- PDF-to-Markdown conversion
- Output: `<pdf_stem>.md` and `<pdf_stem>_images/`

This skill does **not**:

- Download PDFs (use `paper-acquire`)
- Manage paper metadata (use `paper-search`)
- Generate reading notes (use `paper-card`)

## Conversion backends

| 优先级 | 后端 | 需要 | 质量 |
|--------|------|------|------|
| 1 | MinerU API (VLM) | `MINERU_API_TOKEN` | 最高（公式/表格/混合排版） |
| 2 | marker (本地) | `uv tool install marker-pdf` | 高（本地推理，无需 API） |

`hydrate_raw.py` 自动按优先级尝试：有 token 用 MinerU，没有则 fallback 到 marker。

## Usage

```bash
# MinerU API（需要 MINERU_API_TOKEN）
python3 "${SKILL_DIR}/scripts/mineru-api.py" <pdf_path> [-l lang]

# marker 本地（不需要 token）
marker <pdf_path> --output_dir <output_dir>
```

## Output behavior

- Output files are written next to the PDF
- Example: `paper.pdf` → `paper.md` and `paper_images/`

## Error handling

| Condition | Behavior |
|-----------|----------|
| `MINERU_API_TOKEN` not set | 自动 fallback 到 marker |
| MinerU API 返回 401/403 | Token 无效，fallback 到 marker |
| marker 未安装 | 报错，提示 `uv tool install marker-pdf` |
| 两个后端都失败 | 报错，列出所有失败原因 |

## Agent 前置检查

在调用 `hydrate_raw.py` 之前，agent 应检查转换能力是否就绪：

1. 有 `MINERU_API_TOKEN` → 直接使用 MinerU API
2. 无 token → 检查 `marker` 是否可用（`which marker`）
3. marker 也不可用 → **主动为用户安装**：`uv tool install marker-pdf`，而非等脚本报错

这样用户无需手动干预，管线可以自动降级运行。
