from pathlib import Path


def test_publish_archives_requires_manual_publish_flag_for_external_publication() -> None:
    workflow = Path(".github/workflows/publish_archives.yml").read_text(encoding="utf-8")

    assert "PUBLISH_ARCHIVES: ${{ inputs.publish == 'true' }}" in workflow
    assert "github.event_name == 'schedule'" not in workflow
