from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest
import respx
from typer.testing import CliRunner

from citegen.cli import app
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part2
runner = CliRunner()


def create_pdf(path: Path, title: str) -> Path:
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), title, fontsize=24)
    p.insert_text(pymupdf.Point(50, 150), "Paper body text.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return path


@respx.mock
def test_cli_title_command(tmp_path: Path):
    pdf = create_pdf(
        tmp_path / "paper.pdf", "Firehose and mirror instabilities in a collisionless plasma"
    )
    result = runner.invoke(app, ["title", str(pdf)])
    assert result.exit_code == 0
    assert "Firehose and mirror instabilities" in result.output


def test_cli_check_command():
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Tesseract OCR" in result.output
    assert "GROBID Service" in result.output
    assert "Crossref API" in result.output


def test_cli_concurrency_rejected_without_no_interactive(tmp_path: Path):
    pdf = create_pdf(tmp_path / "test.pdf", "Sample Title")
    out = tmp_path / "out.tex"
    result = runner.invoke(app, ["run", str(pdf), "-o", str(out), "--concurrency", "2"])
    assert result.exit_code == 2
    assert "--concurrency > 1 is allowed only with --no-interactive" in result.output


def test_cli_output_protected_without_force(tmp_path: Path):
    pdf = create_pdf(tmp_path / "test.pdf", "Sample Title")
    out = tmp_path / "existing.tex"
    out.write_text("Old tex", encoding="utf-8")

    result = runner.invoke(app, ["run", str(pdf), "-o", str(out)])
    assert result.exit_code == 2
    assert "already exists" in result.output


@respx.mock
def test_cli_run_directory_recursive(crossref_kunz_json, openalex_kunz_json, tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    sub_dir = tmp_path / "nested" / "folder"
    sub_dir.mkdir(parents=True)
    _ = create_pdf(
        sub_dir / "paper.pdf", "Firehose and mirror instabilities in a collisionless plasma"
    )

    out_file = tmp_path / "dir_batch.tex"
    result = runner.invoke(
        app,
        ["run", str(tmp_path), "--recursive", "--no-interactive", "-o", str(out_file)],
    )

    assert result.exit_code == 0
    assert out_file.exists()
    assert r"\bibitem{Kunz2014}" in out_file.read_text(encoding="utf-8")


@respx.mock
def test_cli_scripted_interactive_prompt_pick_title(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    # Ambiguous PDF with competing candidates
    pdf = tmp_path / "prompt_test.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 80), "Candidate One", fontsize=14)
    p.insert_text(
        pymupdf.Point(50, 110),
        "Firehose and mirror instabilities in a collisionless plasma",
        fontsize=14,
    )
    doc.save(str(pdf))
    doc.close()

    out_file = tmp_path / "scripted.tex"

    # Input '2' picks candidate 2
    result = runner.invoke(
        app,
        ["run", str(pdf), "-o", str(out_file)],
        input="2\n",
    )

    assert result.exit_code == 0
    assert out_file.exists()
    assert r"\bibitem{Kunz2014}" in out_file.read_text(encoding="utf-8")


@respx.mock
def test_cli_keyboard_interrupt_writes_accepted(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    pdf1 = create_pdf(
        tmp_path / "pdf1.pdf", "Firehose and mirror instabilities in a collisionless plasma"
    )
    pdf2 = create_pdf(tmp_path / "pdf2.pdf", "Second Paper Title")

    out_file = tmp_path / "interrupted.tex"

    call_count = 0
    from citegen.runner import process_single_pdf as orig_proc

    async def mock_process(
        pdf_path, interactive=True, compiled_graph=None, thread_id=None, prompt_fn=None
    ):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise KeyboardInterrupt()
        return await orig_proc(
            pdf_path,
            interactive=interactive,
            compiled_graph=compiled_graph,
            thread_id=thread_id,
            prompt_fn=prompt_fn,
        )

    with patch("citegen.runner.process_single_pdf", side_effect=mock_process):
        result = runner.invoke(
            app,
            ["run", str(pdf1), str(pdf2), "--no-interactive", "-o", str(out_file)],
        )

    assert result.exit_code == 1
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert r"\bibitem{Kunz2014}" in content
    assert "% UNRESOLVED: pdf2.pdf - Skipped due to interruption" in content
