from pathlib import Path


HISTORICAL_BACKFILL_SCRIPTS = [
    Path("scripts/archive_bluesky_history.py"),
    Path("scripts/archive_x_history.py"),
    Path("scripts/archive_rss_history.py"),
]

FORBIDDEN_BACKFILL_REFERENCES = [
    "conductor/state.json",
    "save_state(",
    "post_to_x",
    "buffer",
    "syndicate",
]


def test_historical_backfill_scripts_do_not_touch_live_syndication_state():
    for script in HISTORICAL_BACKFILL_SCRIPTS:
        source = script.read_text(encoding="utf-8").lower()
        for forbidden in FORBIDDEN_BACKFILL_REFERENCES:
            assert forbidden.lower() not in source, f"{script} references live posting/state: {forbidden}"
