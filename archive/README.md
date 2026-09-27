# Archive

The September 26, 2026 cleanup preserves superseded work under `2026-09-26/`,
using each file's original repository-relative path. Nothing in this archive is
needed by the deployed dashboard. The final presentation and all delivered demo
editions remain in `presentation/`.

| Location under `2026-09-26/` | Contents |
|---|---|
| Root build plan and external HTML guide | Original hackathon brief and planning |
| `docs/` | Work plan, contributor prompts, work log, original ownership contracts |
| `presentation/` | Earlier ZIP/PPTX, unused 60-second audio and its generators |
| `scripts/video/` | Superseded recording, editing, narration, and TTS versions |
| `eval/` | Invalid first ablation retained for provenance, excluded from current results |
| `.chart-data-KA5W7q/`, `output/playwright/` | Presentation/chart scratch files and review screenshots |
| `design-demos/`, `.playwright-*/`, `output/research/`, `output/vercel-dashboard/`, `run/` | Local prototypes, browser traces, research working output, older captures and logs |

`2026-09-26/manifest.json` records every moved file's original path, archive path,
size, SHA-256, and whether it was tracked in Git. The archive's `.gitignore` keeps
previously local working material local; those files are preserved on this
machine but are **not backed up by a Git push**. Back up the complete archive
directory separately if those local captures are needed elsewhere.

To restore a file, copy its archived version to the `original` path recorded in
the manifest. Check for an existing file first; keep the archived copy. Historical
scripts and documents retain their original paths and assumptions, so restore a
consistent set before attempting to reproduce an old edit. They are historical
records, not the current runbook.

Current demo production inputs in `run/video-v6/` and `run/video-v7/` remain local
and ignored, because the current runbook and final presentation cite their
evidence. Runtime state in `run/`, the EEG cache, local environments, credentials,
and active Git worktrees were retained. Live instructions are in `../docs/`.
