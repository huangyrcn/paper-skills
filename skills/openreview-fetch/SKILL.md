---
name: openreview-fetch
description: >
  批量只读抓取 OpenReview 公开数据（投稿、审稿意见、作者回复、审稿人追评、评分、决定），按账号限流预算取数，遇到 429 立即停止。
  用于 rebuttal 案例分析、提分统计、审稿疑虑归纳、整届抽样，或重新拉取自己论文的审稿。
  Read public OpenReview data in bulk without tripping the per-account API rate limit. Read-only: never posts, edits or submits.
---

# OpenReview bulk reading

## Budget before anything else

- `api2.openreview.net` counts requests per logged-in account. Observed 2026-11-13: after 551 requests it returned
  `429 RateLimitError: ... surpassing the limit of 500 requests. Please try again in 37 minutes`; the window is about
  one hour. Failed retries count too. There is no official page for this yet
  ([openreview/openreview#459](https://github.com/openreview/openreview/issues/459) is open).
- While an account is blocked, the user cannot load OpenReview with it either, so a careless crawl stops their own
  work. Spend at most about 300 requests per hour, keep a counter, and stop at the first 429. Do not retry; report the
  wait time from the message.
- Estimate the cost before running: listing pages + forums ÷ 50. Tell the user the estimate when it exceeds 100.

## Access route

- If plain HTTP works (`curl`, or `openreview-py` with
  `openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')`), use it with the same budget. The Python
  client retries 429 and 5xx automatically, so cap retries for bulk jobs.
- If plain HTTP returns 403 or a verification page, use the user's logged-in Chrome: open an `openreview.net` tab and run
  `fetch(url, {credentials: 'include'})` in the page (Claude in Chrome `javascript_tool`). The user logs in; never
  type or store their password.

## Request patterns, cheapest first

| Need | Request | Cost |
|---|---|---|
| All submissions of a venue with reply counts | `GET /notes?content.venueid=<V>/Submission&limit=1000&select=id,details&details=replyCount` | 1 per 1,000 |
| Full discussion of many forums | `GET /notes?ids=<id1,...,id50>&details=replies` | 1 per 50 forums |
| One forum | `GET /notes?forum=<id>&limit=1000` | 1 per forum; avoid in loops |

- `<V>` is the venue id, e.g. `ICLR.cc/2027/Conference`. During review, submissions sit under `<V>/Submission`; after
  decisions, accepted papers use `<V>` and others use `<V>/Rejected_Submission`, `<V>/Withdrawn_Submission`, etc.
  Check one note's `content.venueid` first.
- Filter on `replyCount` before pulling discussions (e.g. ≥ 10 for active threads). In ICLR 2027, 2,409 such forums
  took 49 requests.
- `details.replies` holds every visible reply with `id`, `replyto`, `signatures`, `invitations`, `content`, `cdate`.
  A review's thread is every note whose `replyto` chain reaches the review id. Reviewer notes are signed
  `.../Reviewer_XXXX`, author notes `.../Authors`; author top-level comments (`replyto == forum`) are general responses.
- Review fields differ by venue and year (ICLR 2027: `rating`, `confidence`, `soundness`, `presentation`,
  `informativeness`, `critical_strengths`, `critical_weaknesses`, `questions_for_authors`). Inspect one review first.

`scripts/or_batch.js` implements the listing and batch pull with a counter, spacing and a hard stop on 429, plus a
thread builder. Paste it into the page, then poll `window.__or.status`.

## What the API does not give

- Earlier scores. Notes show the current rating, and `/notes/edits` does not expose previous values to public readers.
  For ICLR 2024–2025 initial and final ratings, use the Paper Copilot snapshots
  (`github.com/papercopilot/iclr-insights`, `dataset/iclr2025_threshold6_11677_reviewers.json`). For a live venue,
  infer changes only from reviewer statements such as "I raise my score to 3", and label them as inferred.
- Fields hidden during double-blind review, and anything not readable by the account.

## Output hygiene

- Keep raw data in page variables and return counts, aggregates and short excerpts. Tool output is capped (about
  1,000 characters per call in Claude in Chrome) and is blocked when it contains cookies or URLs with query strings,
  so strip URLs and never print response headers.
- Exclude the user's own submission from samples and keep its id out of shared notes.
- With every statistic, record the sample definition, the date fetched and the requests used.
