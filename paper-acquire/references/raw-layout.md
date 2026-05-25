# Raw Bundle Layout

Canonical raw assets live under:

```text
$PAPERS_DIR/{folder_slug}/
```

Expected layout:

```text
$PAPERS_DIR/{folder_slug}/
  metadata.yaml
  paper/
    paper.pdf
    paper.md
    latex/
      main.tex
      refs.bib
      *.tex
      images/
  repo/
```

## Rules

- keep raw assets under `$PAPERS_DIR`, never under the project-local note directory
- `paper.md` is the normalized paper text, not the reading note
- `latex/` contains the original LaTeX source when available
- `repo/` contains the cloned implementation repository when found
- the note output path is determined later by `paper-reading-notes` or `paper-pipeline`
