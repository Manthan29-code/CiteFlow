import asyncio
import json
from pathlib import Path
from typing import List, Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from citegen.config import settings
from citegen.pdf.grobid_client import is_grobid_alive
from citegen.pdf.input_validation import PdfValidationError, validate_pdf_input
from citegen.pdf.ocr import is_tesseract_available
from citegen.pdf.text_extractor import extract_pdf_text
from citegen.pdf.title_detector import detect_title_candidates
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL
from citegen.runner import process_single_title, run_batch_pdfs, run_batch_titles

app = typer.Typer(
    help="CiteGen: AI-Free Scholarly Citation Metadata to LaTeX bibitem Generator",
    no_args_is_help=True,
)
console = Console()


# =========================================================================
# Part 1 CLI Commands
# =========================================================================


@app.command(name="lookup")
def lookup_command(
    title: str = typer.Argument(..., help="Article title to search for"),
    json_output: bool = typer.Option(
        False, "--json", help="Output raw JSON data instead of formatted tables"
    ),
):
    """Query both providers, display normalized candidates, chosen match, and provenance."""
    try:
        state = asyncio.run(process_single_title(title))
    except Exception as e:
        console.print(f"[bold red]Error running lookup:[/] {e}")
        raise typer.Exit(code=1)

    if json_output:
        # Dump as json
        out_dict = {
            "input_title": state.get("input_title"),
            "match_status": state.get("match_status"),
            "status": state.get("status"),
            "normalized_candidates": state.get("normalized_candidates", []),
            "selected_metadata": state.get("selected_metadata"),
            "field_provenance": state.get("field_provenance", {}),
            "conflicts": state.get("conflicts", []),
            "missing_fields": state.get("missing_fields", []),
            "validation_errors": state.get("validation_errors", []),
            "draft_bibitem": state.get("bibitem"),
            "errors": state.get("errors", []),
        }
        typer.echo(json.dumps(out_dict, indent=2, default=str))
        return

    # Rich table output
    console.print(f"\n[bold cyan]Lookup Results for:[/] {title}\n")
    console.print(f"[bold]Match Status:[/] {state.get('match_status')}")
    console.print(f"[bold]State Status:[/] {state.get('status')}")

    cands = state.get("normalized_candidates", [])
    if cands:
        c_table = Table(title="Normalized Candidates Found", show_header=True)
        c_table.add_column("Title", style="cyan")
        c_table.add_column("Authors", style="white")
        c_table.add_column("Year", style="yellow")
        c_table.add_column("Provider", style="green")
        for c in cands:
            authors_str = ", ".join(
                f"{a.get('surname', '')} {a.get('given_name', '')}".strip()
                for a in c.get("authors", [])
            )
            c_table.add_row(
                c.get("title", ""),
                authors_str,
                str(c.get("year", "")),
                c.get("source_provider", ""),
            )
        console.print(c_table)

    sel = state.get("selected_metadata")
    if sel:
        table = Table(title="Selected Metadata & Provenance", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Provenance", style="green")

        prov = state.get("field_provenance", {})
        for field in [
            "title",
            "year",
            "journal",
            "journal_abbreviation",
            "doi_url",
            "volume",
            "issue",
            "first_page",
            "article_number",
        ]:
            val = sel.get(field)
            if val is not None:
                table.add_row(field, str(val), prov.get(field, "unknown"))

        # Authors
        authors = sel.get("authors", [])
        author_names = [
            f"{a.get('surname', '')} {a.get('given_name', '')}".strip() for a in authors
        ]
        table.add_row("authors", ", ".join(author_names), prov.get("authors", "unknown"))

        console.print(table)
    else:
        console.print("[yellow]No matching record accepted.[/]")

    if state.get("bibitem"):
        console.print(f"\n[bold green]Draft Bibitem:[/] {state['bibitem']}")

    if state.get("validation_errors"):
        console.print("\n[bold red]Validation Warnings / Errors:[/]")
        for err in state["validation_errors"]:
            console.print(f"  - {err}")


@app.command(name="cite")
def cite_command(
    titles: Optional[List[str]] = typer.Option(
        None, "--title", "-t", help="Article title(s) to process"
    ),
    titles_file: Optional[Path] = typer.Option(
        None, "--titles-file", help="Path to text file containing titles (one per line)"
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Destination path for .tex file"),
    force: bool = typer.Option(False, "--force", help="Force overwrite existing output file"),
    standalone: bool = typer.Option(
        True,
        "--standalone/--fragment",
        help="Generate standalone LaTeX document or thebibliography fragment",
    ),
    report: Optional[Path] = typer.Option(
        None, "--report", help="Path to write JSON summary report"
    ),
    json_path: Optional[Path] = typer.Option(
        None, "--json", help="Path to write JSON metadata for accepted records"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Process batch of titles, resolve citation keys, and write .tex file."""
    all_titles: List[str] = []
    if titles:
        all_titles.extend(titles)

    if titles_file:
        if not titles_file.exists():
            console.print(f"[bold red]Usage error:[/] Titles file '{titles_file}' does not exist.")
            raise typer.Exit(code=2)
        try:
            with open(titles_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        all_titles.append(stripped)
        except Exception as e:
            console.print(f"[bold red]Error reading titles file:[/] {e}")
            raise typer.Exit(code=2)

    if not all_titles:
        console.print(
            "[bold red]Usage error:[/] Must provide at least one title via --title or --titles-file."
        )
        raise typer.Exit(code=2)

    # Check output file existence before running batch
    if output.exists() and not force:
        console.print(
            f"[bold red]Error:[/] Output file '{output}' already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=2)

    try:
        exit_code, batch_results = asyncio.run(
            run_batch_titles(
                titles=all_titles,
                output_path=output,
                standalone=standalone,
                force=force,
                report_path=report,
                json_path=json_path,
                verbose=verbose,
            )
        )
    except FileExistsError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[bold red]Unexpected error during batch processing:[/] {e}")
        raise typer.Exit(code=1)

    # Show summary table
    summary_table = Table(title="Batch Processing Summary", show_header=True)
    summary_table.add_column("Title", style="cyan")
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Reason / Details", style="white")

    for res in batch_results:
        t = res.get("input_title", "")
        st = res.get("status", "unresolved")
        errs = res.get("validation_errors", [])
        status_style = "green" if st == "accepted" else "yellow" if st == "unresolved" else "red"
        summary_table.add_row(
            t,
            f"[{status_style}]{st}[/]",
            "; ".join(errs) if errs else "OK",
        )

    console.print(summary_table)
    console.print(f"\n[bold green]Output written to:[/] {output}")

    raise typer.Exit(code=exit_code)


# =========================================================================
# Part 2 CLI Commands
# =========================================================================


@app.command(name="title")
def title_command(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file to detect title for"),
):
    """Debug command: detect and display ranked title candidates for a single PDF."""
    if not pdf_path.exists():
        console.print(f"[bold red]Error:[/] File '{pdf_path}' does not exist.")
        raise typer.Exit(code=1)

    try:
        validate_pdf_input(pdf_path)
    except PdfValidationError as exc:
        console.print(f"[bold red]Validation Error:[/] {exc}")
        raise typer.Exit(code=1)

    try:
        text_res = extract_pdf_text(pdf_path)
        candidates = asyncio.run(
            detect_title_candidates(pdf_path, fallback_text=text_res.get("extracted_text"))
        )
    except Exception as exc:
        console.print(f"[bold red]Error detecting title:[/] {exc}")
        raise typer.Exit(code=1)

    if not candidates:
        console.print(f"[yellow]No title candidates detected in:[/] {pdf_path.name}")
        raise typer.Exit(code=0)

    table = Table(title=f"Detected Title Candidates: {pdf_path.name}", show_header=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Confidence", style="yellow", width=10)
    table.add_column("Source", style="green", width=14)
    table.add_column("Title Candidate", style="white", overflow="fold")

    for idx, cand in enumerate(candidates, start=1):
        table.add_row(
            str(idx),
            f"{cand.get('confidence', 0.0):.2f}",
            cand.get("source", ""),
            cand.get("title", ""),
        )

    console.print(table)


@app.command(name="check")
def check_command():
    """Report GROBID, Tesseract OCR, and scholarly network API readiness."""
    table = Table(title="CiteFlow System & Service Readiness", show_header=True)
    table.add_column("Service / Tool", style="cyan", width=22)
    table.add_column("Status", style="bold", width=16)
    table.add_column("Endpoint / Details", style="white")

    # 1. Tesseract OCR
    tess_available = is_tesseract_available()
    tess_status = "[green]Available[/]" if tess_available else "[yellow]Not Found[/]"
    table.add_row("Tesseract OCR", tess_status, "Local system binary")

    # 2. GROBID
    grobid_alive = asyncio.run(is_grobid_alive(settings.grobid_url))
    grobid_status = "[green]Reachable[/]" if grobid_alive else "[yellow]Unreachable[/]"
    table.add_row("GROBID Service", grobid_status, settings.grobid_url)

    # 3. Crossref API connectivity
    async def _check_api(url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                return res.status_code == 200
        except Exception:
            return False

    cr_ok = asyncio.run(_check_api(f"{CROSSREF_API_URL}?rows=1"))
    cr_status = "[green]Reachable[/]" if cr_ok else "[red]Unreachable[/]"
    table.add_row("Crossref API", cr_status, CROSSREF_API_URL)

    # 4. OpenAlex API connectivity
    oa_ok = asyncio.run(_check_api(f"{OPENALEX_API_URL}?per_page=1"))
    oa_status = "[green]Reachable[/]" if oa_ok else "[red]Unreachable[/]"
    table.add_row("OpenAlex API", oa_status, OPENALEX_API_URL)

    console.print(table)


@app.command(name="run")
def run_command(
    paths: List[Path] = typer.Argument(..., help="PDF file(s) or directories to process"),
    output: Path = typer.Option(..., "--output", "-o", help="Destination path for .tex file"),
    force: bool = typer.Option(False, "--force", help="Force overwrite existing output file"),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Enable interactive human-in-the-loop prompts",
    ),
    ocr: bool = typer.Option(
        True,
        "--ocr/--no-ocr",
        help="Enable or disable OCR fallback",
    ),
    grobid_url: Optional[str] = typer.Option(
        None, "--grobid-url", help="Custom URL for GROBID service"
    ),
    report: Optional[Path] = typer.Option(
        None, "--report", help="Path to write JSON summary report"
    ),
    json_path: Optional[Path] = typer.Option(
        None, "--json", help="Path to write JSON metadata for accepted records"
    ),
    standalone: bool = typer.Option(
        True,
        "--standalone/--fragment",
        help="Generate standalone LaTeX document or thebibliography fragment",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", help="Recursively scan directories for PDFs"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    concurrency: int = typer.Option(
        1, "--concurrency", help="Number of concurrent PDF workers (only with --no-interactive)"
    ),
):
    """Process one or more PDFs, confirm titles, review metadata, and export .tex."""
    # Concurrency rule
    if interactive and concurrency > 1:
        console.print(
            "[bold red]Usage error:[/] --concurrency > 1 is allowed only with --no-interactive."
        )
        raise typer.Exit(code=2)

    # Output file collision
    if output.exists() and not force:
        console.print(
            f"[bold red]Error:[/] Output file '{output}' already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=2)

    # Gather PDF paths
    collected_pdfs: List[Path] = []
    for p in paths:
        if p.is_file():
            if p.suffix.lower() == ".pdf":
                collected_pdfs.append(p)
            else:
                # Still include so validator checks it and reports invalid extension
                collected_pdfs.append(p)
        elif p.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            found = list(p.glob(pattern))
            collected_pdfs.extend(found)
        else:
            # Missing file: include so validator can report it
            collected_pdfs.append(p)

    if not collected_pdfs:
        console.print("[bold red]Usage error:[/] No PDF files found in specified paths.")
        raise typer.Exit(code=2)

    # Apply configuration overrides
    if grobid_url:
        settings.grobid_url = grobid_url
    if not ocr:
        settings.ocr_enabled = False

    try:
        exit_code, results = asyncio.run(
            run_batch_pdfs(
                pdf_paths=collected_pdfs,
                output_path=output,
                interactive=interactive,
                standalone=standalone,
                force=force,
                report_path=report,
                json_path=json_path,
                concurrency=concurrency,
                verbose=verbose,
            )
        )
    except FileExistsError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=2)
    except Exception as exc:
        console.print(f"[bold red]Unexpected error during PDF processing:[/] {exc}")
        raise typer.Exit(code=1)

    # Summary table
    summary_table = Table(title="PDF Processing Summary", show_header=True)
    summary_table.add_column("PDF / Title", style="cyan")
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Reason / Details", style="white")

    for res in results:
        title_str = (
            res.get("input_title")
            or res.get("selected_title")
            or Path(res.get("input_pdf_path", "Untitled")).name
        )
        st = res.get("status", "unresolved")
        errs = res.get("validation_errors", [])
        status_style = "green" if st == "accepted" else "yellow" if st == "unresolved" else "red"
        summary_table.add_row(
            title_str,
            f"[{status_style}]{st}[/]",
            "; ".join(errs) if errs else "OK",
        )

    console.print(summary_table)
    console.print(f"\n[bold green]Output written to:[/] {output}")

    raise typer.Exit(code=exit_code)
