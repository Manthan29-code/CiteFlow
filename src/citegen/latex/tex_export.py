from pathlib import Path
from typing import Any, Dict, List, Optional


def render_thebibliography(
    bibitems: List[str],
    unresolved_items: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Render the thebibliography block with bibitems and unresolved comments."""
    lines: List[str] = [r"\begin{thebibliography}{99}"]

    # Include unresolved comments first or alongside
    if unresolved_items:
        for item in unresolved_items:
            title = item.get("title", "Untitled")
            reason = item.get("reason", "Not resolved")
            lines.append(f"% UNRESOLVED: {title} - {reason}")

    for b in bibitems:
        lines.append(b)

    lines.append(r"\end{thebibliography}")
    return "\n".join(lines)


def render_tex_document(
    bibitems: List[str],
    unresolved_items: Optional[List[Dict[str, Any]]] = None,
    standalone: bool = True,
) -> str:
    """Render complete LaTeX document or fragment."""
    bib_block = render_thebibliography(bibitems, unresolved_items)
    if not standalone:
        return bib_block + "\n"

    template = f"""\\documentclass{{article}}
\\usepackage{{hyperref}}

\\begin{{document}}

{bib_block}

\\end{{document}}
"""
    return template


def export_tex(
    output_path: Path,
    bibitems: List[str],
    unresolved_items: Optional[List[Dict[str, Any]]] = None,
    standalone: bool = True,
    force: bool = False,
) -> Path:
    """
    Export bibitems and unresolved comments to a .tex file.
    Refuses to overwrite existing file unless force=True.
    """
    path = Path(output_path).resolve()
    if path.exists() and not force:
        raise FileExistsError(f"Output file '{path}' already exists. Use --force to overwrite.")

    content = render_tex_document(
        bibitems=bibitems,
        unresolved_items=unresolved_items,
        standalone=standalone,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path
