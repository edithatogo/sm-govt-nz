from scripts.profile_discovery import build_social_analyzer_command
from scripts.upstream_contribution import build_issue_command, build_pr_command


def test_build_social_analyzer_command_is_operator_installable() -> None:
    command = build_social_analyzer_command("Ministry of Health", command="social-analyzer")

    assert command[:3] == ["social-analyzer", "--username", "Ministry of Health"]
    assert "--metadata" in command


def test_upstream_contribution_commands_target_upstream_repo() -> None:
    issue = build_issue_command("yt-dlp/yt-dlp", "Bug", "Body")
    pr = build_pr_command("yt-dlp/yt-dlp", "60217257:fix-branch", "Fix", "Body")

    assert issue[:4] == ["gh", "issue", "create", "--repo"]
    assert "yt-dlp/yt-dlp" in issue
    assert pr[:4] == ["gh", "pr", "create", "--repo"]
    assert "60217257:fix-branch" in pr
