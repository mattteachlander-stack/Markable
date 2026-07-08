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
    if dashboard:
        from .dashboard_html import run_dashboard

        try:
            out = run_dashboard(package)
        except FileNotFoundError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)
        console.print(f"[green]✓[/green] Dashboard → [bold]{out}[/bold] (single file — open in any browser)")
        return
    if curriculum:
        from .curriculum import CurriculumError, load_pack
        from .standards import run_curriculum_report

        try:
            pack = load_pack(curriculum)
            result = run_curriculum_report(package, pack)
        except (CurriculumError, ValueError, FileNotFoundError) as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)
        console.print(
            f"[green]✓[/green] Standards report: {result['outcomes_assessed']} outcome(s), "
            f"{result['students']} student(s), {result['misconceptions']} misconception signal(s)"
        )
        console.print(f"  [bold]{result['html']}[/bold] (single file — open in any browser)")
        console.print("  export/fact_attainment.csv · export/dim_outcome.csv")
        if result["untagged_questions"]:
            console.print(f"  [yellow]untagged questions excluded: {', '.join(result['untagged_questions'])}[/yellow]")
        if result["outcomes_unassessed"]:
            console.print(f"  coverage: {result['outcomes_unassessed']} outcome(s) at this level not yet assessed")
        return

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
    package: Path = typer.Argument(..., exists=True, help="Assessment package."),
    curriculum: str = typer.Option(..., help="Curriculum pack id (or a pack.yaml path)."),
    tag_map: Optional[Path] = typer.Option(
        None, "--map", help="YAML of confirmed tags {Q1: [CODE, ...]} — non-interactive."
    ),
) -> None:
    """Map each question to curriculum outcomes (interactive confirm)."""
    from .curriculum import CurriculumError, load_pack, run_tag

    try:
        pack = load_pack(curriculum)
    except CurriculumError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    mapping = None
    if tag_map is not None:
        import yaml as _yaml

        mapping = _yaml.safe_load(tag_map.read_text(encoding="utf-8")) or {}

    def interactive(qid: str, proposals) -> list[str]:
        console.print(f"\n[bold]{qid}[/bold] — proposals from {pack.curriculum}:")
        if not proposals:
            console.print("  [dim](no confident proposal — enter codes manually or leave blank)[/dim]")
        for p in proposals:
            console.print(f"  [cyan]{p.code}[/cyan]  score {p.score}  [dim]{p.justification}[/dim]")
        default = proposals[0].code if proposals else ""
        answer = typer.prompt("  Outcome codes (comma-separated, blank = none)", default=default)
        return [c.strip() for c in answer.split(",") if c.strip()]

    try:
        assessment = run_tag(
            package, pack,
            resolver=None if mapping is not None else interactive,
            tag_map=mapping,
        )
    except CurriculumError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    tagged = sum(1 for q in assessment.questions if q.outcome_codes)
    console.print(f"[green]✓[/green] {tagged}/{len(assessment.questions)} questions tagged → assessment.yaml")


@app.command()
def studio(
    out: Path = typer.Option(Path("markable.html"), "-o", "--out", help="Output hub file."),
) -> None:
    """Generate the Markable Studio hub — a single-file landing page + upload tools."""
    from .studio_html import render_studio

    out.write_text(render_studio(), encoding="utf-8")
    console.print(f"[green]✓[/green] Markable Studio → [bold]{out}[/bold]")
    console.print("  Open it in any browser. Keep generated report files (dashboard.html, …)")
    console.print("  in the same folder and they'll open from the left-hand menu.")


@app.command()
def gradebook(
    workbook: Path = typer.Argument(..., exists=True, help="Teacher SAC gradebook (.xlsx)."),
    study_design: Optional[str] = typer.Option(
        None, "--study-design", help="Curriculum/study-design pack id to map SAC questions against."
    ),
    map_file: Optional[Path] = typer.Option(
        None, "--map", help="YAML {sac_number: {question_id: [codes]}} — teacher-confirmed mappings."
    ),
    out: Path = typer.Option(Path("sac_dashboard.html"), "-o", "--out", help="Output HTML file."),
) -> None:
    """Build a multi-SAC dashboard (+ skills mapping) from a marks spreadsheet."""
    try:
        from .gradebook import read_gradebook
    except ImportError:
        console.print("[red]Gradebook reading needs the 'xlsx' extra: uv sync --extra xlsx[/red]")
        raise typer.Exit(code=1)

    try:
        gb = read_gradebook(workbook)
    except (ValueError, RuntimeError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    skills = None
    pack_name = ""
    if study_design:
        from .curriculum import CurriculumError, load_pack
        from .gradebook_html import render_gradebook
        from .studydesign import compute_skills

        try:
            pack = load_pack(study_design)
        except CurriculumError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)
        pack_name = f"{pack.curriculum} v{pack.version}"
        teacher_map = None
        if map_file is not None:
            import yaml as _yaml

            teacher_map = _yaml.safe_load(map_file.read_text(encoding="utf-8")) or {}
        skills = [compute_skills(sac, pack, teacher_map) for sac in gb.sacs]
    else:
        from .gradebook_html import render_gradebook

    out.write_text(render_gradebook(gb, skills, pack_name), encoding="utf-8")

    table = Table(title=f"Parsed {gb.source}", show_edge=False)
    for col in ("SAC", "Topic", "Questions", "Students", "Avg"):
        table.add_column(col)
    for sac in gb.sacs:
        pct = [100 * sac.total_for(s) / sac.total_marks for s in sac.students if sac.total_marks]
        table.add_row(str(sac.number), sac.topic, str(len(sac.questions)),
                      str(len(sac.students)), f"{sum(pct)/len(pct):.0f}%")
    console.print(table)
    if skills:
        mapped = sum(1 for sk in skills for m in sk.question_maps if m.codes)
        total = sum(len(sk.question_maps) for sk in skills)
        console.print(f"  study design: {mapped}/{total} questions mapped against {pack_name}")
    console.print(f"[green]✓[/green] Dashboard → [bold]{out}[/bold] (single file — open in any browser)")


@app.command()
def analyse(
    source: Path = typer.Argument(..., exists=True, help="Assessment draft (.md) or an ingested package dir."),
    curriculum: str = typer.Option(..., help="Curriculum pack id (or a pack.yaml path)."),
    out: Optional[Path] = typer.Option(None, "-o", "--out", help="Output directory (default: beside the source)."),
) -> None:
    """Analyse a test: map every item to curriculum codes + cognitive level."""
    from .analysis import run_analyse
    from .curriculum import CurriculumError, load_pack

    try:
        pack = load_pack(curriculum)
        result = run_analyse(source, pack, out_dir=out)
    except (CurriculumError, Exception) as exc:  # IngestError etc. — show, don't trace
        if not isinstance(exc, (CurriculumError, ValueError)):
            raise
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    table = Table(title="Curriculum mapping (proposals — confirm with `markable tag`)", show_edge=False)
    for col in ("Item", "Marks", "Concept area", "Code", "Level", "Skill"):
        table.add_column(col)
    for r in result["rows"]:
        table.add_row(r.question_id, str(r.marks), r.concept_area, r.code or "—",
                      r.cognitive_level, r.skill[:60] + ("…" if len(r.skill) > 60 else ""))
    console.print(table)
    console.print(
        f"[green]✓[/green] {result['mapped']}/{len(result['rows'])} items mapped → "
        f"[bold]{result['html']}[/bold] + {result['csv'].name}"
    )


@curriculum_app.command("import")
def curriculum_import(
    source: Path = typer.Argument(..., exists=True, help="Curriculum source (pack.yaml; MRAC/PDF later)."),
    pack_id: str = typer.Option(..., "--id", help="Pack id, e.g. ac9-science."),
) -> None:
    """Import a curriculum into a versioned curricula/<id>/pack.yaml."""
    from .curriculum import CurriculumError, import_pack

    try:
        target = import_pack(source, pack_id)
    except CurriculumError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]✓[/green] Imported pack [bold]{pack_id}[/bold] → {target}/")


@curriculum_app.command("list")
def curriculum_list() -> None:
    """List imported curriculum packs."""
    from .curriculum import list_packs

    packs = list_packs()
    if not packs:
        console.print("No packs found under curricula/ — run `markable curriculum import`.")
        raise typer.Exit()
    table = Table(show_edge=False)
    for col in ("id", "curriculum", "version", "levels", "outcomes"):
        table.add_column(col)
    for p in packs:
        table.add_row(p["id"], p["curriculum"], p["version"], ",".join(p["levels"]), str(p["outcomes"]))
    console.print(table)


if __name__ == "__main__":
    app()
