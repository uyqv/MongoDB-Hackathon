from fastapi.testclient import TestClient
from api import main


def test_public_dashboard_blocks_writes_before_touching_database(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    def forbidden():
        raise AssertionError("Read-only controls must not access the database")
    monkeypatch.setattr(main, "db", forbidden)
    client = TestClient(main.app)
    for path in ("/api/worker/start", "/api/worker/kill",
                 "/api/campaigns/example/constraint", "/api/campaigns/example/context-reset"):
        assert client.post(path, json={}).status_code == 403
    assert client.get("/api/worker/status").json()["read_only"] is True
    assert client.get("/").status_code == 200
    assert client.get("/static/live-state.mjs").status_code == 200


def test_local_worker_status_still_works(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("DASHBOARD_READ_ONLY", raising=False)
    monkeypatch.delenv("DASHBOARD_DATA_MODE", raising=False)
    monkeypatch.setattr(main.control, "worker_status", lambda: {"running": True, "pid": 123, "campaign_id": "local"})
    assert TestClient(main.app).get("/api/worker/status").json()["running"] is True


def test_bundled_eeg_preview_never_needs_scientific_dependencies(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "WEB_DIR", tmp_path / "web")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "eeg_preview.json").write_text('{"display_only": true, "source": "recorded EEG"}')
    monkeypatch.delenv("EEG_PREVIEW_CACHE", raising=False)
    def forbidden():
        raise AssertionError("Bundled preview must not be rebuilt")
    monkeypatch.setattr(main, "build_eeg_preview", forbidden)
    assert main.eeg_preview()["source"] == "recorded EEG"


def test_snapshot_routes_are_honest_scoped_and_do_not_connect_to_atlas(monkeypatch):
    from api import snapshot
    monkeypatch.setenv("DASHBOARD_DATA_MODE", "snapshot")
    saved = {"captured_at": "2026-09-26T12:00:00+00:00", "responses": {
        "/api/campaigns": [{"_id": "a"}],
        "/api/campaigns/a/packets/p": {"_id": "p", "campaign_id": "a"},
        "/api/campaigns/a/packets/latest?strategy=evidence": {"_id": "p"},
        "/api/campaigns/a/events": [{"ts": "01"}, {"ts": "02"}, {"ts": "03"}],
    }}
    monkeypatch.setattr(snapshot, "load_snapshot", lambda: saved)
    def forbidden():
        raise AssertionError("Snapshot must not contact Atlas")
    monkeypatch.setattr(main, "db", forbidden)
    c = TestClient(main.app)
    assert c.get("/api/health").json() == {"ok": True, "mode": "snapshot", "captured_at": saved["captured_at"]}
    assert c.get("/api/worker/status").json()["data_mode"] == "snapshot"
    assert c.get("/api/campaigns").json() == [{"_id": "a"}]
    assert c.get("/api/campaigns/a/packets/p").status_code == 200
    assert c.get("/api/campaigns/b/packets/p").status_code == 404
    assert c.get("/api/campaigns/a/packets/latest").json()["_id"] == "p"
    assert c.get("/api/campaigns/a/events?limit=1").json() == [{"ts": "03"}]
    assert c.get("/api/campaigns/a/events?after=01&limit=1").json() == [{"ts": "02"}]
    assert c.get("/api/campaigns/a/events?limit=no").status_code == 422
    assert c.post("/api/worker/kill").status_code == 403
