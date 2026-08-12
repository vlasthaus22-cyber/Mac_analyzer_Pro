# MAC Analyzer Pro v1.0.46

This release completes the Smartroom correctness and performance audit.

## Fixed

- Prevented null or blank Smartroom IDs from causing runtime failures; skipped
  rows are reported with a console warning.
- Fixed snapshot comparison identity to use `smartroom_id + mac`, so additions,
  removals, replacements and total percentages are consistent.
- Fixed complete MAC chronology: the first appearance, every intermediate
  switch/port transition and the current state are retained in date order.
- Fixed primary-file priority: older enrichment rows can fill blanks but can no
  longer overwrite non-empty values from the current final export.
- Fixed DDIO IP warnings so `❗` is based only on the previous switch IP stored
  in IndexedDB. Reservation and lease MAC/IP columns remain independent.
- Fixed delegated navigation for Analytics, History and Room Timeline, including
  controls added or restored after a lazy render.
- Fixed Chart.js instance cleanup, percentage math, legends and inline values.
- Fixed dark/light theme contrast for active controls, labels and icons.

## Added

- Lazy tabs with cached render results and stale-request protection.
- Twenty-row virtual windows for tables larger than 100 rows.
- A dedicated Room Timeline module with Added/Removed table and horizontal CSS
  chronology.
- Worker-based 10,000-row Smartroom aggregation, measured below the 500 ms
  release threshold in the regression suite.
- IndexedDB stores `Equipment`, `History` and `DDIO_Snapshot`, cached OUI lookup,
  ARP resolution fallback `MAC не найден`, known-model persistence and
  automatic DDIO URL fallback.
- ESLint and GitHub Actions checks on every push to `main` and every pull request.

## Release contents

- `release.zip`: autonomous `MAC-Analyzer-Pro.html`, README and UI screenshots.
- `MAC-Analyzer-v1.0.46-Source.zip`: complete tracked project plus the generated
  autonomous HTML and file manifest.

There is no separately hosted public demo in this release. Open the autonomous
HTML locally in Chrome or Edge, or serve `index.html` with Live Server.
