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
| `paper-card` | Structured reading notes via extraction + template filling | `card.md`, `card-deep.md` |
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

# pdf-to-md: convert PDF via MinerU API (requires MINERU_API_TOKEN in plugin settings or env)
uv run --script "${SKILL_DIR}/scripts/mineru-api.py" paper.pdf -l en
```

## External Dependencies

- **paper-search CLI**: complete source is tracked at `vendor/paper-search-mcp`; from the `paper-search` skill use `uv tool install paper-search-mcp --from "${SKILL_DIR}/../../vendor/paper-search-mcp"`. The pinned source identity is in `vendor/PAPER_SEARCH_MCP_PIN.json`.
- **MinerU API**: requires `MINERU_API_TOKEN` — configure via plugin settings (recommended) or env var
- **web-kit skill** (separate plugin): used for PDF download (`wget`, `cdp-download`) and repo page scraping (`crwlr`)

## Plugin Configuration

`plugin.json` declares `userConfig` options that prompt users during installation. Values are exported as `CLAUDE_PLUGIN_OPTION_<KEY>` environment variables to plugin subprocesses. Python scripts check these first, then fall back to standard env var names.

| userConfig Key | Standard Env Var | Type | Default | Notes |
|---|---|---|---|---|
| `PAPERS_DIR` | `PAPERS_DIR` | directory | `~/docs/papers` | Paper storage root |
| `MINERU_API_TOKEN` | `MINERU_API_TOKEN` | string (sensitive) | — | Required for PDF→MD |
| `UNPAYWALL_EMAIL` | `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | string | — | Optional, improves PDF acquisition |
| `SEMANTIC_SCHOLAR_API_KEY` | `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | string (sensitive) | — | Optional, for paper-search-mcp CLI |

Additional env vars for the external `paper-search-mcp` CLI (set via `~/.claude/settings.json` `env` section if needed):
- `IEEE_API_KEY` — IEEE Xplore (paid source)
- `ACM_API_KEY` — ACM Digital Library (paid source)

## Paper Card Extraction Pattern

`paper-card` reads the full `paper.md` and fills card templates directly. Both templates contain inline extraction rules (HTML comments and annotation blocks) that guide how to fill each section — no separate schema file needed.

If the caller supports subagent dispatch, two independent extractions can run in parallel for cross-validation (same templates, same prompt). When only a single pass is available, the main agent fills the templates directly.

## Evals

Each skill has an `evals/evals.json` file for testing skill behavior.
