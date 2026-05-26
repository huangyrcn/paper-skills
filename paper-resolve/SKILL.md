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

本 skill 的脚本通过 `uv run --script` 执行（自动安装依赖，无需手动 pip install）。

检查 uv 是否可用：

```bash
uv --version
```

如果未安装，提示用户安装：


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

### search_identifiers.py

查询学术源，返回结构化标识符。

```bash
uv run --script "${SKILL_DIR}/scripts/search_identifiers.py" "任何查询"
```

自动识别输入类型（DOI、arXiv ID、标题等），按以下顺序查询学术源：
arXiv → Semantic Scholar → OpenAlex → DBLP → Crossref → PubMed。
拿到 DOI 后还会查询 Unpaywall 获取 OA PDF 链接。

输出 JSON 到 stdout，包含：
- `canonical_title` — 确定的论文标题
- `merged` — 合并后的标识符（doi, arxiv, authors, year, venue, ...）
- `sources` — 各源的原始结果

### resolve_metadata.py

从标识符生成 `metadata.yaml`。

```bash
# 通过 CLI 参数
uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" \
  --title "..." --authors "A,B" --year 2020 --venue ICLR \
  --arxiv "2002.05287" --confidence high \
  --out "$PAPERS_DIR"

# 通过 JSON stdin（推荐，从 search_identifiers.py 的 merged 字段传入）
echo '{"title":"...","authors":["A"],"year":2020}' | \
  uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" --from-json --out "$PAPERS_DIR"
```

## 你来决定怎么走

根据输入类型，你自己判断处理路径：

- **有直接标识符**（DOI、arXiv ID、PMID）→ 传给 `search_identifiers.py`，它会直接解析
- **标题** → 直接传给 `search_identifiers.py`，它会跨源搜索
- **URL** → 先判断是学术 URL 还是普通网页。学术 URL 直接传；普通网页可能需要先提取标题
- **方法名** → 需要你推断出论文标题，再传给脚本。可能需要问用户要上下文
- **本地 PDF** → 先检查 `$PAPERS_DIR` 是否已有。没有的话，提取标题再搜索
- **搜索结果不理想** → 尝试换关键词、加上下文、或问用户确认

## references

| 文件 | 内容 |
|------|------|
| [folder-slug.md](references/folder-slug.md) | folder_slug 格式规范 |
| [metadata-schema.md](references/metadata-schema.md) | metadata.yaml 输出 schema |
| [source-metadata-mapping.md](references/source-metadata-mapping.md) | 各学术源字段映射 |
