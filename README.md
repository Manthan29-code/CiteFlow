# CiteFlow / CiteGen

**Deterministic AI-Free Scholarly Citation Metadata to LaTeX `\bibitem` Generator**

Built with Python, LangGraph, PyMuPDF, Typer, and Rich.

---

## Features

### Part 1: Metadata Engine
- **Concurrent Scholarly Lookup**: Queries Crossref and OpenAlex REST APIs in parallel.
- **Deterministic Normalization & Matching**: Handles author names, initials, particles, DOI validation, and journal abbreviations from a curated database (`data/journal_abbreviations.json`).
- **Conflict Tracking & Provenance**: Zero hallucination or fabrication—missing data is flagged and conflicting metadata is captured per field.
- **LaTeX Export**: Produces cleanly escaped, standard `\bibitem` entries and `.tex` documents with batch-level citation key disambiguation (`Kunz2014`, `Kunz2014a`, etc.).
- **Part 1 CLI**:
  - `citegen lookup "Title"`: Inspect provider candidates, matched metadata, and provenance.
  - `citegen cite --title "Title 1" --title "Title 2" -o refs.tex`: Batch citation generation from titles.

### Part 2: PDF Ingestion & Interactive Workflow
- **PDF Ingestion & Validation**: Comprehensive validation (headers, extensions, zero-byte detection, corruption, encryption, and size limits).
- **Text & Title Extraction**: Layout and font-size heuristics across early pages (not just page one). Filters running headers/footers, journal headers, and affiliations.
- **Optional GROBID Integration**: Queries running GROBID service header extraction with graceful heuristic fallback.
- **Optional OCR Fallback**: PyMuPDF rendering with Tesseract OCR for scanned or image-heavy PDFs with automatic image cleanup.
- **Human-in-the-Loop Workflow**: LangGraph `interrupt()` and checkpointers for interactive title confirmation and metadata review/editing.
- **Batch PDF Runner & Non-Interactive Mode**: `--no-interactive` mode with optional concurrency (`--concurrency N`), per-PDF fault isolation, and progress reporting.
- **Part 2 CLI**:
  - `citegen run PATH [PATH ...] -o refs.tex`: Process PDF files or directories interactively or with `--no-interactive`.
  - `citegen title PATH`: Debug tool displaying ranked title candidates detected in a PDF.
  - `citegen check`: Diagnostics command reporting readiness of Tesseract, GROBID, and scholarly APIs.

---

## Installation

### Virtual Environment Setup

```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Linux/macOS
source .venv/bin/activate
```

### Installation Per Part

Install depending on your needs:

```bash
# Part 1 only (Core + Dev)
pip install -e ".[dev]"

# Part 2 (Core + Dev + PDF support)
pip install -e ".[dev,pdf]"

# Part 2 with OCR support
pip install -e ".[dev,pdf,ocr]"
```

---

## Configuration (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Available configuration options:

```ini
# Optional polite pool identifier for Crossref
CROSSREF_MAILTO=your-email@example.com

# Optional OpenAlex API key
OPENALEX_API_KEY=

# HTTP request timeout
REQUEST_TIMEOUT_SECONDS=15

# Maximum allowed PDF file size (MB)
MAX_PDF_SIZE_MB=50

# OCR enablement (requires Tesseract binary installed)
OCR_ENABLED=true

# GROBID server URL
GROBID_URL=http://localhost:8070

# Default directory for outputs
OUTPUT_DIR=./output
```

---

## Optional Services Setup

### 1. Tesseract OCR
- **Windows**: Install via `winget install UB-Mannheim.TesseractOCR` or installer, then ensure `tesseract` is added to your `PATH`.
- **Linux (Ubuntu/Debian)**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

### 2. GROBID Service
Run GROBID using Docker:
```bash
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.1
```

Verify service readiness anytime with:
```bash
citegen check
```

---

## CLI Usage

### Title-Based Operations (Part 1)

```bash
# Look up title candidates and metadata
citegen lookup "Firehose and mirror instabilities in a collisionless plasma"

# Generate references from multiple titles
citegen cite --title "Paper 1" --title "Paper 2" -o output/refs.tex

# Generate from titles file
citegen cite --titles-file titles.txt -o output/refs.tex --report output/report.json
```

### PDF Operations (Part 2)

```bash
# Check service and API readiness
citegen check

# Inspect detected title candidates for a PDF
citegen title samples/paper.pdf

# Run single PDF interactively (confirm title, review metadata)
citegen run samples/paper.pdf -o output/refs.tex

# Run batch of PDFs in a directory non-interactively
citegen run samples/ --no-interactive -o output/batch.tex --report output/report.json

# Concurrent batch processing (only allowed with --no-interactive)
citegen run samples/ --no-interactive --concurrency 4 -o output/batch.tex
```

---

## Test Suites

All unit and integration tests run offline using `respx` and dynamically generated PDFs:

```bash
# Run Part 1 test gate
pytest tests/part1 -q

# Run Part 2 test gate (without local OCR binary)
pytest tests/part2 -m "not ocr" -q

# Run Part 2 test gate (with OCR enabled)
pytest tests/part2 -q

# Run complete test suite (regression gate)
pytest -q

# Code formatting and lint checks
ruff check . && ruff format --check .
```
