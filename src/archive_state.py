import json
from pathlib import Path
from typing import TypedDict, cast


class ArchiveState(TypedDict):
    source_cursors: dict[str, str]


def load_archive_state(path: str | Path = "conductor/archive_state.json") -> ArchiveState:
    state_path = Path(path)
    if not state_path.exists():
        return {"source_cursors": {}}

    with state_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if "source_cursors" not in data or not isinstance(data["source_cursors"], dict):
        raise ValueError("Invalid archive state: must contain source_cursors object.")
    return cast(ArchiveState, data)


def save_archive_cursor(
    source_id: str,
    cursor: str,
    path: str | Path = "conductor/archive_state.json",
) -> ArchiveState:
    state = load_archive_state(path)
    state["source_cursors"][source_id] = cursor
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return state
