from pathlib import Path

import pytest

from citegen.latex.tex_export import export_tex, render_tex_document

pytestmark = pytest.mark.part1


def test_standalone_rendering():
    bibitems = [r"\bibitem{Kunz2014} Kunz M W 2014 \textit{Phys. Rev. Lett.}."]
    doc = render_tex_document(bibitems, standalone=True)

    assert r"\documentclass{article}" in doc
    assert r"\usepackage{hyperref}" in doc
    assert r"\begin{thebibliography}{99}" in doc
    assert r"\bibitem{Kunz2014}" in doc
    assert r"\end{thebibliography}" in doc
    assert r"\end{document}" in doc


def test_fragment_rendering():
    bibitems = [r"\bibitem{Kunz2014} Kunz M W 2014 \textit{Phys. Rev. Lett.}."]
    doc = render_tex_document(bibitems, standalone=False)

    assert r"\documentclass" not in doc
    assert r"\begin{thebibliography}{99}" in doc
    assert r"\bibitem{Kunz2014}" in doc
    assert r"\end{thebibliography}" in doc


def test_unresolved_items_as_comments():
    bibitems = [r"\bibitem{Accepted2020} Accepted Entry."]
    unresolved = [{"title": "Unresolved Title", "reason": "No DOI or volume found"}]
    doc = render_tex_document(bibitems, unresolved_items=unresolved, standalone=False)

    assert "% UNRESOLVED: Unresolved Title - No DOI or volume found" in doc
    assert r"\bibitem{Unresolved" not in doc


def test_export_refuses_overwrite_without_force(tmp_path: Path):
    target = tmp_path / "refs.tex"
    target.write_text("existing content", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Use --force to overwrite"):
        export_tex(target, [r"\bibitem{A} A."], force=False)

    # With force=True, it succeeds
    export_tex(target, [r"\bibitem{A} A."], force=True)
    assert r"\bibitem{A}" in target.read_text(encoding="utf-8")


def test_braces_balanced_in_tex_file(tmp_path: Path):
    target = tmp_path / "check.tex"
    export_tex(
        target,
        [
            r"\bibitem{Kunz2014} Kunz M W 2014 \textit{Phys. Rev. Lett.} \href{https://doi.org/10.1103/PhysRevLett.112.205003}{\textbf{112} 205003}."
        ],
        standalone=True,
    )
    content = target.read_text(encoding="utf-8")
    assert content.count("{") == content.count("}")
