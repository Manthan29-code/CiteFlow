# Metadata Schema Specification

## Required Normalized Fields

Every normalized record maps to `ArticleMetadata` with these output fields:

- `title`: String, normalized whitespace, HTML stripped.
- `authors`: Array of `Author` objects containing:
  - `surname`: Optional[str]
  - `given_name`: Optional[str]
  - `middle_name`: Optional[str]
- `year`: Optional[int]
- `journal`: Optional[str]
- `journal_abbreviation`: Optional[str] (resolved from curated mapping)
- `doi_url`: Optional[str] (`https://doi.org/<DOI>`)
- `volume`: Optional[str]
- `issue`: Optional[str]
- `first_page`: Optional[str]
- `article_number`: Optional[str]

## Field Provenance

Field sources are tracked explicitly (`crossref`, `openalex`, `curated_abbreviation`, `user_correction`).
Conflicting values between providers are recorded as conflicts and routed to unresolved status rather than silently overwritten.
