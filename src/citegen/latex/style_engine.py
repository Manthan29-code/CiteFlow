import re
from typing import Any, Dict, List, Optional, Tuple

from citegen.latex.author_format import escape_latex, format_author_list
from citegen.metadata.models import ArticleMetadata, Author


# Canonical set of supported template field tags
ALLOWED_TEMPLATE_FIELDS = {
    "CITATION_KEY",
    "KEY",
    "AUTHORS",
    "AUTHORS_LAST_FIRST(.)",
    "AUTHORS_LAST_FIRST()",
    "AUTHORS_FIRST(.)_LAST",
    "AUTHORS_FIRST()_LAST",
    "TITLE",
    "JOURNAL",
    "JOURNAL_ABBREVIATION",
    "YEAR",
    "VOLUME",
    "ISSUE",
    "FIRST_PAGE",
    "ARTICLE_NUMBER",
    "LOCATOR",
    "DOI",
    "DOI_URL",
}

# Regex to match any tag delimited by <...>
TAG_PATTERN = re.compile(r"<([^>]+)>")


def validate_citation_template(template: str) -> Tuple[bool, List[str]]:
    """
    Validates a citation template string.
    Checks that:
    1. Template is not empty.
    2. All <...> tags match an allowed tag in ALLOWED_TEMPLATE_FIELDS.
    Returns (is_valid, list_of_error_messages).
    """
    if not template or not template.strip():
        return False, ["Template cannot be empty."]

    errors: List[str] = []
    found_tags = TAG_PATTERN.findall(template)

    if not found_tags:
        errors.append("Template must contain at least one valid metadata field tag in <...>.")

    for raw_tag in found_tags:
        clean_tag = raw_tag.strip()
        if clean_tag not in ALLOWED_TEMPLATE_FIELDS:
            errors.append(
                f"Unknown tag '<{raw_tag}>'. Allowed fields: {', '.join(sorted(ALLOWED_TEMPLATE_FIELDS))}"
            )

    return len(errors) == 0, errors


def extract_initials_list(name_part: str) -> List[str]:
    """
    Extract uppercase initials list from a given or middle name part.
    Handles hyphenated names (e.g. Jean-Pierre -> ['J-P']), dotted initials (M. W. -> ['M', 'W']).
    """
    if not name_part:
        return []
    cleaned = name_part.replace(".", " ").replace(",", " ")
    parts = cleaned.split()
    initials: List[str] = []
    for p in parts:
        if "-" in p:
            sub = [s[0].upper() for s in p.split("-") if s]
            initials.append("-".join(sub))
        elif p:
            initials.append(p[0].upper())
    return initials


def format_single_author_style(author: Author, variant: str) -> str:
    """
    Formats a single Author instance according to the requested style variant:
    - LAST_FIRST_DOTS: 'Ghosh S.' or 'Chattopadhyay P. K.'
    - LAST_FIRST_NODOTS: 'Ghosh S' or 'Chattopadhyay PK'
    - FIRST_DOTS_LAST: 'S. Ghosh' or 'P. K. Chattopadhyay'
    - FIRST_NODOTS_LAST: 'S Ghosh' or 'P K Chattopadhyay'
    - DEFAULT: 'Ghosh S' or 'Chattopadhyay P K' (CiteFlow IOP default)
    """
    if not author.surname:
        raw = author.original_name or "Anonymous"
        return escape_latex(raw)

    surname_esc = escape_latex(author.surname)

    given_inits = extract_initials_list(author.given_name or "")
    middle_inits = extract_initials_list(author.middle_name or "")
    all_inits = given_inits + middle_inits

    if not all_inits:
        return surname_esc

    if variant == "LAST_FIRST_DOTS":
        dotted_str = " ".join(f"{init}." for init in all_inits)
        return f"{surname_esc} {dotted_str}"

    elif variant == "LAST_FIRST_NODOTS":
        # In Vancouver / AMA style, initials are compressed without spaces (e.g. PK)
        compressed_str = "".join(all_inits)
        return f"{surname_esc} {compressed_str}"

    elif variant == "FIRST_DOTS_LAST":
        # In IEEE style, dotted initials separated by space (e.g. P. K. Chattopadhyay)
        dotted_str = " ".join(f"{init}." for init in all_inits)
        return f"{dotted_str} {surname_esc}"

    elif variant == "FIRST_NODOTS_LAST":
        spaced_str = " ".join(all_inits)
        return f"{spaced_str} {surname_esc}"

    else:
        # Default IOP
        spaced_str = " ".join(all_inits)
        return f"{surname_esc} {spaced_str}"


def format_authors_by_variant(authors: List[Author], variant: str) -> str:
    """
    Formats the entire author list based on the requested variant.
    Preserves CiteFlow <= 7 and > 7 rule:
    - If > 7 authors: first author followed by '\\textit{et al.}'
    - If <= 7 authors: formats all authors with appropriate delimiters
    """
    if not authors:
        return "Anonymous"

    if len(authors) > 7:
        first = format_single_author_style(authors[0], variant)
        return f"{first} \\textit{{et al.}}"

    formatted = [format_single_author_style(a, variant) for a in authors]

    if len(formatted) == 1:
        return formatted[0]

    if variant in ("LAST_FIRST_NODOTS", "LAST_FIRST_DOTS"):
        # Vancouver / AMA style: comma between all authors, no 'and'
        return ", ".join(formatted)

    elif variant in ("FIRST_DOTS_LAST", "FIRST_NODOTS_LAST"):
        # IEEE / Chicago style: Oxford comma with 'and'
        if len(formatted) == 2:
            return f"{formatted[0]} and {formatted[1]}"
        else:
            all_except_last = ", ".join(formatted[:-1])
            return f"{all_except_last}, and {formatted[-1]}"

    else:
        # Default IOP style: comma except before last with 'and'
        if len(formatted) == 2:
            return f"{formatted[0]} and {formatted[1]}"
        else:
            all_except_last = ", ".join(formatted[:-1])
            return f"{all_except_last} and {formatted[-1]}"


def clean_latex_punctuation(text: str) -> str:
    """
    Cleans up empty parentheses, dangling punctuation, and extra whitespace
    caused by omitted metadata fields.
    """
    # Remove empty parentheses () or brackets []
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)

    # Remove dangling labels when field was omitted
    text = re.sub(r",\s*no\.\s*,", ",", text)
    text = re.sub(r",\s*Article\s*,", ",", text)
    text = re.sub(r"\bdoi:\s*\.?", "", text)

    # Clean double colons, semicolons, commas
    text = re.sub(r";\s*:", ":", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r":\s*:", ":", text)

    # Clean space before punctuation
    text = re.sub(r"\s+([,.;:])", r"\1", text)

    # Collapse multiple consecutive periods (except \textit{et al.})
    # Avoid breaking \textit{et al.}
    text = re.sub(r"(?<!et al)\.{2,}", ".", text)

    # Collapse multiple spaces (preserving newlines if any)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def format_bibitem_with_style(
    metadata: ArticleMetadata | Dict[str, Any],
    template: str,
    citation_key: str = "DRAFT",
) -> str:
    """
    Renders a LaTeX \\bibitem string according to a customizable citation style template.
    Substitutes all <TAG> placeholders with escaped metadata values,
    respecting locator fallback rules, author formatting, and missing field omission.
    """
    if isinstance(metadata, dict):
        meta = ArticleMetadata(**metadata)
    else:
        meta = metadata

    # 1. Author formatting according to template tag
    authors_val = ""
    if "<AUTHORS_LAST_FIRST()>" in template:
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_NODOTS")
    elif "<AUTHORS_LAST_FIRST(.)>" in template:
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_DOTS")
    elif "<AUTHORS_FIRST(.)_LAST>" in template:
        authors_val = format_authors_by_variant(meta.authors, "FIRST_DOTS_LAST")
    elif "<AUTHORS_FIRST()_LAST>" in template:
        authors_val = format_authors_by_variant(meta.authors, "FIRST_NODOTS_LAST")
    elif "<AUTHORS>" in template:
        authors_val = format_authors_by_variant(meta.authors, "DEFAULT")

    # 2. Key
    key_val = citation_key

    # 3. Title & Journal
    title_val = escape_latex(meta.title) if meta.title else ""
    journal_val = escape_latex(meta.journal) if meta.journal else ""
    journal_abbr_val = (
        escape_latex(meta.journal_abbreviation)
        if meta.journal_abbreviation
        else journal_val
    )

    # 4. Year & Volume & Issue
    year_val = str(meta.year) if meta.year else ""
    volume_val = escape_latex(meta.volume) if meta.volume else ""
    issue_val = escape_latex(meta.issue) if meta.issue else ""

    # 5. Locator Fallback (article_number vs first_page)
    # If only one of ARTICLE_NUMBER or FIRST_PAGE is in template:
    # - If article_number is requested but missing, fallback to first_page
    # - If first_page is requested but missing, fallback to article_number
    # If both are in template, print each if present
    has_art_num = "<ARTICLE_NUMBER>" in template
    has_first_page = "<FIRST_PAGE>" in template

    if has_art_num and not has_first_page:
        article_number_val = escape_latex(meta.article_number or meta.first_page or "")
        first_page_val = escape_latex(meta.first_page or "")
    elif has_first_page and not has_art_num:
        first_page_val = escape_latex(meta.first_page or meta.article_number or "")
        article_number_val = escape_latex(meta.article_number or "")
    else:
        article_number_val = escape_latex(meta.article_number or "")
        first_page_val = escape_latex(meta.first_page or "")

    locator_val = escape_latex(meta.first_page or meta.article_number or "")

    # 6. DOI and DOI_URL
    doi_clean = ""
    doi_url_clean = ""
    if meta.doi_url:
        raw_doi = meta.doi_url.strip()
        doi_clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw_doi, flags=re.IGNORECASE)
        if raw_doi.lower().startswith("http://") or raw_doi.lower().startswith("https://"):
            doi_url_clean = raw_doi
        else:
            doi_url_clean = f"https://doi.org/{doi_clean}"

    # Mapping from tag name to value
    replacements = {
        "<CITATION_KEY>": key_val,
        "<KEY>": key_val,
        "<AUTHORS_LAST_FIRST()>": authors_val,
        "<AUTHORS_LAST_FIRST(.)>": authors_val,
        "<AUTHORS_FIRST(.)_LAST>": authors_val,
        "<AUTHORS_FIRST()_LAST>": authors_val,
        "<AUTHORS>": authors_val,
        "<TITLE>": title_val,
        "<JOURNAL>": journal_val,
        "<JOURNAL_ABBREVIATION>": journal_abbr_val,
        "<YEAR>": year_val,
        "<VOLUME>": volume_val,
        "<ISSUE>": issue_val,
        "<ARTICLE_NUMBER>": article_number_val,
        "<FIRST_PAGE>": first_page_val,
        "<LOCATOR>": locator_val,
        "<DOI>": doi_clean,
        "<DOI_URL>": doi_url_clean,
    }

    result = template
    for tag, val in replacements.items():
        result = result.replace(tag, val)

    # Clean up empty brackets, dangling separators, etc.
    cleaned = clean_latex_punctuation(result)

    # Ensure result starts with \bibitem{key} if template contained citation key
    return cleaned


def get_sample_metadata() -> ArticleMetadata:
    """Returns sample metadata for live previews in UI."""
    return ArticleMetadata(
        title="Transition from single to multiple axial potential structure in expanding helicon plasma",
        authors=[
            Author(surname="Ghosh", given_name="S."),
            Author(surname="Chattopadhyay", given_name="P.", middle_name="K."),
            Author(surname="Ghosh", given_name="J."),
            Author(surname="Pal", given_name="R."),
            Author(surname="Bora", given_name="D."),
        ],
        year=2017,
        journal="Journal of Physics D: Applied Physics",
        journal_abbreviation="J Phys D Appl Phys",
        volume="50",
        issue="6",
        article_number="065201",
        first_page="065201",
        doi_url="https://doi.org/10.1088/1361-6463/aa5068",
    )

