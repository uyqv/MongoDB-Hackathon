"""Export measured, non-synthetic campaigns through the dashboard's normal serializers."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import main


def main_export():
    campaigns = [c for c in main.campaigns() if not c.get("fake")]
    responses = {"/api/campaigns": campaigns}
    for campaign in campaigns:
        cid = campaign["_id"]
        prefix = f"/api/campaigns/{cid}"
        responses[prefix] = main.campaign(cid)
        responses[prefix + "/experiments"] = main.experiments(cid)
        responses[prefix + "/events"] = main.clean(list(main.db().events.find({"campaign_id": cid}).sort("ts", 1)))
        responses[prefix + "/memories"] = main.memories(cid)
        packets = main.clean(list(main.db().packets.find({"campaign_id": cid}).sort("ts", 1)))
        for packet in packets:
            responses[prefix + "/packets/" + packet["_id"]] = packet
            responses[prefix + "/packets/latest?strategy=" + packet["strategy"]] = packet
    output = ROOT / "artifacts" / "dashboard_snapshot.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"captured_at": datetime.now(timezone.utc).isoformat(), "responses": responses}, separators=(",", ":")))
    print(f"Recorded {len(campaigns)} real campaigns, {len(responses)} routes, {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main_export()
