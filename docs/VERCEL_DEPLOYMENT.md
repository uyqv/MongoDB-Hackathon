# Vercel dashboard

Production: https://second-shift-iota.vercel.app

Vercel project: `family-584f/second-shift`.
GitHub repository: `uyqv/MongoDB-Hackathon`.
Production release branch: `codex/vercel-dashboard`.

The public dashboard displays a labeled snapshot of 10 real Atlas campaigns.
The capture time appears above the research loop. Campaign selection, experiment
details, saved evidence packets, activity, proof, and source views remain available.
Operator controls are disabled and all writes are rejected by the API.

The initial live-data deployment built successfully, but Atlas connections from
Vercel timed out. The recorded-data deployment was approved for the immediate
launch. It does not require a database credential in Vercel. Local workers and
the local dashboard continue to use Atlas normally.

## Deploy from GitHub

The project root is the repository root, the framework is FastAPI, and `app.py`
exports the app. `requirements.txt` contains the lightweight dashboard runtime.
`.python-version` selects Python 3.12. `.vercelignore` limits deployment files to
application code, web assets, evaluation JSON, and the recorded artifacts.

Before publishing, run the checks in [Release readiness](PRODUCTION_READINESS.md).
The required `artifacts/` files are versioned; neither the archive nor final
presentation media is sent to the dashboard deployment.

Production and preview environments use `DASHBOARD_READ_ONLY=1` and
`DASHBOARD_DATA_MODE=snapshot`. `MONGODB_URI` is unnecessary in this mode.
Push to the production release branch to trigger a production deployment.

To deploy manually from this checkout:

```sh
npx --yes vercel@60.1.3 link --yes --project second-shift --scope family-584f
npx --yes vercel@60.1.3 deploy --prod --yes --scope family-584f
```

## Refresh recorded campaigns

Install worker dependencies and provide local Atlas credentials in ignored `.env`:

```sh
.venv/bin/pip install -r requirements-worker.txt
.venv/bin/python scripts/export_dashboard_snapshot.py
```

Review and commit `artifacts/dashboard_snapshot.json`, then push the release branch.
The export reads campaigns through existing API serializers. It excludes fake
campaigns and embedding vectors. `artifacts/eeg_preview.json` is the real recorded
PhysioNet EEG preview, so the dashboard runtime needs no numerical dependencies.

## Live data later

Resolve Atlas network access for Vercel, restore `MONGODB_URI` as a production
secret, remove `DASHBOARD_DATA_MODE`, and deploy again. Verify `/api/health` and
campaign endpoints from the production URL. Keep operator controls read-only:
the long-running EEG worker requires a separate persistent process.
