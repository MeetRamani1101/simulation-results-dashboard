# Decisions

## Assumptions

- **No domain CAE background is claimed.** The 15 mm / 0-50 Hz rule is
  implemented exactly as stated and treated as a literal, auditable
  data-review threshold, not a safety margin or a proxy for a resonance/modal
  analysis. Anywhere the UI states a result, it also states the range and
  limit used, per the spec's "make the assessment range and threshold
  visible" requirement.
- **"Project" grouping.** The supplied `Inputs/` folder has no project-level
  directory - it goes straight to `rev1/rev2/rev3`, each containing one CSV
  per component (Bracket, Housing, Lens). Since the spec's user workflow
  starts with "select a project" and expects project/component/revision
  traceability, I introduced one explicit project folder
  (`HeadlampAssembly`, named for what the three parts look like together -
  a headlamp bracket/housing/lens assembly) and built the importer to
  auto-detect **either** layout per file:
  `<root>/<revision>/<component>.csv` (single implicit project) or
  `<root>/<project>/<revision>/<component>.csv` (explicit project folders,
  for when more product lines are added later). This is a guess at intent,
  not a given - see "Questions" below.
- **Frequency range boundaries are inclusive on both ends** (0 and 50 Hz
  count toward the assessed max), per "frequencies from 0 through 50 Hz
  inclusive."
- **A CSV with no sample at all in 0-50 Hz** produces a `null` assessed
  result (not a pass or a fail) rather than silently defaulting to pass -
  surfaced in the UI as "No data ≤50 Hz" rather than a green/red badge, since
  asserting compliance without evidence in that range would be misleading.
- **A malformed CSV row aborts the whole file**, rather than skipping just
  the bad row. A silently dropped row could understate the true peak and
  turn a failing revision into an apparent pass - worse than refusing to
  import until the file is fixed. The failure is reported per-file in the
  import run, and any previously-imported data for that revision is left
  untouched (not blanked out).
- **Samples are not interpolated.** The supplied data is a sparse, irregular
  set of frequency points (e.g. 5, 21.3, 32.2, 35.7, 37.6, 39.7, 44.3, 48.3
  Hz) rather than a uniform sweep. The peak/assessment logic takes the
  maximum of the *sampled* points in range, which is a faithful read of the
  supplied data but could miss a true peak that falls between samples - see
  "Questions."
- **File-change detection uses a SHA-256 content hash**, not mtime alone
  (mtime is kept too, for diagnostics), so copying/moving files or resetting
  timestamps doesn't trigger spurious re-imports, and actual content edits
  are always caught even if a tool preserves the original mtime.
- **Demand "latest observed result" is computed, not stored.** A demand is
  linked to a component (and to the specific origin revision/finding that
  raised it); its per-revision history and "latest result" are derived at
  read time from that component's revisions rather than duplicated into the
  demand row, so there is exactly one source of truth for what a revision's
  result was and it can never drift out of sync with the samples.
- **Python 3.13, not 3.14.** The machine's default Python is 3.14, but
  `pydantic-core` has no published wheel for it yet on Windows and fails to
  build from source without a configured Rust toolchain. The backend was
  built and tested under 3.13.

## Database choice: SQLite

SQLite is sufficient for this MVP: single-writer ingestion, read-mostly API
traffic, no concurrent multi-process writes, and it needs zero setup for a
reviewer to run the project locally (`pip install`, run - no separate DB
server). Everything is accessed through SQLAlchemy's ORM, so moving to
Postgres later (for concurrent ingestion, multi-user demand editing, or
larger datasets) is a connection-string change plus an Alembic migration
setup, not a rewrite.

## Chart and UI choices

- **Recharts**, composed declaratively (`Line`, `ReferenceLine`,
  `ReferenceArea`, `ReferenceDot`) rather than a lower-level canvas library,
  because the chart needs several semantically distinct overlays (the 0-50 Hz
  assessment band, the 15 mm limit line, per-revision curves, peak markers)
  that map directly onto Recharts' composable primitives.
- **Each revision is passed to its own `<Line data=...>`**, rather than
  merging all revisions into one dense table keyed by frequency. The
  supplied data is sparsely and irregularly sampled, and revisions don't
  share frequency points - forcing them into one table would mean mostly
  `null` cells and fragile key-matching. Independent per-line data on a
  shared numeric x-axis handles this cleanly and scales to differently-
  sampled revisions without extra transformation code.
- **Peak markers are explicit `ReferenceDot`s**, not just relying on the
  line's own vertex, so the assessed peak is unambiguous even when multiple
  revisions' curves overlap near resonance. Known limitation: when several
  revisions peak at very similar frequency/magnitude (as Bracket/Housing/
  Lens rev1-3 do, all near 37-38 Hz), the dot labels can visually overlap -
  acceptable for MVP, called out under Future improvements.
- **A shaded `ReferenceArea` for 0-50 Hz plus a dashed line at 15 mm**,
  always rendered regardless of which revisions are toggled, so the
  pass/fail criterion is visible even before reading the table - directly
  addressing "make the assessment range and threshold visible."
- **Revision toggles are chips with checkboxes**, not a multi-select
  dropdown, so the active comparison set and its pass/fail state are visible
  at a glance without opening anything.
- **The comparison table always shows every revision** (not just the
  selected/charted ones), with a delta column computed against the true
  previous revision in sequence - independent of which revisions are
  currently toggled on the chart - so hiding a revision from the chart never
  changes what the "change vs previous" numbers mean.
- **No UI component claims "safe" or "production-ready."** Badges read
  "Pass" / "Fail" against the stated criterion only, per the spec's
  instruction not to overclaim.

## Alternatives considered

- **Chart.js** instead of Recharts - rejected mainly for ergonomics: Recharts'
  JSX composition made the band/limit/peak-marker overlays and per-revision
  series far less code than imperative Chart.js plugin configuration.
- **Storing demand-revision snapshots** (a join table caching each
  revision's result at demand-creation time) instead of computing them live -
  rejected because it duplicates data that's already derivable from
  `Revision`, and would need explicit invalidation logic if a revision's
  source file is later corrected via re-ingestion.
- **A single flat "project" per CSV root instead of auto-detecting project
  folders** - rejected because the spec explicitly asks for project-level
  selection and the ability to extend to more data later ("Additional
  revision folders and project CSV files may be added"); a fixed single-
  project model would have to be reworked the moment a second product line
  showed up.
- **GraphQL instead of REST** - not worth the extra dependency/complexity for
  this endpoint surface; the comparison endpoint already shapes exactly what
  the chart/table need in one call, which was the main thing GraphQL would
  have bought.

## Future improvements

- Interpolate or curve-fit between sampled points (with domain-expert input
  on an appropriate method) so a resonance peak that falls between samples
  isn't missed, and expose the sampling density/method in the UI so a user
  can judge confidence in the reported peak.
- Collision-avoidance layout for overlapping peak-marker labels when
  multiple revisions peak at similar frequency/magnitude.
- Alembic migrations instead of `create_all`, ahead of any schema change
  after first deployment.
- Authentication/authorization and per-user attribution on demand
  creation/edits (currently anyone with API access can edit any demand).
- A "marginal" status band (e.g. within some % of the 15 mm limit) if an
  expert confirms that's meaningful, rather than a strict binary pass/fail
  at exactly 15.000 mm.
- Frontend automated tests (component/interaction tests) to match the
  backend's pytest coverage - not included here due to time; backend data-
  processing/assessment logic was prioritized since it's the highest-risk
  area for silently-wrong results.
- Pagination/virtualization for the demands table and revision lists once
  data volume grows past what fits comfortably on one page.
- A file-watcher (instead of only startup/manual/CLI triggers) for near-real-
  time ingestion when new CSVs land.

## Questions for an engineering domain expert

- Is grouping Bracket/Housing/Lens under one project the right mental model,
  or does "project" mean something more specific in your workflow (e.g. a
  vehicle program or test campaign spanning many assemblies)? The supplied
  data didn't make this explicit.
- Should the peak-detection logic account for the irregular sampling density
  (denser points right around the 35-40 Hz resonance, sparse elsewhere), or
  is "max of the sampled points" an accepted practice for this kind of
  review?
- Is 15 mm/50 Hz a fixed criterion for every component regardless of size,
  material, or mounting, or should the limit vary per component/project (the
  current implementation treats it as one global constant)?
- Should a result that is mathematically at the limit (exactly 15.000 mm)
  truly pass, or is some numerical tolerance/rounding convention expected
  given simulation output precision?
- When a later revision passes, is there a standard engineering workflow for
  when a demand *should* eventually be marked Resolved (e.g. requires a
  second confirming revision, a physical test, or sign-off), or is that
  always a case-by-case human judgment with no pattern to encode?
