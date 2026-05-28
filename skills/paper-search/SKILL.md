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

## Tools

This skill uses two types of tools:

| Tool | Role |
|------|------|
| 网页搜索工具（如 web-kit） | Web search to locate/verify paper identity and extract venue info |
| `paper-search` CLI | Query 23 academic sources for structured metadata (IDs, authors, abstract) |

## Pipeline

```
Any input (title / DOI / arXiv / URL / description)
  |
  v
Step 1: 网页搜索（mandatory for all inputs）
  - Locate or verify the paper
  - Extract venue info (OpenReview, conference pages, DBLP listings)
  |
  v
Step 2: paper-search CLI (progressive, layered)
  - Layer 1: arxiv,semantic,crossref → basic identity
  - Layer 2 (if no venue): dblp,openalex → venue supplement
  - Layer 3 (if still no venue): all sources
  |
  v
Step 3: Merge + resolve conflicts
  - Year: from CLI bib sources only
  - Venue: 网页搜索 primary, CLI extra field supplement
  - IDs/Authors/Abstract: CLI (structured) > 网页搜索
  |
  v
Step 4: resolve_metadata.py → metadata.yaml
```

## 前置条件

### 1. 安装 paper-search CLI

```bash
# 检查是否已安装
paper-search sources 2>/dev/null || paper-search --version 2>/dev/null

# 未安装则执行
uv tool install paper-search-mcp --from "git+https://github.com/openags/paper-search-mcp.git"
```

### 2. 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PAPERS_DIR` | 论文存储根目录 | `~/docs/papers` |
| `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | Unpaywall 必须 | — |
| `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | 提高 S2 限速 | — |

## Step 1: 网页搜索（所有输入必做）

所有输入都先用网页搜索确认。这一步的目的：
1. 定位或验证论文身份
2. 提取 venue 信息（OpenReview 页面、会议 virtual page、DBLP 列表）
3. 对于模糊输入（DOI/arXiv/URL/描述），解析出具体论文

### 搜索策略

| 输入类型 | 网页搜索方式 |
|---------|------------|
| 标题 | 网页搜索 "{title}" |
| DOI | 网页搜索 "{doi}" |
| arXiv ID | 网页搜索 "arxiv {arxiv_id}" |
| URL | 网页抓取直接读取页面内容 |
| 方法名 | 网页搜索 "{method} paper" → 推断论文标题，可能需问用户上下文 |
| 自然语言描述 | 网页搜索 "{description}" → 用户确认是哪篇 |
| 本地 PDF | 先检查 `$PAPERS_DIR` 是否已有该文件，已存在则直接读取 metadata.yaml |

### 从搜索结果提取

重点关注：
- **OpenReview 链接**：`openreview.net/forum?id=xxx` → 确认论文在 OpenReview 上
- **会议 virtual page**：`iclr.cc/virtual/2026/poster/xxx` → 确认被会议收录
- **DBLP 列表**：DBLP 搜索结果中的 venue 和 year
- **论文标题和作者**：验证身份

## Step 2: paper-search CLI（渐进式分层）

用 Step 1 确定的论文标题，调用 CLI 查结构化学术元数据。

### CLI 命令

```bash
paper-search search "<query>" [-n 5] [-s arxiv,semantic,crossref] [-y 2020-2024]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `query` | — | 搜索关键词（必填） |
| `-n, --max-results` | 5 | 每个源最多返回条数 |
| `-s, --sources` | all | 逗号分隔的源名称 |
| `-y, --year` | — | 年份过滤（仅 Semantic Scholar） |

### 渐进式源策略

**Layer 1** — 基本身份（始终执行）：
```bash
paper-search search "<title>" -s arxiv,semantic,crossref -n 3
```

**Layer 2** — 如果 Layer 1 没找到 venue，补充 venue-aware 源：
```bash
paper-search search "<title>" -s dblp,openalex -n 3
```

**Layer 3** — 如果 Layer 2 也没找到 venue，全量搜索：
```bash
paper-search search "<title>" -n 5
```

**"没找到 venue" 的判定**：以下情况视为没找到，需要进入下一层：
- CLI 结果中 `venue` 字段为空
- CLI `extra` 中 venue 为 `"CoRR"`（arXiv 预印本标记，不算正式 venue）
- 网页搜索 Step 1 已找到 venue（如 OpenReview/会议页面）→ CLI 只需 Layer 1 获取 IDs，不需要继续

### 解析 CLI `extra` 字段

venue 信息在 CLI 输出的 `extra` 字段里（字符串形式的 dict），需要解析：

| 源 | `extra` 中的 key | 示例 |
|----|-----------------|------|
| DBLP | `venue` | `{'venue': 'ICLR', 'year': '2020'}` |
| Crossref | `container_title` | `{'container_title': 'Neurocomputing', 'publisher': 'Elsevier'}` |

**注意**：DBLP 可能对已录取的论文仍显示 `venue: 'CoRR'`（arXiv 预印本标记），此时以 Step 1 网页搜索的 venue 为准。

## Step 3: 合并与冲突解决

### Year（年份）

**Year 完全由 CLI 的 bib 源决定**，按以下优先级：

1. DBLP `extra` 中的 `year`
2. Crossref `published_date`
3. OpenAlex `published_date`
4. arXiv `published_date`（首次提交日期）

**arXiv 的 `updated_date` 忽略不用**——只用 `published_date`（首次提交年份）。
网页搜索的 year 仅作参考，不参与决策。

**tiebreaker**：对于未正式发表的 arXiv 预印本，如果多个源返回不同年份，取较新年份。已发表论文以 venue 年份为准，不存在 tiebreaker。

### Venue（发表场所）

- **网页搜索是 venue 的主要来源**（OpenReview、会议 virtual page、会议程序册）
- CLI `extra` 字段作为补充（DBLP `venue` key、Crossref `container_title`）
- 如果 DBLP 显示 `CoRR` 但网页搜索找到会议页面，以网页搜索为准

### 其他字段

- **IDs**（doi, arxiv, openalex, dblp, pmid）：CLI 结构化数据 > 网页搜索
- **Authors**：CLI > 网页搜索（网页搜索可能截断）
- **Abstract**：CLI > 网页搜索（网页搜索可能截断）

## Step 4: 生成 metadata.yaml

### 组装 JSON

从搜索结果中组装 JSON 传给脚本：

```json
{
  "title": "论文标题",
  "authors": ["Author One", "Author Two"],
  "year": 2026,
  "venue": "ICLR",
  "method": "transformer",
  "doi": "10.xxx/xxx",
  "arxiv": "2504.07097",
  "pmid": "12345678",
  "dblp": "conf/iclr/...",
  "openalex": "W123456",
  "abstract": "...",
  "pdf_url": "https://...",
  "confidence": "high",
  "year_sources": {"dblp": 2026, "arxiv": 2025},
  "publication_status": "accepted",
  "venue_context": "International Conference on Learning Representations 2026",
  "openreview": "https://openreview.net/forum?id=xxx"
}
```

### publication_status 推断

| 证据 | publication_status |
|------|-------------------|
| 网页搜索找到会议 virtual page 或 OpenReview poster/oral/spotlight | `"accepted"` |
| DBLP key 在会议下（不是 CoRR） | `"published"` |
| Crossref DOI 指向期刊/会议 | `"published"` |
| 只有 arXiv / DBLP 显示 CoRR / 无 venue | `"unknown"` |

### 调用脚本

```bash
echo '{"title":"...","authors":["A"],"year":2020,"publication_status":"accepted","venue_context":"...","openreview":"https://..."}' | \
  uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" --from-json --out "$PAPERS_DIR"
```

**关于 `method` 字段：**
- 从标题和摘要推断方法名。例如 "Attention Is All You Need" → `"transformer"`
- 如果标题没有明确的方法名，省略 `method` 字段，脚本会用标题第一个有意义的词兜底

脚本自动生成：
- `folder_slug`：`{venue}{year}-{method}-{first_author}`
- `$PAPERS_DIR/{folder_slug}/metadata.yaml`

## CLI 其他命令

```bash
paper-search download <source> <paper_id> [-o ./downloads]   # 由 paper-acquire 处理
paper-search read <source> <paper_id> [-o ./downloads]        # 由 paper-acquire 处理
paper-search sources                                          # 列出可用源
```

## 可用源（23 个）

免费（21）：`arxiv`, `pubmed`, `biorxiv`, `medrxiv`, `google_scholar`, `iacr`, `semantic`, `crossref`, `openalex`, `pmc`, `core`, `europepmc`, `dblp`, `openaire`, `citeseerx`, `doaj`, `base`, `zenodo`, `hal`, `ssrn`, `unpaywall`

付费可选：`ieee`（需 `IEEE_API_KEY`）, `acm`（需 `ACM_API_KEY`）

## references

| 文件 | 内容 |
|------|------|
| [folder-slug.md](references/folder-slug.md) | folder_slug 格式规范 |
| [metadata-schema.md](references/metadata-schema.md) | metadata.yaml 输出 schema |
