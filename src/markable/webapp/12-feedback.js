/* ---------- Feedback slips: printable per-student slips, built in-browser ----------
   Replaces the old sibling-file slips link: slips come straight from the
   uploaded results workbook (marks the teacher already finalised, so nothing
   here is an unreviewed AI proposal). Names never leave this device. */
function renderFeedback(){
  const el=$('fb-body');if(!el)return;
  if(!LAST_SACS){
    el.innerHTML='<div class="card"><p><b>No results loaded yet.</b> Feedback slips are built from your '+
      'results workbook — upload it first. Everything stays on this device.</p>'+
      '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 4px">'+
      '<button class="btn" onclick="$(\'drop-xlsx-input\').click()">📈 Upload results workbook</button>'+
      '<button class="btn ghost" onclick="loadDemo(LAST_TERM);showFeedback()">👀 Try with demo data</button></div>'+
      '<p class="foot">Marking scanned papers with the CLI instead? <code>markable report &lt;package&gt; --feedback</code> '+
      'writes slips that include the per-question AI feedback after your review.</p></div>';
    return;
  }
  const cls=classList(LAST_SACS);
  const opts='<option value="">All classes</option>'+cls.map(c=>'<option value="'+esc(c)+'">'+esc(c)+'</option>').join('');
  el.innerHTML='<div class="card"><div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">'+
    (cls.length?'<select class="picker" id="fb-class" onchange="paintSlips()">'+opts+'</select>':'')+
    '<label style="display:flex;gap:6px;align-items:center;font-size:13px"><input type="checkbox" id="fb-qtable" checked onchange="paintSlips()"> question-by-question table</label>'+
    '<button class="btn" onclick="downloadSlips()">⬇ Download printable slips</button>'+
    '<span class="hint" style="align-self:center">One slip per page when printed — open the download and press Ctrl/Cmd-P.</span></div>'+
    (IS_DEMO?'<p class="foot" style="margin-bottom:0"><span class="mode-chip demo">DEMO DATA</span> fictional students.</p>':'')+
    '</div><div id="fb-preview"></div>';
  paintSlips();
}
function slipStudents(){
  const c=$('fb-class')?$('fb-class').value:'';
  return [...new Set(LAST_SACS.flatMap(s=>s.students.filter(st=>!c||st.cls===c).map(st=>st.name)))].sort();
}
function slipHtml(name,withQ){
  const term=LAST_TERM;
  let rowsHtml='',cls='';const ovr=[];
  LAST_SACS.forEach(sac=>{
    const st=sac.students.find(s=>s.name===name);if(!st)return;cls=cls||st.cls;
    const tot=totalFor(sac,st),p=sac.total?Math.round(100*tot/sac.total):null;
    const cohv=sac.students.map(s2=>sac.total?100*totalFor(sac,s2)/sac.total:0);
    const coh=cohv.length?Math.round(cohv.reduce((a,b)=>a+b,0)/cohv.length):0;
    if(p!==null)ovr.push(p);
    let qrows='';
    if(withQ)qrows='<table class="fb-q"><tr>'+sac.questions.map(q=>'<th>'+esc(q.id)+'</th>').join('')+'</tr><tr>'+
      sac.questions.map(q=>{const mk=st.marks[q.id];return '<td>'+(mk===undefined?'—':mk+'/'+q.max)+'</td>'}).join('')+'</tr></table>';
    rowsHtml+='<div class="fb-sac"><b>'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+':</b> '+
      tot+'/'+sac.total+(p===null?'':' ('+p+'%)')+' <span class="fb-coh">class average '+coh+'%</span>'+qrows+'</div>';
  });
  const perf=[];
  LAST_SACS.forEach(sac=>{const st=sac.students.find(s=>s.name===name);if(!st)return;
    sac.questions.forEach(q=>{const mk=st.marks[q.id];if(mk===undefined||!q.max)return;
      perf.push({label:q.id+' ('+sac.topic+')',p:100*mk/q.max})})});
  perf.sort((a,b)=>b.p-a.p);
  const strengths=perf.slice(0,2).filter(x=>x.p>=60);
  const focus=perf.slice(-2).filter(x=>x.p<60).reverse();
  const overall=ovr.length?Math.round(ovr.reduce((a,b)=>a+b,0)/ovr.length):null;
  return '<div class="slip"><div class="slip-head"><div><h2>'+esc(name)+'</h2>'+
    '<div class="slip-meta">'+(cls?esc(cls)+' · ':'')+esc(LAST_TITLE)+' · '+new Date().toLocaleDateString()+'</div></div>'+
    '<div class="slip-ov">'+(overall===null?'—':overall+'%')+'<span>overall</span></div></div>'+
    rowsHtml+
    (strengths.length?'<p class="fb-line">💪 <b>Strengths:</b> '+strengths.map(x=>esc(x.label)+' ('+Math.round(x.p)+'%)').join(' · ')+'</p>':'')+
    (focus.length?'<p class="fb-line">🎯 <b>Focus next:</b> '+focus.map(x=>esc(x.label)+' ('+Math.round(x.p)+'%)').join(' · ')+'</p>':'')+
    '<p class="slip-foot">Generated locally by Markable from the teacher\'s marks workbook'+(IS_DEMO?' · DEMO DATA (fictional students)':'')+'.</p></div>';
}
function paintSlips(){
  const el=$('fb-preview');if(!el)return;
  const withQ=$('fb-qtable')?$('fb-qtable').checked:true;
  const names=slipStudents();
  el.innerHTML='<p class="foot">'+names.length+' slip(s) — preview below; the download prints one per page.</p>'+
    names.map(n=>slipHtml(n,withQ)).join('');
}
function slipsDoc(withQ){
  const css='body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;padding:24px;color:#111}'+
    '.slip{border:1px solid #ccc;border-radius:10px;padding:18px 22px;margin:0 0 18px;page-break-after:always;page-break-inside:avoid}'+
    '.slip:last-child{page-break-after:auto}'+
    '.slip-head{display:flex;justify-content:space-between;align-items:center;gap:14px;border-bottom:2px solid #1e63d0;padding-bottom:8px;margin-bottom:10px}'+
    '.slip-head h2{margin:0;font-size:20px}.slip-meta{color:#555;font-size:12px;margin-top:2px}'+
    '.slip-ov{font-size:26px;font-weight:700;color:#1e63d0;text-align:right}.slip-ov span{display:block;font-size:11px;color:#555;font-weight:400}'+
    '.fb-sac{margin:8px 0;font-size:14px}.fb-coh{color:#666;font-size:12px;margin-left:6px}'+
    '.fb-q{border-collapse:collapse;margin:6px 0 2px}.fb-q th,.fb-q td{border:1px solid #ddd;padding:3px 8px;font-size:12px;text-align:center}'+
    '.fb-q th{background:#f2f5fa}.fb-line{font-size:13px;margin:8px 0 0}.slip-foot{color:#888;font-size:11px;margin:10px 0 0}';
  return '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Feedback slips — '+esc(LAST_TITLE)+'</title>'+
    '<style>'+css+'</style></head><body>'+slipStudents().map(n=>slipHtml(n,withQ)).join('')+'</body></html>';
}
function downloadSlips(){
  const withQ=$('fb-qtable')?$('fb-qtable').checked:true;
  const blob=new Blob([slipsDoc(withQ)],{type:'text/html'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=(LAST_TITLE.replace(/\.[^.]+$/,'')||'markable')+'-feedback-slips.html';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
