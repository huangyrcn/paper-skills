#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Generate metadata.yaml from collected paper identifiers.

This script handles the deterministic parts of paper-search:
- Generate folder_slug from venue/year/method/first_author
- Merge identifiers from multiple sources into a canonical metadata.yaml
- Write the output file

Usage:
  uv run --script resolve_metadata.py --title "..." --year 2020 --venue ICLR --authors "A,B,C" \
    --doi 10.xxx --arxiv 2002.05287 --s2id abc --openalex W123 --url https://... \
    --confidence high \
    --out $PAPERS_DIR/

Or via JSON stdin:
  echo '{"title":"...","year":2020,...}' | python resolve_metadata.py --from-json --out $PAPERS_DIR/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


STOP_WORDS = {"a", "an", "the", "on", "in", "of", "for", "to", "with", "and", "or", "is", "are", "at", "from", "by"}

def extract_method(title: str) -> str:
    """Extract method name from paper title. Fallback: first meaningful word."""
    # Colon pattern: "BERT: Pre-training..." → "BERT"
    if ":" in title:
        before_colon = title.split(":")[0].strip()
        if before_colon.isupper() or len(before_colon.split()) <= 2:
            return slugify(before_colon)
    # All-caps acronym: "GAT" or "ResNet"
    words = title.split()
    for w in words:
        if w.isupper() and len(w) >= 2:
            return w.lower()
    # First meaningful word (skip stop words)
    for w in words:
        if w.lower() not in STOP_WORDS and len(w) > 2:
            return slugify(w)
    return slugify(words[0]) if words else "unknown"


def last_name(author: str) -> str:
    """Extract lowercase last name from full author name."""
    return author.strip().split()[-1].lower() if author else "unknown"


def generate_folder_slug(venue: Optional[str], year: Optional[int],
                         title: str, authors: list[str],
                         method: Optional[str] = None) -> str:
    """Generate folder slug: {venue}{year}-{method}-{first_author}."""
    v = (venue or "preprint").lower().replace(" ", "")
    y = str(year) if year else "unknown"
    m = slugify(method) if method else extract_method(title)
    a = last_name(authors[0]) if authors else "unknown"
    return f"{v}{y}-{m}-{a}"


def build_metadata(
    title: str,
    authors: list[str],
    year: Optional[int],
    venue: Optional[str],
    doi: Optional[str] = None,
    arxiv: Optional[str] = None,
    s2id: Optional[str] = None,
    openalex: Optional[str] = None,
    dblp: Optional[str] = None,
    pmid: Optional[str] = None,
    pmcid: Optional[str] = None,
    canonical_url: Optional[str] = None,
    pdf_url: Optional[str] = None,
    abstract: Optional[str] = None,
    confidence: str = "high",
    evidence: Optional[list[str]] = None,
    method: Optional[str] = None,
) -> dict[str, Any]:
    """Build the canonical metadata dict."""
    # Build canonical URL from available identifiers
    if not canonical_url:
        if arxiv:
            canonical_url = f"https://arxiv.org/abs/{arxiv}"
        elif doi:
            canonical_url = f"https://doi.org/{doi}"

    # Build PDF URL
    if not pdf_url:
        if arxiv:
            pdf_url = f"https://arxiv.org/pdf/{arxiv}.pdf"

    aliases = {
        "doi": doi,
        "arxiv": arxiv,
        "semantic_scholar": s2id,
        "openalex": openalex,
        "dblp": dblp,
        "pmid": pmid,
        "pmcid": pmcid,
    }

    metadata = {
        "title": title,
        "folder_slug": generate_folder_slug(venue, year, title, authors, method),
        "identity": {
            "canonical_url": canonical_url,
            "primary_id": _pick_primary_id(doi, arxiv, s2id),
            "aliases": {k: v for k, v in aliases.items() if v is not None},
            "resolution_confidence": confidence,
            "resolution_evidence": evidence or [],
        },
        "bibliography": {
            "authors": authors,
            "year": year,
            "venue": venue or "",
            "venue_context": "",
            "publication_status": "unknown",
            "abstract": abstract or "",
        },
        "urls": {
            "canonical": canonical_url,
            "pdf": pdf_url,
            "doi": f"https://doi.org/{doi}" if doi else None,
            "pmc": None,
            "openreview": None,
        },
        "acquisition_hints": {
            "pdf_sources": _build_pdf_sources(arxiv, pdf_url, doi),
            "latex_available": bool(arxiv),
            "latex_url": f"https://arxiv.org/e-print/{arxiv}" if arxiv else None,
        },
        "assets": {},
        "repo_search": {"selected": None, "candidates": []},
    }
    return metadata


def _pick_primary_id(doi, arxiv, s2id) -> dict[str, str]:
    """Pick the best primary identifier."""
    if arxiv:
        return {"type": "arxiv", "value": arxiv}
    if doi:
        return {"type": "doi", "value": doi}
    if s2id:
        return {"type": "semantic_scholar", "value": s2id}
    return {"type": "unknown", "value": ""}


def _build_pdf_sources(arxiv, pdf_url, doi) -> list[dict]:
    """Build prioritized PDF source list for paper-acquire."""
    sources = []
    if arxiv:
        sources.append({
            "source": "arxiv",
            "url": f"https://arxiv.org/pdf/{arxiv}.pdf",
            "priority": 1,
            "notes": "Free, no auth required",
        })
    if pdf_url and not (arxiv and f"arxiv.org/pdf/{arxiv}" in pdf_url):
        sources.append({
            "source": "semantic_scholar",
            "url": pdf_url,
            "priority": 2,
        })
    if doi:
        sources.append({
            "source": "publisher",
            "url": f"https://doi.org/{doi}",
            "priority": 3,
        })
    return sources


def write_metadata_yaml(path: Path, metadata: dict) -> None:
    """Write metadata dict as YAML."""
    try:
        import yaml
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
    except ImportError:
        # Fallback: write as JSON if PyYAML not available
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"Warning: PyYAML not installed, wrote as JSON: {path}", file=sys.stderr)
        print("  Run with: uv run --script resolve_metadata.py", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Generate metadata.yaml from collected identifiers")
    ap.add_argument("--title", help="Canonical paper title")
    ap.add_argument("--authors", help="Comma-separated author names")
    ap.add_argument("--year", type=int, default=None, help="Publication year")
    ap.add_argument("--venue", default=None, help="Conference/journal name")
    ap.add_argument("--doi", default=None)
    ap.add_argument("--arxiv", default=None, help="arXiv ID (e.g., 2002.05287)")
    ap.add_argument("--s2id", default=None, help="Semantic Scholar ID")
    ap.add_argument("--openalex", default=None, help="OpenAlex ID")
    ap.add_argument("--dblp", default=None, help="DBLP key")
    ap.add_argument("--pmid", default=None)
    ap.add_argument("--pmcid", default=None)
    ap.add_argument("--url", default=None, help="Canonical URL")
    ap.add_argument("--pdf-url", default=None)
    ap.add_argument("--abstract", default=None)
    ap.add_argument("--method", default=None,
                    help="Method name for folder slug (e.g., transformer, gat)")
    ap.add_argument("--confidence", default="high",
                    choices=["high", "medium", "low"])
    ap.add_argument("--evidence", nargs="*", default=[],
                    help="Resolution evidence strings")
    default_out = Path(os.environ.get("CLAUDE_PLUGIN_OPTION_PAPERS_DIR") or os.environ.get("PAPERS_DIR", "~/docs/papers")).expanduser()
    ap.add_argument("--out", type=Path, default=default_out,
                    help="Output directory (default: $PAPERS_DIR or ~/docs/papers)")
    ap.add_argument("--from-json", action="store_true",
                    help="Read all fields from JSON stdin instead of CLI args")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing metadata.yaml")
    args = ap.parse_args()

    if not args.from_json and (not args.title or not args.authors):
        ap.error("--title and --authors are required (unless using --from-json)")

    if args.from_json:
        try:
            data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as exc:
            ap.error(f"Invalid JSON on stdin: {exc}")
        title = data["title"]
        authors = data["authors"]
        year = data.get("year")
        year_sources = data.get("year_sources", {})
        venue = data.get("venue")

        # Year conflict detection: warn if sources disagree
        if year_sources and len(set(year_sources.values())) > 1:
            print("WARNING: year conflict detected across sources:", file=sys.stderr)
            for src, yr in sorted(year_sources.items()):
                marker = " <-- selected" if yr == year else ""
                print(f"  {src}: {yr}{marker}", file=sys.stderr)
            if venue:
                venue_year_match = re.search(r"(\d{4})", venue)
                if venue_year_match:
                    venue_yr = int(venue_year_match.group(1))
                    if venue_yr != year:
                        print(
                            f"  WARNING: venue '{venue}' implies year {venue_yr}, "
                            f"but selected year is {year}.",
                            file=sys.stderr,
                        )

        doi = data.get("doi")
        arxiv = data.get("arxiv")
        s2id = data.get("s2id")
        openalex = data.get("openalex")
        dblp = data.get("dblp")
        pmid = data.get("pmid")
        pmcid = data.get("pmcid")
        canonical_url = data.get("url")
        pdf_url = data.get("pdf_url")
        abstract = data.get("abstract")
        confidence = data.get("confidence", "high")
        evidence = data.get("evidence", [])
        method = data.get("method")
    else:
        title = args.title
        authors = [a.strip() for a in args.authors.split(",") if a.strip()]
        year = args.year
        venue = args.venue
        doi = args.doi
        arxiv = args.arxiv
        s2id = args.s2id
        openalex = args.openalex
        dblp = args.dblp
        pmid = args.pmid
        pmcid = args.pmcid
        canonical_url = args.url
        pdf_url = args.pdf_url
        abstract = args.abstract
        confidence = args.confidence
        evidence = args.evidence
        method = args.method

    metadata = build_metadata(
        title=title, authors=authors, year=year, venue=venue,
        doi=doi, arxiv=arxiv, s2id=s2id, openalex=openalex,
        dblp=dblp, pmid=pmid, pmcid=pmcid,
        canonical_url=canonical_url, pdf_url=pdf_url,
        abstract=abstract, confidence=confidence, evidence=evidence,
        method=method,
    )

    slug = metadata["folder_slug"]
    out_path = args.out / slug / "metadata.yaml"

    # Check for existing metadata
    if out_path.exists() and not args.force:
        print(f"Metadata already exists: {out_path}")
        print("Use --force to overwrite, or delete to regenerate.")
        sys.exit(0)

    write_metadata_yaml(out_path, metadata)
    print(f"Title: {title}")
    print(f"Slug:  {slug}")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
