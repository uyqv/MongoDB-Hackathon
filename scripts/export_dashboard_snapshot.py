"""Export measured, non-synthetic campaigns through the dashboard's normal serializers."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import main


def main_export(output: Path | None = None, campaign_id: str | None = None):
    campaigns = [c for c in main.campaigns() if not c.get("fake")]
    if campaign_id:
        campaigns = [c for c in campaigns if c["_id"] == campaign_id]
        if not campaigns:
            raise ValueError("no measured campaign with this ID")
    responses = {"/api/campaigns": campaigns}
    for campaign in campaigns:
        cid = campaign["_id"]
        prefix = f"/api/campaigns/{cid}"
        responses[prefix] = main.campaign(cid)
        responses[prefix + "/experiments"] = main.experiments(cid)
        responses[prefix + "/events"] = main.clean(list(main.db().events.find({"campaign_id": cid}).sort("ts", 1)))
        responses[prefix + "/memories"] = main.memories(cid)
        responses[prefix + "/hypotheses"] = main.hypotheses(cid)
        packets = main.clean(list(main.db().packets.find({"campaign_id": cid}).sort("ts", 1)))
        for packet in packets:
            responses[prefix + "/packets/" + packet["_id"]] = packet
            responses[prefix + "/packets/latest?strategy=" + packet["strategy"]] = packet
    output = output or ROOT / "artifacts" / "dashboard_snapshot.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"captured_at": datetime.now(timezone.utc).isoformat(), "responses": responses}, separators=(",", ":")))
    print(f"Recorded {len(campaigns)} real campaigns, {len(responses)} routes, {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--campaign")
    args = parser.parse_args()
    main_export(args.output, args.campaign)
