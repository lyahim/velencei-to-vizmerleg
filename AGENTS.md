# Velencei-tó vízmérleg — Agent Instructions

## What this project is

Data-archaeology pipeline, not an app. 40 years of Hungarian hydrological yearbooks
(`pdfs/Velencei-tó vízmérleg, YYYY.pdf`, 1986–2025) → structured rows in `output/vizmerleg.db` (SQLite).
A few standalone Python scripts render charts from that DB.

No build system. No package. No test suite. No server. Nothing to install beyond
`sqlite3`, `pdftoppm` (poppler), and the Python deps a given script imports.

The **database is the product**. Everything else is tooling around getting numbers into it correctly.

---

## Read first — routing table

Do not open source or PDFs before the matching doc.

| Task | Read |
|---|---|
| Extract a table from a PDF | `EXTRACTION_GUIDE.md` §0 (hard rules) + §1 (checklist) |
| "What's done / what's next?" | `import_tracker.md` — first `pending` row from top |
| Which DB table / column does this PDF table map to | `EXTRACTION_GUIDE.md` §5 |
| Station name → `station_id` | `EXTRACTION_GUIDE.md` §6 |
| Expected rows/columns of a table | `EXTRACTION_GUIDE.md` §15 (structure registry) |
| Scanned page unreadable / text-only model | `docs/vision-extraction.md` + `EXTRACTION_GUIDE.md` §4b–4c |
| Era differences (A/B/C/D) | `EXTRACTION_GUIDE.md` §11, `import_tracker.md` era table |
| Known bad data already in DB | `EXTRACTION_GUIDE.md` §13, §14 |
| What a script or output file does | `docs/file-index.md` |
| Chart scripts | `docs/climate-charts-plan.md` |

`EXTRACTION_GUIDE.md` is the operating manual. This file is only the map to it.

The `docs/` splits are small (1–3 KB each). **Read them directly — do not spawn a subagent for them.**

---

## Hard rules — extraction

Full text in `EXTRACTION_GUIDE.md` §0. Summary, because these override normal agent instincts:

| Rule | Meaning |
|---|---|
| **A** | One tracker row = one turn. Insert, update tracker, stop. Never batch tables. |
| **B** | Read each value once. No re-reads, no verification loops. **Never check values by recomputing balance equations** — top cause of blown context. |
| **C** | Unclear = stop and ask. Never guess silently. Mark tracker `error` with the question so state survives interruption. |
| **D** | Doubt = `NULL` + a tracker note. Not analysis. |
| **F** | Before transcribing, compare row/column layout against §15 registry. Mismatch → Rule C. New table → add §15 entry after extraction. |
| **G** | One shell command per tool call. No `&&`, no `;`, no batching. |

**Sequential tool calls only.** The user manually confirms every call. Never issue parallel
tool calls, even when they are independent.

---

## Data rules

- `output/vizmerleg.db` is the **sole write target**. `output/vizmerleg_inserts.sql` is a frozen
  historical snapshot — never update it.
- Insert via `sqlite3 output/vizmerleg.db < /tmp/insert_block.sql`, `INSERT OR IGNORE`, wrapped in
  `BEGIN;`/`COMMIT;`.
- Verify with exactly one `SELECT COUNT(*) … WHERE source_doc_id=N AND year=YYYY;`. One query, then move on.
- Never derive, interpolate, or back-compute a missing value. Missing is `NULL`.
- Updating `import_tracker.md` (`status`, `rows_in_db`, `notes`, `updated`) is part of the same turn
  as the insert — not a follow-up.
- Current tables: `documents`, `stations`, `station_metadata_history`, `monthly_balance`,
  `monthly_station_obs`, `evaporation_inputs`, `daily_obs`, `daily_station_extremes`,
  `expedition_flows`, `annual_climate_summary`, `historical_monthly`, `release_events`.
  Check `.schema` before writing SQL against one you have not touched this session.

---

## Code rules — the scripts

Applies to `*.py` in `scripts/`. Keep them boring.

- Flat scripts, run as `python3 scripts/<script>.py <args>`. No package layout, no framework, no CLI library,
  no config files. Argv parsing is hand-rolled and stays that way.
- One script = one job. If a new job appears, write a new script rather than adding modes to an old one.
- Charts emit **self-contained HTML** into `output/`.
- Minimum code that solves the problem. No speculative flexibility, no abstractions for a single
  call site, no error handling for impossible states.
- Surgical edits. Match surrounding style. Don't reformat or "improve" adjacent code. Mention dead
  code, don't delete it.
- Remove only the imports/vars *your* change orphaned.

**Verification instead of TDD.** There is no test suite and none is wanted. A change is verified by
running the script and inspecting the real artifact: the written HTML, or a row count / spot query
against the DB. State the check before making the change:

```
1. <step> → verify: <query or file to inspect>
2. <step> → verify: <…>
```

Never claim something works without running it.

---

## Ask instead of guessing

Use `AskUserQuestion`. Trigger cases (Rule C):

- Table structure differs from §15, or a label/station is not in §6.
- Unit ambiguity (mm vs tómm, m³/s vs m³).
- PDF contradicts data already in the DB.
- One PDF table appears to split across two DB tables.
- Any schema question.
- Any change to a plan the user already approved.

Format:

```
⚠️ UNCLEAR — need decision:
[what was found]
[the options]
[the question]
```

Do not proceed past it.

---

## Documentation update protocol

Route by kind:

| Kind of update | Goes in |
|---|---|
| Extraction rule, table mapping, station id, structure registry, era quirk | `EXTRACTION_GUIDE.md` (the matching §) |
| Per-doc / per-table progress, row counts, NULL notes | `import_tracker.md` |
| New script, output file, or doc file, or per-file detail | `docs/file-index.md` (path-alphabetical row) |
| New top-level area | new row in `docs/file-index.md` |
| Long-form rationale, method write-up | `docs/<topic>.md` + pointer row in `docs/file-index.md` |

Rules:

1. **Do not edit this file.** Propose the rule to the user instead.
2. Every new or renamed root script gets a `docs/file-index.md` row in the same turn.
3. `docs/` prose uses **caveman style**: short declarative fragments, no articles, no copulas, no
   "we"/"you", present tense, one fact per row, concrete tokens (paths, table names, station ids)
   over prose. Identifiers verbatim.
   *Verbose:* "This script is responsible for rendering a page of the PDF and rotating it."
   *Caveman:* "Renders PDF page 300dpi. Rotates 90° CW for /Rotate 270 scans."
4. `docs/` files here are small — edit them directly. No subagent delegation.

---

## Conventions

- **OpenSpec**: new change → `openspec/changes/<name>/` (scaffold with `openspec change new <name>`).
  Completed changes are moved to `openspec/changes/archive/<YYYY-MM-DD>-<name>/` — that is the
  existing layout, keep it.
- **Diagrams**: Mermaid (` ```mermaid ` blocks). No ASCII boxes.
- **Scratch files**: `scratchpad/<year>/` for rendered PNGs and intermediate text. Not project data.
- **Language**: source PDFs, table labels, and station names are Hungarian. Keep identifiers and
  column names in the Hungarian forms the DB already uses (`csapadek_mm`, `parologas`,
  `hozzafolyas`) — do not translate them.
