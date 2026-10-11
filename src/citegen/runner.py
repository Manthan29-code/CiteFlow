import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from langgraph.types import Command

from citegen.cli_prompts import cli_prompt_for
from citegen.graph.state import CitationState
from citegen.graph.workflow import get_compiled_part1_graph, get_compiled_part2_graph
from citegen.latex.citation_keys import assign_batch_citation_keys
from citegen.latex.tex_export import export_tex
from citegen.metadata.models import ArticleMetadata

# =========================================================================
# Part 1: Title Processing
# =========================================================================


async def process_single_title(
    title: str,
    compiled_graph: Any = None,
) -> CitationState:
    """Run a single title through the Part 1 graph."""
    if compiled_graph is None:
        compiled_graph = get_compiled_part1_graph()

    initial_state: CitationState = {
        "input_title": title,
        "errors": [],
    }

    result = await compiled_graph.ainvoke(initial_state)
    return result


async def run_batch_titles(
    titles: List[str],
    output_path: Path,
    standalone: bool = True,
    force: bool = False,
    report_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
    verbose: bool = False,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Process a list of titles through the graph, resolve batch keys, and export LaTeX.
    Handles Ctrl+C cleanly: stops, still writes accepted results.
    Exit codes:
        0: all accepted
        1: some unresolved or failed (or skipped)
    """
    compiled_graph = get_compiled_part1_graph()
    results: List[CitationState] = []
    skipped_titles: List[str] = []

    try:
        for title in titles:
            clean_t = title.strip()
            if not clean_t or clean_t.startswith("#"):
                continue
            try:
                res = await process_single_title(clean_t, compiled_graph=compiled_graph)
                results.append(res)
            except Exception as e:
                # One failure never aborts the others
                results.append(
                    {
                        "input_title": clean_t,
                        "status": "failed",
                        "validation_errors": [str(e)],
                        "errors": [{"type": "unhandled_exception", "message": str(e)}],
                    }
                )
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Gracefully handle Ctrl+C: remaining titles marked skipped
        processed_titles = {r.get("input_title") for r in results}
        for t in titles:
            clean_t = t.strip()
            if clean_t and not clean_t.startswith("#") and clean_t not in processed_titles:
                skipped_titles.append(clean_t)

    # Separate accepted vs unresolved/failed
    accepted_items: List[Tuple[ArticleMetadata, str, CitationState]] = []
    unresolved_comments: List[Dict[str, Any]] = []

    for state in results:
        t = state.get("input_title", "Untitled")
        st = state.get("status", "unresolved")

        if st == "accepted" and state.get("selected_metadata") and state.get("bibitem"):
            meta = ArticleMetadata(**state["selected_metadata"])
            accepted_items.append((meta, state["bibitem"], state))
        else:
            reasons = state.get("validation_errors", [])
            if not reasons:
                reasons = [f"Status: {st}"]
            unresolved_comments.append(
                {
                    "title": t,
                    "reason": "; ".join(reasons),
                    "status": st,
                }
            )

    for sk in skipped_titles:
        unresolved_comments.append(
            {
                "title": sk,
                "reason": "Skipped due to interruption",
                "status": "skipped",
            }
        )

    # Batch citation key resolution for accepted items
    final_bibitems: List[str] = []
    if accepted_items:
        meta_draft_pairs = [(m, b) for m, b, _ in accepted_items]
        resolved_keys_bibitems = assign_batch_citation_keys(meta_draft_pairs)
        for (key, updated_bibitem), (_, _, state) in zip(resolved_keys_bibitems, accepted_items):
            state["bibitem"] = updated_bibitem
            final_bibitems.append(updated_bibitem)

    # Export .tex file
    export_tex(
        output_path=output_path,
        bibitems=final_bibitems,
        unresolved_items=unresolved_comments,
        standalone=standalone,
        force=force,
    )

    # Write report if requested
    report_data = {
        "total": len(titles),
        "accepted": len(accepted_items),
        "unresolved": len(unresolved_comments),
        "items": results,
    }
    if report_path:
        rpath = Path(report_path).resolve()
        rpath.parent.mkdir(parents=True, exist_ok=True)
        with open(rpath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

    # Write JSON metadata if requested
    if json_path:
        jpath = Path(json_path).resolve()
        jpath.parent.mkdir(parents=True, exist_ok=True)
        accepted_meta_list = [m.to_output_dict() for m, _, _ in accepted_items]
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump(accepted_meta_list, f, indent=2)

    has_non_accepted = bool(unresolved_comments) or bool(skipped_titles)
    exit_code = 1 if has_non_accepted else 0
    return exit_code, results


# =========================================================================
# Part 2: PDF & Interactive Title Processing
# =========================================================================


async def process_single_title_interactive(
    title: str,
    interactive: bool = True,
    compiled_graph: Any = None,
    thread_id: Optional[str] = None,
    prompt_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> CitationState:
    """
    Run a single title through the Part 2 graph with interactive human review support.
    """
    if compiled_graph is None:
        compiled_graph = get_compiled_part2_graph()

    clean_title = title.strip()
    tid = thread_id or f"title-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": tid}}

    initial_state: CitationState = {
        "input_title": clean_title,
        "title_confirmed": True,
        "interactive": interactive,
        "errors": [],
    }

    result = await compiled_graph.ainvoke(initial_state, config)

    # Human-in-the-loop interrupt resolution loop
    while "__interrupt__" in result:
        if not interactive:
            break
        interrupt_item = result["__interrupt__"][0]
        payload = interrupt_item.value
        ask_func = prompt_fn or cli_prompt_for
        answer = ask_func(payload)
        result = await compiled_graph.ainvoke(Command(resume=answer), config)

    return result


async def process_single_pdf(
    pdf_path: Path,
    interactive: bool = True,
    compiled_graph: Any = None,
    thread_id: Optional[str] = None,
    prompt_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> CitationState:
    """
    Run a single PDF through the Part 2 graph, handling interrupts for human review.
    """
    if compiled_graph is None:
        compiled_graph = get_compiled_part2_graph()

    resolved_path = Path(pdf_path).resolve()
    tid = thread_id or f"{resolved_path.stem}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": tid}}

    initial_state: CitationState = {
        "input_pdf_path": str(resolved_path),
        "interactive": interactive,
        "errors": [],
    }

    result = await compiled_graph.ainvoke(initial_state, config)

    # Human-in-the-loop interrupt resolution loop
    while "__interrupt__" in result:
        if not interactive:
            break
        interrupt_item = result["__interrupt__"][0]
        payload = interrupt_item.value
        ask_func = prompt_fn or cli_prompt_for
        answer = ask_func(payload)
        result = await compiled_graph.ainvoke(Command(resume=answer), config)

    return result


def _is_pdf_item(item: Any) -> bool:
    if isinstance(item, Path):
        return item.suffix.lower() == ".pdf" or item.is_file()
    if isinstance(item, str):
        p = Path(item)
        return (p.is_file() and p.suffix.lower() == ".pdf") or (not p.is_file() and item.lower().endswith(".pdf"))
    return False


async def run_batch_pdfs(
    pdf_paths: List[Any],
    output_path: Path,
    interactive: bool = True,
    standalone: bool = True,
    force: bool = False,
    report_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
    concurrency: int = 1,
    verbose: bool = False,
    prompt_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Process a batch of PDFs or article titles through the Part 2 graph.
    Handles Ctrl+C cleanly, runs sequential or concurrent, resolves citation keys,
    and exports LaTeX.
    """
    if interactive and concurrency > 1:
        raise ValueError("--concurrency > 1 is allowed only with --no-interactive")

    if output_path.exists() and not force:
        raise FileExistsError(
            f"Output file '{output_path}' already exists. Use --force to overwrite."
        )

    compiled_graph = get_compiled_part2_graph()
    results: List[CitationState] = []
    skipped_paths: List[Any] = []

    async def _dispatch_item(item: Any, is_interact: bool) -> CitationState:
        if _is_pdf_item(item):
            return await process_single_pdf(
                pdf_path=Path(item),
                interactive=is_interact,
                compiled_graph=compiled_graph,
                prompt_fn=prompt_fn,
            )
        else:
            return await process_single_title_interactive(
                title=str(item),
                interactive=is_interact,
                compiled_graph=compiled_graph,
                prompt_fn=prompt_fn,
            )

    try:
        if interactive or concurrency <= 1:
            for p in pdf_paths:
                try:
                    res = await _dispatch_item(p, interactive)
                    results.append(res)
                except Exception as e:
                    item_title = p.stem if isinstance(p, Path) else str(p)
                    fail_dict: Dict[str, Any] = {
                        "input_title": item_title,
                        "status": "failed",
                        "validation_errors": [str(e)],
                        "errors": [{"type": "unhandled_exception", "message": str(e)}],
                    }
                    if _is_pdf_item(p):
                        fail_dict["input_pdf_path"] = str(p)
                    results.append(fail_dict)
        else:
            # Concurrent execution in non-interactive mode
            sem = asyncio.Semaphore(concurrency)

            async def _worker(p: Any) -> CitationState:
                async with sem:
                    try:
                        return await _dispatch_item(p, False)
                    except Exception as e:
                        item_title = p.stem if isinstance(p, Path) else str(p)
                        fail_dict: Dict[str, Any] = {
                            "input_title": item_title,
                            "status": "failed",
                            "validation_errors": [str(e)],
                            "errors": [{"type": "unhandled_exception", "message": str(e)}],
                        }
                        if _is_pdf_item(p):
                            fail_dict["input_pdf_path"] = str(p)
                        return fail_dict

            tasks = [_worker(p) for p in pdf_paths]
            results = await asyncio.gather(*tasks)

    except (KeyboardInterrupt, asyncio.CancelledError):
        # Gracefully handle Ctrl+C: remaining items marked skipped
        processed_identifiers = set()
        for r in results:
            if r.get("input_pdf_path"):
                try:
                    processed_identifiers.add(Path(r["input_pdf_path"]).resolve())
                except Exception:
                    pass
                processed_identifiers.add(r["input_pdf_path"])
            if r.get("input_title"):
                processed_identifiers.add(r["input_title"])

        for p in pdf_paths:
            is_processed = False
            if isinstance(p, Path):
                try:
                    if p.resolve() in processed_identifiers or str(p) in processed_identifiers:
                        is_processed = True
                except Exception:
                    pass
            elif str(p) in processed_identifiers:
                is_processed = True

            if not is_processed:
                skipped_paths.append(p)


    # Separate accepted vs unresolved/failed
    accepted_items: List[Tuple[ArticleMetadata, str, CitationState]] = []
    unresolved_comments: List[Dict[str, Any]] = []

    for state in results:
        title_name = state.get("input_title") or state.get("selected_title")
        if not title_name and state.get("input_pdf_path"):
            title_name = Path(state["input_pdf_path"]).name
        title_name = title_name or "Untitled PDF"

        st = state.get("status", "unresolved")

        if st == "accepted" and state.get("selected_metadata") and state.get("bibitem"):
            meta = ArticleMetadata(**state["selected_metadata"])
            accepted_items.append((meta, state["bibitem"], state))
        else:
            reasons = state.get("validation_errors", [])
            if not reasons:
                reasons = [f"Status: {st}"]
            unresolved_comments.append(
                {
                    "title": title_name,
                    "reason": "; ".join(reasons),
                    "status": st,
                }
            )

    for sk in skipped_paths:
        unresolved_comments.append(
            {
                "title": sk.name,
                "reason": "Skipped due to interruption",
                "status": "skipped",
            }
        )

    # Batch citation key resolution across all accepted items
    final_bibitems: List[str] = []
    if accepted_items:
        meta_draft_pairs = [(m, b) for m, b, _ in accepted_items]
        resolved_keys_bibitems = assign_batch_citation_keys(meta_draft_pairs)
        for (key, updated_bibitem), (_, _, state) in zip(resolved_keys_bibitems, accepted_items):
            state["bibitem"] = updated_bibitem
            final_bibitems.append(updated_bibitem)

    # Export .tex file
    export_tex(
        output_path=output_path,
        bibitems=final_bibitems,
        unresolved_items=unresolved_comments,
        standalone=standalone,
        force=force,
    )

    # Write report if requested
    report_data = {
        "total": len(pdf_paths),
        "accepted": len(accepted_items),
        "unresolved": len(unresolved_comments),
        "items": results,
    }
    if report_path:
        rpath = Path(report_path).resolve()
        rpath.parent.mkdir(parents=True, exist_ok=True)
        with open(rpath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

    # Write JSON metadata if requested
    if json_path:
        jpath = Path(json_path).resolve()
        jpath.parent.mkdir(parents=True, exist_ok=True)
        accepted_meta_list = [m.to_output_dict() for m, _, _ in accepted_items]
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump(accepted_meta_list, f, indent=2)

    has_non_accepted = bool(unresolved_comments) or bool(skipped_paths)
    exit_code = 1 if has_non_accepted else 0
    return exit_code, results
