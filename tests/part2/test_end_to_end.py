from pathlib import Path

import pymupdf
import pytest
import respx

from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL
from citegen.runner import run_batch_pdfs

pytestmark = pytest.mark.part2

GOLDEN_KUNZ = (
    r"\bibitem{Kunz2014} Kunz M W, Schekochihin A A and Stone J M 2014 "
    r"\textit{Phys. Rev. Lett.} "
    r"\href{https://doi.org/10.1103/PhysRevLett.112.205003}{\textbf{112} 205003}."
)


@pytest.mark.asyncio
@respx.mock
async def test_end_to_end_pdf_to_tex_matches_golden_string(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    pdf_file = tmp_path / "kunz_paper.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(
        pymupdf.Point(50, 100),
        "Firehose and mirror instabilities in a collisionless plasma",
        fontsize=24,
    )
    p.insert_text(
        pymupdf.Point(50, 150),
        "M. W. Kunz, A. A. Schekochihin, and J. M. Stone",
        fontsize=12,
    )
    doc.save(str(pdf_file))
    doc.close()

    out_tex = tmp_path / "output.tex"
    exit_code, _ = await run_batch_pdfs(
        pdf_paths=[pdf_file],
        output_path=out_tex,
        interactive=False,
    )

    assert exit_code == 0
    assert out_tex.exists()
    content = out_tex.read_text(encoding="utf-8")
    assert GOLDEN_KUNZ in content


@pytest.mark.asyncio
@respx.mock
async def test_end_to_end_failed_pdf_does_not_affect_valid_entry(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    # Valid PDF
    valid_pdf = tmp_path / "valid.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(
        pymupdf.Point(50, 100),
        "Firehose and mirror instabilities in a collisionless plasma",
        fontsize=24,
    )
    p.insert_text(
        pymupdf.Point(50, 150),
        "M. W. Kunz, A. A. Schekochihin, and J. M. Stone",
        fontsize=12,
    )
    doc.save(str(valid_pdf))
    doc.close()

    # Corrupt PDF
    corrupt_pdf = tmp_path / "bad.pdf"
    corrupt_pdf.write_bytes(b"%PDF-invalid bytes")

    out_tex = tmp_path / "mixed.tex"
    exit_code, results = await run_batch_pdfs(
        pdf_paths=[valid_pdf, corrupt_pdf],
        output_path=out_tex,
        interactive=False,
    )

    assert exit_code == 1
    assert out_tex.exists()
    content = out_tex.read_text(encoding="utf-8")
    assert GOLDEN_KUNZ in content
    assert "% UNRESOLVED:" in content
