import re
import unicodedata
from collections import Counter
from typing import List, Optional, Tuple

from citegen.metadata.models import ArticleMetadata


def sanitize_citation_key_part(text: Optional[str]) -> str:
    """Normalize text into safe ASCII alphanumeric identifier."""
    if not text:
        return ""
    # Normalize unicode to decomposed form (e.g. é -> e + accent)
    nfkd = unicodedata.normalize("NFKD", text)
    # Filter to ASCII only
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Keep only alphanumeric characters
    cleaned = re.sub(r"[^A-Za-z0-9]", "", ascii_text)
    return cleaned


def generate_base_citation_key(metadata: ArticleMetadata) -> str:
    """
    Generate base citation key: First author surname + Year (e.g., Kunz2014).
    """
    surname = ""
    if metadata.authors and metadata.authors[0].surname:
        surname = metadata.authors[0].surname
    elif metadata.authors and metadata.authors[0].original_name:
        surname = metadata.authors[0].original_name
    else:
        surname = "Anon"

    clean_surname = sanitize_citation_key_part(surname)
    if not clean_surname:
        clean_surname = "Anon"

    year_str = str(metadata.year) if metadata.year else "ND"
    return f"{clean_surname}{year_str}"


def update_bibitem_key(bibitem_str: str, new_key: str) -> str:
    """Update the citation key inside a \\bibitem{old_key} string."""
    return re.sub(
        r"\\bibitem\{[^}]+\}",
        lambda _: f"\\bibitem{{{new_key}}}",
        bibitem_str,
        count=1,
    )


def disambiguate_keys(base_keys: List[str]) -> List[str]:
    """
    Deterministically assign unique keys across a batch.
    If a base key appears more than once, append 'a', 'b', 'c', ...
    in stable input order.
    """
    counts = Counter(base_keys)
    seen_counts: dict[str, int] = {}
    final_keys: List[str] = []

    for key in base_keys:
        if counts[key] == 1:
            final_keys.append(key)
        else:
            idx = seen_counts.get(key, 0)
            suffix = chr(ord("a") + idx)
            final_keys.append(f"{key}{suffix}")
            seen_counts[key] = idx + 1

    return final_keys


def assign_batch_citation_keys(
    items: List[Tuple[ArticleMetadata, str]],
) -> List[Tuple[str, str]]:
    """
    Assign final unique citation keys for a batch of (metadata, draft_bibitem) pairs.
    Returns:
        List of (final_key, updated_bibitem)
    """
    base_keys = [generate_base_citation_key(m) for m, _ in items]
    final_keys = disambiguate_keys(base_keys)

    results: List[Tuple[str, str]] = []
    for key, (_, bibitem) in zip(final_keys, items):
        updated_bibitem = update_bibitem_key(bibitem, key)
        results.append((key, updated_bibitem))

    return results
