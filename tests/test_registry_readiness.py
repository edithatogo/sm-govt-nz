import json
from pathlib import Path

from scripts.check_registry_readiness import check


def test_social_media_registry_readiness_contract() -> None:
    check()


def test_registry_submission_manifest_matches_verified_publication_state() -> None:
    manifest = json.loads(
        Path("conductor/registry-submissions/dataset.json").read_text(
            encoding="utf-8"
        )
    )
    registries = {entry["registry_id"]: entry for entry in manifest["registries"]}

    assert manifest["artifact"]["license"] == "other"
    assert registries["hugging_face"]["submission_status"] == "published"
    assert registries["hugging_face"]["verified_at"] == "2026-07-27"
    hf_requirements = {
        item["id"]: item["status"]
        for item in registries["hugging_face"]["requirements"]
    }
    assert hf_requirements["dataset-card"] == "verified"
    assert registries["zenodo"]["submission_status"] == "published"
    assert registries["zenodo"]["doi"] == "10.5281/zenodo.21383327"
    assert registries["zenodo"]["verified_at"] == "2026-07-27"
