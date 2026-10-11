from pathlib import Path

import pymupdf
import pytest
import respx

from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL
from citegen.runner import run_batch_pdfs

pytestmark = pytest.mark.part2


def create_good_pdf(path: Path, title: str) -> Path:
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), title, fontsize=24)
    p.insert_text(pymupdf.Point(50, 150), "Standard body text.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return path


def create_encrypted_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), "Encrypted Title")
    doc.save(str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="owner")
    doc.close()
    return path


@pytest.mark.asyncio
@respx.mock
async def test_mixed_batch_runs_to_completion_and_exports_accepted(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    # Mock Crossref and OpenAlex for Kunz
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    # 1. Good PDF
    good_pdf = create_good_pdf(
        tmp_path / "good.pdf",
        "Firehose and mirror instabilities in a collisionless plasma",
    )

    # 2. Corrupted PDF
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-corrupted gibberish")

    # 3. Encrypted PDF
    enc_pdf = create_encrypted_pdf(tmp_path / "encrypted.pdf")

    # 4. Empty PDF (0 byte)
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")

    pdf_batch = [good_pdf, corrupt_pdf, enc_pdf, empty_pdf]
    out_file = tmp_path / "output.tex"
    report_file = tmp_path / "report.json"

    exit_code, results = await run_batch_pdfs(
        pdf_paths=pdf_batch,
        output_path=out_file,
        interactive=False,
        force=True,
        report_path=report_file,
    )

    # Exit code is 1 because some failed/unresolved
    assert exit_code == 1
    assert len(results) == 4

    # Accepted file must be exported in .tex
    assert out_file.exists()
    tex_content = out_file.read_text(encoding="utf-8")
    assert r"\bibitem{Kunz2014}" in tex_content

    # Unresolved comments for corrupted and encrypted
    assert "% UNRESOLVED:" in tex_content
