"""Unit tests for scripts/validate_git_mirrors.py."""

from dataclasses import dataclass

from scripts.validate_git_mirrors import (
    MirrorValidation,
    build_report,
    mirror_host,
    validate_mirrors,
)


@dataclass
class Completed:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def test_mirror_host_parses_ssh_and_https_urls() -> None:
    assert mirror_host("git@gitlab.com:owner/repo.git") == "gitlab.com"
    assert mirror_host("https://codeberg.org/owner/repo.git") == "codeberg.org"


def test_validate_mirrors_reports_missing_url() -> None:
    result = validate_mirrors(mirror_url="", runner=FakeRunner())

    assert result.status == "missing_mirror_url"
    assert result.ok is False


def test_validate_mirrors_compares_aligned_remote_head() -> None:
    runner = FakeRunner(local_head="abc123", remote_head="abc123")

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        compare_head=True,
        runner=runner,
    )

    assert result.ok is True
    assert result.remote_alignment_checked is True
    assert result.local_head == "abc123"
    assert result.remote_head == "abc123"


def test_validate_mirrors_reports_misaligned_remote_head() -> None:
    runner = FakeRunner(local_head="abc123", remote_head="def456")

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        compare_head=True,
        runner=runner,
    )

    assert result.status == "remote_misaligned"
    assert result.ok is False


def test_validate_mirrors_checks_ssh_before_remote_compare() -> None:
    runner = FakeRunner(local_head="abc123", remote_head="abc123", ssh_ok=True)

    result = validate_mirrors(
        mirror_url="git@gitlab.com:owner/repo.git",
        compare_head=True,
        runner=runner,
    )

    assert result.ok is True
    assert result.ssh_access_checked is True
    assert runner.commands[0][0] == "ssh"


def test_validate_mirrors_reports_ssh_failure() -> None:
    runner = FakeRunner(local_head="abc123", remote_head="abc123", ssh_ok=False)

    result = validate_mirrors(
        mirror_url="git@gitlab.com:owner/repo.git",
        compare_head=True,
        runner=runner,
    )

    assert result.status == "ssh_access_failed"
    assert result.remote_alignment_checked is False


class FakeRunner:
    def __init__(self, *, local_head="abc123", remote_head="", ssh_ok=True) -> None:
        self.local_head = local_head
        self.remote_head = remote_head
        self.ssh_ok = ssh_ok
        self.commands = []

    def __call__(self, args, capture_output, text, check):
        self.commands.append(list(args))
        if args[0] == "ssh":
            stderr = "successfully authenticated" if self.ssh_ok else "Permission denied (publickey)."
            return Completed(list(args), returncode=1, stderr=stderr)
        if args[:3] == ["git", "rev-parse", "master"]:
            return Completed(list(args), stdout=self.local_head)
        if args[:2] == ["git", "ls-remote"]:
            stdout = f"{self.remote_head}\trefs/heads/master\n" if self.remote_head else ""
            return Completed(list(args), stdout=stdout)
        return Completed(list(args), returncode=1, stderr="unexpected command")

def test_validate_mirrors_dry_run_skips_ssh() -> None:
    """dry_run=True should skip SSH access check and skip remote fetch."""
    runner = FakeRunner(ssh_ok=False)  # would fail if SSH was attempted

    result = validate_mirrors(
        mirror_url="git@gitlab.com:owner/repo.git",
        compare_head=True,
        dry_run=True,
        runner=runner,
    )

    assert result.ok is True
    assert result.ssh_access_checked is True
    assert result.remote_alignment_checked is False
    assert "dry-run" in result.detail
    assert not any(cmd[0] == "ssh" for cmd in runner.commands)


def test_validate_mirrors_dry_run_https_skips_ls_remote() -> None:
    """dry-run with HTTPS URL should not invoke ls-remote."""
    runner = FakeRunner(local_head="abc123")

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        compare_head=True,
        dry_run=True,
        runner=runner,
    )

    assert result.ok is True
    assert result.local_head == "abc123"
    assert not any("ls-remote" in cmd for cmd in runner.commands)


def test_validate_mirrors_reports_local_branch_missing() -> None:
    """When git rev-parse fails, report local_branch_missing."""

    def failing_runner(args, capture_output, text, check):
        return Completed(list(args), returncode=128, stderr="fatal: not a git repository")

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        branch="nonexistent",
        compare_head=True,
        runner=failing_runner,
    )

    assert result.status == "local_branch_missing"
    assert result.ok is False
    assert "nonexistent" in result.detail


def test_validate_mirrors_reports_remote_branch_missing() -> None:
    """When ls-remote returns empty, report remote_branch_missing."""
    runner = FakeRunner(local_head="abc123", remote_head="")

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        branch="master",
        compare_head=True,
        runner=runner,
    )

    assert result.status == "remote_branch_missing"
    assert result.ok is False
    assert result.remote_alignment_checked is True


def test_validate_mirrors_reports_remote_lookup_failed() -> None:
    """When ls-remote command itself fails, report remote_lookup_failed."""

    def failing_ls_remote(args, capture_output, text, check):
        cmd = list(args)
        if cmd[:2] == ["git", "ls-remote"]:
            return Completed(cmd, returncode=128, stderr="fatal: could not read Username")
        return FakeRunner()(args, capture_output, text, check)

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        compare_head=True,
        runner=failing_ls_remote,
    )

    assert result.status == "remote_lookup_failed"
    assert result.ok is False
    assert result.remote_alignment_checked is False


def test_validate_mirrors_no_compare_does_not_fetch_remote() -> None:
    runner = FakeRunner()

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        compare_head=False,
        runner=runner,
    )

    assert result.ok is True
    assert result.remote_alignment_checked is False
    assert result.local_head == ""
    assert result.remote_head == ""


def test_validate_mirrors_custom_branch() -> None:
    runner = FakeRunner(local_head="def789", remote_head="def789")

    result = validate_mirrors(
        mirror_url="https://codeberg.org/owner/repo.git",
        branch="develop",
        compare_head=True,
        runner=runner,
    )

    assert result.ok is True
    assert any("develop" in cmd for cmd in runner.commands)


def test_mirror_validation_to_json() -> None:
    v = MirrorValidation(
        status="ok",
        mirror_url_present=True,
        ssh_access_checked=True,
        remote_alignment_checked=True,
        local_head="abc123",
        remote_head="abc123",
        detail="All good.",
    )
    d = v.to_json()
    assert d["status"] == "ok"
    assert d["ok"] is True
    assert d["local_head"] == "abc123"


def test_build_report_includes_tool_and_validation() -> None:
    v = MirrorValidation(
        status="ok",
        mirror_url_present=True,
        ssh_access_checked=False,
        remote_alignment_checked=False,
        detail="Configured.",
    )
    r = build_report(v)
    assert r["tool"] == "validate_git_mirrors"
    assert "timestamp" in r
    assert r["validation"]["status"] == "ok"

