from dataclasses import dataclass

from scripts.validate_git_mirrors import mirror_host, validate_mirrors


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
