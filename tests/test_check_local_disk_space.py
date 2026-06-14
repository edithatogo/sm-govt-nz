from collections import namedtuple

from scripts import check_local_disk_space


Usage = namedtuple("Usage", ["total", "used", "free"])


def test_check_disk_space_passes_when_free_space_meets_threshold(monkeypatch) -> None:
    monkeypatch.setattr(
        check_local_disk_space.shutil,
        "disk_usage",
        lambda path: Usage(total=1000, used=100, free=500 * 1024 * 1024),
    )

    result = check_local_disk_space.check_disk_space(".", required_mb=250)

    assert result.ok is True
    assert result.free_mb == 500
    assert result.required_mb == 250


def test_check_disk_space_fails_when_free_space_is_below_threshold(monkeypatch) -> None:
    monkeypatch.setattr(
        check_local_disk_space.shutil,
        "disk_usage",
        lambda path: Usage(total=1000, used=990, free=10 * 1024 * 1024),
    )

    result = check_local_disk_space.check_disk_space(".", required_mb=250)

    assert result.ok is False
    assert result.free_mb == 10
