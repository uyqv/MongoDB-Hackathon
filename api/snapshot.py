"""Serve explicitly recorded API responses when the dashboard is deployed as a snapshot."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_snapshot():
    return json.loads((Path(__file__).resolve().parents[1] / "artifacts" / "dashboard_snapshot.json").read_text())


def response_for(path, params):
    snapshot = load_snapshot()
    key = path
    if path.endswith("/packets/latest"):
        key += "?strategy=" + params.get("strategy", "evidence")
    body = snapshot["responses"].get(key)
    if body is None:
        return {"detail": "No recorded data for this request"}, 404
    if path.endswith("/events"):
        try:
            limit = int(params.get("limit", "200"))
            if not 1 <= limit <= 2000:
                raise ValueError()
        except ValueError:
            return {"detail": "limit must be between 1 and 2000"}, 422
        after = params.get("after")
        body = [e for e in body if e["ts"] > after][:limit] if after else body[-limit:]
    if path.endswith("/memories") and params.get("kind"):
        body = [m for m in body if m.get("kind") == params["kind"]]
    return body, 200
