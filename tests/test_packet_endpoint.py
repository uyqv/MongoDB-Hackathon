from fastapi.testclient import TestClient
from api import main

def test_packet_is_scoped_and_embedding_is_removed(monkeypatch):
    class Collection:
        def __init__(self, rows): self.rows = rows
        def find_one(self, query):
            return next((r for r in self.rows if all(r.get(k) == v for k, v in query.items())), None)
    class DB:
        campaigns = Collection([{"_id": "a"}, {"_id": "b"}])
        packets = Collection([{"_id": "p", "campaign_id": "a", "retrieved": [{"embedding": [1], "text": "evidence"}]}])
    monkeypatch.setattr(main, "db", lambda: DB())
    client = TestClient(main.app)
    assert client.get('/api/campaigns/a/packets/p').json()['retrieved'] == [{"text": "evidence"}]
    assert client.get('/api/campaigns/b/packets/p').status_code == 404
    assert client.get('/api/campaigns/missing/packets/p').status_code == 404
    assert client.get('/api/campaigns/a/packets/missing').status_code == 404
