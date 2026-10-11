from citegen.latex.author_format import escape_latex, format_author_list
from citegen.metadata.models import ArticleMetadata


def format_bibitem(
    metadata: ArticleMetadata,
    citation_key: str = "DRAFT",
) -> str:
    """
    Format metadata into a LaTeX \\bibitem string.
    Follows:
    \\bibitem{key} Authors Year \\textit{Journal} \\href{DOI}{\\textbf{Volume} Locator}.
    """
    # 1. Authors
    authors_str = format_author_list(metadata.authors)

    # 2. Year
    year_str = str(metadata.year) if metadata.year else ""

    # 3. Journal (prefer abbreviation, fallback to full journal name)
    journal_val = metadata.journal_abbreviation or metadata.journal or ""
    journal_str = f"\\textit{{{escape_latex(journal_val)}}}" if journal_val else ""

    # 4. Locator & Volume
    locator = metadata.first_page or metadata.article_number
    vol = metadata.volume

    locator_parts = []
    if vol:
        locator_parts.append(f"\\textbf{{{escape_latex(vol)}}}")
    if locator:
        locator_parts.append(escape_latex(locator))

    locator_text = " ".join(locator_parts)

    # 5. DOI link
    if metadata.doi_url:
        clean_doi_url = metadata.doi_url.strip()
        if locator_text:
            linked_block = f"\\href{{{clean_doi_url}}}{{{locator_text}}}"
        else:
            # Fallback if no volume/locator: link doi directly
            linked_block = f"\\href{{{clean_doi_url}}}{{\\textit{{in press}}}}"
    else:
        linked_block = locator_text

    # Combine parts
    parts = [authors_str]
    if year_str:
        parts.append(year_str)
    if journal_str:
        parts.append(journal_str)
    if linked_block:
        parts.append(linked_block)

    body = " ".join(parts).strip()
    # Ensure it ends with exactly one period
    if not body.endswith("."):
        body += "."

    return f"\\bibitem{{{citation_key}}} {body}"
