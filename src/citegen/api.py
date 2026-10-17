import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from citegen.graph.state import CitationState
from citegen.graph.workflow import get_compiled_part2_graph
from citegen.latex.citation_keys import (
    generate_base_citation_key,
    update_bibitem_key,
)
from citegen.latex.tex_export import render_tex_document
from citegen.metadata.models import ArticleMetadata


@dataclass
class RunResult:
    """Result returned by the core programmatic entry point."""
    status: str  # "accepted" | "unresolved" | "failed" | "interrupted"
    state: CitationState
    pending_interrupt: Optional[Dict[str, Any]] = None
    draft_record: Optional[Dict[str, Any]] = None
    reasons: List[Dict[str, Any]] = field(default_factory=list)
    error_code: Optional[str] = None
    raw_bibitem: Optional[str] = None


def render_single_record(
    metadata: ArticleMetadata | Dict[str, Any],
    raw_bibitem: Optional[str] = None,
    standalone: bool = True,
) -> str:
    """
    Renders thebibliography LaTeX document (standalone or fragment) for a single record.
    Assigns the deterministic citation key (FirstAuthorYear).
    """
    meta_obj = metadata if isinstance(metadata, ArticleMetadata) else ArticleMetadata(**metadata)
    base_key = generate_base_citation_key(meta_obj)

    if raw_bibitem:
        final_bibitem = update_bibitem_key(raw_bibitem, base_key)
    else:
        # Fallback to standard formatting if raw_bibitem not provided
        from citegen.latex.bibitem import format_bibitem
        final_bibitem = format_bibitem(meta_obj, citation_key=base_key)

    return render_tex_document([final_bibitem], standalone=standalone)


async def run_file(
    file_path: Path,
    thread_id: str,
    checkpointer: Optional[Any] = None,
    resume_payload: Optional[Dict[str, Any]] = None,
    interactive: bool = True,
    temp_dir: Optional[Path] = None,
) -> RunResult:
    """
    Core programmatic entry point for running citation generation on a single file.
    Executes the Part 2 graph, pauses on human interrupts, or resumes from checkpoints.
    Cancellation safety: never swallows asyncio.CancelledError.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled_graph = get_compiled_part2_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": str(thread_id)}}

    try:
        if resume_payload is not None:
            # Resuming an interrupted checkpoint
            result: CitationState = await compiled_graph.ainvoke(
                Command(resume=resume_payload), config
            )
        else:
            # Starting new execution from file
            resolved_path = Path(file_path).resolve()
            initial_state: CitationState = {
                "input_pdf_path": str(resolved_path),
                "interactive": interactive,
                "errors": [],
            }
            if temp_dir:
                initial_state["temp_dir"] = str(temp_dir)

            result = await compiled_graph.ainvoke(initial_state, config)

    except asyncio.CancelledError:
        # Allow cancellation to propagate cleanly
        raise
    except Exception as exc:
        return RunResult(
            status="failed",
            state={"status": "failed", "errors": [{"type": "exception", "message": str(exc)}]},
            error_code="pipeline_error",
            reasons=[{"code": "pipeline_error", "message": str(exc)}],
        )

    # Check for human review interrupt
    if "__interrupt__" in result:
        interrupt_item = result["__interrupt__"][0]
        payload = interrupt_item.value
        return RunResult(
            status="interrupted",
            state=result,
            pending_interrupt=payload,
            draft_record=result.get("selected_metadata"),
        )

    # Completed outcome
    graph_status = result.get("status", "unresolved")
    draft_record = result.get("selected_metadata")
    raw_bibitem = result.get("bibitem")

    # Format machine reasons
    reasons: List[Dict[str, Any]] = []
    for err in result.get("errors", []):
        if isinstance(err, dict):
            reasons.append(err)
        else:
            reasons.append({"message": str(err)})

    for v_err in result.get("validation_errors", []):
        reasons.append({"code": "validation_error", "message": str(v_err)})

    return RunResult(
        status=graph_status,
        state=result,
        draft_record=draft_record,
        raw_bibitem=raw_bibitem,
        reasons=reasons,
    )
