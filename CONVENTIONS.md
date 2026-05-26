# Paper Skills — Shared Conventions

## Papers Directory

All paper storage uses the `$PAPERS_DIR` environment variable.

```bash
# Default if not set:
PAPERS_DIR="${PAPERS_DIR:-$HOME/docs/papers}"
```

All skills reference `$PAPERS_DIR/{folder_slug}` instead of hardcoded paths.

In skill instructions and documentation, write `$PAPERS_DIR/{folder_slug}` — the
expanding agent or script is responsible for resolving `~` or `$HOME`.

## Folder Slug Format

`{venue}{year}-{method}-{first_author}`

See `paper-search/references/folder-slug.md` for details.

## Skill Pipeline Order

```
paper-import (orchestrator)
  └→ paper-search → paper-acquire → paper-card
                                  → paper-repo

pdf-to-md is a utility used by paper-acquire
```

| Skill | Role | Owns |
|---|---|---|
| paper-import | Pipeline orchestrator | Control flow, output folder structure |
| paper-search | Identity resolution | metadata.yaml (identity, bibliography, urls, acquisition_hints) |
| paper-acquire | PDF download + normalization | paper.pdf, paper.md, paper_images/ |
| paper-card | Reading notes | card.md, card-deep.md |
| paper-repo | Repository discovery | repo_search in metadata.yaml, repo/ |
| pdf-to-md | PDF→Markdown utility | (utility, no persistent artifacts) |
