/* ---------- DOCX / markdown → AI-marking readiness ---------- */
let DOC_WARNS=[];   // what the last docText() could NOT extract — shown to the teacher
async function docText(name,buf){
  DOC_WARNS=[];
  if(/\.(md|markdown|txt|yaml|yml)$/i.test(name)) return new TextDecoder().decode(new Uint8Array(buf));
  const zip=await readZip(buf); const xml=await zip.text('word/document.xml'); if(!xml)return '';
  // honest-extraction check: this parser reads paragraph text ONLY
  const counts={tables:(xml.match(/<w:tbl[ >]/g)||[]).length,
    images:(xml.match(/<w:drawing[ >]/g)||[]).length,
    equations:(xml.match(/<m:oMath[ >]/g)||[]).length};
  if(counts.tables)DOC_WARNS.push(counts.tables+' table(s) NOT extracted');
  if(counts.images)DOC_WARNS.push(counts.images+' image(s)/diagram(s) NOT extracted');
  if(counts.equations)DOC_WARNS.push(counts.equations+' equation(s) NOT extracted');
  const d=new DOMParser().parseFromString(xml,'application/xml'); let out=[];
  d.querySelectorAll('p').forEach(p=>{let t='';p.querySelectorAll('t').forEach(x=>t+=x.textContent);
    if(t.trim())out.push(t.trim())}); return out.join('\n');
}
function docWarnSuffix(){return DOC_WARNS.length?' ⚠ '+DOC_WARNS.join('; ')+' — check the extracted text covers everything before sending.':''}
function analyseReadiness(text){
  // strip markdown heading hashes and list bullets so "## Q1 …" / "- Q1 …" count
  const lines=text.split(/\n+/).map(l=>l.trim().replace(/^#+\s*/,'').replace(/^[-*]\s+/,'')).filter(Boolean);
  // question detection: lines starting Q1 / 1. / 1) / a) etc.
  const qRe=/^(?:Q\s?\d+|[0-9]{1,2}[.)]|\([0-9]{1,2}\)|[a-h][.)])/i;
  const questions=lines.filter(l=>qRe.test(l));
  // marks: "(2 marks)", "[3 marks]", "/4", or Markable's "[mcq, 2]" / "[extended, 6]"
  const markRe=/(\(|\[)\s*\d+\s*(mark|marks|m)\s*(\)|\])|\/\s?\d+\b|\[[a-z_]+,\s*\d+\s*\]/i;
  const withMarks=questions.filter(l=>markRe.test(l));
  const mcqish=lines.filter(l=>/^[A-D][.)]\s/.test(l)).length;
  const hasIds=questions.filter(l=>/^Q\s?\d+/i.test(l)).length;
  const checks=[
    ['Questions detected', questions.length>0, questions.length+' question-like items found',
      'No clear question markers — number each question (Q1, Q2 …) so every item is uniquely identified.'],
    ['Unique question IDs', hasIds>=Math.max(1,questions.length*0.5),
      hasIds+' items use explicit IDs (Q1, Q2 …)',
      'Few explicit IDs — Markable assigns stable IDs (Q07a) so a cropped answer is self-identifying.'],
    ['Marks allocated', withMarks.length>=Math.max(1,questions.length*0.5),
      withMarks.length+'/'+questions.length+' questions state their marks',
      'Many questions have no mark allocation — add e.g. "(2 marks)" so the key and analysis are complete.'],
    ['Answer space / structure', /answer|working|space|box|lines/i.test(text) || mcqish>0,
      'Response structure present (options / answer prompts)',
      'No explicit answer zones — Markable’s build step adds bordered response boxes, working frames and a separated final-answer cell.'],
    ['Machine-readable key', false, '',
      'A structured marking key (key.yaml) is generated at build time — criteria, accept/reject, rubric bands — the single biggest driver of reliable AI marking.'],
  ];
  const auto=checks.filter(c=>c[1]).length;
  const score=Math.round((auto/ (checks.length-1))*100); // last item is always a build-time step
  return {questions:questions.length, withMarks:withMarks.length, checks, score};
}
function renderReadiness(name,rep){
  const items=rep.checks.map(c=>'<li class="'+(c[1]?'li-good':'li-warn')+'">'+
    '<b>'+esc(c[0])+'</b> — '+esc(c[1]?c[2]:c[3])+'</li>').join('');
  const grade=rep.score>=70?'good':'warn';
  return '<div class="card"><h3>AI-marking readiness — '+esc(name)+'</h3>'+
    '<div class="readiness"><div class="gauge" style="--v:'+rep.score+'"><span>'+rep.score+'%</span></div>'+
    '<div><p style="margin:0 0 6px">Markable found <b>'+rep.questions+'</b> questions, <b>'+rep.withMarks+
    '</b> with marks allocated. <span class="chip '+grade+'">'+(rep.score>=70?'Close — minor prep':'Needs structuring')+'</span></p>'+
    '<p style="margin:0;color:var(--ink-2);font-size:13px">Run <code>markable ingest</code> then <code>markable build</code> to auto-apply the fixes below and produce a scan-ready paper + marking key.</p></div></div>'+
    '<ul style="margin:0;padding-left:2px;list-style:none;line-height:1.9">'+items+'</ul>'+
    '<div class="aim-actions" style="margin:14px 0 4px">'+
    '<button class="btn" onclick="upgradeTest(\'doc-result\')">🪄 Reformat with '+(PROVIDER==='copilot'?'Copilot':'Claude')+'</button>'+
    '<button class="btn ghost" onclick="show(\'aimark\');scrollToEl(\'prov-claude\')">Switch AI (Claude / Copilot)</button>'+
    '<span class="hint" style="align-self:center">Sends the test + Markable\'s upgrade instructions to your chosen AI; you get back a restructured, AI-marking-ready version with a change log.</span></div>'+
    '<p class="foot">This readiness check runs locally. The build step (unique IDs, answer zones, QR codes, a structured key) is what makes AI marking reliable and auditable.</p></div>';
}

/* ---------- wiring: drag/drop + file pickers ---------- */
function wireDrop(dropId,inputId,handler){
  const drop=$(dropId),input=$(inputId);
  input.addEventListener('change',e=>{if(e.target.files[0])handler(e.target.files[0])});
  ['dragover','dragenter'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('drag')}));
  ['dragleave','dragend','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('drag')}));
  drop.addEventListener('drop',e=>{if(e.dataTransfer.files[0])handler(e.dataTransfer.files[0])});
}
wireDrop('drop-xlsx','drop-xlsx-input',async file=>{
  const st=$('xlsx-status');st.className='status';st.textContent='Reading '+file.name+' …';
  try{
    const sheets=await parseXlsx(await file.arrayBuffer());
    const sacs=sheets.map(detectSac).filter(Boolean);
    if(!sacs.length)throw new Error('No results grid found. Expected a sheet with a "Surname" header row and "/N" mark columns.');
    LAST_SACS=sacs; LAST_TITLE=file.name; LAST_PACK=''; IS_DEMO=false;
    showResults(LAST_TERM);
    const hasCls=classList(sacs).length;
    st.textContent='✓ '+sacs.length+' assessment(s), '+sacs[0].students.length+' students'+(hasCls?', '+classList(sacs).length+' classes':'')+'.';
  }catch(err){st.className='status err';st.textContent='Could not read that file: '+err.message}
});
wireDrop('drop-doc','drop-doc-input',async file=>{
  const st=$('doc-status');st.className='status';st.textContent='Analysing '+file.name+' …';
  try{
    const text=await docText(file.name,await file.arrayBuffer());
    if(!text.trim())throw new Error('No readable text found in that document.');
    LAST_DOC={name:file.name,text};
    const rep=analyseReadiness(text);
    $('doc-result').innerHTML='<h2 class="section">Readiness</h2>'+renderReadiness(file.name,rep);
    $('doc-result').classList.add('active');
    st.textContent='✓ Analysed — readiness '+rep.score+'%.'+docWarnSuffix();
    $('doc-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not analyse that file: '+err.message}
});
