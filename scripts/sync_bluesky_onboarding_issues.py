"""Plan and optionally apply bounded Bluesky onboarding issue reconciliation."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

MIRROR_ID_PATTERN = re.compile(r"Mirror ID:\s*`([^`]+)`", re.IGNORECASE)
COHORT_TITLE_PATTERN = re.compile(
    r"^\[Cohort\s+(\d{2})\]\s+Bluesky archive mirror onboarding$",
    re.IGNORECASE,
)


def gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def load_remote_issues(repo: str) -> list[dict[str, Any]]:
    payload = gh(
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,title,body,state,url",
    )
    value = json.loads(payload)
    if not isinstance(value, list):
        raise ValueError("GitHub issue inventory must be a list")
    return value


def _mirror_id(issue: Mapping[str, Any]) -> str:
    match = MIRROR_ID_PATTERN.search(str(issue.get("body") or ""))
    return match.group(1) if match else ""


def _cohort_number(issue: Mapping[str, Any]) -> int | None:
    match = COHORT_TITLE_PATTERN.fullmatch(str(issue.get("title") or "").strip())
    return int(match.group(1)) if match else None


def build_issue_plan(
    registry: Mapping[str, Any],
    remote_issues: list[Mapping[str, Any]],
    *,
    parent: int,
    cohort_size: int,
    generated_at: str,
) -> dict[str, Any]:
    if not 1 <= cohort_size <= 50:
        raise ValueError("cohort_size must be between 1 and 50")
    mirrors = registry.get("mirrors")
    if not isinstance(mirrors, list):
        raise ValueError("registry mirrors must be a list")
    by_number = {int(issue["number"]): issue for issue in remote_issues}
    by_mirror: dict[str, list[Mapping[str, Any]]] = {}
    remote_cohorts: dict[int, list[Mapping[str, Any]]] = {}
    for issue in remote_issues:
        mirror_id = _mirror_id(issue)
        if mirror_id:
            by_mirror.setdefault(mirror_id, []).append(issue)
        cohort_number = _cohort_number(issue)
        if cohort_number is not None:
            remote_cohorts.setdefault(cohort_number, []).append(issue)

    registry_cohorts = registry.get("onboarding_cohorts") or {}
    cohort_count = (len(mirrors) + cohort_size - 1) // cohort_size
    cohorts: list[dict[str, Any]] = []
    for number in range(1, cohort_count + 1):
        key = f"cohort-{number:02d}"
        expected_title = f"[Cohort {number:02d}] Bluesky archive mirror onboarding"
        registry_issue = registry_cohorts.get(key)
        matches = remote_cohorts.get(number, [])
        remote = by_number.get(int(registry_issue)) if registry_issue else None
        if remote and _cohort_number(remote) == number:
            status = "existing_closed" if remote.get("state") == "CLOSED" else "existing"
            issue_number = int(remote["number"])
        elif len(matches) == 1:
            status = "registry_repair"
            issue_number = int(matches[0]["number"])
        elif len(matches) > 1:
            status = "duplicate"
            issue_number = None
        elif registry_issue:
            status = "stale_registry"
            issue_number = int(registry_issue)
        else:
            status = "proposed"
            issue_number = None
        cohorts.append(
            {
                "cohort_number": number,
                "cohort_key": key,
                "title": expected_title,
                "registry_issue_number": registry_issue,
                "issue_number": issue_number,
                "status": status,
                "remote_matches": sorted(int(issue["number"]) for issue in matches),
                "member_count": min(cohort_size, len(mirrors) - (number - 1) * cohort_size),
            }
        )

    onboarding: list[dict[str, Any]] = []
    for position, mirror in enumerate(mirrors):
        mirror_id = str(mirror["mirror_id"])
        cohort_number = position // cohort_size + 1
        registry_issue = mirror.get("issue_number")
        matches = by_mirror.get(mirror_id, [])
        remote = by_number.get(int(registry_issue)) if registry_issue else None
        if remote and _mirror_id(remote) == mirror_id:
            status = "existing_closed" if remote.get("state") == "CLOSED" else "existing"
            issue_number = int(remote["number"])
        elif len(matches) == 1:
            status = "registry_repair"
            issue_number = int(matches[0]["number"])
        elif len(matches) > 1:
            status = "duplicate"
            issue_number = None
        elif registry_issue:
            status = "stale_registry"
            issue_number = int(registry_issue)
        else:
            status = "proposed"
            issue_number = None
        onboarding.append(
            {
                "position": position,
                "mirror_id": mirror_id,
                "agency_name": mirror["agency_name"],
                "environment": mirror["environment"],
                "cohort_number": cohort_number,
                "cohort_key": f"cohort-{cohort_number:02d}",
                "registry_issue_number": registry_issue,
                "issue_number": issue_number,
                "status": status,
                "remote_matches": sorted(int(issue["number"]) for issue in matches),
            }
        )

    blocker_states = {"duplicate", "stale_registry"}
    summary = {
        "cohort_count": len(cohorts),
        "onboarding_count": len(onboarding),
        "existing": sum(row["status"] == "existing" for row in onboarding),
        "existing_closed": sum(row["status"] == "existing_closed" for row in onboarding),
        "registry_repairs": sum(row["status"] == "registry_repair" for row in onboarding),
        "proposed": sum(row["status"] == "proposed" for row in onboarding),
        "blockers": sum(row["status"] in blocker_states for row in onboarding)
        + sum(row["status"] in blocker_states for row in cohorts),
    }
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "repository": registry.get("repository", "edithatogo/sm-govt-nz"),
        "parent_issue": parent,
        "cohort_size": cohort_size,
        "dry_run": True,
        "summary": summary,
        "cohorts": cohorts,
        "onboarding": onboarding,
        "registry_write_performed": False,
        "github_write_performed": False,
    }


def _node_id(repo: str, issue_number: int) -> str:
    return gh("api", f"repos/{repo}/issues/{issue_number}", "--jq", ".node_id")


def _attach_subissue(repo: str, parent: int, child: int) -> None:
    query = (
        "mutation($issue:ID!,$sub:ID!){addSubIssue(input:"
        "{issueId:$issue,subIssueId:$sub}){issue{number}}}"
    )
    gh(
        "api",
        "graphql",
        "-f",
        f"query={query}",
        "-f",
        f"issue={_node_id(repo, parent)}",
        "-f",
        f"sub={_node_id(repo, child)}",
    )


def _create_issue(repo: str, title: str, body: str) -> tuple[int, str]:
    url = gh("issue", "create", "--repo", repo, "--title", title, "--body", body)
    return int(url.rsplit("/", 1)[-1]), url


def apply_issue_plan(
    registry: dict[str, Any],
    plan: dict[str, Any],
    *,
    repo: str,
    limit: int,
) -> dict[str, Any]:
    if plan["summary"]["blockers"]:
        raise RuntimeError("issue plan contains duplicate or stale-registry blockers")
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    cohorts = registry.setdefault("onboarding_cohorts", {})
    mirrors = {str(row["mirror_id"]): row for row in registry["mirrors"]}
    parent = int(plan["parent_issue"])
    created_cohorts = 0
    created_onboarding = 0
    repaired = 0

    selected_proposals = [row for row in plan["onboarding"] if row["status"] == "proposed"][:limit]
    required_cohorts = {row["cohort_key"] for row in selected_proposals}
    for row in plan["cohorts"]:
        if row["status"] in {"existing", "existing_closed", "registry_repair"}:
            if row["issue_number"]:
                cohorts[row["cohort_key"]] = int(row["issue_number"])
                if row["status"] == "registry_repair":
                    repaired += 1
            continue
        if row["status"] != "proposed" or row["cohort_key"] not in required_cohorts:
            continue
        number, _ = _create_issue(
            repo,
            row["title"],
            f"Parent rollout: #{parent}\n\nContains at most {plan['cohort_size']} operator-supervised agency onboarding subissues.",
        )
        _attach_subissue(repo, parent, number)
        cohorts[row["cohort_key"]] = number
        row["issue_number"] = number
        row["status"] = "created"
        created_cohorts += 1

    selected_mirror_ids = {row["mirror_id"] for row in selected_proposals}
    for row in plan["onboarding"]:
        mirror = mirrors[row["mirror_id"]]
        if row["status"] in {"existing", "existing_closed", "registry_repair"}:
            if row["issue_number"] and mirror.get("issue_number") != row["issue_number"]:
                mirror["issue_number"] = int(row["issue_number"])
                url = f"https://github.com/{repo}/issues/{row['issue_number']}"
                if url not in mirror.setdefault("evidence", []):
                    mirror["evidence"].append(url)
                repaired += 1
            continue
        if row["status"] != "proposed" or row["mirror_id"] not in selected_mirror_ids:
            continue
        cohort_issue = int(cohorts[row["cohort_key"]])
        title = f"[Onboarding] Bluesky archive mirror: {row['agency_name']}"
        body = (
            f"Parent rollout: #{parent}; cohort: #{cohort_issue}\n\n"
            f"Mirror ID: `{row['mirror_id']}`\n"
            f"GitHub Environment: `{row['environment']}`\n\n"
            "Account creation remains operator-supervised and posting remains disabled until preflight passes."
        )
        number, url = _create_issue(repo, title, body)
        _attach_subissue(repo, cohort_issue, number)
        mirror["issue_number"] = number
        if url not in mirror.setdefault("evidence", []):
            mirror["evidence"].append(url)
        row["issue_number"] = number
        row["status"] = "created"
        created_onboarding += 1

    plan["dry_run"] = False
    plan["registry_write_performed"] = True
    plan["github_write_performed"] = bool(created_cohorts or created_onboarding)
    plan["apply_result"] = {
        "created_cohorts": created_cohorts,
        "created_onboarding": created_onboarding,
        "registry_repairs": repaired,
        "limit": limit,
    }
    return plan


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/mirror_accounts.json"))
    parser.add_argument("--repo", default="edithatogo/sm-govt-nz")
    parser.add_argument("--parent", type=int, default=23)
    parser.add_argument("--cohort-size", type=int, default=50)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--plan-output",
        type=Path,
        default=Path("conductor/bluesky_onboarding_issue_plan.json"),
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    remote_issues = load_remote_issues(args.repo)
    plan = build_issue_plan(
        registry,
        remote_issues,
        parent=args.parent,
        cohort_size=args.cohort_size,
        generated_at="live_github_reconciliation",
    )
    if args.apply:
        apply_issue_plan(registry, plan, repo=args.repo, limit=args.limit)
        args.registry.write_text(
            json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    _write(args.plan_output, plan)
    print(json.dumps({**plan["summary"], **plan.get("apply_result", {})}, sort_keys=True))


if __name__ == "__main__":
    main()
