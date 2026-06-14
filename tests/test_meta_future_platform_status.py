import json
from pathlib import Path


def test_meta_future_platforms_remain_disabled_and_out_of_syndication() -> None:
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    targets = config["syndication_targets"]
    syndicate_to = set(config["monitored_accounts"][0]["syndicate_to"])

    assert targets["instagram"]["enabled"] is False
    assert targets["facebook"]["enabled"] is False
    assert "instagram" not in syndicate_to
    assert "facebook" not in syndicate_to


def test_meta_future_platform_status_matches_launch_blockers() -> None:
    status = json.loads(
        Path("conductor/meta_future_platform_status_20260614.json").read_text(encoding="utf-8")
    )

    assert status["instagram"]["current_status"] == "future_track_pending_launch_review"
    assert status["instagram"]["api_identity_permission_confirmation"] == "pending"
    assert status["facebook"]["current_status"] == "future_track_blocked"
    assert status["facebook"]["dedicated_page_identity"] == "not_confirmed"
    assert status["instagram"]["syndicate_to_configured"] is False
    assert status["facebook"]["syndicate_to_configured"] is False
