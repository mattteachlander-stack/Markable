/* ---------- SAC detection (mirrors gradebook.py) ----------
   Identity rules (P0): students are keyed by the ID column when one exists;
   two different students who share a display name are kept separate (the ID is
   appended to disambiguate) and surfaced in a visible warning — never merged
   silently. Scan bounds come from the sheet's real extents, not fixed limits. */
function cell(g,r,c){return (g[r]&&g[r][c]!==undefined)?g[r][c]:null}
function detectSac(sheet){
  const g=sheet.grid;
  const {rmax,cmax}=gridExtents(g);
  const warnings=[];
  let h=null;
  for(let r=1;r<=rmax && !h;r++) for(let c=0;c<=Math.min(cmax,12);c++){
    if(String(cell(g,r,c)).trim().toLowerCase()==='surname'){h=r;break}}
  if(!h) return null;
  const cols={};
  for(let c=0;c<=cmax;c++){const k=String(cell(g,h,c)||'').trim().toLowerCase();
    if(['surname','first name','id','vcaa number','class','form','class group'].includes(k))cols[k]=c;}
  if(cols['surname']===undefined) return null;
  if(cols['id']===undefined&&cols['vcaa number']===undefined)
    warnings.push('No ID column found — students are matched by name only. Two students with the same name would be merged; add an ID column to be safe.');
  const classCol=cols['class']!==undefined?cols['class']:(cols['class group']!==undefined?cols['class group']:cols['form']);
  const qs=[];const seenQ={};
  for(let c=0;c<=cmax;c++){const mm=String(cell(g,h,c)||'').trim().match(/^\/\s*(\d+(?:\.\d+)?)$/);
    if(!mm)continue; let lab=cell(g,h-1,c); lab=(lab===null||lab==='')?String(c):String(lab).trim();
    if(lab.toUpperCase()==='TOTAL')continue;
    if(seenQ[lab]){warnings.push('Duplicate question label "'+lab+'" — the second column was kept as "'+lab+'#2".');lab=lab+'#2'}
    seenQ[lab]=true;
    qs.push({id:lab,max:parseFloat(mm[1]),col:c});}
  if(!qs.length) return null;
  const students=[];const byName={};const byId={};
  for(let r=h+1;r<=rmax;r++){const sn=cell(g,r,cols['surname']); if(sn===null||sn==='')continue;
    const fn=cols['first name']!==undefined?cell(g,r,cols['first name']):'';
    const cl=classCol!==undefined?String(cell(g,r,classCol)||'').trim():'';
    const idCol=cols['id']!==undefined?cols['id']:cols['vcaa number'];
    const sid=idCol!==undefined?String(cell(g,r,idCol)||'').trim():'';
    let name=(String(sn).trim()+', '+String(fn||'').trim()).replace(/, $/,'');
    const st={name,sid,cls:cl,marks:{}};
    let any=false; for(const q of qs){const v=cell(g,r,q.col);
      if(typeof v==='number'){st.marks[q.id]=v;any=true}else if(v!==null&&!isNaN(parseFloat(v))){st.marks[q.id]=parseFloat(v);any=true}
      if(st.marks[q.id]!==undefined){
        if(st.marks[q.id]>q.max){warnings.push(st.name+' · '+q.id+': mark '+st.marks[q.id]+' exceeds the /'+q.max+' maximum — check the workbook.')}
        if(st.marks[q.id]<0){warnings.push(st.name+' · '+q.id+': negative mark '+st.marks[q.id]+' — check the workbook.')}}}
    if(!any)continue;
    if(sid&&byId[sid]){warnings.push('Duplicate student ID "'+sid+'" ('+byId[sid].name+' and '+name+') — both rows kept; fix the workbook before trusting totals.')}
    if(byName[name]){
      const other=byName[name];
      if(sid&&other.sid&&sid!==other.sid){
        // same name, different IDs: keep both, disambiguate visibly
        other.name=other.name+' ('+other.sid+')';name=name+' ('+sid+')';st.name=name;
        warnings.push('Two students named "'+other.name.replace(/ \(.*\)$/,'')+'" — kept separate using their IDs.');
      }else{
        warnings.push('Duplicate row for "'+name+'"'+(sid?'':' (no ID to tell them apart)')+' — both rows kept as separate entries; check the workbook.');
        st.name=name+' (row '+r+')';
      }
    }
    byName[st.name]=st;if(sid)byId[sid]=st;
    students.push(st);}
  if(!students.length) return null;
  // topic/total from labelled cells near top
  function labelled(label){const t=label.toLowerCase();
    for(let r=1;r<=8;r++)for(let c=0;c<6;c++){const cc=String(cell(g,r,c)||'').trim().toLowerCase().replace(/:$/,'');
      if(cc===t){for(let cc2=c+1;cc2<c+5;cc2++){const v=cell(g,r,cc2);if(v!==null&&v!=='')return String(v).trim()}}}return null}
  const total=parseFloat(labelled('total marks'))||qs.reduce((a,q)=>a+q.max,0);
  return {number:labelled('sac #')||sheet.name, topic:labelled('topic')||sheet.name,
    total, questions:qs, students, warnings};
}

/* ---------- render dashboard (port of gradebook_html) ---------- */
function greenBin(p){return Math.min(6,Math.floor(p/100*7))}
function heatBin(p){return Math.min(6,Math.floor(p/100*7))}
function esc(s){return String(s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]))}
function med(a){const s=[...a].sort((x,y)=>x-y),n=s.length;return n?(n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2):0}
function totalFor(sac,st){return sac.questions.reduce((a,q)=>a+(st.marks[q.id]||0),0)}
function rampCss(){
  let s='<style>';
  RAMPS.greenLight.forEach((c,i)=>s+='.mx td.g'+i+'{background:'+c+'}');
  RAMPS.heatLight.forEach((c,i)=>s+='.mx td.h'+i+',.hpct.h'+i+',.bars .fill.h'+i+'{background:'+c+'}');
  s+='@media (prefers-color-scheme:dark){';
  RAMPS.greenDark.forEach((c,i)=>s+='.mx td.g'+i+'{background:'+c+'}');
  RAMPS.heatDark.forEach((c,i)=>s+='.mx td.h'+i+',.hpct.h'+i+',.bars .fill.h'+i+'{background:'+c+'}');
  s+='}</style>'; return s;
}
function tiles(items){return items.map(([l,v,n,hero])=>
  '<div class="tile"><div class="label">'+esc(l)+'</div><div class="value'+(hero?' hero':'')+'">'+esc(v)+'</div>'+
  (n?'<div class="note">'+esc(n)+'</div>':'')+'</div>').join('')}
function histogram(vals){let b=Array(10).fill(0);vals.forEach(v=>b[Math.min(9,Math.floor(v/10))]++);
  const peak=Math.max(...b)||1;
  return '<div class="hist">'+b.map((x,i)=>'<div class="col" style="height:'+Math.max(2,x/peak*100)+'%">'+
    (x?'<span class="n">'+x+'</span>':'')+'</div>').join('')+'</div>'+
    '<div class="hist-x">'+b.map((x,i)=>'<span>'+(i*10)+'</span>').join('')+'</div>'}
function quartSeg(pct){const names=Object.keys(pct).sort((a,b)=>pct[b]-pct[a]),n=names.length,o={};
  names.forEach((nm,i)=>{const q=n?Math.min(4,1+Math.floor(i*4/n)):1;o[nm]=q===1?1:q===4?3:2});return o}
function hcell(p,title){if(p===null||p===undefined)return '<td class="na">—</td>';
  return '<td class="h'+heatBin(p)+'" title="'+esc(title||'')+'">'+Math.round(p)+'</td>'}
function shortA(a){return a.includes('—')?a.split('—')[1].trim():a}
function facSet(sac,q,set){const m=sac.students.filter(s=>set.has(s.name)).map(s=>s.marks[q.id]||0);
  return (!m.length||!q.max)?null:m.reduce((a,b)=>a+b,0)/(q.max*m.length)}
function classList(sacs){const seen=[];sacs.forEach(sac=>sac.students.forEach(st=>{
  if(st.cls&&!seen.includes(st.cls))seen.push(st.cls)}));return seen.sort()}
/* {sacNumber:{qid:area}} from the auto-mapper — the studio packs carry areas, not codes */
function qmetaFor(sacs,packId){const out={};if(!packId||!PACKS[packId])return out;
  const pack=PACKS[packId];sacs.forEach(sac=>{const m={};sac.questions.forEach(q=>{const r=autoAreaScored(q.id,pack);if(r.area)m[q.id]=r.area;m[q.id+'::state']=r.state});out[sac.number]=m});return out}

function highlightsCard(sacs,packId,term){
  const qmeta=qmetaFor(sacs,packId);
  let hardest=[];
  sacs.forEach(sac=>{const names=new Set(sac.students.map(s=>s.name));
    sac.questions.forEach(q=>{const f=facSet(sac,q,names);
      if(f!==null)hardest.push({f,sac,qid:q.id,area:(qmeta[sac.number]||{})[q.id]||''})})});
  hardest.sort((a,b)=>a.f-b.f);const top=hardest.slice(0,5);
  const items=top.map(t=>{const concept=t.area?' <span class="concept">— '+esc(shortA(t.area))+'</span>':'';
    const p=Math.round(t.f*100);
    return '<li><b>'+esc(t.qid)+'</b> <span class="muted">('+esc(t.sac.topic)+')</span> — '+
      '<span class="hpct h'+heatBin(p)+'">'+p+'%</span>'+concept+'</li>'}).join('');
  // weakest / strongest area across cohort
  let areaLine='';
  if(packId&&PACKS[packId]){const agg={};
    sacs.forEach(sac=>{const qm=qmeta[sac.number]||{};const names=new Set(sac.students.map(s=>s.name));
      sac.questions.forEach(q=>{const a=qm[q.id];if(!a)return;
        const aw=sac.students.reduce((s,st)=>s+(st.marks[q.id]||0),0);
        agg[a]=agg[a]||[0,0];agg[a][0]+=aw;agg[a][1]+=q.max*names.size})});
    const pcts={};Object.keys(agg).forEach(a=>{if(agg[a][1])pcts[a]=100*agg[a][0]/agg[a][1]});
    const ks=Object.keys(pcts);
    if(ks.length){const weak=ks.reduce((m,a)=>pcts[a]<pcts[m]?a:m),strong=ks.reduce((m,a)=>pcts[a]>pcts[m]?a:m);
      areaLine='<p class="hi-area">Weakest area: <b>'+esc(shortA(weak))+'</b> ('+Math.round(pcts[weak])+
        '%) · Strongest: <b>'+esc(shortA(strong))+'</b> ('+Math.round(pcts[strong])+'%)</p>'}}
  const allPct=[];sacs.forEach(sac=>sac.students.forEach(st=>{if(sac.total)allPct.push(100*totalFor(sac,st)/sac.total)}));
  const avg=allPct.length?allPct.reduce((a,b)=>a+b,0)/allPct.length:0;
  const below=allPct.filter(p=>p<50).length;
  return '<div class="card highlights"><h3>🔑 Key highlights</h3>'+
    '<p class="hi-lead">Cohort average <b>'+Math.round(avg)+'%</b> across '+sacs.length+' '+esc(term.toLowerCase())+'(s) · '+
    below+' result(s) below 50% flagged for support.</p>'+
    '<div class="hi-cols"><div><h4>Hardest questions</h4><ul class="hi-list">'+items+'</ul></div>'+
    '<div><h4>Where to focus</h4>'+(areaLine||'<p class="muted">Add a study design to link questions to concepts.</p>')+
    '<p class="muted" style="margin-top:8px">Each hardest question shows its linked concept where mapped.</p></div></div></div>';
}

function sacTab(sac,idx,term){
  const totals={},pct={}; sac.students.forEach(st=>{totals[st.name]=totalFor(sac,st);
    if(sac.total)pct[st.name]=100*totals[st.name]/sac.total});
  const seg=quartSeg(pct), vals=Object.values(pct).sort((a,b)=>a-b);
  const segName={0:'All',1:'Top 25%',2:'Middle 50%',3:'Bottom 25%'};
  const segSets={0:new Set(Object.keys(pct)),1:new Set(),2:new Set(),3:new Set()};
  Object.keys(pct).forEach(nm=>segSets[seg[nm]].add(nm));
  const kt=tiles([['Class average',Math.round(vals.reduce((a,b)=>a+b,0)/vals.length)+'%','of '+sac.total+' marks',true],
    ['Median',Math.round(med(vals))+'%','',false],['Highest',Math.round(Math.max(...vals))+'%','',false],
    ['Lowest',Math.round(Math.min(...vals))+'%','',false],
    ['At/above 70%',vals.filter(v=>v>=70).length,'of '+vals.length,false],
    ['Below 50%',vals.filter(v=>v<50).length,'intervention',false]]);
  function fac(q,set){const m=sac.students.filter(s=>set.has(s.name)).map(s=>s.marks[q.id]||0);
    return (!m.length||!q.max)?null:m.reduce((a,b)=>a+b,0)/(q.max*m.length)}
  function cellHtml(q,s){const f=fac(q,segSets[s]); if(f===null)return '<td class="na">—</td>';
    const p=f*100;return '<td class="g'+greenBin(p)+'">'+Math.round(p)+'</td>'}
  const rows=sac.questions.map(q=>{const f=fac(q,segSets[0])||0,d=f>=.8?'easy':f>=.5?'moderate':'difficult';
    return '<tr><th class="rowh">'+esc(q.id)+'</th>'+[0,1,2,3].map(s=>cellHtml(q,s)).join('')+
      '<td style="background:none"><span class="chip '+d+'">'+d+'</span></td></tr>'}).join('');
  const head='<tr><th class="rowh">Question</th>'+[0,1,2,3].map(s=>'<th>'+segName[s]+'</th>').join('')+'<th>Difficulty</th></tr>';
  const smallN=sac.students.length<10?'<span class="chip warn" title="statistics on fewer than 10 students are unstable">small cohort n='+sac.students.length+' — interpret with care</span> ':'';
  return '<div class="subtab" id="st'+idx+'"><h3 class="tab-h">'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+' '+smallN+'</h3>'+
    '<div class="kpis">'+kt+'</div>'+
    '<div class="card"><h3>Score distribution</h3>'+histogram(vals)+'</div>'+
    '<div class="card"><h3>Question performance by cohort quartile</h3><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">easy ≥80% · moderate 50–79% · difficult &lt;50%</p></div></div>';
}
function overviewTab(sacs,term,highlights){
  const lo=term.toLowerCase();
  const sacPct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const students=[...new Set(sacs.flatMap((s,i)=>Object.keys(sacPct[i])))].sort();
  const allVals=sacPct.flatMap(p=>Object.values(p));
  const kt=tiles([['Students',students.length,'',true],[term+'s',sacs.length,'',false],
    ['Overall average',Math.round(allVals.reduce((a,b)=>a+b,0)/allVals.length)+'%','across all '+lo+'s',false]]);
  const bars=sacs.map((sac,i)=>{const p=sacPct[i],avg=Object.values(p).reduce((a,b)=>a+b,0)/Object.values(p).length;
    return '<div style="display:grid;grid-template-columns:220px 1fr 48px;gap:10px;align-items:center;padding:5px 0">'+
      '<div style="color:var(--ink-2);font-size:13px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(term)+' '+esc(sac.number)+': '+esc(sac.topic)+'</div>'+
      '<div style="border-left:1px solid var(--baseline);height:16px"><div class="fill h'+heatBin(avg)+'" style="height:16px;border-radius:0 4px 4px 0;width:'+avg.toFixed(1)+'%"></div></div>'+
      '<div style="font-variant-numeric:tabular-nums">'+Math.round(avg)+'%</div></div>'}).join('');
  const head='<tr><th class="rowh">Student</th>'+sacs.map(s=>'<th>'+esc(term)+' '+esc(s.number)+'</th>').join('')+'<th>Overall</th></tr>';
  const rows=students.map(nm=>{const vals=sacs.map((s,i)=>sacPct[i][nm]);
    const present=vals.filter(v=>v!==undefined);const ov=present.length?present.reduce((a,b)=>a+b,0)/present.length:null;
    const cells=vals.map(v=>v===undefined?'<td class="na">—</td>':'<td class="h'+heatBin(v)+'">'+Math.round(v)+'</td>').join('');
    return '<tr><th class="rowh">'+esc(nm)+'</th>'+cells+(ov===null?'<td class="na">—</td>':'<td class="h'+heatBin(ov)+'">'+Math.round(ov)+'</td>')+'</tr>'}).join('');
  return '<div class="subtab active" id="st-ov"><div class="kpis">'+kt+'</div>'+(highlights||'')+
    '<div class="card"><h3>Cohort average by '+esc(lo)+'</h3>'+bars+'</div>'+
    '<div class="card"><h3>Every student across every '+esc(lo)+'</h3><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">Coloured by percentage · red = at risk · green = secure · names shown locally only.</p></div></div>';
}
/* ---- study-design auto-mapping (mirrors studydesign.py, keyword overlap) ---- */
const STOP=new Set(('the a an and or of to in on for with your is are how what which that this its it be by '+
  'using use used their them when each one two give show state describe explain identify draw label should '+
  'answer question marks mark simple').split(' '));
function terms(s){const out=new Set();(String(s).toLowerCase().match(/[a-z]{3,}/g)||[]).forEach(w=>{
  if(STOP.has(w))return;out.add(w.endsWith('s')?w.slice(0,-1):w)});return out}
function autoAreaScored(label,pack){const q=terms(label);const scored=[];
  pack.outcomes.forEach(o=>{let n=0;o.terms.forEach(t=>{if(q.has(t.endsWith('s')?t.slice(0,-1):t))n++});
    if(n>0)scored.push([n,o.area])});
  scored.sort((a,b)=>b[0]-a[0]);
  if(!scored.length)return {area:null,state:'unmapped'};
  const distinct=scored.filter(s=>s[1]!==scored[0][1]);
  const state=(distinct.length&&distinct[0][0]>=scored[0][0]-1&&distinct[0][0]>0&&scored[0][0]-distinct[0][0]<=1&&distinct[0][1]!==scored[0][1])?'ambiguous':'suggested';
  return {area:scored[0][1],state};
}
function autoArea(label,pack){return autoAreaScored(label,pack).area}
function skillsTab(sacs,packId,term){
  const pack=PACKS[packId];
  let blocks='';
  sacs.forEach(sac=>{
    const qArea={},areas=new Set();
    sac.questions.forEach(q=>{const a=autoArea(q.id,pack);if(a){qArea[q.id]=a;areas.add(a)}});
    if(!areas.size)return;
    const areaList=[...areas];
    const per={},coh={};
    sac.students.forEach(st=>{areaList.forEach(a=>{per[st.name+'|'+a]=[0,0]});});
    areaList.forEach(a=>coh[a]=[0,0]);
    sac.students.forEach(st=>{sac.questions.forEach(q=>{const a=qArea[q.id];if(!a)return;
      const aw=st.marks[q.id]||0;per[st.name+'|'+a][0]+=aw;per[st.name+'|'+a][1]+=q.max;
      coh[a][0]+=aw;coh[a][1]+=q.max})});
    const shortA=a=>a.includes('—')?a.split('—')[1].trim():a;
    const head='<tr><th class="rowh">Student</th>'+areaList.map(a=>'<th>'+esc(shortA(a))+'</th>').join('')+'</tr>';
    const pc=(p)=>p[1]?Math.round(100*p[0]/p[1]):null;
    const cell=v=>v===null?'<td class="na">—</td>':'<td class="h'+heatBin(v)+'">'+v+'</td>';
    const cohRow='<tr style="font-weight:600"><th class="rowh">Cohort</th>'+areaList.map(a=>cell(pc(coh[a]))).join('')+'</tr>';
    const rows=sac.students.map(st=>'<tr><th class="rowh">'+esc(st.name)+'</th>'+
      areaList.map(a=>cell(pc(per[st.name+'|'+a]))).join('')+'</tr>').join('');
    const mapped=Object.keys(qArea).length,tot=sac.questions.length;
    blocks+='<div class="card"><h3>'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+': attainment by study-design area <span class="mode-chip local">SUGGESTED MAPPING</span></h3>'+
      '<div class="mx"><table>'+head+cohRow+rows+'</table></div>'+
      '<p class="foot">'+mapped+'/'+tot+' items auto-mapped from their labels. Content items that are just '+
      'numbered (1, 2, 3a) need a teacher map via the CLI — criterion-named items (prac skills) map here directly.</p></div>';
  });
  if(!blocks) blocks='<div class="card"><p>No items could be auto-mapped from their labels for '+
    esc(pack.name)+'. Named criteria (e.g. a prac SAC\'s skill columns) map automatically; '+
    'numbered content questions need a teacher map via <code>markable gradebook --map</code>.</p></div>';
  return '<div class="subtab" id="st-skills"><p class="foot" style="margin-top:0">Mapped against '+esc(pack.name)+
    ' — representative codes, confirm against the official study design.</p>'+blocks+'</div>';
}

/* ---------- classes: class×assessment + my-class question analysis ---------- */
function classesTab(sacs,term){
  const cls=classList(sacs);if(!cls.length)return '';
  const lo=term.toLowerCase();
  const pct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const head='<tr><th class="rowh">Class</th>'+sacs.map(s=>'<th>'+esc(term)+' '+esc(s.number)+'</th>').join('')+'<th>Overall</th><th>Students</th></tr>';
  const rows=cls.map(c=>{let cells='',ov=[],n=0;
    sacs.forEach((s,i)=>{const members=s.students.filter(st=>st.cls===c).map(st=>st.name);n=Math.max(n,members.length);
      const vals=members.map(m=>pct[i][m]).filter(v=>v!==undefined);
      if(vals.length){const avg=vals.reduce((a,b)=>a+b,0)/vals.length;ov.push(avg);cells+=hcell(avg,c+' · '+term+' '+s.number)}
      else cells+='<td class="na">—</td>'});
    const o=ov.length?ov.reduce((a,b)=>a+b,0)/ov.length:null;
    return '<tr><th class="rowh">'+esc(c)+'</th>'+cells+hcell(o,c+' · overall')+
      '<td style="background:none;color:var(--ink-2)">'+n+'</td></tr>'}).join('');
  const opts=cls.map((c,i)=>'<option value="'+esc(c)+'"'+(i===0?' selected':'')+'>'+esc(c)+'</option>').join('');
  return '<div class="subtab" id="st-cls"><h3 class="tab-h">Class-by-class comparison</h3>'+
    '<div class="card"><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">Average % per class per '+esc(lo)+'.</p></div>'+
    '<div class="card"><h3>My class — question-level analysis</h3>'+
    '<p class="foot" style="margin-top:0">Pick your class to see how it went on each question, against the whole cohort. '+
    'Questions where your class is 10+ points below the cohort are flagged.</p>'+
    '<select class="picker" id="clsq-pick" onchange="renderClassQ()">'+opts+'</select><div id="clsq-body"></div></div></div>';
}
function renderClassQ(){
  const el=document.getElementById('clsq-body');if(!el)return;
  const c=document.getElementById('clsq-pick').value;
  const sacs=LAST_SACS,qmeta=qmetaFor(sacs,LAST_PACK),term=LAST_TERM;let h='';
  sacs.forEach(sac=>{const all=new Set(sac.students.map(s=>s.name));
    const mine=new Set(sac.students.filter(s=>s.cls===c).map(s=>s.name));let rows='',flagged=0;
    sac.questions.forEach(q=>{const cf=facSet(sac,q,mine),coh=facSet(sac,q,all);
      const cp=cf===null?null:Math.round(cf*100),chp=coh===null?null:Math.round(coh*100);
      const delta=(cp===null||chp===null)?null:cp-chp;const flag=(delta!==null&&delta<=-10);if(flag)flagged++;
      const area=(qmeta[sac.number]||{})[q.id]||'';
      const mstate=(qmeta[sac.number]||{})[q.id+'::state']||'unmapped';
      const concept=area
        ?esc(shortA(area))+(mstate==='ambiguous'?' <span class="chip warn" title="two study-design areas match this label almost equally — confirm with a teacher map">ambiguous</span>':'')
        :'<span class="muted">unmapped</span>';
      rows+='<tr'+(flag?' class="flag"':'')+'><td><b>'+esc(q.id)+'</b></td>'+hcell(cp,c+' · '+q.id)+
        '<td class="num" style="color:var(--ink-2)">'+(chp===null?'—':chp)+'</td>'+
        '<td class="num '+(delta!==null&&delta<0?'neg':'pos')+'">'+(delta===null?'—':(delta>0?'+':'')+delta)+'</td>'+
        '<td class="concept-cell">'+concept+'</td></tr>'});
    h+='<div class="card"><h3>'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+'</h3>'+
      '<p class="foot" style="margin:0 0 10px">'+(flagged?('<b>'+flagged+'</b> question(s) where '+esc(c)+' is 10+ points below the cohort — worth reviewing.'):(esc(c)+' is at or above the cohort on every question here.'))+'</p>'+
      '<div class="mx"><table class="clsq"><tr><th class="rowh">Q</th><th>'+esc(c)+'</th><th>Cohort</th><th>Δ</th><th>Concept (suggested)</th></tr>'+rows+'</table></div></div>'});
  el.innerHTML=h;
}
/* ---------- student spotlight ---------- */
function studentTab(sacs,term){
  const names=[...new Set(sacs.flatMap(s=>s.students.map(st=>st.name)))].sort();
  const opts=names.map((n,i)=>'<option value="'+esc(n)+'"'+(i===0?' selected':'')+'>'+esc(n)+'</option>').join('');
  return '<div class="subtab" id="st-student"><h3 class="tab-h">Student spotlight</h3>'+
    '<p class="foot" style="margin-top:0">Pick a student to see how they went on every '+esc(term.toLowerCase())+', question by question.</p>'+
    '<select class="picker" id="spot-pick" onchange="renderSpot()">'+opts+'</select><div id="spot-body"></div></div>';
}
function renderSpot(){
  const el=document.getElementById('spot-body');if(!el)return;
  const name=document.getElementById('spot-pick').value;const sacs=LAST_SACS,term=LAST_TERM,lo=term.toLowerCase();
  const qmeta=qmetaFor(sacs,LAST_PACK);
  const pct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const coh=sacs.map((sac,i)=>{const v=Object.values(pct[i]);return v.length?v.reduce((a,b)=>a+b,0)/v.length:0});
  let mine=[],cls='';const ov=[];
  sacs.forEach((sac,i)=>{const st=sac.students.find(s=>s.name===name);if(!st)return;cls=cls||st.cls;
    const p=pct[i][name];if(p!==undefined)ov.push(p);
    mine.push({sac,i,st,p:p===undefined?null:p})});
  const overall=ov.length?Math.round(ov.reduce((a,b)=>a+b,0)/ov.length):null;
  let h='<div class="spot-head"><div class="big">'+(overall==null?'—':overall+'%')+'</div>'+
    '<div class="meta"><b>'+esc(name)+'</b>'+(cls?' · '+esc(cls):'')+' · overall across '+mine.length+' '+esc(lo)+'(s)</div></div>';
  h+='<div class="card"><h3>Result on each '+esc(lo)+' vs cohort average</h3><div class="bars">';
  mine.forEach(m=>{const p=m.p==null?0:m.p,cavg=Math.round(coh[m.i]);
    h+='<div class="row"><div class="name">'+esc(term)+' '+esc(m.sac.number)+': '+esc(m.sac.topic)+'</div>'+
      '<div class="track"><div class="fill h'+heatBin(p)+'" style="width:'+p+'%"></div></div>'+
      '<div class="val">'+(m.p==null?'—':Math.round(m.p)+'%')+'<span style="color:var(--ink-2)"> / '+cavg+'</span></div></div>'});
  h+='</div><p class="foot">Green→red = this student\'s %. The grey number is the cohort average.</p></div>';
  mine.forEach(m=>{let head='<tr><th class="rowh">'+esc(term)+' '+esc(m.sac.number)+'</th>',row='<tr><th class="rowh">% of marks</th>';
    m.sac.questions.forEach(q=>{head+='<th>'+esc(q.id)+'</th>';const mk=m.st.marks[q.id];
      const p=(mk==null||!q.max)?null:100*mk/q.max;row+=hcell(p,name+' · '+q.id+' ('+(mk==null?'—':mk)+'/'+q.max+')')});
    head+='</tr>';row+='</tr>';
    h+='<div class="card"><h3>'+esc(m.sac.topic)+' — question by question</h3><div class="mx"><table>'+head+row+'</table></div></div>'});
  // study-design areas
  if(LAST_PACK&&PACKS[LAST_PACK]){const agg={};
    sacs.forEach((sac,i)=>{const st=sac.students.find(s=>s.name===name);if(!st)return;const qm=qmeta[sac.number]||{};
      sac.questions.forEach(q=>{const a=qm[q.id];if(!a)return;agg[a]=agg[a]||[0,0];agg[a][0]+=(st.marks[q.id]||0);agg[a][1]+=q.max})});
    const areas=Object.keys(agg).filter(a=>agg[a][1]).map(a=>({area:a,pct:Math.round(100*agg[a][0]/agg[a][1])})).sort((x,y)=>x.pct-y.pct);
    if(areas.length){h+='<div class="card"><h3>Study-design areas — strengths &amp; growth</h3><div class="bars">';
      areas.forEach(a=>{h+='<div class="row"><div class="name">'+esc(shortA(a.area))+'</div>'+
        '<div class="track"><div class="fill h'+heatBin(a.pct)+'" style="width:'+a.pct+'%"></div></div>'+
        '<div class="val">'+a.pct+'%</div></div>'});
      h+='</div><p class="foot">Sorted weakest→strongest — the top rows are where to focus support.</p></div>'}}
  el.innerHTML=h;
}

let LAST_SACS=null, LAST_TITLE='', LAST_PACK='', LAST_TERM='SAC';
function packOptions(sel){return '<option value="">Study design: none</option>'+
  Object.keys(PACKS).map(id=>'<option value="'+id+'"'+(id===sel?' selected':'')+'>'+esc(PACKS[id].name)+'</option>').join('')}
const SELCSS='padding:7px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--ink);font:inherit';
function renderDashboard(sacs,packId,term){
  term=term||'SAC';
  const hasCls=classList(sacs).length>0;
  const levelSel='<select onchange="LAST_TERM=this.value;reRenderDash()" style="'+SELCSS+'" title="Level / terminology">'+
    ['SAC','Assessment'].map(t=>'<option value="'+t+'"'+(t===term?' selected':'')+'>'+
      (t==='SAC'?'VCE (SACs)':'Years 7–10 (Assessments)')+'</option>').join('')+'</select>';
  const toolbar='<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">'+
    levelSel+
    '<select onchange="LAST_PACK=this.value;reRenderDash()" style="'+SELCSS+'">'+packOptions(packId)+'</select>'+
    '<button class="btn ghost" onclick="downloadDash()">⬇ Download this dashboard</button></div>';
  const allWarns=sacs.flatMap(s=>s.warnings||[]);
  const warnBanner=allWarns.length
    ?'<div class="warn-banner" role="alert"><b>⚠ Check your data before trusting this dashboard ('+allWarns.length+' issue'+(allWarns.length>1?'s':'')+'):</b><ul>'+
      allWarns.map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul></div>'
    :'';
  const highlights=highlightsCard(sacs,packId,term);
  const tabs=['<button class="active" onclick="pickSub(this,\'st-ov\')">Overview</button>']
    .concat(sacs.map((s,i)=>'<button onclick="pickSub(this,\'st'+i+'\')">'+esc(term)+' '+esc(s.number)+'</button>'));
  if(hasCls) tabs.push('<button onclick="pickSub(this,\'st-cls\')">Classes</button>');
  tabs.push('<button onclick="pickSub(this,\'st-student\')">Student</button>');
  if(packId) tabs.push('<button onclick="pickSub(this,\'st-skills\')">Skills &amp; content</button>');
  let bodies=overviewTab(sacs,term,highlights)+sacs.map((s,i)=>sacTab(s,i,term)).join('');
  if(hasCls) bodies+=classesTab(sacs,term);
  bodies+=studentTab(sacs,term);
  if(packId) bodies+=skillsTab(sacs,packId,term);
  return rampCss()+warnBanner+toolbar+'<div class="subtabs">'+tabs.join('')+'</div>'+bodies;
}
function mountDash(){
  $('xlsx-result').innerHTML='<h2 class="section" id="dash-title">Dashboard — '+esc(LAST_TITLE)+'</h2>'+
    renderDashboard(LAST_SACS,LAST_PACK,LAST_TERM);
  if(classList(LAST_SACS).length)renderClassQ();
  renderSpot();
}
function reRenderDash(){ if(LAST_SACS) mountDash(); }
function downloadDash(){
  const fns=[esc,med,totalFor,greenBin,heatBin,hcell,shortA,facSet,classList,qmetaFor,tiles,histogram,
    quartSeg,rampCss,highlightsCard,sacTab,overviewTab,terms,autoArea,skillsTab,classesTab,renderClassQ,
    studentTab,renderSpot,packOptions,renderDashboard,mountDash,reRenderDash,downloadDash,pickSub];
  const runtime='var STOP=new Set('+JSON.stringify([...STOP])+');\n'+
    'var RAMPS='+JSON.stringify(RAMPS)+';\nvar PACKS='+JSON.stringify(PACKS)+';\n'+
    'var STUDIO_CSS='+JSON.stringify(STUDIO_CSS)+';\n'+
    'var SELCSS='+JSON.stringify(SELCSS)+';\n'+
    'var LAST_SACS='+JSON.stringify(LAST_SACS)+';\nvar LAST_TITLE='+JSON.stringify(LAST_TITLE)+';\n'+
    'var LAST_PACK='+JSON.stringify(LAST_PACK)+';\nvar LAST_TERM='+JSON.stringify(LAST_TERM)+';\n'+
    'function $(id){return document.getElementById(id)}\n'+
    fns.map(f=>f.toString()).join('\n')+'\n'+
    'document.addEventListener("DOMContentLoaded",function(){reRenderDash()});';
  const doc='<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'+
    '<meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>'+esc(LAST_TITLE)+' — Markable dashboard</title><style>'+STUDIO_CSS+
    'body{padding:24px 30px}</style></head><body><div class="result active" id="xlsx-result"></div>'+
    '<script>'+runtime+'<\/script></body></html>';
  const blob=new Blob([doc],{type:'text/html'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=(LAST_TITLE.replace(/\.[^.]+$/,'')||'markable')+'-dashboard.html';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function pickSub(btn,id){
  const root=btn.closest('.result')||document;
  root.querySelectorAll('.subtabs button').forEach(b=>b.classList.toggle('active',b===btn));
  root.querySelectorAll('.subtab').forEach(t=>t.classList.toggle('active',t.id===id));
}
