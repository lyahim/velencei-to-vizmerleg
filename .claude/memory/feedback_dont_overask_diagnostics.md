---
name: feedback-dont-overask-diagnostics
description: When diagnosing an environment/process issue, don't chain multiple speculative AskUserQuestion rounds — after one clarifying question, pivot to making the fix robust to unknown causes instead of continuing to guess.
metadata:
  type: feedback
---

While debugging why `scripts/dev.sh`'s backend process kept ending up in state `T` (stopped), I asked three rounds of AskUserQuestion in a row (Ctrl+Z?, tmux?, "!" prefix?, machine sleep?) trying to pin down the exact external cause. The user rejected the third/fourth round outright and said "it was killed not by me" — a signal that the back-and-forth guessing had gone on too long.

**Why:** Repeated speculative multiple-choice questions about an environment detail the user may not know precisely (or finds tedious to diagnose) reads as stalling. One clarifying question is reasonable; a chain of them is not.

**How to apply:**
- Ask at most one round of clarifying questions for a given diagnostic thread. If the answer doesn't fully resolve it, stop asking and pivot to making the fix defensive/robust against the unknown cause, rather than continuing to narrow it down via more questions.
- Prefer investigating technically myself first (ps state, process groups, logs) before asking the user anything — only ask what I genuinely cannot determine by inspection.
- If a root cause can't be pinned down, say so plainly and ship a mitigation that works regardless of cause (e.g., detect-and-recover) instead of holding the fix hostage to full understanding.
