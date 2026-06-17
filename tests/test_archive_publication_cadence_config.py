import json
from pathlib import Path


def test_archive_publication_cadence_config_documents_guardrails() -> None:
    config = json.loads(
        Path("config/courts_nz_archive_publication_cadence.json").read_text(encoding="utf-8")
    )

    assert config["hugging_face"]["cadence"] == "weekly_scheduled_rolling_update"
    assert config["hugging_face"]["workflow_target"] == "huggingface"
    assert config["zenodo"]["cadence"] == "manual_release_snapshot"
    assert config["zenodo"]["requires_confirmation"] == "publish-zenodo-doi"
    assert config["guardrails"]["scheduled_runs_must_not_publish_zenodo"] is True
    assert config["manual_publish_archives"]["default_mode"] == "artifact_only"
