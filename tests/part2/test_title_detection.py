from pathlib import Path

import pymupdf
import pytest

from citegen.pdf.title_detector import detect_title_candidates

pytestmark = pytest.mark.part2


@pytest.mark.asyncio
async def test_title_on_page_one_found(tmp_path: Path):
    pdf_file = tmp_path / "page_one.pdf"
    doc = pymupdf.open()
    p = doc.new_page()

    # Title with large font
    p.insert_text(
        pymupdf.Point(50, 100),
        "Firehose and mirror instabilities in a collisionless plasma",
        fontsize=22,
    )
    # Body text with normal font
    p.insert_text(
        pymupdf.Point(50, 150),
        "We present linear and nonlinear simulations of plasma instabilities.",
        fontsize=10,
    )
    doc.save(str(pdf_file))
    doc.close()

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert len(candidates) >= 1
    top = candidates[0]
    assert "Firehose and mirror instabilities" in top["title"]
    assert top["confidence"] >= 0.85
    assert top["page"] == 1


@pytest.mark.asyncio
async def test_title_only_on_page_three_found(tmp_path: Path):
    pdf_file = tmp_path / "title_page_three.pdf"
    doc = pymupdf.open()

    # Page 1: Cover sheet / disclaimer
    p1 = doc.new_page()
    p1.insert_text(
        pymupdf.Point(50, 100), "Distribution statement: Public domain document.", fontsize=9
    )

    # Page 2: Blank / disclaimer
    p2 = doc.new_page()
    p2.insert_text(pymupdf.Point(50, 100), "Notes and metadata page.", fontsize=9)

    # Page 3: Real title in large font
    p3 = doc.new_page()
    p3.insert_text(
        pymupdf.Point(50, 120),
        "Plasma Dynamics in Collisionless Accretion Flows",
        fontsize=24,
    )
    p3.insert_text(
        pymupdf.Point(50, 170),
        "Introduction to accretion flow dynamics.",
        fontsize=10,
    )

    doc.save(str(pdf_file))
    doc.close()

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert len(candidates) >= 1
    top = candidates[0]
    assert "Plasma Dynamics in Collisionless Accretion Flows" in top["title"]
    assert top["page"] == 3


@pytest.mark.asyncio
async def test_font_size_ranking_beats_running_headers_footers(tmp_path: Path):
    pdf_file = tmp_path / "headers_footers.pdf"
    doc = pymupdf.open()
    p = doc.new_page()

    # Running header at top
    p.insert_text(pymupdf.Point(50, 30), "Page 1 of 12 - Physical Review Letters", fontsize=9)

    # Actual article title
    p.insert_text(
        pymupdf.Point(50, 110),
        "Kinetic Modeling of Solar Wind Turbulence",
        fontsize=20,
    )

    # Running footer at bottom
    p.insert_text(
        pymupdf.Point(50, 780), "https://doi.org/10.1103/PhysRevLett.112.205003", fontsize=8
    )

    doc.save(str(pdf_file))
    doc.close()

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert len(candidates) >= 1
    assert "Kinetic Modeling of Solar Wind Turbulence" == candidates[0]["title"]


@pytest.mark.asyncio
async def test_journal_name_and_author_line_not_chosen(tmp_path: Path):
    pdf_file = tmp_path / "paper_layout.pdf"
    doc = pymupdf.open()
    p = doc.new_page()

    # Journal header
    p.insert_text(
        pymupdf.Point(50, 50), "Journal of Plasma Physics and Fluid Dynamics", fontsize=11
    )

    # Title
    p.insert_text(
        pymupdf.Point(50, 100),
        "Thermal Conduction in Magnetized Astrophysical Plasmas",
        fontsize=18,
    )

    # Author line and affiliation
    p.insert_text(pymupdf.Point(50, 140), "John Doe and Jane Smith", fontsize=11)
    p.insert_text(pymupdf.Point(50, 160), "Department of Physics, Oxford University", fontsize=9)

    doc.save(str(pdf_file))
    doc.close()

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert len(candidates) >= 1
    top_title = candidates[0]["title"]
    assert "Thermal Conduction in Magnetized Astrophysical Plasmas" == top_title
    # Verify journal name and author lines are not chosen
    for cand in candidates:
        assert "Journal of Plasma Physics" not in cand["title"]
        assert "Oxford University" not in cand["title"]


@pytest.mark.asyncio
async def test_no_candidate_gives_empty_list(tmp_path: Path):
    pdf_file = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    _ = doc.new_page()  # completely empty page
    doc.save(str(pdf_file))
    doc.close()

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert candidates == []
