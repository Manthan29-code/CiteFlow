# Workflow Architecture

## Part 1: Metadata Engine

```text
START
  |
fan_out_search
  |                         |
crossref_search        openalex_search      (concurrent execution)
  |                         |
  +------------+------------+
               |
       normalize_provider_results
               |
       match_and_merge_records
               |
         validate_metadata
               |
        review_gate ----------------------> mark_unresolved ---> END
          (accepted?)       no
               | yes
         format_bibitem
               |
              END
```

### Key Principles:
- **No LLMs**: Fully deterministic parsing, querying, matching, and formatting.
- **Concurrency**: Crossref and OpenAlex queried simultaneously.
- **Failure Isolation**: One provider timeout/error does not crash the workflow; the other provider's result is used.
- **Zero Hallucination / Fabrication**: No fabricated fields, fake DOIs, or truncated abbreviations.
