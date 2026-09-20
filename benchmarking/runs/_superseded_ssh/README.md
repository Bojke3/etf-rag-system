# Superseded runs

Runs kept for the record but excluded from the matrix. `build_run_index.py` skips
any directory whose name starts with `_`, so these do not appear in `INDEX.md`.

Nothing here was rewritten. The raw records are exactly as collected; only their
location changed, and the move is a tracked git rename.

## `dev_combined_c105_r01` … `r05` (moved 2026-09-20)

Collected over SSH on `rticuda.etf.bg.ac.rs`. Superseded because `c105` was
re-collected from scratch on the Mac, so that all five repetitions of that
configuration come from one machine. Mixing machines inside one configuration
would put machine differences into the run-to-run spread that the paper reports
as repetition variance.

| run | state when superseded |
|---|---|
| `dev_combined_c105_r01` | 60/60 successful |
| `dev_combined_c105_r02` | 60/60 successful, generated while the server GPU was already failing (median 100.5 s per question) |
| `dev_combined_c105_r03` | 0/60 — 60 errors after the SSH tunnel dropped |
| `dev_combined_c105_r05` | 6/60, interrupted |

`r01` and `r02` are valid runs and can still be used as a separate, server-side
comparison. They are not part of the current matrix.
