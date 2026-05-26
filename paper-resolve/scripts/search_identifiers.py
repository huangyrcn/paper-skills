#!/usr/bin/env python3
"""Search academic sources for paper identifiers.

Takes a query (title, DOI, arXiv ID, URL, or any string) and searches
multiple academic APIs. Returns structured JSON with all found identifiers.

Usage:
  python3 search_identifiers.py "Attention Is All You Need"
  python3 search_identifiers.py "10.48550/arxiv.1706.03762"
  python3 search_identifiers.py "2002.05287"
  python3 search_identifiers.py --from-json '{"title":"...","doi":"..."}'
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("Error: requests library required. pip install requests", file=sys.stderr)
    sys.exit(1)


TITLE_SIM_THRESHOLD = 0.85
USER_AGENT = "paper-resolve/1.0 (search_identifiers)"


# ---------------------------------------------------------------------------
# Title matching utilities

def norm_title(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jacc = len(ta & tb) / max(1, len(ta | tb))
    return 0.5 * (seq + jacc)


# ---------------------------------------------------------------------------
# Input type detection

def detect_input_type(query: str) -> str:
    """Detect what kind of input the query is."""
    q = query.strip()
    # DOI
    if re.match(r"^10\.\d{4,}/", q):
        return "doi"
    # arXiv ID (YYMM.NNNNN or YYMM.NNNNNNN)
    if re.match(r"^\d{4}\.\d{4,7}$", q):
        return "arxiv"
    # URL
    if re.match(r"https?://", q):
        if "arxiv.org" in q:
            return "arxiv_url"
        if "openreview.net" in q:
            return "url"
        if "doi.org" in q:
            return "doi_url"
        return "url"
    # PMID (pure digits, 6-8 chars)
    if re.match(r"^\d{6,8}$", q):
        return "pmid"
    # Everything else: treat as title/method name
    return "title"


def extract_arxiv_id(s: str) -> str:
    """Extract arXiv ID from URL or bare ID."""
    m = re.search(r"(\d{4}\.\d{4,7})", s)
    return m.group(1) if m else s


def extract_doi_from_url(s: str) -> str:
    """Extract DOI from doi.org URL."""
    m = re.match(r"https?://doi\.org/(.+)", s)
    return m.group(1) if m else s


# ---------------------------------------------------------------------------
# HTTP helper with caching and rate limiting

class CachedHTTP:
    def __init__(self, cache_dir: Path, use_cache: bool = True):
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self._last_call: dict[str, float] = {}

    def _cache_path(self, source: str, key: str) -> Path:
        import hashlib
        h = hashlib.sha1(key.encode()).hexdigest()
        d = self.cache_dir / source
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{h}.json"

    def _throttle(self, source: str, min_interval: float):
        if min_interval <= 0:
            return
        now = time.time()
        wait = min_interval - (now - self._last_call.get(source, 0))
        if wait > 0:
            time.sleep(wait)
        self._last_call[source] = time.time()

    def get(self, source: str, url: str, *,
            params: dict | None = None, headers: dict | None = None,
            min_interval: float = 0.0, parse: str = "json") -> dict | None:
        cache_key = url + ("?" + urllib.parse.urlencode(sorted((params or {}).items())) if params else "")
        cpath = self._cache_path(source, cache_key)
        if self.use_cache and cpath.exists():
            try:
                return json.loads(cpath.read_text())
            except Exception:
                pass

        self._throttle(source, min_interval)
        h = {"User-Agent": USER_AGENT, **(headers or {})}
        try:
            r = requests.get(url, params=params, headers=h, timeout=30)
        except requests.RequestException as e:
            print(f"[search] {source} error: {e}", file=sys.stderr)
            return None

        if r.status_code == 429:
            time.sleep(5)
            try:
                r = requests.get(url, params=params, headers=h, timeout=30)
            except requests.RequestException:
                return None
        if r.status_code != 200:
            return None

        data = r.json() if parse == "json" else {"_text": r.text}
        if self.use_cache:
            try:
                cpath.write_text(json.dumps(data, ensure_ascii=False))
            except Exception:
                pass
        return data


# ---------------------------------------------------------------------------
# Source queries

def query_semantic_scholar(http: CachedHTTP, title: str, api_key: str | None) -> dict | None:
    headers = {"x-api-key": api_key} if api_key else {}
    interval = 0.05 if api_key else 1.1
    data = http.get(
        "semantic_scholar",
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": title, "limit": 5,
                "fields": "title,authors,year,venue,externalIds,abstract,tldr"},
        headers=headers, min_interval=interval,
    )
    if not data or not data.get("data"):
        return None
    best, score = None, 0.0
    for h in data["data"]:
        s = title_similarity(title, h.get("title", ""))
        if s > score:
            score, best = s, h
    if not best or score < TITLE_SIM_THRESHOLD:
        return None
    return {
        "source": "semantic_scholar",
        "title": best.get("title", ""),
        "authors": [a.get("name", "") for a in (best.get("authors") or [])],
        "year": best.get("year"),
        "venue": best.get("venue") or "",
        "doi": (best.get("externalIds") or {}).get("DOI"),
        "arxiv": (best.get("externalIds") or {}).get("ArXiv"),
        "pmid": (best.get("externalIds") or {}).get("PubMed"),
        "abstract": best.get("abstract") or "",
        "tldr": ((best.get("tldr") or {}).get("text")) or "",
        "match_score": round(score, 3),
    }


def query_openalex(http: CachedHTTP, title: str, mailto: str) -> dict | None:
    data = http.get(
        "openalex",
        "https://api.openalex.org/works",
        params={"search": title, "per-page": 5, "mailto": mailto},
        min_interval=0.1,
    )
    if not data or not data.get("results"):
        return None
    best, score = None, 0.0
    for h in data["results"]:
        s = title_similarity(title, h.get("title", "") or h.get("display_name", ""))
        if s > score:
            score, best = s, h
    if not best or score < TITLE_SIM_THRESHOLD:
        return None
    abstract = ""
    inv = best.get("abstract_inverted_index")
    if inv:
        n = max((p for ps in inv.values() for p in ps), default=-1) + 1
        words = [""] * n
        for w, ps in inv.items():
            for p in ps:
                if 0 <= p < n:
                    words[p] = w
        abstract = " ".join(w for w in words if w)
    venue = ((best.get("primary_location") or {}).get("source") or {}).get("display_name", "")
    return {
        "source": "openalex",
        "title": best.get("title") or best.get("display_name") or "",
        "authors": [(a.get("author") or {}).get("display_name", "")
                    for a in (best.get("authorships") or [])],
        "year": best.get("publication_year"),
        "venue": venue,
        "doi": (best.get("doi") or "").replace("https://doi.org/", "") or None,
        "openalex": best.get("id", "").replace("https://openalex.org/", ""),
        "abstract": abstract,
        "match_score": round(score, 3),
    }


def query_dblp(http: CachedHTTP, title: str) -> dict | None:
    data = http.get(
        "dblp",
        "https://dblp.org/search/publ/api",
        params={"q": title, "format": "json", "h": 10},
        min_interval=0.5,
    )
    hits = (((data or {}).get("result") or {}).get("hits") or {}).get("hit") or []
    best, score = None, 0.0
    for hit in hits:
        info = hit.get("info") or {}
        s = title_similarity(title, info.get("title", ""))
        if s > score:
            score, best = s, hit
    if not best or score < TITLE_SIM_THRESHOLD:
        return None
    info = best.get("info") or {}
    record_key = (best.get("@id") or "").rsplit("/", 1)[-1] or info.get("key", "")
    url = info.get("url", "")
    if url:
        m = re.search(r"dblp\.org/rec/([^/?#]+(?:/[^/?#]+)*)", url)
        if m:
            record_key = m.group(1)
    a_list = (info.get("authors") or {}).get("author") or []
    if isinstance(a_list, dict):
        a_list = [a_list]
    return {
        "source": "dblp",
        "title": info.get("title", ""),
        "authors": [(a.get("text") if isinstance(a, dict) else str(a)) for a in a_list],
        "year": info.get("year"),
        "venue": info.get("venue", ""),
        "doi": info.get("doi"),
        "dblp": record_key,
        "match_score": round(score, 3),
    }


def query_crossref_by_doi(http: CachedHTTP, doi: str) -> dict | None:
    """Resolve a DOI directly via Crossref."""
    data = http.get(
        "crossref",
        f"https://api.crossref.org/works/{doi}",
        min_interval=0.1,
    )
    if not data or not data.get("message"):
        return None
    it = data["message"]
    venue = ""
    if it.get("container-title"):
        venue = it["container-title"][0]
    year = None
    for k in ("published-print", "published-online", "issued"):
        dp = ((it.get(k) or {}).get("date-parts") or [[]])[0]
        if dp:
            year = dp[0]
            break
    abstract = re.sub(r"<[^>]+>", "", it.get("abstract", "") or "").strip()
    return {
        "source": "crossref",
        "title": (it.get("title") or [""])[0],
        "authors": [f"{a.get('given','').strip()} {a.get('family','').strip()}".strip()
                    for a in (it.get("author") or [])],
        "year": year,
        "venue": venue,
        "doi": it.get("DOI"),
        "abstract": abstract,
        "match_score": 1.0,
    }


def query_crossref(http: CachedHTTP, title: str) -> dict | None:
    data = http.get(
        "crossref",
        "https://api.crossref.org/works",
        params={"query.title": title, "rows": 5},
        min_interval=0.1,
    )
    if not data:
        return None
    items = ((data.get("message") or {}).get("items")) or []
    best, score = None, 0.0
    for it in items:
        t = (it.get("title") or [""])[0]
        s = title_similarity(title, t)
        if s > score:
            score, best = s, it
    if not best or score < TITLE_SIM_THRESHOLD:
        return None
    venue = ""
    if best.get("container-title"):
        venue = best["container-title"][0]
    year = None
    for k in ("published-print", "published-online", "issued"):
        dp = ((best.get(k) or {}).get("date-parts") or [[]])[0]
        if dp:
            year = dp[0]
            break
    abstract = re.sub(r"<[^>]+>", "", best.get("abstract", "") or "").strip()
    return {
        "source": "crossref",
        "title": (best.get("title") or [""])[0],
        "authors": [f"{a.get('given','').strip()} {a.get('family','').strip()}".strip()
                    for a in (best.get("author") or [])],
        "year": year,
        "venue": venue,
        "doi": best.get("DOI"),
        "abstract": abstract,
        "match_score": round(score, 3),
    }


def query_arxiv(http: CachedHTTP, query: str) -> dict | None:
    """Query arXiv by title or ID."""
    arxiv_id = extract_arxiv_id(query)
    is_id_search = bool(re.match(r"\d{4}\.\d{4,7}", arxiv_id))
    if is_id_search:
        search_query = f"id:{arxiv_id}"
    else:
        search_query = f'ti:"{query}"'

    data = http.get(
        "arxiv",
        "http://export.arxiv.org/api/query",
        params={"search_query": search_query, "max_results": 5},
        min_interval=3.0, parse="text",
    )
    if not data or "_text" not in data:
        return None
    try:
        root = ET.fromstring(data["_text"])
    except ET.ParseError:
        return None
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    best, score = None, 0.0
    for entry in root.findall("atom:entry", ns):
        t = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        # ID search: skip title similarity check, first result is the match
        if is_id_search:
            best = entry
            score = 1.0
            break
        s = title_similarity(query, t)
        if s > score:
            score, best = s, entry
    if best is None or score < TITLE_SIM_THRESHOLD:
        return None
    aid = (best.findtext("atom:id", default="", namespaces=ns) or "").rsplit("/", 1)[-1]
    aid = re.sub(r"v\d+$", "", aid)
    authors = [(a.findtext("atom:name", default="", namespaces=ns) or "").strip()
               for a in best.findall("atom:author", ns)]
    published = best.findtext("atom:published", default="", namespaces=ns) or ""
    year = int(published[:4]) if published[:4].isdigit() else None
    abstract = (best.findtext("atom:summary", default="", namespaces=ns) or "").strip()
    # Extract DOI if present
    doi = None
    for link in best.findall("atom:link", ns):
        href = link.get("href", "")
        if "doi.org" in href:
            doi = href.split("doi.org/")[-1]
    return {
        "source": "arxiv",
        "title": (best.findtext("atom:title", default="", namespaces=ns) or "").strip(),
        "authors": authors,
        "year": year,
        "venue": "arXiv",
        "doi": doi,
        "arxiv": aid,
        "abstract": abstract,
        "match_score": round(score, 3),
    }


def query_pubmed(http: CachedHTTP, title: str, mailto: str) -> dict | None:
    api_key = os.environ.get("NCBI_API_KEY")
    base_params = {"db": "pubmed", "term": title, "retmode": "json", "retmax": 3}
    if mailto:
        base_params["email"] = mailto
    if api_key:
        base_params["api_key"] = api_key
    res = http.get(
        "pubmed",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params=base_params, min_interval=0.4,
    )
    if not res:
        return None
    ids = (res.get("esearchresult") or {}).get("idlist") or []
    if not ids:
        return None
    fetch_params = {"db": "pubmed", "id": ",".join(ids[:3]),
                    "retmode": "xml", "rettype": "abstract"}
    if mailto:
        fetch_params["email"] = mailto
    if api_key:
        fetch_params["api_key"] = api_key
    xml = http.get(
        "pubmed",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params=fetch_params, min_interval=0.4, parse="text",
    )
    if not xml or "_text" not in xml:
        return None
    try:
        root = ET.fromstring(xml["_text"])
    except ET.ParseError:
        return None
    best, score = None, 0.0
    for art in root.findall(".//PubmedArticle"):
        t = (art.findtext(".//Article/ArticleTitle", default="") or "").strip()
        s = title_similarity(title, t)
        if s > score:
            score, best = s, art
    if best is None or score < TITLE_SIM_THRESHOLD:
        return None
    a = best.find(".//Article") or best
    pmid = best.findtext(".//PMID", default="") or ""
    doi = ""
    for aid in best.findall(".//ArticleId"):
        if aid.get("IdType") == "doi":
            doi = (aid.text or "").strip()
            break
    journal = a.findtext(".//Journal/Title", default="") or ""
    year_str = a.findtext(".//Journal/JournalIssue/PubDate/Year", default="") or ""
    year = int(year_str) if year_str.isdigit() else None
    authors = []
    for au in a.findall(".//Author"):
        ln = au.findtext("LastName", default="") or ""
        fn = au.findtext("ForeName", default="") or ""
        if ln:
            authors.append(f"{ln}, {fn}".strip().rstrip(","))
    abstract_parts = [t.text or "" for t in a.findall(".//Abstract/AbstractText")]
    return {
        "source": "pubmed",
        "title": (a.findtext(".//ArticleTitle", default="") or "").strip(),
        "authors": authors,
        "year": year,
        "venue": journal,
        "doi": doi or None,
        "pmid": pmid,
        "abstract": " ".join(p for p in abstract_parts if p),
        "match_score": round(score, 3),
    }


# ---------------------------------------------------------------------------
# Main search logic

def search_all(query: str, http: CachedHTTP, mailto: str,
               s2_key: str | None) -> dict[str, Any]:
    """Search all sources for a query. Returns structured result."""
    input_type = detect_input_type(query)

    # For direct identifiers, we might get a title from the first hit
    # to use for cross-source verification
    results: dict[str, dict] = {}
    canonical_title = query  # Start with query as canonical title

    # Direct resolution for arXiv
    if input_type in ("arxiv", "arxiv_url"):
        arxiv_id = extract_arxiv_id(query)
        r = query_arxiv(http, arxiv_id)
        if r:
            results["arxiv"] = r
            canonical_title = r["title"]

    # Direct resolution for DOI
    if input_type in ("doi", "doi_url"):
        doi = extract_doi_from_url(query) if input_type == "doi_url" else query
        r = query_crossref_by_doi(http, doi)
        if r:
            results["crossref"] = r
            canonical_title = r["title"]

    # For URLs (non-arxiv, non-doi): try to extract title from page
    # This would need crwlr/web scraping - skip for now, let LLM handle
    if input_type == "url":
        # Try treating the URL content as a title search
        canonical_title = query

    # For PMID: direct PubMed lookup
    if input_type == "pmid":
        # PubMed esearch by PMID
        r = query_pubmed(http, query, mailto)
        if r:
            results["pubmed"] = r
            canonical_title = r["title"]

    # Use canonical title for cross-source search
    # If we got a title from direct resolution, use it; otherwise use query
    search_title = canonical_title if results else query

    # Search remaining sources with the canonical title
    if "semantic_scholar" not in results:
        r = query_semantic_scholar(http, search_title, s2_key)
        if r:
            results["semantic_scholar"] = r
            if not canonical_title or canonical_title == query:
                canonical_title = r["title"]

    if "openalex" not in results:
        r = query_openalex(http, search_title, mailto)
        if r:
            results["openalex"] = r

    if "dblp" not in results:
        r = query_dblp(http, search_title)
        if r:
            results["dblp"] = r

    if "crossref" not in results:
        r = query_crossref(http, search_title)
        if r:
            results["crossref"] = r

    if "arxiv" not in results:
        r = query_arxiv(http, search_title)
        if r:
            results["arxiv"] = r

    if "pubmed" not in results:
        r = query_pubmed(http, search_title, mailto)
        if r:
            results["pubmed"] = r

    # Merge into a unified identifier set
    merged = merge_results(results, canonical_title)

    return {
        "input_type": input_type,
        "query": query,
        "canonical_title": canonical_title,
        "sources": results,
        "merged": merged,
    }


def merge_results(results: dict[str, dict], canonical_title: str) -> dict:
    """Merge results from multiple sources into unified identifiers."""
    # Pick best title (from source with highest match score)
    best_title = canonical_title
    best_score = 0.0
    for r in results.values():
        if r.get("match_score", 0) > best_score:
            best_score = r["match_score"]
            best_title = r.get("title", canonical_title)

    # Collect all authors (prefer longest list)
    all_authors = []
    for r in results.values():
        a = r.get("authors", [])
        if len(a) > len(all_authors):
            all_authors = a

    # Collect year (majority vote)
    years = [r["year"] for r in results.values() if r.get("year")]
    year = max(set(years), key=years.count) if years else None

    # Collect venue (prefer non-arXiv)
    venue = ""
    for r in results.values():
        v = r.get("venue", "")
        if v and v != "arXiv":
            venue = v
            break
    if not venue:
        venue = results.get("arxiv", {}).get("venue", "")

    # Collect identifiers
    doi = None
    arxiv = None
    s2id = None
    openalex_id = None
    dblp_key = None
    pmid = None
    for r in results.values():
        if r.get("doi") and not doi:
            doi = r["doi"]
        if r.get("arxiv") and not arxiv:
            arxiv = r["arxiv"]
        if r.get("source") == "semantic_scholar" and not s2id:
            s2id = r.get("s2id")
        if r.get("openalex") and not openalex_id:
            openalex_id = r["openalex"]
        if r.get("dblp") and not dblp_key:
            dblp_key = r["dblp"]
        if r.get("pmid") and not pmid:
            pmid = r["pmid"]

    # Best abstract
    abstract = ""
    for src in ("semantic_scholar", "openalex", "arxiv", "pubmed", "crossref"):
        if results.get(src, {}).get("abstract"):
            abstract = results[src]["abstract"]
            break

    # Confidence
    n_sources = len(results)
    confidence = "high" if n_sources >= 3 else "medium" if n_sources >= 2 else "low"

    return {
        "title": best_title,
        "authors": all_authors,
        "year": year,
        "venue": venue,
        "doi": doi,
        "arxiv": arxiv,
        "s2id": s2id,
        "openalex": openalex_id,
        "dblp": dblp_key,
        "pmid": pmid,
        "abstract": abstract,
        "confidence": confidence,
        "n_sources": n_sources,
        "evidence": [f"{src}: match_score={r.get('match_score', '?')}"
                     for src, r in results.items()],
    }


def main():
    ap = argparse.ArgumentParser(description="Search academic sources for paper identifiers")
    ap.add_argument("query", help="Title, DOI, arXiv ID/URL, or search query")
    ap.add_argument("--mailto", default="noreply@example.com",
                    help="Email for polite API pools")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None,
                    help="Write result to file instead of stdout")
    args = ap.parse_args()

    cache_dir = args.cache_dir or Path(tempfile.gettempdir()) / "paper-resolve-cache"
    http = CachedHTTP(cache_dir, use_cache=not args.no_cache)

    s2_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    print(f"[search] query: {args.query}", file=sys.stderr)
    print(f"[search] type:  {detect_input_type(args.query)}", file=sys.stderr)

    result = search_all(args.query, http, args.mailto, s2_key)

    n = len(result["sources"])
    print(f"[search] found {n} sources", file=sys.stderr)
    for src, r in result["sources"].items():
        print(f"  {src}: {r.get('title', '?')[:60]} (score={r.get('match_score', '?')})",
              file=sys.stderr)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"[search] written to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    import tempfile
    main()
