import json

from scripts.check_follow_status import generate_follow_matrix
from scripts import check_follow_status

REGISTRY_PATH = "registry/agencies.json"
MIRROR_ACCOUNTS = {
    "mirrors": [
        {
            "platform": "bluesky",
            "handle": "mirnzcourts.bsky.social",
            "status": "active",
            "target_registry": "active_platform_accounts",
        }
    ]
}


def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_follow_matrix_generation():
    registry = load_registry()
    matrix = generate_follow_matrix(registry, MIRROR_ACCOUNTS)

    assert "bluesky" in matrix
    # Based on current registry/agencies.json, the mirror follows 4 active Bluesky accounts:
    # 1. courtsofnz.bsky.social
    # 2. health.govt.nz
    # 3. healthnz.govt.nz
    # 4. beehivenz.bsky.social

    bluesky_follows = matrix["bluesky"]
    assert len(bluesky_follows) == 4

    # Check for specific expected follows
    expected = ("mirnzcourts.bsky.social", "courtsofnz.bsky.social")
    assert expected in bluesky_follows

    # Ensure no self-follows
    for follower, target in bluesky_follows:
        assert follower != target


def test_no_duplicate_follows():
    registry = load_registry()
    matrix = generate_follow_matrix(registry, MIRROR_ACCOUNTS)

    for platform, follows in matrix.items():
        assert len(follows) == len(set(follows))


def test_empty_mirror_config_generates_no_follow_work():
    registry = load_registry()

    matrix = generate_follow_matrix(registry, {"mirrors": []})

    assert matrix == {}


def test_bluesky_follow_check_resolves_targets_before_relationship_lookup(monkeypatch):
    class FakeBlueskyClient:
        def __init__(self):
            self.relationship_others = []

        def resolve_handle(self, handle):
            return {
                "target-a.bsky.social": "did:plc:targeta",
                "target-b.bsky.social": "did:plc:targetb",
            }[handle]

        def get_relationships(self, actor, others):
            self.relationship_others = others
            assert actor == "mirror.bsky.social"
            assert others == ["did:plc:targeta", "did:plc:targetb"]
            return [
                {
                    "did": "did:plc:targeta",
                    "following": "at://did:plc:mirror/app.bsky.graph.follow/record-a",
                },
                {"did": "did:plc:targetb"},
            ]

    fake_client = FakeBlueskyClient()
    monkeypatch.setattr(check_follow_status, "BlueskyApiClient", lambda: fake_client)

    results = check_follow_status.check_bluesky_follows(
        {
            "bluesky": [
                ("mirror.bsky.social", "target-a.bsky.social"),
                ("mirror.bsky.social", "target-b.bsky.social"),
            ]
        }
    )

    assert fake_client.relationship_others == ["did:plc:targeta", "did:plc:targetb"]
    assert results[0]["status"] == "following"
    assert results[0]["target_did"] == "did:plc:targeta"
    assert results[1]["status"] == "not_following"
