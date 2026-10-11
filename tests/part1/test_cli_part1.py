import json
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from typer.testing import CliRunner

from citegen.cli import app
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part1
runner = CliRunner()


@respx.mock
def test_cli_lookup_plain_and_json(crossref_kunz_json, openalex_kunz_json):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    # 1. Plain rich output
    result = runner.invoke(app, ["lookup", "Firehose and mirror instabilities"])
    assert result.exit_code == 0
    assert "Kunz" in result.output
    assert "Physical Review Letters" in result.output

    # 2. JSON output
    result_json = runner.invoke(app, ["lookup", "Firehose and mirror instabilities", "--json"])
    assert result_json.exit_code == 0
    parsed = json.loads(result_json.output)
    assert parsed["status"] == "accepted"
    assert (
        parsed["selected_metadata"]["title"]
        == "Firehose and mirror instabilities in a collisionless plasma"
    )


@respx.mock
def test_cli_cite_all_accepted(crossref_kunz_json, openalex_kunz_json, tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    out_file = tmp_path / "refs.tex"
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


@respx.mock
def test_cli_cite_titles_file_and_mixed_batch(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    titles_file = tmp_path / "titles.txt"
    titles_file.write_text(
        "# Header comment\n"
        "Firehose and mirror instabilities in a collisionless plasma\n"
        "\n"
        "# Another comment\n"
        "Completely Unknown Title 12345\n",
        encoding="utf-8",
    )

    out_file = tmp_path / "batch.tex"
    report_file = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "cite",
            "--titles-file",
            str(titles_file),
            "-o",
            str(out_file),
            "--report",
            str(report_file),
        ],
    )
    # Mixed batch returns exit code 1
    assert result.exit_code == 1
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    # Accepted entry is still written
    assert r"\bibitem{Kunz2014}" in content
    # Unresolved is in comment
    assert "% UNRESOLVED: Completely Unknown Title 12345" in content

    # Check report JSON
    assert report_file.exists()
    rep = json.loads(report_file.read_text(encoding="utf-8"))
    assert rep["accepted"] == 1
    assert rep["unresolved"] == 1


def test_cli_usage_error_no_titles(tmp_path: Path):
    out_file = tmp_path / "refs.tex"
    result = runner.invoke(app, ["cite", "-o", str(out_file)])
    assert result.exit_code == 2


def test_cli_refuse_overwrite_without_force(tmp_path: Path):
    out_file = tmp_path / "exists.tex"
    out_file.write_text("old content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["cite", "--title", "Sample Title", "-o", str(out_file)],
    )
    assert result.exit_code == 2
    assert "already exists" in result.output


@respx.mock
def test_cli_keyboard_interrupt_handled(crossref_kunz_json, openalex_kunz_json, tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    out_file = tmp_path / "interrupted.tex"

    call_count = 0
    from citegen.runner import process_single_title as orig_proc

    async def mock_process(t, compiled_graph=None):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise KeyboardInterrupt()
        return await orig_proc(t, compiled_graph=compiled_graph)

    with patch("citegen.runner.process_single_title", side_effect=mock_process):
        result = runner.invoke(
            app,
            [
                "cite",
                "--title",
                "Firehose and mirror instabilities in a collisionless plasma",
                "--title",
                "Second Title",
                "-o",
                str(out_file),
            ],
        )

    assert result.exit_code == 1
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert r"\bibitem{Kunz2014}" in content
    assert "% UNRESOLVED: Second Title - Skipped due to interruption" in content
