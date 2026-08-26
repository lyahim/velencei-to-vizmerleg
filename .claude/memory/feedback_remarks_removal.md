---
name: feedback-remarks-removal
description: "When a REMARKS.md item is solved, delete that item from REMARKS.md as part of the same change."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6c3f3750-c679-4d03-b54f-ee34f9400f07
  modified: 2026-08-05T15:00:11.743Z
---

`REMARKS.md` at the repo root is a running, untriaged list of known issues. When a change solves one of its items, **remove that item from `REMARKS.md` in the same change** — do not leave it there, and do not mark it "done" in place.

**Why:** the file is defined at its top as "things to look at, not triaged, not fixed yet". An item that stays after being fixed contradicts that definition, and the list stops being trustworthy as a to-do list.

**How to apply:** when implementing a change that closes a remark, edit `REMARKS.md` to drop the numbered item, and say in the change summary which remark it closed. Renumber the remaining items. Items deliberately deferred stay in the file untouched.

Related: [[feedback-docs-after-apply]].
