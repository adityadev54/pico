# Agent — LoGesH

Implement the server-side Meta client and bounded agent loop. Accept the shared request format, validate tools, emit real step progress, pause for clarification/approval, and consume verification results before completion. Support text first while developing image/context handling in parallel.

First deliverable: a runnable Meta request selecting one tool and processing a structured result. Fixtures must be labeled simulated; do not report real execution from fixtures.

No arbitrary shell tool. Do not own native OS execution or bypass helper permissions. Coordinate outcome checks with Santosh.
