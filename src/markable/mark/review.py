"""Generate `review.html` — the teacher's interactive review queue (brief 4.4).

A single self-contained page (crops embedded as data URIs — email it, open it
anywhere, no server). Each flagged item shows the evidence crop beside the AI's
proposal, and the teacher decides right on the page:

- **Accept** the proposed mark, or type a different mark and **Set** it.
- Progress is tracked (n of N decided) and saved in the browser
  (localStorage, keyed by test id) so a half-done review survives a reopen.
- **Download review_overrides.yaml** emits the decisions in exactly the format
  `markable report` merges over `marks.json` — save it over the scaffold file
  beside this page and run `markable report`.

The YAML scaffold is still written for teachers who prefer editing by hand.
"""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import yaml

from ..models import Judgement

_STYLE = """
:root{--surface:#fff;--page:#f4f6fb;--ink:#0f1729;--ink2:#48566f;--muted:#8a95a8;
  --border:rgba(15,23,41,.12);--accent:#1e63d0;--wash:rgba(30,99,208,.08);
  --warn:#a15c00;--ok:#1f7a44;--okwash:rgba(31,122,68,.08)}
@media (prefers-color-scheme:dark){:root{--surface:#141a26;--page:#0b0f17;--ink:#eaf0fb;
  --ink2:#a9b6cc;--muted:#6f7c93;--border:rgba(255,255,255,.12);--accent:#4b93ff;
  --wash:rgba(75,147,255,.12);--warn:#e79a41;--ok:#4dbd7f;--okwash:rgba(77,189,127,.12)}}
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;margin:0;background:var(--page);color:var(--ink);font-size:14px;line-height:1.45}
.wrap{max-width:72rem;margin:0 auto;padding:26px 30px 60px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--ink2);margin:0 0 18px}
.bar{position:sticky;top:0;z-index:5;background:var(--page);padding:12px 0;border-bottom:1px solid var(--border);
  display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:18px}
.progress{flex:1;min-width:180px;height:10px;background:var(--surface);border:1px solid var(--border);border-radius:99px;overflow:hidden}
.progress div{height:100%;background:var(--accent);width:0;transition:width .2s}
.count{font-variant-numeric:tabular-nums;color:var(--ink2)}
.btn{appearance:none;border:0;border-radius:8px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer;
  background:var(--accent);color:#fff}
.btn.ghost{background:var(--surface);color:var(--ink);border:1px solid var(--border)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.filters button{appearance:none;border:1px solid var(--border);background:var(--surface);color:var(--ink2);
  border-radius:99px;padding:5px 13px;font:inherit;font-size:12.5px;cursor:pointer}
.filters button.on{border-color:var(--accent);color:var(--accent);font-weight:600}
.item{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:16px}
.item.done{border-color:var(--ok);background:linear-gradient(var(--okwash),var(--okwash)),var(--surface)}
.item h2{font-size:15px;margin:0 0 6px}
.item img{max-width:100%;border:1px solid var(--border);border-radius:8px;background:#fff}
.reason{display:inline-block;color:var(--warn);border:1px solid var(--warn);border-radius:99px;
  padding:2px 10px;font-size:12px;font-weight:600;margin-bottom:8px}
.decided-chip{display:inline-block;color:var(--ok);border:1px solid var(--ok);border-radius:99px;
  padding:2px 10px;font-size:12px;font-weight:700;margin-left:8px}
.meta{color:var(--ink2);font-size:12.5px}
.grid{display:grid;grid-template-columns:minmax(280px,1.2fr) 1fr;gap:16px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.kv{margin:4px 0}.kv b{color:var(--ink2);font-weight:600}
.decide{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px;padding-top:12px;border-top:1px dashed var(--border)}
.decide input{width:80px;padding:8px 10px;border-radius:8px;border:1px solid var(--border);
  background:var(--page);color:var(--ink);font:inherit}
code{background:var(--wash);padding:.1rem .35rem;border-radius:4px}
.foot{color:var(--muted);font-size:12px;margin-top:26px}
"""

_JS = r"""
function $(id){return document.getElementById(id)}
const STORE='markable_review_'+TEST_ID;
let DEC={};try{DEC=JSON.parse(localStorage.getItem(STORE)||'{}')}catch(e){DEC={}}
function key(it){return it.student+'|'+it.question}
function save(){localStorage.setItem(STORE,JSON.stringify(DEC))}
function decide(i,val){
  const it=ITEMS[i];
  val=parseFloat(val);
  if(isNaN(val)||val<0||val>it.available){alert('Enter a mark between 0 and '+it.available);return}
  DEC[key(it)]=val;save();paint();
}
function undo(i){delete DEC[key(ITEMS[i])];save();paint()}
function paint(){
  let done=0;
  ITEMS.forEach((it,i)=>{
    const el=$('item'+i),v=DEC[key(it)];
    const decided=v!==undefined;if(decided)done++;
    el.classList.toggle('done',decided);
    $('chip'+i).style.display=decided?'inline-block':'none';
    if(decided)$('chip'+i).textContent='✓ '+v+' / '+it.available;
    $('accept'+i).disabled=decided;
    $('undo'+i).style.display=decided?'inline-block':'none';
    const f=FILTER==='all'||(FILTER==='todo'&&!decided)||(FILTER==='done'&&decided);
    el.style.display=f?'block':'none';
  });
  $('done-count').textContent=done+' of '+ITEMS.length+' decided';
  $('pbar').style.width=(ITEMS.length?100*done/ITEMS.length:0)+'%';
  $('dl').disabled=done===0;
}
let FILTER='all';
function setFilter(f,btn){FILTER=f;
  document.querySelectorAll('.filters button').forEach(b=>b.classList.toggle('on',b===btn));paint()}
function yamlStr(){
  // {student:{question:marks}} — exactly what `markable report` merges.
  const by={};
  ITEMS.forEach(it=>{const v=DEC[key(it)];if(v!==undefined)(by[it.student]=by[it.student]||{})[it.question]=v});
  let out='# Final marks decided in review.html — merged by `markable report`.\n';
  Object.keys(by).sort().forEach(s=>{out+=s+':\n';
    Object.keys(by[s]).sort().forEach(q=>{out+='  '+q+': '+by[s][q]+'\n'})});
  return out;
}
function downloadOverrides(){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([yamlStr()],{type:'text/yaml'}));
  a.download='review_overrides.yaml';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
window.addEventListener('DOMContentLoaded',paint);
"""


def _img_tag(path: Path) -> str:
    if not path.exists():
        return "<p><em>crop missing</em></p>"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" alt="response crop" loading="lazy">'


def write_review_html(package_dir: Path, items: list[Judgement], test_id: str = "") -> Path:
    payload = [
        {
            "student": j.student,
            "question": j.question,
            "proposed": j.marks_awarded,
            "available": j.marks_available,
        }
        for j in items
    ]

    blocks = []
    for i, j in enumerate(items):
        crop = package_dir / "scripts" / j.student / f"{j.question}.png"
        blocks.append(f"""
<div class="item" id="item{i}">
  <h2>{html.escape(j.student)} · {html.escape(j.question)}
    <span class="decided-chip" id="chip{i}" style="display:none"></span></h2>
  <span class="reason">⚠ {html.escape(j.review_reason or "flagged for review")}</span>
  <div class="grid">
    <div>{_img_tag(crop)}</div>
    <div>
      <p class="kv"><b>AI proposed:</b> {j.marks_awarded:g} / {j.marks_available:g}
        <span class="meta">· confidence {j.confidence:.2f}</span></p>
      <p class="kv"><b>Transcription:</b> {html.escape(j.transcription) or "—"}</p>
      <p class="kv"><b>Evidence:</b> {html.escape(j.evidence) or "—"}</p>
      {f'<p class="kv"><b>Feedback:</b> {html.escape(j.feedback)}</p>' if j.feedback else ''}
    </div>
  </div>
  <div class="decide">
    <button class="btn" id="accept{i}" onclick="decide({i},{j.marks_awarded:g})">✓ Accept {j.marks_awarded:g}</button>
    <span class="meta">or</span>
    <input id="mark{i}" type="number" min="0" max="{j.marks_available:g}" step="0.5" placeholder="mark">
    <button class="btn ghost" onclick="decide({i},document.getElementById('mark{i}').value)">Set mark</button>
    <button class="btn ghost" id="undo{i}" style="display:none" onclick="undo({i})">↺ Undo</button>
    <span class="meta">out of {j.marks_available:g}</span>
  </div>
</div>""")

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Markable review queue</title>
<style>{_STYLE}</style></head><body><div class="wrap">
<h1>Review queue — {len(items)} item(s)</h1>
<p class="sub">Decide each flagged item: accept the AI's mark or set your own. Your progress
saves in this browser. When done, download <code>review_overrides.yaml</code>, save it beside
this file (replacing the scaffold), and run <code>markable report</code>.</p>
<div class="bar">
  <span class="count" id="done-count"></span>
  <div class="progress"><div id="pbar"></div></div>
  <span class="filters">
    <button class="on" onclick="setFilter('all',this)">All</button>
    <button onclick="setFilter('todo',this)">Undecided</button>
    <button onclick="setFilter('done',this)">Decided</button>
  </span>
  <button class="btn" id="dl" onclick="downloadOverrides()">⬇ Download review_overrides.yaml</button>
</div>
{''.join(blocks)}
<p class="foot">Markable · single-file review queue — decisions never leave this browser until
you download the overrides file. Items not decided keep the AI's proposed mark.</p>
</div>
<script>const TEST_ID={json.dumps(test_id)};const ITEMS={json.dumps(payload)};
{_JS}</script>
</body></html>"""

    out = package_dir / "review.html"
    out.write_text(page, encoding="utf-8")

    # Scaffold the overrides file for hand-editors (never clobber teacher edits).
    overrides = package_dir / "review_overrides.yaml"
    if not overrides.exists():
        scaffold: dict = {}
        for j in items:
            scaffold.setdefault(j.student, {})[j.question] = None
        overrides.write_text(
            "# Final marks for review-queue items. Replace null with the marks awarded,\n"
            "# or decide everything in review.html and download this file from there.\n"
            + yaml.safe_dump(scaffold, sort_keys=True),
            encoding="utf-8",
        )
    return out
