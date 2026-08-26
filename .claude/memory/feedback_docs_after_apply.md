---
name: feedback-docs-after-apply
description: Always run the AGENTS.md Documentation Update Protocol at the end of every /opsx:apply run, without being asked.
metadata:
  type: feedback
---

After `/opsx:apply` finishes a change (all tasks complete), automatically create/update the required documentation per the project's Documentation Update Protocol (in `AGENTS.md`) — do not wait for the user to ask.

**Why:** User explicitly confirmed this after having to ask for it manually once (scaffold-auth-metadata-admin change) — this is a recurring, standing expectation, not a one-off request.

**How to apply:**
- Trigger: right after the last task in `tasks.md` is marked `[x]` and the apply summary is given (before or alongside suggesting `/opsx:archive`).
- Route each doc per the AGENTS.md table: README.md (end-user/dev setup, structure), PROJECT_INFO.md (root, "Key Files" rows ≤200 chars, no change-history), `docs/file-index.md` + per-area `docs/file-index-<area>.md` splits (per-file detail), `docs/architecture.md` (data flow, persistence, protocol, config reference).
- **AGENTS.md itself is never updated** — it's a fixed rules file; new cross-cutting rules get mentioned to the user instead.
- Every write under `docs/` must be delegated to a general-purpose subagent with the caveman-style rule (short declarative fragments, no articles/copulas, one fact per line, present tense, no "we"/"you") passed verbatim in the prompt. README.md and PROJECT_INFO.md are NOT under `docs/`, so the main agent may write those directly.
- If this is the first time these docs are being created for the repo (greenfield), bootstrap the whole structure (file-index.md + splits + architecture.md) from scratch rather than waiting for an existing skeleton to append to.
