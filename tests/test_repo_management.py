from pathlib import Path
import json


def test_ci_runs_actionlint_before_python_tests() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "raven-actions/actionlint@v2" in workflow
    assert 'python-version: "3.14"' in workflow
    assert "python -m pytest tests -q" in workflow


def test_register_archive_source_workflow_has_valid_defaults() -> None:
    workflow = Path(".github/workflows/register_archive_source.yml").read_text(encoding="utf-8")

    assert 'default: "review_required"' in workflow
    assert 'python-version: "3.14"' in workflow
    assert 'default: "candidate"' in workflow


def test_local_repo_validation_wrapper_uses_uv_and_workflow_contract_tests() -> None:
    wrapper = Path("scripts/validate_repo.ps1").read_text(encoding="utf-8")

    assert "scripts/dev.ps1" in wrapper
    assert "actionlint is not installed locally" in wrapper
    assert "tests/test_govt_source_discovery_workflow.py" in wrapper
    assert "tests/test_archive_registered_sources_workflow.py" in wrapper
    assert "tests/test_threads_workflow_reporting.py" in wrapper
    assert "tests/test_publish_archives_workflow.py" in wrapper


def test_workflows_do_not_pin_python_311() -> None:
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in Path(".github/workflows").glob("*.yml")
    )

    assert 'python-version: "3.11"' not in workflow_text
    assert "uv python install 3.11" not in workflow_text


def test_workflows_install_python_dependencies_with_uv() -> None:
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in Path(".github/workflows").glob("*.yml")
    )

    assert "python -m pip install -r requirements" not in workflow_text
    assert "uv pip install --system -r requirements" in workflow_text


def test_renovate_tracks_latest_python_and_workflow_dependencies() -> None:
    config = json.loads(Path("renovate.json").read_text(encoding="utf-8"))

    managers = {
        manager
        for rule in config["packageRules"]
        for manager in rule.get("matchManagers", [])
    }
    assert config["lockFileMaintenance"]["enabled"] is True
    assert "pip_requirements" in managers
    assert "pep621" in managers
    assert "github-actions" in managers


def test_repo_management_docs_capture_script_workflow_guardrails() -> None:
    docs = Path("docs/repo-management.md").read_text(encoding="utf-8")

    assert ".\\scripts\\validate_repo.ps1 workflows" in docs
    assert "actionlint" in docs
    assert "Workflow behavior that affects archive state" in docs
    assert "conductor/archive_publication_status.json" in docs
