"""Generate `review.html` — the teacher's review queue (brief 4.4).

A single self-contained page: each flagged crop (embedded as a data URI, so the
file can be emailed or opened anywhere) beside the AI's proposed mark, evidence,
and the reason it was flagged. The teacher records final marks in
`review_overrides.yaml`, which `report` merges over `marks.json`.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

import yaml

from ..models import Judgement

_STYLE = """
body { font-family: system-ui, sans-serif; margin: 2rem; max-width: 70rem; }
.item { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem; }
.item img { max-width: 100%; border: 1px solid #eee; }
.meta { color: #555; font-size: 0.9rem; }
.reason { color: #a15c00; font-weight: 600; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.1rem; margin: 0 0 .5rem; }
code { background: #f4f4f4; padding: .1rem .3rem; border-radius: 4px; }
"""


def _img_tag(path: Path) -> str:
    if not path.exists():
        return "<p><em>crop missing</em></p>"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" alt="response crop">'


def write_review_html(package_dir: Path, items: list[Judgement]) -> Path:
    blocks = []
    for j in items:
        crop = package_dir / "scripts" / j.student / f"{j.question}.png"
        blocks.append(f"""
<div class="item">
  <h2>{html.escape(j.student)} · {html.escape(j.question)}</h2>
  <p class="reason">⚠ {html.escape(j.review_reason or "flagged for review")}</p>
  {_img_tag(crop)}
  <p><strong>Proposed:</strong> {j.marks_awarded:g} / {j.marks_available:g}
     &nbsp; <span class="meta">confidence {j.confidence:.2f}</span></p>
  <p><strong>Transcription:</strong> {html.escape(j.transcription) or "—"}</p>
  <p><strong>Evidence:</strong> {html.escape(j.evidence) or "—"}</p>
</div>""")

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Markable review queue</title>
<style>{_STYLE}</style></head><body>
<h1>Review queue — {len(items)} item(s)</h1>
<p>Record your final marks in <code>review_overrides.yaml</code> (created beside this
file), then run <code>markable report</code>. Entries look like:</p>
<pre>S1042:
  Q3: 2      # final marks awarded</pre>
{''.join(blocks)}
</body></html>"""

    out = package_dir / "review.html"
    out.write_text(page, encoding="utf-8")

    # Scaffold the overrides file (never clobber teacher edits).
    overrides = package_dir / "review_overrides.yaml"
    if not overrides.exists():
        scaffold: dict = {}
        for j in items:
            scaffold.setdefault(j.student, {})[j.question] = None
        overrides.write_text(
            "# Final marks for review-queue items. Replace null with the marks awarded.\n"
            + yaml.safe_dump(scaffold, sort_keys=True),
            encoding="utf-8",
        )
    return out
