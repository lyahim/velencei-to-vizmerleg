---
name: feedback-mirror-memory-to-repo
description: Mirror every memory file into the project repo's .claude/memory/ folder in addition to the harness's own memory store.
metadata:
  type: feedback
---

Whenever a memory file is written or updated (in the harness's per-project memory store), also write/update the same file content under `.claude/memory/` inside this project repo, and keep `.claude/memory/MEMORY.md` there in sync as the index.

**Why:** User explicitly asked for memory to be saved into the project folder "from now on," plus a copy of what already existed at the time of the request — wants memory portable via git and visible from inside the repo, not only in the harness's external per-project store.

**How to apply:**
- Two write operations per memory change: one to the harness path (as normal, so the harness still auto-loads it into context), one to `.claude/memory/<name>.md` in the repo (same filename/slug).
- Keep frontmatter minimal in the repo copy — drop harness-internal fields like `node_type`, `originSessionId`, `modified` (meaningless/stale outside the harness); keep `name`, `description`, `metadata.type`.
- Also keep `.claude/memory/MEMORY.md` in the repo as a mirrored index, same one-line-per-entry format as the harness's own `MEMORY.md`.
- `PROJECT_INFO.md` documents that `.claude/memory/` exists and what it's for — check it stays accurate if the memory folder's role changes later.
