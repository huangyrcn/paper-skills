# Acquisition Workflow

paper-acquire 接收 paper-search 产出的 `metadata.yaml`，使用其中的 URLs 和 identifiers 进行下载。

## 整体流程

```
所有论文流程:
1. 下载 PDF (arXiv/PMC/S2/Unpaywall/出版商)
2. PDF → MinerU 转换 (或 LaTeX → pandoc 优先)
```

## PDF 下载优先级

按以下顺序尝试下载，直到成功：

| 优先级 | 数据来源 | metadata 字段 | URL 模式 | 说明 |
|---|--------|--------------|---------|------|
| 1 | arXiv PDF | `identity.aliases.arxiv` | `https://arxiv.org/pdf/{arxiv_id}.pdf` | 免费，无需认证 |
| 2 | PMC PDF | `urls.pmc` | 直接使用 | 免费，全文 PDF |
| 3 | Semantic Scholar OA | `urls.pdf` (S2 来源) | 直接使用 | 免费 open access |
| 4 | Unpaywall | `identity.aliases.doi` | Unpaywall API 查询 | 聚合多个 OA 来源 |
| 5 | 出版商 PDF | `urls.doi` 或 `canonical_url` | 直接使用 | 可能需要认证/付费 |

## Normalization

优先尝试 LaTeX → pandoc，回退到 PDF → MinerU：

```bash
# 如果有 LaTeX 源码
pandoc -f latex+raw_tex -t markdown+tex_math_dollars main.tex -o paper.md

# 否则回退到 MinerU
python3 "${SKILL_DIR}/../pdf-to-md/scripts/mineru-api.py" paper/paper.pdf -l en
# 输出: paper/paper.md + paper/paper_images/
```

## 失败处理

如果所有优先级都失败：

1. 检查 metadata 是否缺少关键字段
2. 使用 `web-kit` skill 的 `ask-search` 搜索其他 PDF 来源
3. 记录失败原因到 `metadata.yaml` 的 `assets.paper_pdf.error` 字段
