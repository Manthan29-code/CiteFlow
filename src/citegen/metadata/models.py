from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Author(BaseModel):
    surname: Optional[str] = None
    given_name: Optional[str] = None
    middle_name: Optional[str] = None
    original_name: Optional[str] = None
    is_ambiguous: bool = False
    warning: Optional[str] = None

    def model_dump_for_display(self) -> Dict[str, Any]:
        return {
            "surname": self.surname,
            "given_name": self.given_name,
            "middle_name": self.middle_name,
            "original_name": self.original_name,
        }


class ArticleMetadata(BaseModel):
    title: str
    authors: List[Author] = Field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    journal_abbreviation: Optional[str] = None
    doi_url: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    first_page: Optional[str] = None
    article_number: Optional[str] = None

    # Internal tracking fields
    source_provider: Optional[str] = None  # "crossref", "openalex", or "merged"
    provider_id: Optional[str] = None
    source_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    field_provenance: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    is_preprint: bool = False

    def to_output_dict(self) -> Dict[str, Any]:
        """Returns the dictionary with the required output fields."""
        return {
            "title": self.title,
            "authors": [
                {
                    "surname": a.surname,
                    "given_name": a.given_name,
                    "middle_name": a.middle_name,
                }
                for a in self.authors
            ],
            "year": self.year,
            "journal": self.journal,
            "journal_abbreviation": self.journal_abbreviation,
            "doi_url": self.doi_url,
            "volume": self.volume,
            "issue": self.issue,
            "first_page": self.first_page,
            "article_number": self.article_number,
        }
