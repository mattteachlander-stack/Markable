"""Emit the print-ready paper as Typst, then compile to PDF.

Typst is used with a zero-margin page and absolute `place()` positioning, so
every element lands at the exact millimetre coordinate the layout engine
computed. The QR and registration marks are drawn from `layout`'s values, so the
printed page matches `manifest.json` exactly.

Compilation uses the `typst` Python package (no system binary needed). If it is
unavailable the `.typ` source is still written and `render` returns `None` for
the PDF, so the pipeline never hard-fails on a missing compiler.
"""

from __future__ import annotations

from pathlib import Path

from ..models import BBox, QuestionType
from ..qr import write_png
from .layout import (
    LaidOutPaper,
    LaidOutPage,
    MARGIN,
    QR_SIZE,
    QR_X,
    QR_Y,
    REG_SIZE,
    HEADER_TOP,
    id_box_bbox,
)


def _mm(v: float) -> str:
    return f"{v:.2f}mm"


def _place(dx: float, dy: float, body: str) -> str:
    return f"#place(top + left, dx: {_mm(dx)}, dy: {_mm(dy)})[{body}]\n"


def _rect(bbox: BBox, stroke: float = 0.5, radius: float = 1.0) -> str:
    return _place(
        bbox.x,
        bbox.y,
        f"#rect(width: {_mm(bbox.w)}, height: {_mm(bbox.h)}, "
        f"stroke: {stroke}pt, radius: {radius}pt)[]",
    )


def _ruled_lines(bbox: BBox, spacing: float = 8.0, top_pad: float = 8.0) -> str:
    out = ""
    y = bbox.y + top_pad
    while y < bbox.y + bbox.h - 2:
        out += _place(
            bbox.x + 3,
            y,
            f"#line(length: {_mm(bbox.w - 6)}, stroke: 0.25pt + luma(60%))",
        )
        y += spacing
    return out


def _label(x: float, y: float, text: str, size: int = 7) -> str:
    return _place(x, y, f"#text(size: {size}pt, fill: luma(35%))[{_escape(text)}]")


def _escape(s: str) -> str:
    # Minimal Typst escaping for text run into markup.
    for ch in ["\\", "#", "$", "*", "_", "`", "<", ">", "@", "[", "]"]:
        s = s.replace(ch, "\\" + ch)
    return s


def _registration(page: LaidOutPage) -> str:
    out = ""
    for cx, cy in [
        page.registration.top_left,
        page.registration.top_right,
        page.registration.bottom_left,
        page.registration.bottom_right,
    ]:
        out += _place(
            cx - REG_SIZE / 2,
            cy - REG_SIZE / 2,
            f"#rect(width: {_mm(REG_SIZE)}, height: {_mm(REG_SIZE)}, fill: black)[]",
        )
    return out


def _header(paper: LaidOutPaper, page: LaidOutPage, qr_rel: str) -> str:
    a = paper.assessment
    out = ""
    # Test id + title (top-left).
    out += _place(
        MARGIN,
        HEADER_TOP,
        f"#text(size: 11pt, weight: \"bold\")[{_escape(a.test_id)}]",
    )
    if a.title:
        out += _place(MARGIN, HEADER_TOP + 5, f"#text(size: 9pt)[{_escape(a.title)}]")
    # Page n of N (centre-ish).
    out += _place(
        MARGIN,
        HEADER_TOP + 11,
        f"#text(size: 9pt)[Page {page.number} of {len(paper.pages)}]",
    )
    # Student-ID box (handwritten id box; a pre-printed grid is a future option).
    # Geometry comes from layout.id_box_bbox() — the same bbox the manifest records.
    idb = id_box_bbox()
    out += _place(
        idb.x,
        idb.y,
        f"#rect(width: {_mm(idb.w)}, height: {_mm(idb.h)}, stroke: 0.5pt)[]",
    )
    out += _label(idb.x + 1.5, idb.y + 1.5, "Student ID", size=7)
    # QR (top-right).
    out += _place(QR_X, QR_Y, f"#image(\"{qr_rel}\", width: {_mm(QR_SIZE)})")
    return out


def _mcq_zone(pq) -> str:
    zone = pq.zone.bbox
    options = pq.question.options or {}
    out = ""
    cy = zone.y + zone.h / 2
    for i, label in enumerate(sorted(options)):
        bx = zone.x + 4 + i * 26
        out += _place(bx, cy - 3, "#circle(radius: 3mm, stroke: 0.5pt)[]")
        out += _place(bx + 7, cy - 3.2, f"#text(size: 9pt)[{_escape(label)}]")
    return out


def _numerical_zone(pq) -> str:
    zone = pq.zone.bbox
    out = _rect(zone)
    fa = pq.zone.final_answer_bbox
    if fa is not None:
        out += _rect(fa, stroke=0.6)
        out += _label(fa.x + 2, fa.y + 1.5, "Final answer:", size=8)
    return out


def _zone(pq) -> str:
    q = pq.question
    zone = pq.zone.bbox
    # Small self-identifying id tag beside every zone (brief 4.2).
    out = _label(zone.x, zone.y - 4.2, q.id, size=8)

    if q.type is QuestionType.mcq:
        out += _mcq_zone(pq)
    elif q.type is QuestionType.short_answer:
        out += _rect(zone) + _ruled_lines(zone)
    elif q.type is QuestionType.numerical:
        out += _numerical_zone(pq)
    elif q.type is QuestionType.extended:
        out += _rect(zone) + _ruled_lines(zone)
    elif q.type is QuestionType.diagram:
        out += _rect(zone, stroke=0.8)
        out += _label(zone.x + 2, zone.y + 2, "Draw and label here", size=8)
    return out


def _question(pq) -> str:
    q = pq.question
    stem = pq.stem_bbox
    marks = f"  [{q.marks} mark{'s' if q.marks != 1 else ''}]"
    body = f"#text(size: 10pt)[*{_escape(q.id)}.* {_escape(q.stem)}{_escape(marks)}]"
    out = _place(stem.x, stem.y, f"#box(width: {_mm(stem.w)})[{body}]")
    # For MCQ, list the option texts under the stem.
    if q.type is QuestionType.mcq and q.options:
        lines = "  ".join(f"*{_escape(k)}*) {_escape(v)}" for k, v in sorted(q.options.items()))
        out += _place(stem.x + 4, stem.y + 5, f"#box(width: {_mm(stem.w - 4)})[#text(size: 9pt)[{lines}]]")
    out += _zone(pq)
    return out


def emit_typst(paper: LaidOutPaper, qr_names: dict[int, str]) -> str:
    out = [
        f"#set page(width: {_mm(paper.page_w)}, height: {_mm(paper.page_h)}, margin: 0pt)",
        "#set text(size: 10pt)",
        "",
    ]
    for idx, page in enumerate(paper.pages):
        if idx > 0:
            out.append("#pagebreak()")
        out.append(_registration(page))
        out.append(_header(paper, page, qr_names[page.number]))
        for pq in page.questions:
            out.append(_question(pq))
    return "\n".join(out) + "\n"


def render(paper: LaidOutPaper, package_dir: Path, compile_pdf: bool = True) -> Path | None:
    """Write `paper.typ` (+ QR assets) and optionally compile `paper.pdf`."""
    assets = package_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    qr_names: dict[int, str] = {}
    for page in paper.pages:
        name = f"assets/qr_p{page.number}.png"
        write_png(page.qr_payload, package_dir / name)
        qr_names[page.number] = name

    typ_path = package_dir / "paper.typ"
    typ_path.write_text(emit_typst(paper, qr_names), encoding="utf-8")

    if not compile_pdf:
        return None

    try:
        import typst
    except ImportError:
        return None

    pdf_path = package_dir / "paper.pdf"
    typst.compile(str(typ_path), output=str(pdf_path), root=str(package_dir))
    return pdf_path
