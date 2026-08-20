from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_github_actions_are_pinned_to_full_commit_shas() -> None:
    workflow_paths = sorted(WORKFLOWS.glob("*.yml"))
    assert workflow_paths
    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        uses = re.findall(r"uses:\s*([^\s#]+)", workflow)
        assert uses, path.name
        for value in uses:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", value), (path.name, value)


def test_future_release_includes_attested_wheel_provenance() -> None:
    release = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    assert "id-token: write" in release
    assert "attestations: write" in release
    assert "actions/attest@" in release
    assert 'subject-path: "dist/*.whl"' in release
    assert 'romm-mcp-${GITHUB_REF_NAME}.sigstore.json' in release


def test_scorecard_uploads_sarif_without_checkout_credentials() -> None:
    scorecard = (WORKFLOWS / "scorecards.yml").read_text(encoding="utf-8")
    assert "ossf/scorecard-action@" in scorecard
    assert "publish_results: true" in scorecard
    assert "persist-credentials: false" in scorecard
    assert "github/codeql-action/upload-sarif@" in scorecard
