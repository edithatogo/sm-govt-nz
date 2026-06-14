import argparse
from pathlib import Path


def render_worker_config(
    *,
    output_path: str | Path,
    worker_name: str,
    github_repo: str,
    allowed_recipients: str,
) -> None:
    content = "\n".join(
        [
            f'name = "{_toml_string(worker_name)}"',
            'main = "courts_nz_email_worker.mjs"',
            'compatibility_date = "2026-06-14"',
            "",
            "[vars]",
            f'GITHUB_REPO = "{_toml_string(github_repo)}"',
            f'ALLOWED_RECIPIENTS = "{_toml_string(allowed_recipients)}"',
            "",
            "# GITHUB_TOKEN is set as a Cloudflare Worker secret during deployment.",
            "",
        ]
    )
    Path(output_path).write_text(content, encoding="utf-8")


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Cloudflare Worker Wrangler config.")
    parser.add_argument("--output", default="cloudflare/wrangler.toml")
    parser.add_argument("--worker-name", default="courts-nz-email-archive")
    parser.add_argument("--github-repo", default="edithatogo/sm-govt-nz")
    parser.add_argument("--allowed-recipients", required=True)
    args = parser.parse_args()

    render_worker_config(
        output_path=args.output,
        worker_name=args.worker_name,
        github_repo=args.github_repo,
        allowed_recipients=args.allowed_recipients,
    )


if __name__ == "__main__":
    main()
