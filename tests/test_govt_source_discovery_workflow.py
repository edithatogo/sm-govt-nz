from pathlib import Path


def test_govt_source_discovery_workflow_uses_manual_inputs() -> None:
    workflow = Path(".github/workflows/govt_source_discovery.yml").read_text(encoding="utf-8")

    assert "probe_homepages" in workflow
    assert "max_agencies" in workflow
    assert "--max-agencies \"${{ inputs.max_agencies || '0' }}\"" in workflow
    assert "if [ \"${{ inputs.probe_homepages || 'true' }}\" = \"true\" ]; then" in workflow
    assert "python scripts/discover_govt_source_candidates.py \"${args[@]}\"" in workflow
    assert "--probe-homepages --max-agencies 0" not in workflow
