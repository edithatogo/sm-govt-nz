from pathlib import Path


def test_publish_zenodo_deposition_workflow_requires_explicit_confirmation() -> None:
    workflow = Path(".github/workflows/publish_zenodo_deposition.yml").read_text(
        encoding="utf-8"
    )

    assert "Publish Zenodo Deposition" in workflow
    assert "description: Type publish-zenodo-doi to publish the DOI." in workflow
    assert "--confirm \"${{ inputs.confirm }}\"" in workflow
    assert "Record Zenodo DOI publication" in workflow
