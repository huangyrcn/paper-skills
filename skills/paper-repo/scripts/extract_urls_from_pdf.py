#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf"]
# ///
"""Extract URLs from PDF metadata and annotations.

Scans PDF for:
- Document metadata (URLs in info dict)
- Embedded links / annotations
- PDF metadata fields like 'Subject' or 'Keywords' that may contain URLs

Usage:
    python3 extract_urls_from_pdf.py paper.pdf
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF not installed. Run with: uv run --script extract_urls_from_pdf.py")


URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


def extract_urls_from_metadata(doc: fitz.Document) -> list[dict]:
    """Extract URLs from PDF metadata."""
    results = []
    metadata = doc.metadata or {}

    for key, value in metadata.items():
        if not value:
            continue
        urls = URL_PATTERN.findall(str(value))
        for url in urls:
            results.append({
                "url": url,
                "source": f"metadata.{key}",
                "context": str(value)[:200],
            })

    return results


def extract_urls_from_annotations(
    doc: fitz.Document, ref_start: int = 0,
) -> list[dict]:
    """Extract URLs from PDF annotations (links).

    Args:
        doc: PyMuPDF document.
        ref_start: 0-based page index where References section begins.
            Annotations on pages >= ref_start are flagged with
            ``likely_reference: True``.
    """
    results = []

    for page_num, page in enumerate(doc):
        for link in page.get_links():
            uri = link.get("uri")
            if uri and URL_PATTERN.match(uri):
                # Get surrounding text context
                rect = link.get("rect")
                context = ""
                if rect:
                    # Expand rect slightly to get surrounding text
                    expanded = fitz.Rect(
                        rect.x0 - 50, rect.y0 - 20,
                        rect.x1 + 50, rect.y1 + 20
                    )
                    context = page.get_text("text", clip=expanded).strip()

                results.append({
                    "url": uri,
                    "source": f"annotation.page{page_num + 1}",
                    "context": context[:300],
                    "likely_reference": page_num >= ref_start and ref_start > 0,
                })

    return results


def _detect_references_page(doc: fitz.Document) -> int:
    """Return the 0-based page index where References section starts.

    Scans from the end looking for a heading like "References" / "Bibliography".
    Returns 0 (conservative: no pages flagged) if not found.
    """
    heading_re = re.compile(
        r"^\s*(references|bibliography|参考文献)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    for page_num in range(len(doc) - 1, -1, -1):
        text = doc[page_num].get_text("text")
        if heading_re.search(text):
            return page_num
    return 0


def extract_urls_from_text(doc: fitz.Document) -> list[dict]:
    """Scan full PDF text for code-related URLs."""
    results = []
    seen_urls = set()

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        urls = URL_PATTERN.findall(text)

        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Get context around the URL
            idx = text.find(url)
            start = max(0, idx - 100)
            end = min(len(text), idx + len(url) + 100)
            context = text[start:end].strip()

            url_lower = url.lower()
            is_code_host = any(h in url_lower for h in (
                "github.com", "gitlab.com", "bitbucket.org",
            ))
            is_homepage = any(h in url_lower for h in (
                ".github.io", ".gitlab.io",
                ".edu/", ".edu~", ".ac.uk", ".ac.jp", ".ac.cn",
            ))
            is_archive = any(url_lower.endswith(ext) for ext in (
                ".zip", ".tar.gz", ".tar.bz2", ".tgz", ".7z", ".rar",
            ))
            ctx_lower = context.lower()
            context_hit = any(kw in ctx_lower for kw in (
                "code", "source", "repository", "github", "gitlab",
                "implementation", "available at", "download",
                "homepage", "project page", "demo",
            ))

            if is_code_host or is_homepage or is_archive or context_hit:
                results.append({
                    "url": url,
                    "source": f"text.page{page_num + 1}",
                    "context": context,
                })

    return results


def main():
    parser = argparse.ArgumentParser(description="Extract URLs from PDF")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--filter-refs", action="store_true",
        help="Drop URLs likely from the References section",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    doc = fitz.open(pdf_path)

    ref_start = _detect_references_page(doc)

    all_results = []
    all_results.extend(extract_urls_from_metadata(doc))
    all_results.extend(extract_urls_from_annotations(doc, ref_start=ref_start))
    all_results.extend(extract_urls_from_text(doc))

    if args.filter_refs:
        all_results = [r for r in all_results if not r.get("likely_reference")]

    # Deduplicate by URL
    seen = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)

    if args.json:
        print(json.dumps(unique_results, indent=2))
    else:
        if not unique_results:
            print("No URLs found in PDF")
        else:
            print(f"Found {len(unique_results)} URLs:")
            for r in unique_results:
                ref_tag = " [ref]" if r.get("likely_reference") else ""
                print(f"\n  URL: {r['url']}{ref_tag}")
                print(f"  Source: {r['source']}")
                print(f"  Context: {r['context'][:100]}...")

    doc.close()


if __name__ == "__main__":
    main()