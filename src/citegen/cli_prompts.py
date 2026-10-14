from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def prompt_confirm_title(payload: Dict[str, Any], input_func=None) -> Dict[str, Any]:
    """Display title candidates and prompt user to choose, enter custom, or skip."""
    ask = input_func or console.input
    pdf_path = payload.get("pdf_path", "Unknown PDF")
    candidates = payload.get("candidates", [])

    console.print(f"\n[bold yellow]Title Confirmation Required for:[/] [bold]{pdf_path}[/]\n")

    if candidates:
        cand_table = Table(title="Detected Title Candidates", show_header=True)
        cand_table.add_column("#", style="cyan", width=4)
        cand_table.add_column("Confidence", style="yellow", width=12)
        cand_table.add_column("Source", style="green", width=20)
        cand_table.add_column("Title Candidate", style="white")

        for idx, cand in enumerate(candidates, start=1):
            conf = cand.get("confidence", 0.0)
            src = cand.get("source", "heuristics")
            cand_table.add_row(str(idx), f"{conf:.2f}", src, cand.get("title", ""))

        console.print(cand_table)
        console.print(
            "[dim]Options: Enter candidate number (1..N), [bold cyan]'c'[/] to enter custom title, or [bold red]'s'[/] to skip.[/dim]"
        )

        choice = ask("\n[bold]Select an option:[/] ").strip()

        if choice.lower() in ("s", "skip"):
            return {"action": "skip"}

        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            selected = candidates[int(choice) - 1]["title"]
            return {"action": "select", "title": selected}

        if choice.lower() == "c":
            custom_title = ask("[bold cyan]Enter custom title:[/] ").strip()
            return {"action": "custom", "title": custom_title}

        # If user directly typed a non-empty string that wasn't a command, treat as custom title
        if choice:
            return {"action": "custom", "title": choice}

        return {"action": "skip"}

    else:
        console.print("[yellow]No title candidates were automatically detected.[/]")
        console.print("[dim]Options: Type an article title, or [bold red]'s'[/] to skip.[/dim]")
        custom = ask("\n[bold]Enter title (or 's' to skip):[/] ").strip()
        if not custom or custom.lower() in ("s", "skip"):
            return {"action": "skip"}
        return {"action": "custom", "title": custom}


def prompt_user_review(payload: Dict[str, Any], input_func=None) -> Dict[str, Any]:
    """Display metadata review table and prompt user to accept, edit, or skip."""
    ask = input_func or console.input
    title = payload.get("title") or "Unknown Title"
    meta = payload.get("selected_metadata") or {}
    prov = payload.get("field_provenance") or {}
    val_errors = payload.get("validation_errors", [])
    conflicts = payload.get("conflicts", [])

    console.print(Panel(f"[bold cyan]Review Article Metadata:[/] {title}", expand=False))

    table = Table(show_header=True)
    table.add_column("Field", style="cyan", width=22)
    table.add_column("Value", style="white")
    table.add_column("Source", style="green", width=18)

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
        val = meta.get(field)
        table.add_row(
            field,
            str(val) if val is not None else "[dim]null[/dim]",
            prov.get(field, "unknown"),
        )

    # Authors
    authors = meta.get("authors", [])
    authors_str = ", ".join(
        f"{a.get('surname', '')} {a.get('given_name', '')}".strip() for a in authors
    )
    table.add_row(
        "authors",
        authors_str or "[dim]null[/dim]",
        prov.get("authors", "unknown"),
    )

    console.print(table)

    if val_errors or conflicts:
        console.print("\n[bold red]Issues & Warnings:[/]")
        # Print non-duplicate validation errors
        for err in val_errors:
            if not any(f"Conflict in field '{c.get('field')}'" in err for c in conflicts):
                console.print(f"  [red]• {err}[/]")
        for c in conflicts:
            field = c.get("field", "field")
            reason = c.get("reason", "")
            cr_val = c.get("crossref")
            oa_val = c.get("openalex")
            if cr_val is not None and oa_val is not None:
                console.print(f"  [yellow]• Conflict in '{field}': {reason}[/]")
                console.print(f"      [1] CrossRef: [bold]{cr_val}[/]")
                console.print(f"      [2] OpenAlex: [bold]{oa_val}[/]")
            else:
                console.print(f"  [yellow]• Conflict in '{field}': {reason}[/]")

    candidates = payload.get("candidate_options") or []
    if not candidates:
        for c in conflicts:
            if "candidate_options" in c and c["candidate_options"]:
                candidates = c["candidate_options"]
                break

    if candidates:
        console.print("\n[bold yellow]Matching Candidate Options:[/] [dim](Select a candidate by number or enter custom)[/dim]")
        for idx, cand in enumerate(candidates, start=1):
            cand_title = cand.get("title") or "Untitled"
            cand_year = cand.get("year") or "n.d."
            cand_journal = cand.get("journal_abbreviation") or cand.get("journal") or "Unknown Journal"
            cand_doi = cand.get("doi_url") or "no DOI"
            authors = cand.get("authors") or []
            auth_str = authors[0].get("surname", "") if authors else "Unknown"
            if len(authors) > 1:
                auth_str += " et al."
            console.print(f"  [bold cyan][{idx}][/] [white]{cand_title}[/]")
            console.print(f"      [dim]{auth_str} ({cand_year}) | {cand_journal} | {cand_doi}[/dim]")

    has_resolvable = any(
        c.get("crossref") is not None and c.get("openalex") is not None for c in conflicts
    )

    if candidates:
        console.print(
            f"\n[dim]Options: Enter candidate number [bold cyan][1-{len(candidates)}][/], [bold green]'a'[/] to accept current as-is, [bold yellow]'c'[/] to enter custom, [bold cyan]'e'[/] to edit, [bold red]'s'[/] to skip.[/dim]"
        )
        action = ask(f"[bold]Select an action [1-{len(candidates)}/a/c/e/s]:[/] ").strip()
    elif has_resolvable:
        console.print(
            "\n[dim]Options: [bold green]'a'[/] to accept as-is, [bold yellow]'r'[/] to resolve conflict, [bold cyan]'e'[/] to edit a field, [bold red]'s'[/] to skip.[/dim]"
        )
        action = ask("[bold]Select an action [a/r/e/s]:[/] ").strip().lower()
    else:
        console.print(
            "\n[dim]Options: [bold green]'a'[/] to accept as-is, [bold cyan]'e'[/] to edit a field, [bold red]'s'[/] to skip.[/dim]"
        )
        action = ask("[bold]Select an action [a/e/s]:[/] ").strip().lower()

    if candidates and action.isdigit():
        idx = int(action) - 1
        if 0 <= idx < len(candidates):
            return {
                "action": "select_candidate",
                "candidate": candidates[idx],
                "candidate_index": idx,
            }

    if action.lower() in ("a", "accept"):
        return {"action": "accept"}

    if action.lower() in ("s", "skip"):
        return {"action": "skip"}

    if candidates and action.lower() in ("c", "custom"):
        custom_input = ask("[bold cyan]Enter custom DOI or Article Title:[/] ").strip()
        if not custom_input or custom_input.lower() in ("s", "skip"):
            return {"action": "skip"}
        if custom_input.startswith("10.") or "doi.org" in custom_input:
            doi_val = custom_input if custom_input.startswith("http") else f"https://doi.org/{custom_input}"
            return {"action": "edit", "edits": {"doi_url": doi_val}}
        return {"action": "edit", "edits": {"title": custom_input}}

    if action.lower() in ("r", "resolve") and has_resolvable:
        edits: Dict[str, Any] = {}
        for c in conflicts:
            field = c.get("field")
            cr_val = c.get("crossref")
            oa_val = c.get("openalex")
            if not field or cr_val is None or oa_val is None:
                continue
            console.print(f"\nSelect value for conflict in [bold cyan]'{field}'[/]:")
            console.print(f"  [bold]1[/]: CrossRef -> {cr_val}")
            console.print(f"  [bold]2[/]: OpenAlex -> {oa_val}")
            console.print(f"  [bold]c[/]: Custom value")
            choice = ask("Choice [1/2/c]: ").strip().lower()
            if choice == "1":
                edits[field] = cr_val
            elif choice == "2":
                edits[field] = oa_val
            elif choice == "c":
                edits[field] = ask(f"Enter custom value for '{field}': ").strip()
        if edits:
            return {"action": "edit", "edits": edits}

    if action.lower() in ("e", "edit"):
        field_name = ask("Enter field name to edit: ").strip()
        new_val = ask(f"Enter new value for '{field_name}': ").strip()
        return {
            "action": "edit",
            "edits": {field_name: new_val},
        }

    return {"action": "skip"}


def cli_prompt_for(payload: Dict[str, Any], input_func=None) -> Dict[str, Any]:
    """Router for interactive CLI prompts based on payload kind."""
    kind = payload.get("kind")
    if kind == "confirm_title":
        return prompt_confirm_title(payload, input_func=input_func)
    elif kind == "user_review":
        return prompt_user_review(payload, input_func=input_func)
    else:
        return {"action": "skip"}
