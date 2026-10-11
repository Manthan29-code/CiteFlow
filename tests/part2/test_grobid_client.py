from pathlib import Path

import pymupdf
import pytest
import respx

from citegen.pdf.grobid_client import fetch_grobid_title
from citegen.pdf.title_detector import detect_title_candidates

pytestmark = pytest.mark.part2

GROBID_SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title level="a" type="main">Extracted Title via GROBID Service</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
</TEI>
"""


@pytest.mark.asyncio
@respx.mock
async def test_grobid_success_returns_title(tmp_path: Path):
    respx.post("http://localhost:8070/api/processHeaderDocument").respond(
        status_code=200,
        text=GROBID_SAMPLE_TEI,
    )

    pdf_file = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), "Sample Content")
    doc.save(str(pdf_file))
    doc.close()

    title = await fetch_grobid_title(pdf_file, grobid_url="http://localhost:8070")
    assert title == "Extracted Title via GROBID Service"


@pytest.mark.asyncio
@respx.mock
async def test_grobid_unreachable_or_5xx_falls_back_to_heuristics(tmp_path: Path):
    # Mock GROBID 500 error
    respx.post("http://localhost:8070/api/processHeaderDocument").respond(
        status_code=500,
        text="Internal Server Error",
    )

    pdf_file = tmp_path / "fallback.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), "Heuristically Detected Title", fontsize=20)
    p.insert_text(pymupdf.Point(50, 150), "Body text of paper", fontsize=10)
    doc.save(str(pdf_file))
    doc.close()

    # detect_title_candidates should not crash and fall back to heuristics
    candidates = await detect_title_candidates(
        pdf_file, grobid_url="http://localhost:8070", use_grobid=True
    )
    assert len(candidates) >= 1
    assert candidates[0]["title"] == "Heuristically Detected Title"


@pytest.mark.asyncio
@respx.mock
async def test_grobid_configurable_url(tmp_path: Path):
    custom_url = "http://my-custom-grobid:9999"
    respx.post(f"{custom_url}/api/processHeaderDocument").respond(
        status_code=200,
        text=GROBID_SAMPLE_TEI,
    )

    pdf_file = tmp_path / "custom.pdf"
    doc = pymupdf.open()
    _ = doc.new_page()
    doc.save(str(pdf_file))
    doc.close()

    title = await fetch_grobid_title(pdf_file, grobid_url=custom_url)
    assert title == "Extracted Title via GROBID Service"
