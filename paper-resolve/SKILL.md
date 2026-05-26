---
name: paper-resolve
description: >
  确定用户提到的论文具体是哪篇，解析出所有标识符。
  当用户给出论文标题、DOI、arXiv 链接/ID、OpenReview URL、
  出版商链接、模糊描述、方法名（如 GAT、BERT）时触发。
  即使用户没有明确说"帮我查"，只要上下文涉及一篇尚未解析的论文，就应该先用这个 skill。
argument-hint: "<论文引用>"
---

# Paper Resolve

确定用户指的是哪篇论文，收集全部标识符，生成 `metadata.yaml`。

## 前置条件

本 skill 依赖 `paper-search` CLI 工具。

检查是否已安装：

```bash
paper-search --version 2>/dev/null || paper-search sources 2>/dev/null
```

如果未安装：

```bash
uv tool install paper-search-mcp --from "git+https://github.com/openags/paper-search-mcp.git"
```

如果 `uv` 也未安装，先装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 你可能收到的输入

| 类型 | 示例 |
|------|------|
| 标题 | "Attention Is All You Need" |
| DOI | "10.48550/arxiv.2002.05287" |
| arXiv ID / URL | "2002.05287" 或 `arxiv.org/abs/2002.05287` |
| OpenReview URL | `openreview.net/forum?id=SkgBfaNKPr` |
| 出版商 URL | `nature.com/articles/...` |
| 方法名 | "GAT"、"BERT"、"MManiST" |
| 本地 PDF | `~/papers/foo.pdf` |

## 你需要产出

`$PAPERS_DIR/{folder_slug}/metadata.yaml`

其中 `folder_slug` 格式为 `{venue}{year}-{method}-{first_author}`（如 `iclr2020-geom-gcn-pei`）。

## 可用工具

### paper-search CLI

搜索学术源，返回结构化 JSON。

```bash
# 搜索标题（查询所有源）
paper-search search "Attention Is All You Need" -n 3

# 指定源
paper-search search "Attention Is All You Need" -s arxiv,semantic,dblp,crossref,pubmed,openalex -n 3

# 限制年份
paper-search search "GNN" -s semantic -y 2020-2024 -n 5

# 查看可用源
paper-search sources
```

输出 JSON 包含：`papers` 数组，每个 paper 有 `paper_id`, `title`, `authors`, `abstract`, `doi`, `published_date`, `pdf_url`, `url`, `source`。

### resolve_metadata.py

从标识符生成 `metadata.yaml`（通过 `uv run --script` 执行）。

```bash
# 通过 CLI 参数
uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" \
  --title "..." --authors "A,B" --year 2020 --venue ICLR \
  --arxiv "2002.05287" --confidence high \
  --out "$PAPERS_DIR"

# 通过 JSON stdin
echo '{"title":"...","authors":["A"],"year":2020}' | \
  uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" --from-json --out "$PAPERS_DIR"
```

## 你来决定怎么走

1. **用 paper-search 搜索** — 从结果中提取标题、作者、年份、venue、DOI、arXiv ID 等
2. **组装 JSON** — 把提取的信息组装成 `resolve_metadata.py --from-json` 需要的格式
3. **调 resolve_metadata.py** — 生成 `metadata.yaml`

根据输入类型调整搜索策略：

- **标题** → 直接 `paper-search search "标题"`
- **DOI** → `paper-search search "DOI" -s crossref,semantic` 或直接传给 resolve_metadata.py
- **arXiv ID** → `paper-search search "arXiv ID" -s arxiv`
- **方法名** → 你先推断论文标题，再搜索。可能需要问用户要上下文
- **URL** → 先判断是学术 URL 还是普通网页。学术 URL 可直接提取标题搜索
- **本地 PDF** → 先检查 `$PAPERS_DIR` 是否已有

## references

| 文件 | 内容 |
|------|------|
| [folder-slug.md](references/folder-slug.md) | folder_slug 格式规范 |
| [metadata-schema.md](references/metadata-schema.md) | metadata.yaml 输出 schema |
| [source-metadata-mapping.md](references/source-metadata-mapping.md) | 各学术源字段映射 |
