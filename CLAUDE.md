# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin (`paper-skills`) providing a skill pipeline for academic paper workflows: search, download, normalize, take reading notes, and discover code repositories. Each skill is a `SKILL.md` file under `skills/` — these are prompt-based skills executed by Claude, not standalone programs.

## Architecture

```
paper-import (orchestrator)
  └→ paper-search → paper-acquire → paper-card
                                  → paper-repo

pdf-to-md is a utility called by paper-acquire
```

| Skill | Role | Key Output |
|---|---|---|
| `paper-import` | Orchestrator — chains search → acquire → repo | Control flow only |
| `paper-search` | Identity resolution via 23 academic sources | `metadata.yaml` (identity, bibliography, urls, acquisition_hints) |
| `paper-acquire` | PDF download + PDF→Markdown normalization | `paper.pdf`, `paper.md`, `paper_images/` |
| `paper-card` | Structured reading notes via parallel subagents | `card.md`, `card-deep.md` |
| `paper-repo` | Code repository discovery + verification + clone | `repo/`, `repo_search` section in metadata.yaml |
| `pdf-to-md` | PDF→Markdown via MinerU API (called by paper-acquire) | `.md` + `_images/` |

## Key Conventions

### Papers Directory

All storage is under `$PAPERS_DIR` (defaults to `~/docs/papers`). Every paper lives at `$PAPERS_DIR/{folder_slug}/`.

### Folder Slug Format

`{venue}{year}-{method}-{first_author}` — e.g. `iclr2020-geom-gcn-pei`, `neurips2017-transformer-vaswani`, `preprint2024-spami-pei`. See `skills/paper-search/references/folder-slug.md` for method extraction rules and collision handling.

### metadata.yaml Ownership

Each skill has exclusive write ownership of specific sections:

| Section | Owner |
|---|---|
| `identity`, `bibliography`, `urls`, `acquisition_hints` | paper-search |
| `assets`, `normalization` | paper-acquire |
| `repo_search` | paper-repo |

No skill may modify another skill's sections. Schema is documented in `skills/paper-search/references/metadata-schema.md`.

## Scripts

All Python scripts are meant to be run via `uv run --script`:

```bash
# paper-search: generate metadata.yaml from search results
echo '{"title":"...","authors":["A"],"year":2020}' | \
  uv run --script "${SKILL_DIR}/scripts/resolve_metadata.py" --from-json --out "$PAPERS_DIR"

# paper-acquire: one-shot acquire (download PDF + normalize)
uv run --script "${SKILL_DIR}/scripts/hydrate_raw.py" \
  --metadata "$PAPERS_DIR/{folder_slug}/metadata.yaml" --md-lang en

# paper-repo: extract URLs from PDF or code links from markdown
uv run --script "${SKILL_DIR}/scripts/extract_urls_from_pdf.py" paper.pdf
uv run --script "${SKILL_DIR}/scripts/extract_code_links_from_md.py" paper.md

# pdf-to-md: convert PDF via MinerU API (requires MINERU_API_TOKEN)
uv run --script "${SKILL_DIR}/scripts/mineru-api.py" paper.pdf -l en
```

## External Dependencies

- **paper-search CLI**: `uv tool install paper-search-mcp --from "git+https://github.com/openags/paper-search-mcp.git"`
- **MinerU API**: requires `MINERU_API_TOKEN` env var
- **web-kit skill** (separate plugin): used for PDF download (`wget`, `cdp-download`) and repo page scraping (`crwlr`)

## Paper Card Subagent Pattern

`paper-card` dispatches two parallel subagents that independently read `paper.md`:
1. **Structure Extractor** — factual content (method, results, datasets)
2. **Evaluation Extractor** — judgments (novelty, soundness, limitations)

The main agent then synthesizes both outputs into the card templates. Reference schemas are in `skills/paper-card/references/`.

## Evals

Each skill has an `evals/evals.json` file for testing skill behavior.
