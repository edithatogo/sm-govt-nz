import json
import os
from typing import Dict, List, Literal, NotRequired, TypedDict, cast

class MonitoredAccount(TypedDict):
    handle: str
    did: str
    name: str
    syndicate_to: List[str]

class SyndicationTargetConfig(TypedDict):
    enabled: bool
    max_posts_per_run: NotRequired[int]
    backlog_enabled: NotRequired[bool]
    backlog_max_posts_per_run: NotRequired[int]
    backlog_order: NotRequired[Literal["oldest_first", "newest_first"]]
    archive_replay_enabled: NotRequired[bool]
    archive_replay_max_posts_per_run: NotRequired[int]
    archive_replay_sources: NotRequired[List[str]]
    pipeline_stage_enabled: NotRequired[bool]
    account_handle: NotRequired[str]
    profile_url: NotRequired[str]
    gated_by: NotRequired[str]

class AppConfig(TypedDict):
    monitored_accounts: List[MonitoredAccount]
    syndication_targets: Dict[str, SyndicationTargetConfig]

class AppState(TypedDict):
    last_seen_post_ids: Dict[str, str]

class BacklogState(TypedDict):
    posted_post_ids: Dict[str, List[str]]

def load_config(config_path: str = "config.json") -> AppConfig:
    """Loads and returns the main application configuration from config.json."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Basic validation
    if "monitored_accounts" not in data or "syndication_targets" not in data:
        raise ValueError("Invalid config.json: Must contain 'monitored_accounts' and 'syndication_targets'.")
        
    return cast(AppConfig, data)

def load_state(state_path: str = "conductor/state.json") -> AppState:
    """Loads and returns the application state from state.json."""
    if not os.path.exists(state_path):
        # Return an empty default state if the state file doesn't exist
        return {"last_seen_post_ids": {}}
        
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if "last_seen_post_ids" not in data:
        raise ValueError("Invalid state.json: Must contain 'last_seen_post_ids'.")
        
    return cast(AppState, data)

def save_state(state: AppState, state_path: str = "conductor/state.json") -> None:
    """Saves the application state back to state.json."""
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def load_backlog_state(state_path: str = "conductor/bluesky_backlog_state.json") -> BacklogState:
    """Loads backlog posting state for historical mirror batches."""
    if not os.path.exists(state_path):
        return {"posted_post_ids": {}}

    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "posted_post_ids" not in data:
        raise ValueError("Invalid backlog state: Must contain 'posted_post_ids'.")

    return cast(BacklogState, data)

def save_backlog_state(
    state: BacklogState,
    state_path: str = "conductor/bluesky_backlog_state.json",
) -> None:
    """Saves historical backlog posting state."""
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
