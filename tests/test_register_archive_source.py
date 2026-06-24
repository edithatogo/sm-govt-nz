import json

from scripts.register_archive_source import load_manifest, upsert_source, write_manifest


def test_register_archive_source_adds_and_updates_manifest(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = load_manifest(manifest_path)
    source = {
        "source_id": "agency-bluesky",
        "agency_id": "agency",
        "agency_name": "Agency",
        "source_type": "social_profile",
        "platform": "bluesky",
        "url": "https://bsky.app/profile/agency.bsky.social",
        "account": "agency.bsky.social",
        "feasibility": "high",
        "archive_status": "candidate",
        "access_method": "public_at_protocol",
        "auth": "none",
        "origin": "test",
        "notes": "",
    }

    assert upsert_source(manifest, source) == "added"
    assert upsert_source(manifest, {**source, "archive_status": "ready"}) == "updated"
    write_manifest(manifest_path, manifest)

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["summary"] == {"total_sources": 1, "archive_status_counts": {"ready": 1}}
    assert saved["sources"][0]["archive_status"] == "ready"
