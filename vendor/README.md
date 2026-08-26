# Vendored source dependencies

`paper-search-mcp/` is the complete ordinary-directory source snapshot used by
the `paper-search` skill. It is installed from this local path, not fetched
from Git at runtime. Exact provenance is recorded in
[`PAPER_SEARCH_MCP_PIN.json`](PAPER_SEARCH_MCP_PIN.json).

Refreshes must record a fixed upstream commit and tree, retain every tracked
file, and remove nested Git metadata before committing.
