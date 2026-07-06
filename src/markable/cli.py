"""Markable CLI — five pipeline commands plus Part 2 stubs.

Phase 1 implements `ingest` and `build`. `scan`, `mark`, `report`, `curriculum`,
and `tag` are stubs that state their phase and exit non-zero, so the command
surface (and the architecture for Parts 2-3) exists from day one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .ingest import IngestError, ingest_file, write_assessment, load_assessment

app = typer.Typer(
    name="markable",
    help="Prepare, mark, and analyse paper-based school assessments.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

# Curriculum + tag are Part 2; grouped under their own sub-app as stubs so the
# architecture anticipates them (brief section 11.2).
curriculum_app = typer.Typer(help="[Phase 5] Manage curriculum packs.", no_args_is_help=True)
app.add_typer(curriculum_app, name="curriculum")


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"markable {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Markable — assessment structuring, marking, and curriculum intelligence."""


def _phase_stub(command: str, phase: str, summary: str) -> None:
    console.print(f"[yellow]`markable {command}` is not implemented yet.[/yellow]")
    console.print(f"  Scheduled for [bold]{phase}[/bold]: {summary}")
    console.print("  Phase 1 covers `ingest` and `build` only (see PROJECT_BRIEF.md section 6).")
    raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# Phase 1 — ingest
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    draft: Path = typer.Argument(..., exists=True, readable=True, help="Draft .md (.docx/.pdf are Phase 1b)."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Where to write assessment.yaml."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive: fail on unresolved gaps instead of prompting."),
) -> None:
    """Parse a teacher's draft into the canonical `assessment.yaml`."""

    def prompt_resolver(qid: str, gap) -> object:
        return typer.prompt(f"  {gap.prompt}", type=int)

    resolver = None if yes else prompt_resolver
    try:
        assessment = ingest_file(draft, resolver=resolver, assume_yes=yes)
    except IngestError as exc:
        console.print(f"[red]Ingest failed:[/red] {exc}")
        raise typer.Exit(code=1)

    target = out or (draft.parent / "assessment.yaml")
    write_assessment(assessment, target)

    table = Table(title=f"Ingested {assessment.test_id}", show_edge=False)
    table.add_column("Question")
    table.add_column("Type")
    table.add_column("Marks", justify="right")
    for q in assessment.questions:
        table.add_row(q.id, q.type.value, str(q.marks))
    console.print(table)
    console.print(
        f"[green]✓[/green] {len(assessment.questions)} questions, "
        f"{assessment.total_marks} marks → [bold]{target}[/bold]"
    )


# ---------------------------------------------------------------------------
# Phase 1 — build
# ---------------------------------------------------------------------------


@app.command()
def build(
    package: Path = typer.Argument(..., help="Package directory to create/populate."),
    assessment: Optional[Path] = typer.Option(
        None, "--assessment", "-a", help="assessment.yaml (defaults to <package>/assessment.yaml)."
    ),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="Emit paper.typ but skip PDF compilation."),
) -> None:
    """Generate the print-ready paper + marking pack + manifest."""
    from .build import build_package  # local import keeps `typst` cost off the ingest path

    src = assessment or (package / "assessment.yaml")
    if not src.exists():
        console.print(
            f"[red]No assessment found at {src}.[/red] Run `markable ingest` first, "
            "or pass --assessment."
        )
        raise typer.Exit(code=1)

    model = load_assessment(src)
    result = build_package(model, package, compile_pdf=not no_pdf)

    console.print(f"[green]✓[/green] Built package [bold]{result.package_dir}[/bold]")
    console.print(f"  version_hash: {result.version_hash}  ·  {result.total_pages} page(s)")
    console.print(f"  assessment:   {result.assessment_path.name}")
    console.print(f"  key:          {result.key_path.name} [dim](scaffold — refine before scanning)[/dim]")
    console.print(f"  manifest:     {result.manifest_path.name}")
    console.print(f"  paper:        {result.typst_path.name}" + (
        f" + {result.pdf_path.name}" if result.pdf_path else " [dim](PDF skipped)[/dim]"
    ))
    if result.pdf_path is None and not no_pdf:
        console.print("  [yellow]PDF not compiled — install the 'typst' package (uv sync).[/yellow]")


# ---------------------------------------------------------------------------
# Phase 2+ stubs
# ---------------------------------------------------------------------------


@app.command()
def scan(
    package: Path = typer.Argument(..., exists=True, help="Assessment package."),
    pdfs: list[Path] = typer.Argument(..., help="Scanned script PDF(s) or page images."),
    dpi: float = typer.Option(300.0, help="Nominal resolution of the scans."),
    id_map: Optional[Path] = typer.Option(
        None,
        "--id-map",
        help="YAML mapping scans to student ids: '<file.pdf>: S1042' (whole file) "
        "or '<file.pdf>:<page>: S1042' (per page).",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive: leave unknown ids unassigned."),
) -> None:
    """Split, deskew, and match scanned scripts; crop every answer zone."""
    try:
        from .scan import scan_package
    except ImportError:
        console.print(
            "[red]Scan dependencies missing.[/red] Install them with: uv sync --extra scan"
        )
        raise typer.Exit(code=1)

    mapping = None
    if id_map is not None:
        import yaml as _yaml

        mapping = _yaml.safe_load(id_map.read_text(encoding="utf-8")) or {}

    last: dict = {"sid": None, "page": 0}

    def interactive_resolver(source: str, index: int, page_number: int, id_crop) -> Optional[str]:
        # Heuristic default: consecutive pages of the same script arrive in
        # order, so if the paper page number advanced, offer the previous id.
        default = last["sid"] if last["sid"] and page_number > last["page"] else None
        hint = f" [dim](ID box image: {id_crop})[/dim]" if id_crop else ""
        console.print(f"  {source} page {index} → paper page {page_number}{hint}")
        answer = typer.prompt("  Student ID", default=default or "", show_default=bool(default))
        answer = answer.strip() or None
        last["sid"], last["page"] = answer, page_number
        return answer

    report = scan_package(
        package,
        pdfs,
        dpi=dpi,
        id_map=mapping,
        id_resolver=None if yes else interactive_resolver,
    )

    ok = sum(1 for p in report.pages if p.status.value == "ok")
    console.print(
        f"[green]✓[/green] {ok}/{len(report.pages)} pages matched → "
        f"{len(report.students)} student(s) · scan_report.json written"
    )
    for p in report.pages:
        if p.status.value != "ok":
            console.print(f"  [yellow]{p.status.value}[/yellow] {p.source} p{p.source_index}: {p.detail or ''}")
    for s in report.students:
        if s.pages_missing:
            console.print(f"  [yellow]{s.student_id} missing pages {s.pages_missing}[/yellow]")
        if s.blank_questions:
            console.print(f"  [dim]{s.student_id} blank: {', '.join(s.blank_questions)}[/dim]")


@app.command()
def mark(
    package: Path = typer.Argument(..., exists=True, help="Assessment package."),
    model: str = typer.Option("claude-opus-4-8", help="Anthropic model id."),
    batch: bool = typer.Option(False, "--batch", help="Use the Message Batches API (cheaper for whole classes)."),
) -> None:
    """AI-mark all scanned scripts, per question, against key.yaml."""
    from .mark import run_mark

    try:
        from .mark.anthropic_marker import AnthropicMarker

        marker = AnthropicMarker(model=model, use_batches=batch)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    run = run_mark(package, marker)
    marked = sum(1 for j in run.judgements if j.status.value == "marked")
    review = sum(1 for j in run.judgements if j.status.value == "review")
    errors = sum(1 for j in run.judgements if j.status.value == "error")
    console.print(
        f"[green]✓[/green] {marked}/{len(run.judgements)} responses marked · "
        f"{review} in review queue" + (f" · [red]{errors} errors[/red]" if errors else "")
    )
    if review:
        console.print(f"  Review queue → [bold]{package / 'review.html'}[/bold], record final marks in review_overrides.yaml")


@app.command()
def report(
    package: Path = typer.Argument(..., exists=True, help="Assessment package."),
    curriculum: Optional[str] = typer.Option(None, help="[Phase 6] Standards-referenced reporting."),
    dashboard: bool = typer.Option(False, help="[Phase 8] Emit the self-contained HTML dashboard."),
) -> None:
    """Scores, item analysis, teacher summary, star-schema export."""
    if curriculum:
        _phase_stub("report --curriculum", "Phase 6", "standards-referenced reporting needs Part 2 tagging")
    if dashboard:
        _phase_stub("report --dashboard", "Phase 8", "self-contained HTML dashboard")

    from .report import run_report

    try:
        result = run_report(package)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓[/green] Reported {result['judgements']} judgements for "
        f"{result['students']} student(s)"
    )
    console.print("  results.csv · totals.csv · item_analysis.csv · summary.md · export/ (star schema)")
    if result["overrides_applied"]:
        console.print(f"  {result['overrides_applied']} teacher override(s) applied")
    if result["still_in_review"]:
        console.print(
            f"  [yellow]{result['still_in_review']} judgement(s) still unreviewed[/yellow] — "
            "finalise them in review_overrides.yaml and re-run report"
        )


@app.command()
def tag(
    package: Path = typer.Argument(..., help="Assessment package."),
    curriculum: str = typer.Option(..., help="Curriculum pack id, e.g. ac9-science."),
) -> None:
    """[Phase 5] Map each question to curriculum outcomes (interactive)."""
    _phase_stub("tag", "Phase 5", "propose + confirm outcome codes per question against a pack")


@curriculum_app.command("import")
def curriculum_import(
    source: Path = typer.Argument(..., help="Curriculum source (MRAC file, PDF, or URL export)."),
    pack_id: str = typer.Option(..., "--id", help="Pack id, e.g. ac9-science."),
) -> None:
    """[Phase 5] Import an official curriculum into a versioned pack.yaml."""
    _phase_stub("curriculum import", "Phase 5", "ingest AC v9 (MRAC) or Claude-assisted PDF → pack.yaml")


@curriculum_app.command("list")
def curriculum_list() -> None:
    """[Phase 5] List imported curriculum packs."""
    _phase_stub("curriculum list", "Phase 5", "enumerate curricula/*/pack.yaml")


if __name__ == "__main__":
    app()
