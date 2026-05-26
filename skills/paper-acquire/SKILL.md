---
name: paper-acquire
description: >
  获取论文原文：下载 PDF 并转成结构化 markdown。
  当用户要求下载论文、获取 PDF、把论文转成 markdown 时触发。
  也作为 paper-search 的下游自动步骤——确定了论文身份后自动获取原文。
argument-hint: "<folder_slug> | <metadata_path>"
---

# Paper Acquire

Hydrate the canonical raw bundle for a resolved paper.

## Ownership

This skill owns:

- `$PAPERS_DIR/{folder_slug}/metadata.yaml` (extends with assets, normalization)
- `$PAPERS_DIR/{folder_slug}/paper/paper.pdf`
- `$PAPERS_DIR/{folder_slug}/paper/paper.md`
- `$PAPERS_DIR/{folder_slug}/paper/paper_images/`

This skill does **not**:
- Resolve paper identity from a title/DOI/URL (use `paper-search`)
- Write the final reading note (use `paper-card`)
- Perform full repository discovery and verification (use `paper-repo`)
- Modify `identity` or `bibliography` sections in metadata.yaml

Note: The `hydrate_raw.py` script does not perform repository discovery. Use `paper-repo` for that.

## Workflow

### 1. Start from a resolved metadata bundle

**必须先有 `metadata.yaml`**（由 `paper-search` 产出）。

如果用户只给了一个模糊引用，先用 `paper-search`。

读取 metadata.yaml，提取对 acquire 有用的信息：

```yaml
# 从 metadata.yaml 提取
identifiers:
  arxiv: "1704.01212"        # → arXiv PDF
  pmcid: "PMC11399094"       # → PMC 全文 PDF
  semantic_scholar: "..."    # → S2 openAccessPdf
  doi: "10.xxx"              # → 出版商 PDF

urls:
  pdf: "https://..."         # → 直接下载 URL
  pmc: "https://pmc..."      # → PMC 页面，提取 PDF
```

### 2. PDF Acquisition (Priority Order)

按以下优先级下载 PDF：

| 优先级 | 来源 | 条件 | URL 模式 |
|---|---|---|---|
| **1** | arXiv PDF | `identity.aliases.arxiv` 存在 | `https://arxiv.org/pdf/{arxiv_id}.pdf` |
| **2** | PMC PDF | `identity.aliases.pmcid` 存在 | 从 `urls.pmc` 页面提取 |
| **3** | Semantic Scholar | `urls.pdf` 来自 S2 | 直接用 `urls.pdf` |
| **4** | Unpaywall | `identity.aliases.doi` 存在 | 通过 Unpaywall API 查询 oa 地址 |
| **5** | 出版商 PDF | `identity.aliases.doi` 存在 | `https://doi.org/{doi}` 重定向 |

**下载流程**：

```bash
# 优先级 1: arXiv (免费)
if identity.aliases.arxiv exists:
  wget "https://arxiv.org/pdf/${arxiv_id}.pdf" -O paper/paper.pdf

# 优先级 2: PMC (免费全文)
if identity.aliases.pmcid exists:
  # PMC 页面通常有 PDF 链接
  crwlr crawl -o md "${urls.pmc}"  # 提取 PDF URL
  wget "${pmc_pdf_url}" -O paper/paper.pdf

# 优先级 3: Semantic Scholar openAccessPdf
if urls.pdf exists and looks like S2/pdfs.semanticscholar.org:
  wget "${urls.pdf}" -O paper/paper.pdf

# 优先级 4: Unpaywall (免费开放获取)
if identity.aliases.doi exists and no PDF yet:
  # Unpaywall API: https://api.unpaywall.org/v2/{doi}?email=...
  oa_url=$(curl -s "https://api.unpaywall.org/v2/${doi}?email=${PAPER_SEARCH_MCP_UNPAYWALL_EMAIL}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('best_oa_location',{}).get('url_for_pdf',''))")
  if [ -n "$oa_url" ]; then
    wget "$oa_url" -O paper/paper.pdf
  fi

# 优先级 5: 出版商 PDF (可能需要认证)
if identity.aliases.doi exists and no PDF yet:
  # 尝试 wget，可能需要 cdp-download 处理认证
  wget "https://doi.org/${doi}" -O paper/paper.pdf || \
  ${SKILL_DIR}/../web-kit/scripts/cdp-download "https://doi.org/${doi}" paper/paper.pdf
```

**为什么这个优先级**：

1. **arXiv 最优先**：免费 + 无认证
2. **PMC 其次**：免费全文
3. **S2 openAccessPdf**：免费开放获取
4. **Unpaywall**：聚合多个 OA 来源，免费
5. **出版商最后**：可能需要订阅/认证

### 3. Normalization (PDF → Markdown)

使用 `pdf-to-md` skill 的 MinerU 进行转换：

```bash
# PDF → MinerU
python3 "${SKILL_DIR}/../pdf-to-md/scripts/mineru-api.py" paper/paper.pdf -l en
# 输出: paper/paper.md + paper/paper_images/
```

### 4. Update metadata.yaml

完成 acquisition 后，更新 metadata.yaml 的 `assets` 和 `normalization` 部分：

```yaml
assets:
  paper_pdf:
    path: "paper/paper.pdf"
    size_bytes: 2950183
    source: "arxiv"  # 或 "pmc", "semantic_scholar", "publisher"
  paper_md:
    path: "paper/paper.md"
    backend: "mineru_vlm"
    generated_at: "2026-04-13"
  paper_images:
    path: "paper/paper_images/"
    count: 12

normalization:
  backend: "mineru_vlm"
  completed_at: "2026-04-13"
```

## Storage Rules

Read [references/raw-layout.md](references/raw-layout.md) for directory structure.

## Scripts

### hydrate_raw.py

一键完成 acquire 全流程：下载 PDF、获取 LaTeX（如有）、生成 paper.md、记录 repo hints。

```bash
python3 "${SKILL_DIR}/scripts/hydrate_raw.py" \
  --metadata "$PAPERS_DIR/{folder_slug}/metadata.yaml" \
  --md-lang en
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--metadata, -m` | metadata.yaml 路径（必填） | — |
| `--md-lang` | PDF 转 markdown 语言提示 | `en` |
| `--skip-pdf` | 跳过 PDF 下载 | 不跳过 |
| `--skip-latex` | 跳过 LaTeX 下载 | 不跳过 |
| `--skip-normalize` | 跳过 paper.md 生成 | 不跳过 |

脚本自动处理 LaTeX → pandoc 优先、PDF → MinerU 回退的 normalization 策略。
仓库搜索由 `paper-repo` 负责，本脚本不处理。

适合需要一次性完成所有步骤的场景；如果需要逐步控制（如只下载 PDF 不转 markdown），按上面的手动流程操作。

## Dependencies

- `web-kit` skill — wget, cdp-download, crwlr
- `pdf-to-md` skill — MinerU API PDF conversion

## References

| 文件 | 用途 |
|---|---|
| [raw-layout.md](references/raw-layout.md) | 目录结构规范 |
| [acquisition-workflow.md](references/acquisition-workflow.md) | 详细 acquisition 流程 |
| [paper-normalization.md](references/paper-normalization.md) | normalization 策略 |