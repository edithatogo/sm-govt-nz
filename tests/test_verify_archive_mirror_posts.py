import json

from scripts.verify_archive_mirror_posts import verify_archive_mirror_posts


def test_verify_archive_mirror_posts_checks_sampled_uris(tmp_path) -> None:
    state_path = tmp_path / "archive_mirror_state.json"
    write_state(state_path)

    result = verify_archive_mirror_posts(
        state_path=state_path,
        limit=1,
        client=FakePostClient(["at://did:plc:mirror/app.bsky.feed.post/second"]),
    )

    assert result == {
        "checked": 1,
        "failures": [],
        "target": "bluesky",
        "valid": True,
    }


def test_verify_archive_mirror_posts_reports_missing_public_post(tmp_path) -> None:
    state_path = tmp_path / "archive_mirror_state.json"
    write_state(state_path)

    result = verify_archive_mirror_posts(
        state_path=state_path,
        limit=1,
        client=FakePostClient([]),
    )

    assert result["valid"] is False
    assert result["failures"] == [
        {
            "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/second",
            "record_id": "x:2",
            "uri": "at://did:plc:mirror/app.bsky.feed.post/second",
            "valid": False,
        }
    ]


def write_state(path) -> None:
    path.write_text(
        json.dumps(
            {
                "posted_records": {
                    "bluesky": {
                        "x:CourtsofNZ": [
                            {
                                "detail": "at://did:plc:mirror/app.bsky.feed.post/first",
                                "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/first",
                                "record_id": "x:1",
                            },
                            {
                                "detail": "at://did:plc:mirror/app.bsky.feed.post/second",
                                "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/second",
                                "record_id": "x:2",
                            },
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )


class FakePostClient:
    def __init__(self, uris: list[str]) -> None:
        self.uris = uris

    def fetch_posts(self, uris: list[str]):
        return [{"uri": uri} for uri in self.uris if uri in uris]
