from pathlib import Path


def test_publish_archives_requires_manual_publish_flag_for_external_publication() -> None:
    workflow = Path(".github/workflows/publish_archives.yml").read_text(encoding="utf-8")

    assert "./.github/actions/setup-python-uv" in workflow
    assert "requirements: requirements.txt" in workflow
    assert "ARCHIVE_PUBLICATION_TARGET" in workflow
    assert "echo \"target=all\"" in workflow
    assert "scripts/monthly_publication_guard.py" in workflow
    assert "--publish-target \"$ARCHIVE_PUBLICATION_TARGET\"" in workflow
    assert "if [ \"$ARCHIVE_PUBLICATION_TARGET\" != \"artifact\" ]; then" in workflow
    assert "--status-report conductor/archive_publication_status.json" in workflow
    assert "dist/archive_publication_status_artifact.json" in workflow
    assert "--path conductor/archive_publication_status.json" in workflow


def test_publish_archives_keeps_zenodo_behind_manual_confirmation() -> None:
    publish_archives = Path(".github/workflows/publish_archives.yml").read_text(encoding="utf-8")
    zenodo = Path(".github/workflows/publish_zenodo_deposition.yml").read_text(encoding="utf-8")
    retrospective = Path(".github/workflows/publish_retrospective_monthly_archive.yml").read_text(encoding="utf-8")

    assert "publication_target" in publish_archives
    assert "- \"zenodo\"" in publish_archives
    assert "./.github/actions/setup-python-uv" in retrospective
    assert "requirements: requirements.txt" in retrospective
    assert "confirm" in zenodo
    assert "publish-zenodo-doi" in zenodo
