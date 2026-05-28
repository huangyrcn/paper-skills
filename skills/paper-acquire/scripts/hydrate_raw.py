#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "requests"]
# ///
"""Hydrate or update the canonical raw bundle for a resolved paper metadata file."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Run with: uv run --script hydrate_raw.py")

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


def load_metadata(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_metadata(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def ensure_assets(metadata_path: Path) -> tuple[dict, Path, dict]:
    metadata = load_metadata(metadata_path)
    paper_dir = metadata_path.parent / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    assets = metadata.setdefault("assets", {})
    return metadata, paper_dir, assets


def persist_metadata(metadata_path: Path, metadata: dict) -> None:
    write_metadata(metadata_path, metadata)


def has_meaningful_source(path: Path) -> bool:
    return path.is_file() and len(path.read_text(encoding="utf-8", errors="ignore").strip()) > 500


def find_main_tex(paper_dir: Path) -> Path | None:
    explicit = paper_dir / "main.tex"
    if explicit.is_file():
        return explicit
    tex_files = sorted(paper_dir.glob("*.tex"))
    if not tex_files:
        return None
    return max(tex_files, key=lambda item: item.stat().st_size)


def _resolve_pdf_to_md_script() -> Path:
    """Locate the mineru-api.py script in the sibling pdf-to-md skill."""
    p = Path(__file__).resolve().parents[2] / "pdf-to-md" / "scripts" / "mineru-api.py"
    if p.is_file():
        return p
    raise FileNotFoundError("Cannot find pdf-to-md/scripts/mineru-api.py")


def _is_pdf_content(resp: requests.Response) -> bool:
    """Check if response content is actually a PDF file."""
    ct = resp.headers.get("content-type", "")
    if "application/pdf" in ct:
        return True
    if "text/html" in ct:
        return False
    return resp.content[:4] == b"%PDF"


def _extract_pdf_url_from_html(html: str) -> str | None:
    """Extract PDF URL from publisher HTML page via meta tags or OJS patterns."""
    import re

    # citation_pdf_url meta tag (common across publishers)
    m = re.search(
        r'<meta\s+[^>]*name=["\']citation_pdf_url["\'][^>]*content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # OJS pattern: /article/download/{id}/{galley_id}
    m = re.search(
        r'(https?://[^"\'<>\s]+/article/download/\d+/\d+)',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # Generic: look for PDF download links with common patterns
    m = re.search(
        r'(https?://[^"\'<>\s]+\.pdf(?:\?[^"\'<>\s]*)?)',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    return None


def register_pdf(metadata_path: Path, pdf_source: Path) -> Path:
    """Copy a manually obtained PDF into the paper directory and update assets."""
    metadata, paper_dir, assets = ensure_assets(metadata_path)
    pdf_path = paper_dir / "paper.pdf"
    import shutil
    shutil.copy2(pdf_source, pdf_path)
    assets.setdefault("paper_pdf", {})
    assets["paper_pdf"]["source"] = f"manual:{pdf_source.name}"
    persist_metadata(metadata_path, metadata)
    return pdf_path


def download_pdf_asset(metadata_path: Path) -> Path:
    """Download PDF using URLs from metadata.yaml. Returns path to saved PDF."""
    metadata = load_metadata(metadata_path)
    paper_dir = metadata_path.parent / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = paper_dir / "paper.pdf"

    if pdf_path.is_file() and pdf_path.stat().st_size > 1000:
        print(f"  PDF already exists: {pdf_path}")
        return pdf_path

    identity = metadata.get("identity", {})
    aliases = identity.get("aliases", {})
    urls = metadata.get("urls", {})

    download_attempts: list[tuple[str, str]] = []

    # Priority 1: arXiv
    arxiv_id = aliases.get("arxiv")
    if arxiv_id:
        download_attempts.append(("arxiv", f"https://arxiv.org/pdf/{arxiv_id}.pdf"))

    # Priority 2: PMC
    pmc_url = urls.get("pmc")
    if pmc_url:
        download_attempts.append(("pmc", pmc_url))

    # Priority 3: Semantic Scholar openAccessPdf
    pdf_url = urls.get("pdf", "")
    if pdf_url and "semanticscholar" in pdf_url:
        download_attempts.append(("semantic_scholar", pdf_url))

    # Priority 4: Unpaywall (deferred — sentinel triggers API call inside loop)
    def _unpaywall_url():
        doi = aliases.get("doi")
        if doi and requests:
            email = os.environ.get("CLAUDE_PLUGIN_OPTION_UNPAYWALL_EMAIL") or os.environ.get("PAPER_SEARCH_MCP_UNPAYWALL_EMAIL", "")
            if email:
                try:
                    resp = requests.get(
                        f"https://api.unpaywall.org/v2/{doi}?email={email}", timeout=15
                    )
                    if resp.ok:
                        oa = resp.json().get("best_oa_location", {})
                        return oa.get("url_for_pdf") or oa.get("url")
                except Exception as exc:
                    print(f"  ! Unpaywall lookup failed: {exc}")
        return None

    # Priority 5: Publisher (direct URL)
    if pdf_url:
        download_attempts.append(("publisher", pdf_url))

    # Priority 6: DOI landing page (may have citation_pdf_url meta tag)
    doi = aliases.get("doi")
    if doi:
        download_attempts.append(("doi_page", f"https://doi.org/{doi}"))

    download_attempts.append(("unpaywall", "__DEFERRED__"))

    for source, url in download_attempts:
        if url == "__DEFERRED__":
            url = _unpaywall_url()
            if not url:
                continue
        try:
            print(f"  Trying {source}: {url}")
            if requests:
                resp = requests.get(url, timeout=60, allow_redirects=True)
                if resp.ok and len(resp.content) > 1000 and _is_pdf_content(resp):
                    pdf_path.write_bytes(resp.content)
                    metadata.setdefault("assets", {}).setdefault("paper_pdf", {})
                    metadata["assets"]["paper_pdf"]["source"] = source
                    persist_metadata(metadata_path, metadata)
                    return pdf_path
                elif resp.ok:
                    ct = resp.headers.get("content-type", "unknown")
                    # If we got HTML, try extracting PDF URL from the page
                    if "text/html" in ct:
                        extracted = _extract_pdf_url_from_html(resp.text)
                        if extracted:
                            print(f"  ! {source}: got HTML, found PDF link: {extracted}")
                            try:
                                resp2 = requests.get(extracted, timeout=60, allow_redirects=True)
                                if resp2.ok and len(resp2.content) > 1000 and _is_pdf_content(resp2):
                                    pdf_path.write_bytes(resp2.content)
                                    metadata.setdefault("assets", {}).setdefault("paper_pdf", {})
                                    metadata["assets"]["paper_pdf"]["source"] = f"{source}-page"
                                    persist_metadata(metadata_path, metadata)
                                    return pdf_path
                            except Exception as exc2:
                                print(f"  ! {source}-page failed: {exc2}")
                    print(f"  ! {source}: not a PDF (content-type: {ct}, size: {len(resp.content)})")
            else:
                subprocess.run(
                    ["wget", "-q", "--timeout=60", "-O", str(pdf_path), url],
                    check=True,
                )
                if pdf_path.is_file() and pdf_path.stat().st_size > 1000:
                    with open(pdf_path, "rb") as f:
                        header = f.read(4)
                    if header == b"%PDF":
                        metadata.setdefault("assets", {}).setdefault("paper_pdf", {})
                        metadata["assets"]["paper_pdf"]["source"] = source
                        persist_metadata(metadata_path, metadata)
                        return pdf_path
                    else:
                        pdf_path.unlink()
                        print(f"  ! {source}: downloaded file is not a PDF")
        except Exception as exc:
            print(f"  ! {source} failed: {exc}")

    raise RuntimeError("All PDF download sources failed")


def download_latex_asset(metadata_path: Path) -> list[str]:
    """Download LaTeX source from arXiv if available."""
    metadata = load_metadata(metadata_path)
    paper_dir = metadata_path.parent / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)

    aliases = metadata.get("identity", {}).get("aliases", {})
    hints = metadata.get("acquisition_hints", {})
    arxiv_id = aliases.get("arxiv")

    if not arxiv_id or not hints.get("latex_available"):
        return []

    latex_url = hints.get("latex_url") or f"https://arxiv.org/e-print/{arxiv_id}"
    latex_dir = paper_dir / "latex"
    latex_dir.mkdir(parents=True, exist_ok=True)

    try:
        tar_path = paper_dir / "latex_source.tar.gz"
        if requests:
            resp = requests.get(
                latex_url,
                timeout=60,
                headers={"User-Agent": "paper-skills/1.0 (academic paper tool)"},
            )
            resp.raise_for_status()
            tar_path.write_bytes(resp.content)
        else:
            subprocess.run(
                ["wget", "-q", "--timeout=60", "-O", str(tar_path), latex_url],
                check=True,
            )
        subprocess.run(
            ["tar", "xzf", str(tar_path), "-C", str(latex_dir)],
            check=True,
        )
        tar_path.unlink(missing_ok=True)
        tex_files = [str(f.relative_to(latex_dir)) for f in latex_dir.glob("**/*.tex")]
        return tex_files
    except Exception as exc:
        print(f"  ! LaTeX download failed: {exc}")
        return []


def convert_latex_to_source(metadata_path: Path) -> Path:
    metadata, paper_dir, assets = ensure_assets(metadata_path)
    source_path = paper_dir / "paper.md"
    latex_dir = paper_dir / "latex"
    # Also check paper_dir itself for pre-existing bundles with tex files at top level
    main_tex = find_main_tex(latex_dir) if latex_dir.is_dir() else None
    if main_tex is None and any(paper_dir.glob("*.tex")):
        main_tex = find_main_tex(paper_dir)
    if main_tex is None:
        raise FileNotFoundError("No usable TeX source found")

    subprocess.run(
        [
            "pandoc", "-f", "latex+raw_tex", "-t", "markdown+tex_math_dollars",
            str(main_tex), "-o", str(source_path),
        ],
        check=True,
    )

    if not has_meaningful_source(source_path):
        raise RuntimeError("Pandoc output is too small to trust")

    metadata["normalization"] = {"backend": "latex-pandoc", "source": "paper/paper.md"}
    assets["source"] = "paper/paper.md"
    persist_metadata(metadata_path, metadata)
    return source_path


def convert_pdf_to_source(metadata_path: Path, md_lang: str) -> Path:
    metadata, paper_dir, assets = ensure_assets(metadata_path)
    pdf_path = paper_dir / "paper.pdf"
    source_path = paper_dir / "paper.md"

    if not pdf_path.is_file():
        raise FileNotFoundError(f"Missing PDF: {pdf_path}")

    script_path = _resolve_pdf_to_md_script()
    subprocess.run(
        [sys.executable, str(script_path), str(pdf_path), "-l", md_lang],
        check=True,
    )

    if not source_path.is_file():
        raise FileNotFoundError(f"Expected MinerU output missing: {source_path}")

    metadata["normalization"] = {"backend": "pdf-mineru", "source": "paper/paper.md"}
    assets["source"] = "paper/paper.md"
    persist_metadata(metadata_path, metadata)
    return source_path


def normalize_source(metadata_path: Path, md_lang: str) -> Path:
    metadata, paper_dir, assets = ensure_assets(metadata_path)
    source_path = paper_dir / "paper.md"
    if source_path.is_file() and assets.get("source"):
        return source_path

    try:
        return convert_latex_to_source(metadata_path)
    except Exception as exc:
        print(f"! LaTeX normalization failed, falling back to PDF: {exc}")
        return convert_pdf_to_source(metadata_path, md_lang)


def run_pipeline(
    metadata_path: Path,
    *,
    md_lang: str,
    skip_pdf: bool,
    skip_latex: bool,
    skip_normalize: bool,
) -> None:
    if not skip_pdf:
        pdf_path = download_pdf_asset(metadata_path)
        print(f"✓ PDF: {pdf_path}")

    if not skip_latex:
        try:
            latex_files = download_latex_asset(metadata_path)
        except Exception as exc:
            latex_files = []
            print(f"! LaTeX download failed: {exc}")
        if latex_files:
            print(f"✓ LaTeX: {', '.join(latex_files[:5])}")

    if not skip_normalize:
        source_path = normalize_source(metadata_path, md_lang)
        print(f"✓ Source: {source_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate the canonical raw bundle for a resolved paper")
    parser.add_argument("--metadata", "-m", required=True, help="Path to metadata.yaml")
    parser.add_argument("--md-lang", default="en", choices=["en", "ch"], help="Language hint for PDF normalization")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF download")
    parser.add_argument("--skip-latex", action="store_true", help="Skip LaTeX download")
    parser.add_argument("--skip-normalize", action="store_true", help="Skip paper.md generation")
    parser.add_argument("--pdf", type=str, default=None, help="Path to a manually obtained PDF to use instead of downloading")
    args = parser.parse_args()

    metadata_path = Path(args.metadata).resolve()

    if args.pdf:
        register_pdf(metadata_path, Path(args.pdf).resolve())
        print(f"✓ Registered manual PDF: {args.pdf}")

    run_pipeline(
        metadata_path,
        md_lang=args.md_lang,
        skip_pdf=args.skip_pdf,
        skip_latex=args.skip_latex,
        skip_normalize=args.skip_normalize,
    )


if __name__ == "__main__":
    main()
