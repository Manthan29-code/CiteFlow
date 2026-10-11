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
        for err in val_errors:
            console.print(f"  [red]• {err}[/]")
        for c in conflicts:
            console.print(
                f"  [yellow]• Conflict in {c.get('field', 'field')}: {c.get('reason', '')}[/]"
            )

    console.print(
        "\n[dim]Options: [bold green]'a'[/] to accept as-is, [bold cyan]'e'[/] to edit a field, [bold red]'s'[/] to skip.[/dim]"
    )
    action = ask("[bold]Select an action [a/e/s]:[/] ").strip().lower()

    if action in ("a", "accept"):
        return {"action": "accept"}

    if action in ("s", "skip"):
        return {"action": "skip"}

    if action in ("e", "edit"):
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
