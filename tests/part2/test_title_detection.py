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


def _make_aip_style_cover_pdf(pdf_file: Path, title: str, set_metadata: bool = True) -> None:
    """Mimic AIP Publishing cover page: big icon glyph buttons, boilerplate, related list."""
    doc = pymupdf.open()
    cover = doc.new_page()
    cover.insert_text(pymupdf.Point(120, 80), "RESEARCH ARTICLE | APRIL 08 2014", fontsize=8)
    cover.insert_text(pymupdf.Point(120, 100), title, fontsize=13.8)
    cover.insert_text(pymupdf.Point(120, 125), "S. K. Saha; S. Chowdhury; A. Ghosh", fontsize=8)
    # Large "button" text (stand-in for the 28.8pt icon-font glyph rendered next to it)
    cover.insert_text(pymupdf.Point(450, 230), "View Online", fontsize=28.8)
    cover.insert_text(pymupdf.Point(450, 260), "Export Citation", fontsize=9.2)
    cover.insert_text(pymupdf.Point(130, 300), "Articles You May Be Interested In", fontsize=10.4)
    cover.insert_text(
        pymupdf.Point(130, 330), "A different paper about expanding magnetic fields", fontsize=16
    )
    cover.insert_text(pymupdf.Point(130, 360), "Phys. Plasmas (September 2019)", fontsize=7)

    article = doc.new_page()
    article.insert_text(pymupdf.Point(50, 70), title, fontsize=14)
    article.insert_text(
        pymupdf.Point(50, 120), "Two-dimensional density measurements are reported.", fontsize=10
    )
    if set_metadata:
        doc.set_metadata({"title": title})
    doc.save(str(pdf_file))
    doc.close()


@pytest.mark.asyncio
async def test_publisher_cover_page_ui_text_not_chosen(tmp_path: Path):
    pdf_file = tmp_path / "aip_cover.pdf"
    title = "Plasma density accumulation on a conical surface for diffusion"
    _make_aip_style_cover_pdf(pdf_file, title)

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert candidates[0]["title"] == title
    assert candidates[0]["confidence"] >= 0.85
    for cand in candidates:
        assert "View Online" not in cand["title"]
        assert "Export Citation" not in cand["title"]
        assert "Articles You May Be Interested In" not in cand["title"]
        assert "A different paper" not in cand["title"]
    # Clear winner so non-interactive mode auto-accepts it
    if len(candidates) > 1:
        assert candidates[0]["confidence"] - candidates[1]["confidence"] >= 0.15


@pytest.mark.asyncio
async def test_title_containing_journal_words_is_kept(tmp_path: Path):
    pdf_file = tmp_path / "journal_words.pdf"
    title = "High temperature electrons exhausted from rf plasma sources along a nozzle"
    _make_aip_style_cover_pdf(pdf_file, title)

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    assert candidates[0]["title"] == title


@pytest.mark.asyncio
async def test_icon_font_glyphs_are_stripped(tmp_path: Path):
    from citegen.pdf.title_detector import _clean_text

    assert _clean_text("Online \ue92d") == "Online "
    assert _clean_text("\ufb01eld") == "field"


@pytest.mark.asyncio
async def test_metadata_title_offered_when_layout_fails(tmp_path: Path):
    pdf_file = tmp_path / "meta_only.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), "x = 2y + 3z", fontsize=10)
    doc.set_metadata({"title": "Collisionless electron heating in inductive discharges"})
    doc.save(str(pdf_file))
    doc.close()

    candidates = await detect_title_candidates(pdf_file, use_grobid=False)
    titles = [c["title"] for c in candidates]
    assert "Collisionless electron heating in inductive discharges" in titles


@pytest.mark.asyncio
async def test_bad_metadata_title_ignored(tmp_path: Path):
    from citegen.pdf.title_detector import _clean_metadata_title

    assert _clean_metadata_title("Microsoft Word - paper_final.docx") is None
    assert _clean_metadata_title("untitled") is None
    assert _clean_metadata_title("paper.pdf") is None
    assert _clean_metadata_title("Journal of Plasma Physics") is None
    assert _clean_metadata_title("Firehose and mirror instabilities") == (
        "Firehose and mirror instabilities"
    )
