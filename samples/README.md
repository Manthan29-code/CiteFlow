# Sample Files

This directory is intended for local sample files (e.g. test papers, PDF files in Part 2).
Generated files and personal documents in this directory should not be committed to version control.

Without --no-interactive (Interactive Mode — Default):

When title confidence is high ($\ge 0.85$) with a clear winner, CiteFlow automatically accepts the title without interrupting you.
If a PDF has low confidence, an ambiguous title, or metadata conflicts (e.g., missing author, mismatching year between Crossref and OpenAlex), it halts and asks you in the terminal to confirm/edit the title or select the correct candidate.
Best for: Working on individual PDFs or when you want human verification before writing .tex files.
With --no-interactive:

Automatically picks the highest-ranked title candidate without prompting the user.
If metadata validation fails or is ambiguous, it marks it as unresolved in the final summary report rather than pausing for input.
Best for: Batch processing folders or scripts (e.g., citegen run samples/ --no-interactive).
