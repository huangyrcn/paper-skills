# Academic Paper Search APIs — 完整列表

## 免费 API（无需机构订阅）

| # | 名称 | Base URL | 需要 Key | 覆盖量 | 提供数据 | 速率限制 | 已集成 |
|---|------|----------|----------|--------|----------|----------|--------|
| 1 | **Semantic Scholar** | `api.semanticscholar.org/graph/v1/` | 可选（免费申请，无 key 限流严重） | 200M+ 论文 | 元数据、摘要、作者、引用、TLDR、S2 ID | 无 key: ~1 req/s; 有 key: ~10 req/s | ✅ |
| 2 | **OpenAlex** | `api.openalex.org/` | 可选（免费，$1/day 额度） | 450M+ 作品 | 元数据、摘要、作者、机构、OA 状态、引用 | 免费额度覆盖绝大多数学术用途 | ✅ |
| 3 | **Crossref** | `api.crossref.org/works/` | 否（`mailto` 进 polite pool 10x 快） | 180M+ DOI | 元数据、作者、摘要、引用、出版商 | polite pool 无硬限制 | ✅ |
| 4 | **arXiv** | `export.arxiv.org/api/query` | 否 | 2M+ 预印本 | 元数据、摘要、分类 | 1 req/3s | ✅ |
| 5 | **PubMed (E-utilities)** | `eutils.ncbi.nlm.nih.gov/entrez/eutils/` | 可选（免费注册提额） | 36M+ 生物医学 | 元数据、摘要、MeSH 词 | 未注册 ~3 req/s; 注册 ~10 req/s | ✅ |
| 6 | **DBLP** | `dblp.org/search/publ/api` | 否 | 6M+ CS 论文 | 规范化 venue、作者、DBLP key | ~1 req/2s | ✅ |
| 7 | **CORE** | `api.core.ac.uk/v3/` | 是（免费注册） | 300M+ OA 论文 | 元数据、全文（部分） | 未公开 | ❌ |
| 8 | **DataCite** | `api.datacite.org/dois/` | 否 | 研究数据集 DOI | 数据集元数据、创建者、关联标识符 | 未公开 | ❌ |
| 9 | **OpenCitations (COCI)** | `opencitations.net/` | 否 | 1.09B 引用链接 | DOI→DOI 引用关系 | 未公开 | ❌ |
| 10 | **Unpaywall** | `api.unpaywall.org/` | 否（需 email） | 数千万 OA 论文 | OA 状态、合法 PDF URL | 大量使用可能限流 | ❌ |
| 11 | **NASA ADS** | `api.adsabs.harvard.edu/` | 是（免费注册） | 14M+ 天文物理 | 元数据、引用、含 arXiv 预印本 | 未公开 | ❌ |
| 12 | **ORCID** | `pub.orcid.org/v3.0/` | 否（公开读取） | 20M+ 研究者 | 研究者档案、作品列表、机构 | 未公开 | ❌ |
| 13 | **Lens.org** | `api.lens.org/` | 是（免费注册） | 专利 + 学术 | 专利和学术文献元数据 | 有频率限制 | ❌ |

## 商业 API（需机构订阅）

| # | 名称 | 需要 Key | 覆盖量 | 提供数据 | 免费替代 |
|---|------|----------|--------|----------|----------|
| 14 | **Scopus** (Elsevier) | 机构订阅 | 100M+ | 摘要、引用、作者、机构 | OpenAlex |
| 15 | **Web of Science** (Clarivate) | 机构订阅 | 90M+ | SCI/SSCI/A&HCI 引用 | OpenAlex |
| 16 | **Dimensions** | 机构订阅 | 136M+ 论文 + 154M 专利 + 7M 基金 | 跨实体统一查询 | OpenAlex |
| 17 | **Altmetric.com** | 商业 | 替代计量 | 社交媒体/新闻/政策提及 | — |

## 特殊用途

| # | 名称 | 类型 | 说明 |
|---|------|------|------|
| 18 | **Google Scholar** | 无官方 API | 最全但需爬虫（SerpAPI/SearchAPI 付费代理） |
| 19 | **IEEE Xplore** | 机构订阅 | 5M+ IEEE/IET 文献 |
| 20 | **ACM Digital Library** | 机构订阅 | ACM 全文 |
| 21 | **Springer Nature** | 部分开放 | OA API 可获取 280K+ OA 文章 |
| 22 | **ScienceDirect** (Elsevier) | 机构订阅 | Elsevier 全文 |
| 23 | **PMC** | 免费 API | `eutils.ncbi.nlm.nih.gov/` 下的 EFetch，全文 PDF |

## 按领域推荐

| 领域 | 首选 API | 补充 |
|------|----------|------|
| CS / AI | Semantic Scholar + DBLP + arXiv | OpenAlex |
| 生物医学 | PubMed + PMC | OpenAlex |
| 通用学术 | OpenAlex + Crossref | Semantic Scholar |
| 物理 / 数学 | arXiv + NASA ADS | OpenAlex |
| 天文 | NASA ADS | arXiv |
| 研究数据 | DataCite | OpenAlex |
| 引用分析 | OpenCitations + Semantic Scholar | OpenAlex |
| OA 全文 | CORE + Unpaywall | PMC |
