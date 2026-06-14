import json
from pathlib import Path


def test_govt_registry_status_keeps_track_open_until_external_gates_close() -> None:
    status = json.loads(Path("conductor/govt_registry_status_20260614.json").read_text())

    assert status["status"] == "open"
    assert status["open_gates"]["manual_verification"]["status"] == "open"
    assert status["open_gates"]["mirror_remote_validation"]["status"] == "open"
    assert status["open_gates"]["unified_transparency_feed"]["status"] == "open"


def test_govt_registry_status_records_known_remaining_blockers() -> None:
    status = json.loads(Path("conductor/govt_registry_status_20260614.json").read_text())
    mirror = status["open_gates"]["mirror_remote_validation"]
    unified = status["open_gates"]["unified_transparency_feed"]

    assert mirror["latest_observed_result"] == "skipped_missing_GIT_MIRROR_URL"
    assert mirror["required_secrets"] == ["GIT_MIRROR_URL", "GIT_MIRROR_SSH_PRIVATE_KEY"]
    assert unified["adapter_groundwork"] == "present"
    assert unified["integration_status"] == "wired_behind_disabled_config"
    assert unified["live_test_status"] == "not_run"
