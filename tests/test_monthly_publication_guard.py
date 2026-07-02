import json

from scripts.monthly_publication_guard import release_version_in_ledger


def test_release_version_in_ledger_blocks_previously_published_month(tmp_path) -> None:
    ledger = tmp_path / "monthly_release_ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "releases": [
                    {
                        "release_version": "2026-07",
                        "mode": "published",
                        "hugging_face": "published",
                        "zenodo": "published",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert release_version_in_ledger(ledger, "2026-07") is True
    assert release_version_in_ledger(ledger, "2026-08") is False
