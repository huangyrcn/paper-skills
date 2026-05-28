# paper-search Skill Redesign

## Problem

paper-search skill fails to detect formal publication venues. Root cause: only uses `paper-search` CLI (often arXiv-only), no web search for venue verification, and `resolve_metadata.py` doesn't accept venue-related fields.

Example: "Sculpting Subspaces" (ICLR 2026) was recorded as `arxiv2025-...` preprint with `publication_status: "unknown"`.

## Design

### Two Tools

| Tool | Role |
|------|------|
| `web-kit` | Search the web to identify/verify paper identity and extract venue info |
| `paper-search` CLI | Query 23 academic sources for structured metadata (IDs, authors, abstract) |

### Two Input Modes

| Mode | Input | Flow |
|------|-------|------|
| **A: Title** | Exact paper title | web-kit verify → CLI → script |
| **B: Fuzzy** | DOI / arXiv ID / URL / description | web-kit locate → CLI → script |

Both modes follow the same pipeline; the difference is what web-kit does (verify vs locate).

### Pipeline

```
Any input (title / DOI / arXiv / URL / description)
  |
  v
Step 1: web-kit search
  - Mode A (title): ask-search "{title}" → verify identity + look for venue
  - Mode B (fuzzy):
    - DOI → ask-search "{doi}"
    - arXiv → ask-search "arxiv {arxiv_id}"
    - URL → crwlr read the URL directly
    - Description → ask-search "{description}" → user confirms which paper
  - Extract from web-kit results: title, authors, venue, year, OpenReview URL, identifiers
  - Key venue sources in results: OpenReview links, DBLP listings, conference pages
  |
  v
Step 2: paper-search CLI (progressive, layered)
  - Layer 1: arxiv,semantic,crossref → basic identity
  - Layer 2 (if no venue): dblp,openalex → venue from DBLP key / OpenAlex venue
  - Layer 3 (if still no venue): all sources
  |
  v
Step 3: Merge results + conflict resolution
  - Year: CLI bib sources only (DBLP > Crossref > OpenAlex > arXiv published_date). Ignore updated_date.
  - Venue: union (whichever source found it, prefer CLI's DBLP key)
  - IDs/Authors/Abstract: CLI (structured data) > web-kit
  |
  v
Step 4: resolve_metadata.py → metadata.yaml
  - Receives all fields via JSON including publication_status, venue_context, openreview
```

### Changes to `resolve_metadata.py`

Add 3 parameters to `build_metadata()`:

```python
def build_metadata(
    ...,
    publication_status: str = "unknown",   # NEW
    venue_context: str = "",               # NEW
    openreview_url: Optional[str] = None,  # NEW
) -> dict[str, Any]:
```

Use them in output:

```python
"bibliography": {
    ...
    "venue_context": venue_context,           # was hardcoded ""
    "publication_status": publication_status,  # was hardcoded "unknown"
},
"urls": {
    ...
    "openreview": openreview_url,  # was hardcoded null
},
```

Add CLI args: `--publication-status`, `--venue-context`, `--openreview`
Wire JSON path: read `publication_status`, `venue_context`, `openreview` from stdin JSON.

### Changes to SKILL.md

Rewrite around the new flow:

1. **Input routing**: two modes (title vs fuzzy), both start with web-kit
2. **Step 1 — web-kit**: mandatory search for all inputs, extract venue info
3. **Step 2 — paper-search CLI**: progressive layered sources
4. **Step 3 — Merge & resolve**: conflict resolution rules
5. **Step 4 — Script**: expanded JSON schema with venue fields
6. **Publication status inference rules**:

| Evidence | publication_status |
|---|---|
| web-kit finds conference virtual page or OpenReview poster/oral/spotlight | `"accepted"` |
| DBLP key under conference (not CoRR) | `"published"` |
| Crossref DOI to journal/conference | `"published"` |
| Only arXiv / DBLP shows CoRR / no venue from any source | `"unknown"` |

### Conflict Resolution

- **Year**: CLI bib sources only (DBLP key year > Crossref publication date > OpenAlex > arXiv `published_date`). arXiv's `updated_date` is ignored — use `published_date` (first submission year). web-kit year is reference only, not used for resolution.
- **Venue**: web-kit is the primary source (OpenReview, ICLR/NeurIPS virtual pages, conference programs). CLI `extra` field as supplement (DBLP `venue` key, Crossref `container_title`). DBLP may lag for recently accepted papers (stuck at `CoRR`).
- **IDs/Authors/Abstract**: CLI (structured data) > web-kit (supplementary)
- **publication_status**: derived from venue evidence (see table above). web-kit's OpenReview/venue page is the decisive signal for recently accepted papers.

### CLI `extra` Field Parsing

Venue info is buried in the CLI's `extra` field (a string repr of a dict). The LLM must parse it:

| Source | `extra` key | Example |
|--------|-------------|---------|
| DBLP | `venue` | `{'venue': 'ICLR', 'year': '2020'}` |
| Crossref | `container_title` | `{'container_title': 'Neurocomputing', 'publisher': 'Elsevier'}` |

Note: DBLP may return `venue: 'CoRR'` for arXiv preprints even if the paper has been accepted at a conference. Trust web-kit's venue info over DBLP's `CoRR`.

### Evals

Add eval case for venue verification:
- Prompt: "导入 Sculpting Subspaces 这篇论文"
- Expectations: venue=ICLR, year=2026, publication_status="accepted", folder_slug starts with "iclr2026"

### Files to Modify

- `skills/paper-search/SKILL.md` — full rewrite of flow
- `skills/paper-search/scripts/resolve_metadata.py` — add 3 venue fields
- `skills/paper-search/evals/evals.json` — add venue verification eval
