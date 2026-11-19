import re
from typing import Any, Dict, List, Optional, Tuple, Union

from citegen.latex.author_format import escape_latex, format_author_list
from citegen.metadata.models import ArticleMetadata, Author


# Canonical set of supported template field tags in lowercase
LOWERCASE_VARIABLES = [
    "citation key",
    "key",
    "firstname",
    "first name",
    "surname",
    "middle name",
    "authors last first .",
    "authors last first.",
    "authors last first",
    "authors first. last",
    "authors first last",
    "authors",
    "title",
    "journal abbr",
    "journal abbreviation",
    "journal",
    "year",
    "volume",
    "issue",
    "article number",
    "first page",
    "locator",
    "doi url",
    "doi",
]

# Legacy bracketed variables for backward compatibility
LEGACY_TEMPLATE_FIELDS = {
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

# The exposed list of fields for autocomplete, API, and guides
ALLOWED_TEMPLATE_FIELDS = LOWERCASE_VARIABLES

# Regex to match any tag delimited by <...>
TAG_PATTERN = re.compile(r"<([^>]+)>")


def validate_citation_template(template: str) -> Tuple[bool, List[str]]:
    """
    Validates a citation template string.
    Checks that:
    1. Template is not empty.
    2. Template contains at least one recognized metadata variable (lowercase or uppercase, plain or in <TAG>).
    3. Any explicit <...> bracketed tag matches a recognized field.
    Returns (is_valid, list_of_error_messages).
    """
    if not template or not template.strip():
        return False, ["Template cannot be empty."]

    errors: List[str] = []

    # Validate explicit <TAG> brackets if present
    found_tags = TAG_PATTERN.findall(template)
    for raw_tag in found_tags:
        clean_tag = raw_tag.strip()
        upper_clean = clean_tag.upper()
        lower_clean = clean_tag.lower()
        if (
            upper_clean not in LEGACY_TEMPLATE_FIELDS
            and lower_clean not in LOWERCASE_VARIABLES
        ):
            errors.append(
                f"Unknown tag '<{raw_tag}>'. Supported variables: {', '.join(LOWERCASE_VARIABLES)}"
            )

    # Check that at least one known variable appears in the template (case-insensitive)
    lower_tpl = template.lower()
    has_variable = False
    for var in LOWERCASE_VARIABLES:
        if var in lower_tpl:
            has_variable = True
            break

    if not has_variable:
        for legacy_var in LEGACY_TEMPLATE_FIELDS:
            if legacy_var.lower() in lower_tpl:
                has_variable = True
                break

    if not has_variable:
        errors.append(
            "Template must contain at least one valid metadata variable (e.g. authors, title, journal, year, doi)."
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


def format_authors_by_variant(
    authors: List[Author],
    variant: str,
    truncate_over_7: bool = True,
    author_threshold: int = 7,
) -> str:
    """
    Formats the entire author list based on the requested variant.
    Preserves CiteFlow <= threshold and > threshold rule:
    - If truncate_over_7 is True and > author_threshold authors: first author followed by '\\textit{et al.}'
    - Otherwise: formats all authors with appropriate delimiters
    """
    if not authors:
        return "Anonymous"

    if truncate_over_7 and len(authors) > author_threshold:
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


def format_author_by_template_tokens(
    author: Author,
    order: str,  # "FIRST_LAST" or "LAST_FIRST"
    dotted: bool,
    has_middle: bool,
) -> str:
    """Formats an individual Author using fine-grained component rules."""
    if not author.surname:
        return escape_latex(author.original_name or "Anonymous")

    surname_esc = escape_latex(author.surname)
    given_inits = extract_initials_list(author.given_name or "")
    middle_inits = extract_initials_list(author.middle_name or "")
    all_inits = given_inits + (middle_inits if has_middle else [])

    if not all_inits:
        return surname_esc

    if order == "FIRST_LAST":
        init_str = " ".join(f"{i}." if dotted else i for i in all_inits)
        return f"{init_str} {surname_esc}".strip()
    else:
        if dotted:
            init_str = " ".join(f"{i}." for i in all_inits)
            return f"{surname_esc} {init_str}".strip()
        else:
            # Undotted compressed initials (e.g. Ghosh S or Chattopadhyay PK)
            init_str = "".join(all_inits)
            return f"{surname_esc} {init_str}".strip()


def format_authors_from_components(
    authors: List[Author],
    order: str,
    dotted: bool,
    has_middle: bool,
    and_before_last: Union[str, bool],
    truncate_over_7: bool,
    author_threshold: int = 7,
) -> str:
    """Formats the list of authors based on component variables and builder flags."""
    if not authors:
        return "Anonymous"

    if truncate_over_7 and len(authors) > author_threshold:
        first = format_author_by_template_tokens(authors[0], order, dotted, has_middle)
        return f"{first} \\textit{{et al.}}"

    formatted = [format_author_by_template_tokens(a, order, dotted, has_middle) for a in authors]
    if len(formatted) == 1:
        return formatted[0]

    # Normalize and_before_last mode:
    # 'no_comma' -> IOP style: "A, B and C"
    # 'comma' (or True) -> AIP style: "A, B, and C"
    # 'none' (or False) -> Plain comma: "A, B, C"
    if and_before_last is True or and_before_last == "comma":
        mode = "comma"
    elif and_before_last == "no_comma":
        mode = "no_comma"
    else:
        mode = "none"

    if mode in ("no_comma", "comma"):
        if len(formatted) == 2:
            return f"{formatted[0]} and {formatted[1]}"
        else:
            all_except_last = ", ".join(formatted[:-1])
            if mode == "no_comma":
                return f"{all_except_last} and {formatted[-1]}"
            else:
                return f"{all_except_last}, and {formatted[-1]}"
    else:
        return ", ".join(formatted)


def clean_latex_punctuation(text: str) -> str:
    """
    Cleans up empty parentheses, dangling punctuation, directives, and extra whitespace
    caused by omitted metadata fields.
    """
    # Strip any comment directives or builder state comments
    text = re.sub(r"(?m)^\s*%.*\n?", "", text)
    text = re.sub(r"\s*%.*", "", text)

    # Remove empty parentheses () or brackets []
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)

    # Remove dangling labels when field was omitted
    text = re.sub(r",\s*no\.\s*,", ",", text)
    text = re.sub(r",\s*Article\s*,", ",", text)
    text = re.sub(r"\bdoi:\s*(?=\.|\s*$)", "", text)

    # Clean double colons, semicolons, commas
    text = re.sub(r";\s*:", ":", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r":\s*:", ":", text)

    # Clean space before punctuation
    text = re.sub(r"\s+([,.;:])", r"\1", text)

    # Collapse multiple consecutive periods (except \textit{et al.})
    text = re.sub(r"(?<!et al)\.{2,}", ".", text)

    # Collapse multiple spaces (preserving newlines if any)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def format_bibitem_with_style(
    metadata: ArticleMetadata | Dict[str, Any],
    template: str,
    citation_key: str = "DRAFT",
    truncate_over_7: Optional[bool] = None,
    author_threshold: Optional[int] = None,
) -> str:
    """
    Renders a LaTeX \\bibitem string according to a customizable citation style template.
    Substitutes all variables (lowercase or legacy <TAG>) case-insensitively,
    respecting locator fallback rules, author formatting, and missing field omission.
    """
    if isinstance(metadata, dict):
        meta = ArticleMetadata(**metadata)
    else:
        meta = metadata

    lower_tpl = template.lower()
    result = template

    # Determine author truncation rule
    if "% truncate_authors: false" in lower_tpl or "% no_et_al" in lower_tpl:
        should_truncate = False
    elif "% truncate_authors: true" in lower_tpl or "% et_al" in lower_tpl:
        should_truncate = True
    elif truncate_over_7 is not None:
        should_truncate = truncate_over_7
    else:
        should_truncate = True

    # Determine author threshold count (default 7, min 1)
    if author_threshold is not None:
        threshold = max(1, author_threshold)
    else:
        threshold_match = re.search(r"%\s*author_threshold:\s*(\d+)", lower_tpl)
        threshold = max(1, int(threshold_match.group(1))) if threshold_match else 7

    if "% and_before_last: no_comma" in lower_tpl:
        and_before_last = "no_comma"
    elif "% and_before_last: comma" in lower_tpl or "% and_before_last: true" in lower_tpl:
        and_before_last = "comma"
    else:
        and_before_last = "none"

    # 1. Author formatting according to template tag, plain variable, or fine-grained components
    author_tokens = list(
        re.finditer(
            r"(?i)(?:firstname|first\s+name|surname|middle\s+name)",
            result,
        )
    )
    if len(author_tokens) >= 2:
        start_pos = author_tokens[0].start()
        end_pos = author_tokens[-1].end()
        matched_text = result[start_pos:end_pos]
        matched_lower = matched_text.lower()
        first_idx = min(
            [matched_lower.find(k) for k in ("firstname", "first name") if k in matched_lower] or [999]
        )
        last_idx = min(
            [matched_lower.find("surname")] if "surname" in matched_lower else [999]
        )
        order = "FIRST_LAST" if first_idx < last_idx else "LAST_FIRST"
        dotted = "." in matched_text or "." in lower_tpl[end_pos : end_pos + 2]
        has_middle = "middle" in matched_lower

        authors_val = format_authors_from_components(
            authors=meta.authors,
            order=order,
            dotted=dotted,
            has_middle=has_middle,
            and_before_last=and_before_last,
            truncate_over_7=should_truncate,
            author_threshold=threshold,
        )
        result = result[:start_pos] + authors_val + result[end_pos:]
    elif len(author_tokens) == 1:
        t = author_tokens[0]
        val = t.group(0).lower()
        if "surname" in val:
            authors_val = format_authors_from_components(
                authors=meta.authors,
                order="LAST_FIRST",
                dotted=False,
                has_middle=False,
                and_before_last=and_before_last,
                truncate_over_7=should_truncate,
                author_threshold=threshold,
            )
        else:
            authors_val = format_authors_from_components(
                authors=meta.authors,
                order="FIRST_LAST",
                dotted=True,
                has_middle=False,
                and_before_last=and_before_last,
                truncate_over_7=should_truncate,
                author_threshold=threshold,
            )
        result = result[:t.start()] + authors_val + result[t.end():]
    elif "authors last first ." in lower_tpl:
        # Undotted initials with sentence trailing period (space before dot)
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_NODOTS", truncate_over_7=should_truncate, author_threshold=threshold) + "."
        result = re.sub(r"(?i)\bauthors\s+last\s+first\s+\.", lambda _: authors_val, result)
    elif "authors last first.." in lower_tpl:
        # Dotted initials with extra sentence trailing period
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_DOTS", truncate_over_7=should_truncate, author_threshold=threshold) + "."
        result = re.sub(r"(?i)\bauthors\s+last\s+first\.\.", lambda _: authors_val, result)
    elif "<authors_last_first(.)>" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_DOTS", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)<authors_last_first\(\.\)>", lambda _: authors_val, result)
    elif "authors last first." in lower_tpl:
        # Surname first, dotted initials (Ghosh S., Chattopadhyay P. K.)
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_DOTS", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)\bauthors\s+last\s+first\.", lambda _: authors_val, result)
    elif "<authors_last_first()>" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_NODOTS", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)<authors_last_first\(\)>", lambda _: authors_val, result)
    elif "authors last first" in lower_tpl:
        # Surname first, undotted compressed initials without trailing dot (Ghosh S, Chattopadhyay PK)
        authors_val = format_authors_by_variant(meta.authors, "LAST_FIRST_NODOTS", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)\bauthors\s+last\s+first\b", lambda _: authors_val, result)
    elif "authors first. last" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "FIRST_DOTS_LAST", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)\bauthors\s+first\.\s+last\b", lambda _: authors_val, result)
    elif "<authors_first(.)_last>" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "FIRST_DOTS_LAST", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)<authors_first\(\.\)_last>", lambda _: authors_val, result)
    elif "authors first last" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "FIRST_NODOTS_LAST", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)\bauthors\s+first\s+last\b", lambda _: authors_val, result)
    elif "<authors_first()_last>" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "FIRST_NODOTS_LAST", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)<authors_first\(\)_last>", lambda _: authors_val, result)
    elif "authors" in lower_tpl or "<authors>" in lower_tpl:
        authors_val = format_authors_by_variant(meta.authors, "DEFAULT", truncate_over_7=should_truncate, author_threshold=threshold)
        result = re.sub(r"(?i)<authors>", lambda _: authors_val, result)
        result = re.sub(r"(?i)(?<!\\)\bauthors\b(?!\s+(?:last|first))", lambda _: authors_val, result)

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
    has_art_num = (
        "article number" in lower_tpl
        or "<article_number>" in lower_tpl
    )
    has_first_page = (
        "first page" in lower_tpl
        or "<first_page>" in lower_tpl
    )

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

    # Perform substitutions in order (longer/specific names first)
    # Citation Key
    result = re.sub(r"(?i)(?:<citation_key>|\bcitation\s+key\b)", lambda _: key_val, result)
    result = re.sub(r"(?i)(?:<key>|(?<=\{)key(?=\}))", lambda _: key_val, result)

    # Journal Abbreviation & Journal
    result = re.sub(r"(?i)(?:<journal_abbreviation>|\bjournal\s+abbreviation\b)", lambda _: journal_abbr_val, result)
    result = re.sub(r"(?i)(?:<journal_abbr>|\bjournal\s+abbr\b)", lambda _: journal_abbr_val, result)
    result = re.sub(r"(?i)(?:<journal>|\bjournal\b(?!\s+(?:abbreviation|abbr)))", lambda _: journal_val, result)

    # DOI URL & DOI (do not match .org or : label)
    result = re.sub(r"(?i)(?:<doi_url>|\bdoi\s+url\b)", lambda _: doi_url_clean, result)
    result = re.sub(r"(?i)<doi>", lambda _: doi_clean, result)
    result = re.sub(r"(?i)(?<!//)(?<!dx\.)\bdoi\b(?!\.org)(?!\s*:)", lambda _: doi_clean, result)

    # Article Number & First Page & Locator
    result = re.sub(r"(?i)(?:<article_number>|\barticle\s+number\b)", lambda _: article_number_val, result)
    result = re.sub(r"(?i)(?:<first_page>|\bfirst\s+page\b)", lambda _: first_page_val, result)
    result = re.sub(r"(?i)(?:<locator>|\blocator\b)", lambda _: locator_val, result)

    # Title, Year, Volume, Issue
    result = re.sub(r"(?i)(?:<title>|\btitle\b)", lambda _: title_val, result)
    result = re.sub(r"(?i)(?:<year>|\byear\b)", lambda _: year_val, result)
    result = re.sub(r"(?i)(?:<volume>|\bvolume\b)", lambda _: volume_val, result)
    result = re.sub(r"(?i)(?:<issue>|\bissue\b)", lambda _: issue_val, result)

    # Clean up empty brackets, dangling separators, etc.
    cleaned = clean_latex_punctuation(result)
    return cleaned


def get_sample_metadata() -> ArticleMetadata:
    """Returns sample metadata with >7 authors for live previews and threshold testing in UI."""
    return ArticleMetadata(
        title="Transition from single to multiple axial potential structure in expanding helicon plasma",
        authors=[
            Author(surname="Ghosh", given_name="S."),
            Author(surname="Yadav", given_name="S."),
            Author(surname="Barada", given_name="K.", middle_name="K."),
            Author(surname="Chattopadhyay", given_name="P.", middle_name="K."),
            Author(surname="Ghosh", given_name="J."),
            Author(surname="Pal", given_name="R."),
            Author(surname="Bora", given_name="D."),
            Author(surname="Kumar", given_name="A."),
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
