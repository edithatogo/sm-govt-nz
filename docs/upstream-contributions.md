# Upstream Contribution Workflow

When one of the external source tools needs a fix or improvement, do not carry
a silent local patch in this repository.

Use this workflow:

1. Open an upstream issue describing the bug, missing feature, or integration
   gap.
2. Fork the upstream repository into the GitHub account configured for this
   project.
3. Implement the fix in the fork.
4. Submit a pull request from the fork branch to the upstream repository.
5. Reference the upstream issue and PR from any local workaround in this repo.

Configured upstreams are listed in `config/upstream_tools.json`.

Dry-run example:

```powershell
python scripts/upstream_contribution.py yt-dlp `
  --title "Expose stable metadata field for government video archive workflows" `
  --body "Describe the issue and proposed fix." `
  --create-issue `
  --fork
```

Execute for real by adding `--execute`. The script uses the GitHub CLI (`gh`) and
therefore requires an authenticated GitHub session with rights to create forks,
issues, and pull requests.
