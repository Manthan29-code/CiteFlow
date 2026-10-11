import re
from typing import List

from citegen.metadata.models import Author

LATEX_ESCAPE_MAP = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}
ESCAPE_REGEX = re.compile(r"[&%$#_{}~^\\]")


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters in a single pass."""
    if not text:
        return ""
    return ESCAPE_REGEX.sub(lambda m: LATEX_ESCAPE_MAP[m.group(0)], text)


def extract_initials(name_part: str) -> str:
    """
    Extract uppercase space-separated initials from given or middle name part.
    Handles hyphenated names (e.g. Jean-Pierre -> J-P), dotted initials (M. W. -> M W).
    """
    if not name_part:
        return ""
    # Clean dots and commas
    cleaned = name_part.replace(".", " ").replace(",", " ")
    parts = cleaned.split()
    initials: List[str] = []
    for p in parts:
        if "-" in p:
            sub = [s[0].upper() for s in p.split("-") if s]
            initials.append("-".join(sub))
        elif p:
            initials.append(p[0].upper())
    return " ".join(initials)


def format_single_author(author: Author) -> str:
    """
    Format a single author as `Surname Initials`.
    Omit middle initial when there is no middle name.
    """
    if not author.surname:
        raw = author.original_name or "Anonymous"
        return escape_latex(raw)

    surname_escaped = escape_latex(author.surname)

    given_init = extract_initials(author.given_name or "")
    middle_init = extract_initials(author.middle_name or "")

    initial_parts: List[str] = []
    if given_init:
        initial_parts.append(given_init)
    if middle_init:
        initial_parts.append(middle_init)

    initials = " ".join(initial_parts).strip()
    if initials:
        return f"{surname_escaped} {initials}"
    return surname_escaped


def format_author_list(authors: List[Author]) -> str:
    """
    Format author list:
    - 7 or fewer: comma-separated with 'and' before the last.
    - More than 7: first author followed by '\\textit{et al.}'.
    """
    if not authors:
        return "Anonymous"

    if len(authors) > 7:
        first = format_single_author(authors[0])
        return f"{first} \\textit{{et al.}}"

    formatted_authors = [format_single_author(a) for a in authors]

    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return f"{formatted_authors[0]} and {formatted_authors[1]}"
    else:
        all_except_last = ", ".join(formatted_authors[:-1])
        return f"{all_except_last} and {formatted_authors[-1]}"
