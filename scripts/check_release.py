"""Check the recorded dashboard and retained presentation without credentials.

Run from any directory: python scripts/check_release.py
Requires requirements.txt plus httpx (also in requirements-dev.txt).
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check_files():
    saved = json.loads((ROOT / "presentation/checksums.json").read_text())
    for record in saved["files"]:
        path = ROOT / record["path"]
        with path.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != record["sha256"]:
            raise RuntimeError(f"Retained presentation/demo changed: {record['path']}")
    print(f"Presentation: {len(saved['files'])} retained files match their SHA-256 checksums")


def check_dashboard():
    # Do not load local .env credentials or use a running worker during this check.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["DASHBOARD_DATA_MODE"] = "snapshot"
    os.environ["DASHBOARD_READ_ONLY"] = "1"
    os.environ.pop("EEG_PREVIEW_CACHE", None)
    from fastapi.testclient import TestClient
    from api import main, snapshot

    snapshot.load_snapshot.cache_clear()
    saved = snapshot.load_snapshot()
    campaigns = saved["responses"]["/api/campaigns"]
    if not campaigns or any(c.get("fake") for c in campaigns):
        raise RuntimeError("Release requires measured, non-fake recorded campaigns")
    with patch.object(main, "db", side_effect=AssertionError("Release check contacted Atlas")), \
         patch.object(main, "build_eeg_preview", side_effect=AssertionError("Missing bundled EEG preview")), \
         TestClient(main.app) as client:
        def get(path):
            response = client.get(path)
            if response.status_code != 200:
                raise RuntimeError(f"{path}: HTTP {response.status_code}")
            return response

        for path in ("/", "/static/app.js", "/static/styles.css", "/static/live-state.mjs",
                     "/static/fonts/fonts.css", "/api/proof", "/api/eeg/preview"):
            get(path)
        health = get("/api/health").json()
        if health.get("mode") != "snapshot" or not health.get("captured_at"):
            raise RuntimeError("Dashboard must label its recorded data with a timestamp")
        for path in saved["responses"]:
            response = get(path)
            if response.headers.get("cache-control") != "no-store":
                raise RuntimeError(f"Missing API cache policy: {path}")
        for campaign in campaigns:
            prefix = f"/api/campaigns/{campaign['_id']}"
            for suffix in ("", "/experiments", "/events", "/memories"):
                get(prefix + suffix)
        get("/api/source?file=harness/worker.py&fn=Worker")
        if get("/api/worker/status").json().get("read_only") is not True:
            raise RuntimeError("Operator controls are enabled in the release")
        for path in ("/api/worker/start", "/api/worker/kill",
                     f"/api/campaigns/{campaigns[0]['_id']}/constraint",
                     f"/api/campaigns/{campaigns[0]['_id']}/context-reset"):
            if client.post(path, json={}).status_code != 403:
                raise RuntimeError(f"Public dashboard accepted a write: {path}")
        if client.get("/api/campaigns/not-in-the-snapshot").status_code != 404:
            raise RuntimeError("Unknown campaign did not return 404")
    print(f"Dashboard: {len(campaigns)} campaigns, {len(saved['responses'])} recorded routes, read-only controls OK")


if __name__ == "__main__":
    check_files()
    check_dashboard()
