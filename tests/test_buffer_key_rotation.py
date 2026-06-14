from scripts.check_buffer_key_rotation import build_rotation_status, write_github_output


def test_buffer_key_rotation_status_ok_before_warning_window() -> None:
    status = build_rotation_status(expires_on="2026-07-12", today="2026-06-01")

    assert status["status"] == "ok"
    assert status["due"] is False
    assert status["days_remaining"] == 41


def test_buffer_key_rotation_status_warning_inside_warning_window() -> None:
    status = build_rotation_status(expires_on="2026-07-12", today="2026-06-14")

    assert status["status"] == "warning"
    assert status["due"] is True
    assert status["days_remaining"] == 28
    assert "BUFFER_API_KEY" in status["issue_body"]


def test_buffer_key_rotation_status_critical_and_expired() -> None:
    critical = build_rotation_status(expires_on="2026-07-12", today="2026-07-08")
    expired = build_rotation_status(expires_on="2026-07-12", today="2026-07-13")

    assert critical["status"] == "critical"
    assert critical["days_remaining"] == 4
    assert expired["status"] == "expired"
    assert expired["days_remaining"] == -1


def test_write_github_output(tmp_path) -> None:
    status = build_rotation_status(expires_on="2026-07-12", today="2026-06-14")
    output_path = tmp_path / "github-output.txt"

    write_github_output(status, output_path)

    output = dict(
        line.split("=", maxsplit=1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    )
    assert output["due"] == "true"
    assert output["status"] == "warning"
    assert output["issue_title"] == "Buffer API key rotation due"
