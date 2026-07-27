"""Bounded, secret-free learning policy for operator-supervised Bluesky onboarding.

This is intentionally not an autonomous account creator. It learns which
navigation plans and candidate ordering work from sanitized outcome events.
Credentials, cookies, challenge data, mailbox contents, and verification URLs
must never be supplied to this module.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

DEFAULT_STATE = Path("conductor/bluesky_onboarding_heuristic_state.json")
DEFAULT_PILOT_REPORT = Path("conductor/bluesky_mirror_pilot_candidates.json")
OUTCOMES = {
    "account_created",
    "challenge_operator_required",
    "email_verification_operator_required",
    "profile_compliance_passed",
    "profile_compliance_failed",
    "credential_handoff_passed",
    "credential_handoff_failed",
    "preflight_passed",
    "preflight_failed",
    "blocked_external",
}
PLANS = ("headed_uc_cdp", "headed_standard_cdp", "operator_manual")


@dataclass(frozen=True)
class Plan:
    name: str
    steps: tuple[str, ...]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "policy": "bounded_uc_cdp_operator_supervision",
        "events": [],
        "plans": {name: {"attempts": 0, "successes": 0} for name in PLANS},
        "updated_at": None,
    }


def load_state(path: str | Path = DEFAULT_STATE) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return default_state()
    state = json.loads(target.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1 or not isinstance(state.get("events"), list):
        raise ValueError("Invalid onboarding heuristic state")
    return state


def load_pilot_report(path: str | Path = DEFAULT_PILOT_REPORT) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {"schema_version": 1, "candidates": []}
    report = json.loads(target.read_text(encoding="utf-8"))
    if report.get("schema_version") != 1 or not isinstance(
        report.get("candidates"), list
    ):
        raise ValueError("Invalid Bluesky pilot candidate report")
    return report


def save_state(state: Mapping[str, Any], path: str | Path = DEFAULT_STATE) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _score(stats: Mapping[str, Any], total_attempts: int) -> float:
    attempts = int(stats.get("attempts", 0))
    successes = int(stats.get("successes", 0))
    # Upper-confidence bound: explore plans with little evidence while
    # preferring plans with a strong observed completion rate.
    total = max(1, total_attempts)
    return (successes + 1) / (attempts + 2) + math.sqrt(
        2 * math.log(total + 1) / (attempts + 1)
    )


def choose_plan(state: Mapping[str, Any]) -> Plan:
    plans = state.get("plans", {})
    total_attempts = sum(
        int(value.get("attempts", 0))
        for value in plans.values()
        if isinstance(value, Mapping)
    )
    name = max(
        PLANS,
        key=lambda item: _score(
            plans.get(item, {}) if isinstance(plans.get(item), Mapping) else {},
            total_attempts,
        ),
    )
    steps = {
        "headed_uc_cdp": (
            "launch headed SeleniumBase UC browser",
            "attach Playwright with connect_over_cdp",
            "fill only non-challenge registration fields",
            "stop for operator submission or platform challenge",
            "configure disclosure and bot label",
            "create app password with direct messages disabled",
            "run non-posting preflight",
        ),
        "headed_standard_cdp": (
            "launch headed Chromium browser",
            "attach Playwright with connect_over_cdp",
            "follow the same operator-stop policy",
            "run profile compliance and non-posting preflight",
        ),
        "operator_manual": (
            "provide a deterministic onboarding checklist",
            "operator completes registration and challenges",
            "resume at profile compliance and credential handoff",
        ),
    }
    return Plan(name, steps[name])


def rank_candidates(
    registry: Mapping[str, Any],
    state: Mapping[str, Any],
    pilot_report: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    events = state.get("events", [])
    failures: dict[str, int] = {}
    for event in events:
        if (
            event.get("outcome", "").endswith("failed")
            or event.get("outcome") == "blocked_external"
        ):
            mirror_id = str(event.get("mirror_id") or "")
            failures[mirror_id] = failures.get(mirror_id, 0) + 1
    ranked_backlogs = {
        str(row.get("mirror_id")): int(row.get("eligible_backlog", 0))
        for row in (pilot_report or {}).get("candidates", [])
        if (
            isinstance(row, Mapping)
            and int(row.get("eligible_backlog", 0)) > 0
            and isinstance(row.get("issue_number"), int)
        )
    }
    rows = [
        row
        for row in registry.get("mirrors", [])
        if row.get("lifecycle_state") in {"candidate", "operator_onboarding"}
    ]
    return sorted(
        rows,
        key=lambda row: (
            failures.get(str(row.get("mirror_id")), 0),
            0 if str(row.get("mirror_id")) in ranked_backlogs else 1,
            ranked_backlogs.get(str(row.get("mirror_id")), 0),
            str(row.get("mirror_id")),
        ),
    )


def record_event(state: dict[str, Any], mirror_id: str, outcome: str, plan: str) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise ValueError(f"Unsupported sanitized outcome: {outcome}")
    if plan not in PLANS:
        raise ValueError(f"Unsupported onboarding plan: {plan}")
    event = {"mirror_id": mirror_id, "outcome": outcome, "plan": plan, "recorded_at": _now()}
    state.setdefault("events", []).append(event)
    stats = state.setdefault("plans", {}).setdefault(plan, {"attempts": 0, "successes": 0})
    stats["attempts"] = int(stats.get("attempts", 0)) + 1
    if outcome in {"account_created", "profile_compliance_passed", "credential_handoff_passed", "preflight_passed"}:
        stats["successes"] = int(stats.get("successes", 0)) + 1
    state["updated_at"] = _now()
    return event
