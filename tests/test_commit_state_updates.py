from scripts import commit_state_updates as commit_state


def test_commit_selected_paths_skips_when_no_selected_changes(monkeypatch) -> None:
    calls = []

    def fake_run_git(args, check=True):
        calls.append(args)
        if args == ["diff", "--cached", "--quiet"]:
            return commit_state.GitResult(returncode=0, stdout="", stderr="")
        return commit_state.GitResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(commit_state, "run_git", fake_run_git)

    committed = commit_state.commit_selected_paths("Update state", ["conductor/state.json"])

    assert committed is False
    assert ["add", "--", "conductor/state.json"] in calls
    assert ["commit", "-m", "Update state"] not in calls


def test_commit_selected_paths_skips_unmatched_globs(monkeypatch, capsys, tmp_path) -> None:
    calls = []

    def fake_run_git(args, check=True):
        calls.append(args)
        return commit_state.GitResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(commit_state, "run_git", fake_run_git)

    committed = commit_state.commit_selected_paths(
        "Archive empty platform",
        [str(tmp_path / "raw" / "**"), str(tmp_path / "normalized" / "**")],
    )

    assert committed is False
    assert f"Skipping unmatched state path glob: {tmp_path / 'raw' / '**'}" in capsys.readouterr().out
    assert not any(call[:1] == ["add"] for call in calls)


def test_push_with_rebase_retries_when_remote_moves(monkeypatch) -> None:
    calls = []
    push_attempts = {"count": 0}

    def fake_run_git(args, check=True):
        calls.append(args)
        if args[:2] == ["push", "origin"]:
            push_attempts["count"] += 1
            if push_attempts["count"] == 1:
                return commit_state.GitResult(returncode=1, stdout="", stderr="non-fast-forward")
        return commit_state.GitResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(commit_state, "run_git", fake_run_git)

    commit_state.push_with_rebase("master", max_attempts=2)

    assert push_attempts["count"] == 2
    assert calls.count(["fetch", "origin", "master"]) == 2
    assert calls.count(["rebase", "origin/master"]) == 2


def test_push_with_rebase_delays_only_after_a_failed_push(monkeypatch) -> None:
    sleeps = []
    monkeypatch.setattr(commit_state.time, "sleep", sleeps.append)
    push_attempts = {"count": 0}

    def fake_run_git(args, check=True):
        if args[:2] == ["push", "origin"]:
            push_attempts["count"] += 1
            if push_attempts["count"] == 1:
                return commit_state.GitResult(returncode=1, stdout="", stderr="remote moved")
        return commit_state.GitResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(commit_state, "run_git", fake_run_git)
    commit_state.push_with_rebase("master", max_attempts=2)

    assert len(sleeps) == 1
    assert 1.0 <= sleeps[0] <= 3.0
