# Changelog

## 2026-10-13 — Initial public results, study v1

- Separate Japanese/English Results site; original LUX SPIRIA history remains in its repository.
- Published allowlisted aggregates for a real-record SHIORI pilot: 42 source messages, 24 authored queries, four conditions, all outcomes and limitations.
- Published opaque per-query summaries, first-run local timing and the scope of internal reproduction checks.
- Private conversation, queries, native IDs, feature terms, database and experimental code remain private. Public website rebuilds do not rerun the experiment.
- Public wording explicitly limits old-sample overlap checks to text hashes/scenes and excludes timing equality from reproduction claims.
- Clarified that 203 counts feature occurrences and that method equality covers 24 queries × four conditions (96 cases). Numerical results are unchanged.

## 2026-10-13 — Complete public website migration

- Moved the full public LUX SPIRIA website into this repository: the Japanese/English overview, scroll mechanisms, LRE, SHIORI, Emotion, historical pages and their static assets.
- The overview now occupies the site root. The study listing moved to `results.html` / `results.en.html`; study URLs and numerical data are unchanged. The previous `en.html` listing URL redirects to `results.en.html` with its fragment and query preserved.
- Updated canonical URLs, language routes, home-screen manifests and the sitemap. Historical research source links are pinned to the original commit.
- The original research repository retains its README, releases, records and an exact pre-migration website snapshot. Old HTML URLs redirect to matching new pages.
- `site-migration.json` identifies the previously public files used. No private research source was imported.
