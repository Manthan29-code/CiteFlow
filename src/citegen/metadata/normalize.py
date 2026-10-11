import re
from typing import Any, Dict, List, Optional, Tuple

from citegen.metadata.abbreviations import get_journal_abbreviation
from citegen.metadata.models import ArticleMetadata, Author

# Common surname particles
SURNAME_PARTICLES = {
    "van",
    "von",
    "de",
    "del",
    "da",
    "di",
    "der",
    "den",
    "la",
    "le",
    "du",
    "della",
    "ter",
    "al",
}

# Institutional hints
INSTITUTIONAL_KEYWORDS = {
    "collaboration",
    "group",
    "consortium",
    "team",
    "agency",
    "institute",
    "society",
    "association",
    "working group",
    "organization",
    "committee",
    "project",
}


def clean_whitespace(text: Optional[str]) -> Optional[str]:
    """Clean whitespace without destroying the original string meaning."""
    if text is None:
        return None
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple whitespaces
    cleaned = " ".join(cleaned.split())
    return cleaned if cleaned else None


def parse_author_name(
    given: Optional[str] = None,
    family: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Author:
    """
    Parse author names into surname, given_name, middle_name preserving original_name.
    Handles compound surnames, particles, middle initials, and unsplittable names.
    """
    given_clean = clean_whitespace(given)
    family_clean = clean_whitespace(family)
    full_clean = clean_whitespace(full_name)

    # 1. When family and given are both provided directly
    if family_clean and given_clean:
        orig = f"{given_clean} {family_clean}"
        tokens = given_clean.split()
        if len(tokens) == 1:
            return Author(
                surname=family_clean,
                given_name=tokens[0],
                middle_name=None,
                original_name=orig,
            )
        else:
            return Author(
                surname=family_clean,
                given_name=tokens[0],
                middle_name=" ".join(tokens[1:]),
                original_name=orig,
            )

    # 2. When only family is provided
    if family_clean and not given_clean and not full_clean:
        return Author(
            surname=family_clean,
            given_name=None,
            middle_name=None,
            original_name=family_clean,
            is_ambiguous=True,
            warning="Author has family name only; given name missing",
        )

    # 3. Parse from full_name (or given if only given was provided)
    raw = full_clean or given_clean or family_clean
    if not raw:
        return Author(
            surname=None,
            given_name=None,
            middle_name=None,
            original_name=None,
            is_ambiguous=True,
            warning="Empty author name",
        )

    # Check for institutional or collaboration author
    raw_lower = raw.lower()
    for kw in INSTITUTIONAL_KEYWORDS:
        if kw in raw_lower:
            return Author(
                surname=raw,
                given_name=None,
                middle_name=None,
                original_name=raw,
                is_ambiguous=True,
                warning=f"Author appears to be an institution or group: {raw}",
            )

    # Check comma-separated format: "Surname, Given Middle"
    if "," in raw:
        parts = [p.strip() for p in raw.split(",", 1)]
        surname = parts[0]
        given_part = parts[1]
        gtokens = given_part.split()
        if not gtokens:
            return Author(
                surname=surname,
                given_name=None,
                middle_name=None,
                original_name=raw,
            )
        return Author(
            surname=surname,
            given_name=gtokens[0],
            middle_name=" ".join(gtokens[1:]) if len(gtokens) > 1 else None,
            original_name=raw,
        )

    # Space-separated tokens
    tokens = raw.split()
    if len(tokens) == 1:
        # Single token name - unsplittable
        return Author(
            surname=tokens[0],
            given_name=None,
            middle_name=None,
            original_name=raw,
            is_ambiguous=True,
            warning=f"Unsplittable single-token author name: {raw}",
        )

    # Check particles from right to left
    # e.g., "Ludwig van Beethoven" -> surname="van Beethoven", given="Ludwig"
    # "Gabriel García Márquez" -> compound surname
    particle_idx = -1
    for i in range(len(tokens) - 1, 0, -1):
        if tokens[i].lower() in SURNAME_PARTICLES:
            particle_idx = i
            break

    if particle_idx > 0 and particle_idx < len(tokens) - 1:
        surname = " ".join(tokens[particle_idx:])
        given_tokens = tokens[:particle_idx]
        given_name = given_tokens[0]
        middle_name = " ".join(given_tokens[1:]) if len(given_tokens) > 1 else None
        return Author(
            surname=surname,
            given_name=given_name,
            middle_name=middle_name,
            original_name=raw,
        )

    # Default: last token is surname, preceding are given and middle
    surname = tokens[-1]
    given_tokens = tokens[:-1]
    given_name = given_tokens[0]
    middle_name = " ".join(given_tokens[1:]) if len(given_tokens) > 1 else None

    return Author(
        surname=surname,
        given_name=given_name,
        middle_name=middle_name,
        original_name=raw,
    )


def normalize_doi(doi_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract clean DOI and build https://doi.org/<DOI>.
    Never guesses or invents a DOI.
    """
    if not doi_str:
        return None, None
    clean = doi_str.strip()
    # Strip URL prefixes
    clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", clean, flags=re.IGNORECASE)
    clean = clean.strip("/")
    if not clean or "/" not in clean:
        return None, None
    return clean, f"https://doi.org/{clean}"


def normalize_crossref(item: Dict[str, Any]) -> ArticleMetadata:
    """Normalize a Crossref API work item into ArticleMetadata."""
    warnings: List[str] = []
    field_provenance: Dict[str, str] = {}

    # Title
    raw_title = ""
    if "title" in item and item["title"]:
        if isinstance(item["title"], list):
            raw_title = item["title"][0]
        else:
            raw_title = str(item["title"])
    title = clean_whitespace(raw_title) or "Untitled"
    field_provenance["title"] = "crossref"

    # Authors
    authors: List[Author] = []
    for a_data in item.get("author", []):
        author_obj = parse_author_name(
            given=a_data.get("given"),
            family=a_data.get("family"),
            full_name=a_data.get("name"),
        )
        if author_obj.warning:
            warnings.append(author_obj.warning)
        authors.append(author_obj)
    if authors:
        field_provenance["authors"] = "crossref"

    # Year
    year: Optional[int] = None
    date_fields = ["issued", "published", "published-online", "created"]
    for df in date_fields:
        if df in item and isinstance(item[df], dict):
            parts = item[df].get("date-parts", [])
            if parts and isinstance(parts[0], list) and parts[0]:
                try:
                    year = int(parts[0][0])
                    field_provenance["year"] = "crossref"
                    break
                except (ValueError, TypeError):
                    continue

    # Journal
    journal: Optional[str] = None
    container_titles = item.get("container-title", [])
    if container_titles and isinstance(container_titles, list) and container_titles[0]:
        journal = clean_whitespace(str(container_titles[0]))
        field_provenance["journal"] = "crossref"

    # Journal Abbreviation
    journal_abbreviation: Optional[str] = None
    # Check short-container-title
    short_titles = item.get("short-container-title", [])
    if short_titles and isinstance(short_titles, list) and short_titles[0]:
        short_val = clean_whitespace(str(short_titles[0]))
        if short_val:
            journal_abbreviation = short_val
            field_provenance["journal_abbreviation"] = "crossref"

    # Curated abbreviation lookup
    if not journal_abbreviation and journal:
        curated_abbrev, abbrev_warn = get_journal_abbreviation(journal)
        if curated_abbrev:
            journal_abbreviation = curated_abbrev
            field_provenance["journal_abbreviation"] = "curated_abbreviation"
        elif abbrev_warn:
            warnings.append(abbrev_warn)

    # DOI
    doi_raw = item.get("DOI")
    clean_doi, doi_url = normalize_doi(doi_raw)
    if doi_url:
        field_provenance["doi_url"] = "crossref"

    # Volume & Issue (Strictly independent!)
    volume: Optional[str] = (
        clean_whitespace(str(item.get("volume"))) if item.get("volume") is not None else None
    )
    if volume:
        field_provenance["volume"] = "crossref"

    issue: Optional[str] = (
        clean_whitespace(str(item.get("issue"))) if item.get("issue") is not None else None
    )
    if issue:
        field_provenance["issue"] = "crossref"

    # First page and article number
    first_page: Optional[str] = None
    article_number: Optional[str] = None

    raw_article_num = item.get("article-number")
    if raw_article_num is not None:
        article_number = clean_whitespace(str(raw_article_num))
        if article_number:
            field_provenance["article_number"] = "crossref"

    raw_page = item.get("page")
    if raw_page is not None:
        page_str = clean_whitespace(str(raw_page))
        if page_str:
            # If formatted like 123-145
            if "-" in page_str:
                first_page = page_str.split("-")[0].strip()
                field_provenance["first_page"] = "crossref"
            else:
                # Could be a single page or an article ID
                # If length >= 6 and numeric, and no article_number set, could be an article number
                if page_str.isdigit() and len(page_str) >= 6 and not article_number:
                    article_number = page_str
                    field_provenance["article_number"] = "crossref"
                    warnings.append(
                        f"Ambiguous page-like value '{page_str}' treated as article number"
                    )
                else:
                    first_page = page_str
                    field_provenance["first_page"] = "crossref"

    # Preprint check
    work_type = str(item.get("type", "")).lower()
    subtype = str(item.get("subtype", "")).lower()
    is_preprint = (
        ("posted-content" in work_type) or ("preprint" in subtype) or ("preprint" in work_type)
    )

    return ArticleMetadata(
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        journal_abbreviation=journal_abbreviation,
        doi_url=doi_url,
        volume=volume,
        issue=issue,
        first_page=first_page,
        article_number=article_number,
        source_provider="crossref",
        provider_id=clean_doi,
        source_url=item.get("URL")
        or (f"https://api.crossref.org/works/{clean_doi}" if clean_doi else None),
        raw_data=item,
        field_provenance=field_provenance,
        warnings=warnings,
        is_preprint=is_preprint,
    )


def normalize_openalex(item: Dict[str, Any]) -> ArticleMetadata:
    """Normalize an OpenAlex API work item into ArticleMetadata."""
    warnings: List[str] = []
    field_provenance: Dict[str, str] = {}

    # Title
    raw_title = item.get("title") or item.get("display_name") or ""
    title = clean_whitespace(raw_title) or "Untitled"
    field_provenance["title"] = "openalex"

    # Authors
    authors: List[Author] = []
    for authorship in item.get("authorships", []):
        author_dict = authorship.get("author", {})
        display_name = author_dict.get("display_name")
        author_obj = parse_author_name(full_name=display_name)
        if author_obj.warning:
            warnings.append(author_obj.warning)
        authors.append(author_obj)
    if authors:
        field_provenance["authors"] = "openalex"

    # Year
    year = item.get("publication_year")
    if year:
        try:
            year = int(year)
            field_provenance["year"] = "openalex"
        except (ValueError, TypeError):
            year = None

    # Journal
    journal: Optional[str] = None
    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    host_venue = item.get("host_venue") or {}

    source_name = source.get("display_name") or host_venue.get("display_name")
    if source_name:
        journal = clean_whitespace(str(source_name))
        field_provenance["journal"] = "openalex"

    # Journal Abbreviation (lookup from curated mapping)
    journal_abbreviation: Optional[str] = None
    if journal:
        curated_abbrev, abbrev_warn = get_journal_abbreviation(journal)
        if curated_abbrev:
            journal_abbreviation = curated_abbrev
            field_provenance["journal_abbreviation"] = "curated_abbreviation"
        elif abbrev_warn:
            warnings.append(abbrev_warn)

    # DOI
    doi_raw = item.get("doi")
    clean_doi, doi_url = normalize_doi(doi_raw)
    if doi_url:
        field_provenance["doi_url"] = "openalex"

    # Biblio: volume, issue, first_page
    biblio = item.get("biblio") or {}
    volume: Optional[str] = (
        clean_whitespace(str(biblio.get("volume"))) if biblio.get("volume") is not None else None
    )
    if volume:
        field_provenance["volume"] = "openalex"

    issue: Optional[str] = (
        clean_whitespace(str(biblio.get("issue"))) if biblio.get("issue") is not None else None
    )
    if issue:
        field_provenance["issue"] = "openalex"

    first_page: Optional[str] = (
        clean_whitespace(str(biblio.get("first_page")))
        if biblio.get("first_page") is not None
        else None
    )
    if first_page:
        field_provenance["first_page"] = "openalex"

    article_number: Optional[str] = None
    raw_article_num = biblio.get("article_number") or item.get("article_number")
    if raw_article_num is not None:
        article_number = clean_whitespace(str(raw_article_num))
        if article_number:
            field_provenance["article_number"] = "openalex"

    # If first_page looks like an article ID (>= 6 digits numeric) and no article_number
    if first_page and first_page.isdigit() and len(first_page) >= 6 and not article_number:
        article_number = first_page
        first_page = None
        field_provenance["article_number"] = "openalex"
        warnings.append(f"Ambiguous page-like value '{article_number}' treated as article number")

    # Preprint check
    work_type = str(item.get("type", "")).lower()
    source_type = str(source.get("type", "")).lower()
    is_preprint = ("preprint" in work_type) or (source_type == "repository")

    work_id = item.get("id")
    return ArticleMetadata(
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        journal_abbreviation=journal_abbreviation,
        doi_url=doi_url,
        volume=volume,
        issue=issue,
        first_page=first_page,
        article_number=article_number,
        source_provider="openalex",
        provider_id=work_id,
        source_url=doi_url or work_id,
        raw_data=item,
        field_provenance=field_provenance,
        warnings=warnings,
        is_preprint=is_preprint,
    )
