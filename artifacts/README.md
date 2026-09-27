# Recorded dashboard data

`dashboard_snapshot.json` and `eeg_preview.json` are restored byte-for-byte from
the existing `codex/vercel-dashboard` release commit `bb7b57e`.
The campaign snapshot was captured at `2026-09-26T20:08:38.087318+00:00` and
contains ten measured campaigns and 148 recorded API routes. It predates the
optional research policy's hypothesis exports; it is not a fresh live export.

These files are versioned deployment inputs. `data/` contains local caches and
is ignored. Keep the distinction: the public dashboard must work from a fresh
checkout without Atlas credentials or scientific libraries.

Refresh campaigns with `scripts/export_dashboard_snapshot.py`, review the
resulting JSON, then run `python scripts/check_release.py`. See
`../docs/VERCEL_DEPLOYMENT.md` for release instructions.
