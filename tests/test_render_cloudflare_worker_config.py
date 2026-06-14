from scripts.render_cloudflare_worker_config import render_worker_config


def test_render_worker_config_writes_expected_wrangler_toml(tmp_path) -> None:
    output = tmp_path / "wrangler.toml"

    render_worker_config(
        output_path=output,
        worker_name="courts-worker",
        github_repo="owner/repo",
        allowed_recipients='courts@example.test,"quoted"@example.test',
    )

    content = output.read_text(encoding="utf-8")
    assert 'name = "courts-worker"' in content
    assert 'main = "courts_nz_email_worker.mjs"' in content
    assert 'GITHUB_REPO = "owner/repo"' in content
    assert 'ALLOWED_RECIPIENTS = "courts@example.test,\\"quoted\\"@example.test"' in content
    assert "GITHUB_TOKEN is set as a Cloudflare Worker secret" in content
