from scripts.dispatch_archive_completion_queue import command_for, select_dispatches


def test_dispatch_selection_is_bounded_and_deduplicated() -> None:
    dispatch = {"dispatchable": True, "workflow": "archive.yml", "inputs": {"source_type": "linkedin"}}
    queue = {"items": [{"dispatch": dispatch}, {"dispatch": dispatch}, {"dispatch": {"dispatchable": False}}]}
    assert select_dispatches(queue, 5) == [dispatch]


def test_command_uses_structured_workflow_inputs() -> None:
    command = command_for({"workflow": "archive.yml", "inputs": {"dry_run": "false"}}, "master")
    assert command == ["gh", "workflow", "run", "archive.yml", "--ref", "master", "--field", "dry_run=false"]
