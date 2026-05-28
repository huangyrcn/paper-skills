---
name: paper-search
description: >
  搜索论文并解析论文身份，生成结构化 metadata.yaml。
  当用户要搜论文、找文献、确认论文身份（标题/DOI/arXiv ID/URL）、
  查论文信息、做论文 metadata 时触发。
  不负责下载 PDF 或转 markdown（那是 paper-acquire 的工作）。
  覆盖 20+ 学术源（arXiv、PubMed、Semantic Scholar、Crossref、OpenAlex、DBLP、Unpaywall 等）。
  如果用户想要"导入论文"或"下载论文"，应使用 paper-import skill。
argument-hint: "<query> [-s sources] [-n max]"
---

# Paper Search

搜索论文并解析论文身份，生成结构化 metadata.yaml。

## Ownership

This skill owns:

- `$PAPERS_DIR/{folder_slug}/metadata.yaml` (identity, bibliography, urls, acquisition_hints sections)

This skill does **not**:

- Download PDF or convert to markdown (use `paper-acquire`)
- Generate reading notes (use `paper-card`)
- Discover code repositories (use `paper-repo`)

## 前置条件

### 1. 安装 paper-search CLI

```bash
# 检查是否已安装
paper-search sources 2>/dev/null || paper-search --version 2>/dev/null

# 未安装则执行
uv tool install paper-search-mcp --from "git+https://github.com/openags/paper-search-mcp.git"
```

如果 `uv` 也未安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PAPERS_DIR` | 论文存储根目录 | `~/docs/papers` |
| `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | Unpaywall 必须 | — |
| `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | 提高 S2 限速 | — |

`PAPERS_DIR` 未设置时默认 `~/docs/papers`。metadata.yaml 写入 `$PAPERS_DIR/{folder_slug}/metadata.yaml`。

## CLI 命令

### search — 搜索论文

```bash
paper-search search "<query>" [-n 5] [-s arxiv,semantic,crossref] [-y 2020-2024]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `query` | — | 搜索关键词（必填） |
| `-n, --max-results` | 5 | 每个源最多返回条数 |
| `-s, --sources` | all | 逗号分隔的源名称 |
| `-y, --year` | — | 年份过滤（仅 Semantic Scholar） |

**推荐源组合：**
- 通用搜索：`-s arxiv,semantic,dblp,crossref,pubmed,openalex`
- 生物医学：`-s pubmed,pmc,europepmc,biorxiv`
- 快速定位：`-s semantic,crossref`（覆盖面广）

### download — 下载 PDF

```bash
paper-search download <source> <paper_id> [-o ./downloads]
```

### read — 提取全文

```bash
paper-search read <source> <paper_id> [-o ./downloads]
```

### sources — 列出可用源

```bash
paper-search sources
```

Note: The `download` and `read` subcommands are provided by the CLI but are not used by this skill. PDF download is handled by `paper-acquire`.

## 生成 metadata.yaml

搜索到论文后，用 `resolve_metadata.py` 生成结构化 metadata。

### 从 paper-search 结果组装 JSON

从搜索结果中提取以下字段，组装成 JSON 传给脚本：

```json
{
  "title": "论文标题",
  "authors": ["Author One", "Author Two"],
  "year": 2020,
  "venue": "ICLR",
  "method": "transformer",
  "doi": "10.xxx/xxx",
  "arxiv": "2002.05287",
  "pmid": "12345678",
  "dblp": "conf/iclr/...",
  "openalex": "W123456",
  "abstract": "...",
  "pdf_url": "https://...",
  "confidence": "high",
  "year_sources": {"crossref": 2024, "semantic": 2025}
}
```

### 年份冲突处理

多个源返回不同年份时，按以下优先级选择 `year`：

1. **venue 名称中的年份**（如 "IJCAI 2025"），以 venue 年份为准
2. **官方出版物页面**（OpenReview、ACM DL、IEEE Xplore 等）确认的年份
3. **arXiv**：用会议年份而非上传年份（arXiv 通常早一年）
4. **多数投票**：超过半数源一致的年份
5. **取较新年份**：无法判断时取较新值

将各源原始年份记入 `year_sources`（可选字段，脚本用它做交叉校验）。

### 调用脚本

```bash
echo '{"title":"...","authors":["A"],"year":2020}' | \
  uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" --from-json --out "$PAPERS_DIR"
```

**关于 `method` 字段：**
- 你从标题和摘要推断方法名。例如 "Attention Is All You Need" → `"transformer"`，"Geom-GCN: ..." → `"geom-gcn"`
- 如果标题没有明确的方法名，省略 `method` 字段，脚本会用标题第一个有意义的词兜底
- 推断不出就不要硬编，让脚本自动处理

脚本自动生成：
- `folder_slug`：`{venue}{year}-{method}-{first_author}`
- `$PAPERS_DIR/{folder_slug}/metadata.yaml`：完整的 identity、bibliography、urls、acquisition_hints

## 输入类型处理

| 用户输入 | 处理方式 |
|---------|---------|
| 标题 | `paper-search search "标题"` |
| DOI | `paper-search search "DOI" -s crossref,semantic` 或直接传给 resolve_metadata.py |
| arXiv ID | `paper-search search "arXiv ID" -s arxiv` |
| 方法名 | 先推断论文标题，再搜索。可能需要问用户要上下文 |
| URL | 先判断学术 URL 还是普通网页。学术 URL 提取标题搜索 |
| 本地 PDF | 先检查 `$PAPERS_DIR` 是否已有 |

## 可用源（23 个）

免费（21）：`arxiv`, `pubmed`, `biorxiv`, `medrxiv`, `google_scholar`, `iacr`, `semantic`, `crossref`, `openalex`, `pmc`, `core`, `europepmc`, `dblp`, `openaire`, `citeseerx`, `doaj`, `base`, `zenodo`, `hal`, `ssrn`, `unpaywall`

付费可选：`ieee`（需 `IEEE_API_KEY`）, `acm`（需 `ACM_API_KEY`）

## references

| 文件 | 内容 |
|------|------|
| [folder-slug.md](references/folder-slug.md) | folder_slug 格式规范 |
| [metadata-schema.md](references/metadata-schema.md) | metadata.yaml 输出 schema |
