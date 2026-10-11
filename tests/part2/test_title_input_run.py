from pathlib import Path

import pytest
import respx
from typer.testing import CliRunner

from citegen.cli import app
from citegen.config import settings
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part2
runner = CliRunner()


@respx.mock
def test_cli_run_direct_title_as_argument(crossref_kunz_json, openalex_kunz_json, tmp_path: Path, monkeypatch):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    out_file = tmp_path / "output" / "references.tex"
    monkeypatch.setattr(settings, "output_dir", tmp_path / "output")

    result = runner.invoke(
        app,
        ["run", "Firehose and mirror instabilities in a collisionless plasma"],
    )

    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert r"\bibitem{Kunz2014}" in content
    assert "Output written to:" in result.output


@respx.mock
def test_cli_run_interactive_terminal_prompt(crossref_kunz_json, openalex_kunz_json, tmp_path: Path, monkeypatch):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    out_file = tmp_path / "output" / "references.tex"
    monkeypatch.setattr(settings, "output_dir", tmp_path / "output")

    # Run with no arguments, simulate typing title into prompt
    result = runner.invoke(
        app,
        ["run"],
        input="Firehose and mirror instabilities in a collisionless plasma\n",
    )

    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert r"\bibitem{Kunz2014}" in content


@respx.mock
def test_cli_run_direct_title_with_custom_output(crossref_kunz_json, openalex_kunz_json, tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    custom_out = tmp_path / "my_refs.tex"

    result = runner.invoke(
        app,
        ["run", "Firehose and mirror instabilities in a collisionless plasma", "-o", str(custom_out)],
    )

    assert result.exit_code == 0
    assert custom_out.exists()
    content = custom_out.read_text(encoding="utf-8")
    assert r"\bibitem{Kunz2014}" in content


@respx.mock
def test_cli_run_empty_terminal_prompt_exits():
    result = runner.invoke(
        app,
        ["run"],
        input="\n",
    )
    assert result.exit_code == 1
    assert "No title entered. Exiting." in result.output


@respx.mock
def test_cli_run_interactive_user_review_accept(crossref_masheyeva_json, tmp_path: Path, monkeypatch):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_masheyeva_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    out_file = tmp_path / "output" / "references.tex"
    monkeypatch.setattr(settings, "output_dir", tmp_path / "output")

    # Enter 'a' to accept ambiguous metadata
    result = runner.invoke(
        app,
        ["run", "Experimental and numerical study of the ionization-attachment instability"],
        input="a\n",
    )

    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert r"\bibitem{Masheyeva2025}" in content

