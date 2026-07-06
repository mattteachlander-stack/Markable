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
    package: Path = typer.Argument(..., help="Assessment package."),
    pdfs: list[Path] = typer.Argument(None, help="Scanned script PDF(s)."),
) -> None:
    """[Phase 2] Split, deskew, and match scanned scripts to students + zones."""
    _phase_stub("scan", "Phase 2", "split/deskew scans, read QR, crop answer zones via the manifest")


@app.command()
def mark(package: Path = typer.Argument(..., help="Assessment package.")) -> None:
    """[Phase 2] AI-mark all matched scripts, per question."""
    _phase_stub("mark", "Phase 2/3", "batch cropped responses per question and mark against key.yaml")


@app.command()
def report(
    package: Path = typer.Argument(..., help="Assessment package."),
    curriculum: Optional[str] = typer.Option(None, help="[Phase 6] Standards-referenced reporting."),
    dashboard: bool = typer.Option(False, help="[Phase 8] Emit the self-contained HTML dashboard."),
) -> None:
    """[Phase 4] Scores, feedback sheets, item analysis, star-schema export."""
    _phase_stub("report", "Phase 4", "results.csv, item analysis, feedback sheets, fact_response + dims")


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
