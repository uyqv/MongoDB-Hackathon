# Release readiness

The supported public release is the read-only, recorded dashboard. The worker
and its unauthenticated operator controls are for a local or privately protected
environment. Preparing this checkout does not deploy it or change the existing
release branch.

## Reproducible checks

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
node --test tests/test_live_state.mjs
node --check web/app.js
.venv/bin/python scripts/check_release.py
```

The release check verifies retained presentation/demo media and package SHA-256 hashes and serves
every bundled snapshot route through the real ASGI app. It also checks assets,
EEG preview, proof, source inspection, missing campaigns, the snapshot timestamp,
and blocked operator writes. Database access and EEG regeneration are forbidden
during that check, so missing deployment inputs fail locally and in CI.

GitHub Actions runs the local suite and a separate dashboard check with only
the lightweight runtime plus the HTTP test client installed. Scientific and
provider packages stay out of the dashboard environment. Direct dependency
versions are pinned to the tested versions; transitive dependencies are still
resolved by pip and are not a complete lockfile.

MongoDB integration tests are opt-in. They create and remove fixtures in
`second_shift_david`, drop `second_shift_pytest`, and create/drop uniquely named
`second_shift_research_test_*` databases. Use credentials for a test cluster:

```sh
DB_NAME=second_shift_david .venv/bin/python -m pytest -q --run-integration
```

Paid provider smoke tests additionally require `LIVE=1`; ordinary runs keep
them skipped. Numerical unit tests use synthetic data without an EEG download.

## Public dashboard release

1. Run the checks above and review the recorded capture timestamp and campaigns.
2. Keep `DASHBOARD_DATA_MODE=snapshot` and `DASHBOARD_READ_ONLY=1` in both Vercel
   production and preview environments. Vercel also disables writes by default.
3. Follow `VERCEL_DEPLOYMENT.md` for the existing release branch and project.
4. After deployment, verify `/api/health`, campaign selection, EEG preview, and
   write rejection at the deployed URL. Roll back to the prior successful Vercel
   deployment if validation fails.

`.vercelignore` limits the deployment to application files, web assets, measured
evaluation JSON, and recorded artifacts. The archive, presentations, development
tools, tests, and local credentials are excluded.

## Before exposing live worker operations

The current API has no operator authentication or authorization. Keep it bound
to `127.0.0.1` for local use. A public live service still needs authenticated
operators, request limits, a supervised persistent worker, verified Atlas
connectivity, backup/restore validation, and health/error alerting. The existing
Vercel deployment previously timed out connecting to Atlas, which is why the
supported release uses a snapshot. None of those live-service controls is
established by the repository cleanup.

## Verified during the September 26 cleanup

- Default suite: 69 passed, 29 explicitly skipped (database/provider tests).
- Full suite with disposable MongoDB test namespaces: 95 passed, 3 optional
  provider tests skipped.
- Browser state suite: 8 passed; JavaScript syntax and diff whitespace checks passed.
- A fresh Python 3.13 environment with only dashboard requirements and the HTTP
  test client served all 148 saved routes across ten campaigns, with writes blocked.
- Every archived file matched its pre-move SHA-256 (3,383 files, 1,170,562,275 bytes).
- Final media and packages passed the retained-file checksum check. Concurrent
  presentation source edits were preserved.

CI is configured for the deployed Python 3.12 version; that hosted CI run and a
new Vercel deployment have not been performed by this cleanup.
