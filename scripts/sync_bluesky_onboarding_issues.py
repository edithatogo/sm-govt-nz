import argparse
import json
import subprocess
from pathlib import Path


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create bounded Bluesky onboarding subissues.")
    parser.add_argument("--registry", default="config/mirror_accounts.json")
    parser.add_argument("--repo", default="edithatogo/sm-govt-nz")
    parser.add_argument("--parent", type=int, default=23)
    parser.add_argument("--cohort-size", type=int, default=50)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    path = Path(args.registry)
    registry = json.loads(path.read_text(encoding="utf-8"))
    parent_node = gh("api", f"repos/{args.repo}/issues/{args.parent}", "--jq", ".node_id")
    cohorts = registry.setdefault("onboarding_cohorts", {})
    created = 0
    for position, mirror in enumerate(registry["mirrors"]):
        if mirror.get("issue_number") or created >= args.limit:
            continue
        cohort_number = position // args.cohort_size + 1
        cohort_key = f"cohort-{cohort_number:02d}"
        cohort_issue = cohorts.get(cohort_key)
        if not cohort_issue:
            cohort_url = gh(
                "issue",
                "create",
                "--repo",
                args.repo,
                "--title",
                f"[Cohort {cohort_number:02d}] Bluesky archive mirror onboarding",
                "--body",
                f"Parent rollout: #{args.parent}\n\nContains at most {args.cohort_size} operator-supervised agency onboarding subissues.",
            )
            cohort_issue = int(cohort_url.rsplit("/", 1)[-1])
            cohort_node = gh(
                "api", f"repos/{args.repo}/issues/{cohort_issue}", "--jq", ".node_id"
            )
            query = "mutation($issue:ID!,$sub:ID!){addSubIssue(input:{issueId:$issue,subIssueId:$sub}){issue{number}}}"
            gh(
                "api",
                "graphql",
                "-f",
                f"query={query}",
                "-f",
                f"issue={parent_node}",
                "-f",
                f"sub={cohort_node}",
            )
            cohorts[cohort_key] = cohort_issue
        cohort_node = gh(
            "api", f"repos/{args.repo}/issues/{cohort_issue}", "--jq", ".node_id"
        )
        title = f"[Onboarding] Bluesky archive mirror: {mirror['agency_name']}"
        body = (
            f"Parent rollout: #{args.parent}; cohort: #{cohort_issue}\n\n"
            f"Mirror ID: `{mirror['mirror_id']}`\n"
            f"GitHub Environment: `{mirror['environment']}`\n\n"
            "Account creation remains operator-supervised and posting remains disabled until preflight passes."
        )
        url = gh("issue", "create", "--repo", args.repo, "--title", title, "--body", body)
        number = int(url.rsplit("/", 1)[-1])
        child_node = gh("api", f"repos/{args.repo}/issues/{number}", "--jq", ".node_id")
        query = "mutation($issue:ID!,$sub:ID!){addSubIssue(input:{issueId:$issue,subIssueId:$sub}){issue{number}}}"
        gh("api", "graphql", "-f", f"query={query}", "-f", f"issue={cohort_node}", "-f", f"sub={child_node}")
        mirror["issue_number"] = number
        mirror.setdefault("evidence", []).append(url)
        created += 1
    path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"created": created, "parent": args.parent, "cohorts": cohorts}))


if __name__ == "__main__":
    main()
