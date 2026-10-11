from pathlib import Path

import pytest
import respx
from typer.testing import CliRunner

from citegen.cli import app
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL
from citegen.runner import process_single_title

pytestmark = pytest.mark.part2
runner = CliRunner()


@pytest.mark.asyncio
@respx.mock
async def test_part1_runner_regression(crossref_kunz_json, openalex_kunz_json):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    res = await process_single_title("Firehose and mirror instabilities in a collisionless plasma")
    assert res.get("status") == "accepted"
    assert res.get("match_status") == "matched"
    assert res.get("bibitem") is not None


@respx.mock
def test_part1_cli_cite_regression(crossref_kunz_json, openalex_kunz_json, tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    out_file = tmp_path / "regression_refs.tex"
    result = runner.invoke(
        app,
        [
            "cite",
            "--title",
            "Firehose and mirror instabilities in a collisionless plasma",
            "-o",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    assert r"\bibitem{Kunz2014}" in out_file.read_text(encoding="utf-8")
