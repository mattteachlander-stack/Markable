/* 00-pure.js — dependency-free functions shared by the browser bundle and
   the node unit tests (see tests/js/). No DOM, no fetch, no storage. */

function gridExtents(g){
  let rmax=0,cmax=0;
  for(const r of Object.keys(g)){const rn=+r;if(rn>rmax)rmax=rn;
    for(const c of Object.keys(g[r])){const cn=+c;if(cn>cmax)cmax=cn}}
  return {rmax:Math.min(rmax,5000),cmax:Math.min(cmax,512)};
}

const REVIEW_CONF=0.85;

/* ---------- client-side exporters: markdown → .docx / .pdf (no libraries) ---------- */
const CRC_T=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;
  for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c}return t})();
function crc32(u8){let c=0xFFFFFFFF;for(let i=0;i<u8.length;i++)c=CRC_T[(c^u8[i])&255]^(c>>>8);
  return (c^0xFFFFFFFF)>>>0}
function makeZip(files){ // [[name, Uint8Array], …] → stored (method 0) ZIP
  const enc=new TextEncoder();const parts=[];const cd=[];let off=0;
  function u16(v){return [v&255,(v>>8)&255]} function u32(v){return [v&255,(v>>8)&255,(v>>16)&255,(v>>>24)&255]}
  for(const [name,data] of files){
    const n=enc.encode(name),crc=crc32(data);
    const lh=new Uint8Array([0x50,0x4b,3,4,...u16(20),...u16(0),...u16(0),...u16(0),...u16(0),
      ...u32(crc),...u32(data.length),...u32(data.length),...u16(n.length),...u16(0)]);
    parts.push(lh,n,data);
    cd.push({n,crc,size:data.length,off});
    off+=lh.length+n.length+data.length;
  }
  const cdParts=[];let cdLen=0;
  for(const e of cd){
    const h=new Uint8Array([0x50,0x4b,1,2,...u16(20),...u16(20),...u16(0),...u16(0),...u16(0),...u16(0),
      ...u32(e.crc),...u32(e.size),...u32(e.size),...u16(e.n.length),...u16(0),...u16(0),
      ...u16(0),...u16(0),...u32(0),...u32(e.off)]);
    cdParts.push(h,e.n);cdLen+=h.length+e.n.length;
  }
  const eocd=new Uint8Array([0x50,0x4b,5,6,...u16(0),...u16(0),...u16(cd.length),...u16(cd.length),
    ...u32(cdLen),...u32(off),...u16(0)]);
  const total=[...parts,...cdParts,eocd];
  const out=new Uint8Array(total.reduce((a,p)=>a+p.length,0));
  let p=0;for(const part of total){out.set(part,p);p+=part.length}
  return out;
}
function xmlEsc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function mdToDocx(md){ // one paragraph per line; #/## headings bold + larger
  const paras=md.split('\n').map(line=>{
    const h1=/^#\s+/.test(line),h2=/^##\s+/.test(line);
    const text=xmlEsc(line.replace(/^#{1,3}\s+/,''));
    const rpr=h1?'<w:rPr><w:b/><w:sz w:val="36"/></w:rPr>':h2?'<w:rPr><w:b/><w:sz w:val="28"/></w:rPr>':'';
    return '<w:p><w:r>'+rpr+'<w:t xml:space="preserve">'+text+'</w:t></w:r></w:p>';
  }).join('');
  const doc='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'+
    '<w:body>'+paras+'</w:body></w:document>';
  const ct='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'+
    '<Default Extension="xml" ContentType="application/xml"/>'+
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>';
  const rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>';
  const enc=new TextEncoder();
  return makeZip([['[Content_Types].xml',enc.encode(ct)],['_rels/.rels',enc.encode(rels)],
    ['word/document.xml',enc.encode(doc)]]);
}
function pdfSan(s){ // standard-font safe: swap common unicode for ASCII, escape PDF specials
  return s.replace(/[—–]/g,'-').replace(/[’‘]/g,"'").replace(/[“”]/g,'"').replace(/[→]/g,'->')
    .replace(/[×]/g,'x').replace(/[≥]/g,'>=').replace(/[≤]/g,'<=').replace(/[·•]/g,'*')
    .replace(/[^\x20-\x7e]/g,'?').replace(/\\/g,'\\\\').replace(/\(/g,'\\(').replace(/\)/g,'\\)');
}
function mdToPdf(md){ // minimal text PDF: A4, Helvetica, bold headings, wrapped lines
  const raw=[];
  md.split('\n').forEach(line=>{
    const head=/^#{1,3}\s+/.test(line);
    let t=line.replace(/^#{1,3}\s+/,'');
    if(!t){raw.push({t:'',head:false});return}
    while(t.length>92){let cut=t.lastIndexOf(' ',92);if(cut<40)cut=92;
      raw.push({t:t.slice(0,cut),head});t=t.slice(cut).replace(/^ /,'')}
    raw.push({t,head});
  });
  const perPage=46;const pages=[];
  for(let i=0;i<raw.length;i+=perPage)pages.push(raw.slice(i,i+perPage));
  if(!pages.length)pages.push([{t:'',head:false}]);
  const objs=[];  // 1:catalog 2:pages 3:F1 4:F2 then per page: page,content
  const pageIds=pages.map((_,i)=>5+i*2);
  objs[1]='<< /Type /Catalog /Pages 2 0 R >>';
  objs[2]='<< /Type /Pages /Kids ['+pageIds.map(i=>i+' 0 R').join(' ')+'] /Count '+pages.length+' >>';
  objs[3]='<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>';
  objs[4]='<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>';
  pages.forEach((pl,i)=>{
    let s='BT /F1 10 Tf 14 TL 56 800 Td\n';let bold=false;
    pl.forEach(l=>{
      if(l.head!==bold){s+=l.head?'/F2 13 Tf\n':'/F1 10 Tf\n';bold=l.head}
      s+='('+pdfSan(l.t)+') Tj T*\n';
    });
    s+='ET';
    objs[5+i*2]='<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '+
      '/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents '+(6+i*2)+' 0 R >>';
    objs[6+i*2]='<< /Length '+s.length+' >>\nstream\n'+s+'\nendstream';
  });
  let out='%PDF-1.4\n';const xref=[0];
  for(let i=1;i<objs.length;i++){xref[i]=out.length;out+=i+' 0 obj\n'+objs[i]+'\nendobj\n'}
  const startx=out.length;
  out+='xref\n0 '+objs.length+'\n0000000000 65535 f \n';
  for(let i=1;i<objs.length;i++)out+=String(xref[i]).padStart(10,'0')+' 00000 n \n';
  out+='trailer\n<< /Size '+objs.length+' /Root 1 0 R >>\nstartxref\n'+startx+'\n%%EOF';
  return new TextEncoder().encode(out);
}

function stripAnswerMarkers(md){
  // remove the trailing * that flags the correct MCQ option in the teacher master
  return md.split('\n').map(l=>l.replace(/^(\s*-\s*[A-Da-d]\)\s.*?)\s*\*+\s*$/,'$1')).join('\n');
}
function detectAnswerLeaks(md){
  const leaks=[];
  md.split('\n').forEach((l,i)=>{
    const t=l.trim();
    if(/^-\s*[A-Da-d]\).*\*\s*$/.test(t))leaks.push('line '+(i+1)+': MCQ option still marked with *');
    if(/^(answer|correct answer|correct option|model answer|marking key|accept|reject|solution)\s*[:\-]/i.test(t))
      leaks.push('line '+(i+1)+': "'+t.slice(0,50)+'"');
  });
  return leaks;
}

function y(s){return JSON.stringify(String(s))} // YAML-safe scalar (double-quoted)
function keyYaml(k){
  let out='# Marking key drafted in Markable\'s Rubric builder — teacher-reviewed export.\n'+
    'test_id: '+y(k.test_id)+'\ntotal_marks: '+k.total_marks+'\nquestions:\n';
  k.questions.forEach(q=>{
    out+='- id: '+y(q.id)+'\n  type: '+q.type+'\n  marks: '+q.marks+'\n';
    if(q.correct)out+='  correct: '+y(q.correct)+'\n';
    if(q.distractor_notes){out+='  distractor_notes:\n';
      Object.keys(q.distractor_notes).forEach(o=>out+='    '+y(o)+': '+y(q.distractor_notes[o])+'\n')}
    if(q.criteria&&q.criteria.length){out+='  criteria:\n';
      q.criteria.forEach(c=>out+='  - point: '+y(c.point)+'\n    marks: '+c.marks+'\n')}
    if(q.accept&&q.accept.length){out+='  accept:\n';q.accept.forEach(a=>out+='  - '+y(a)+'\n')}
    if(q.reject&&q.reject.length){out+='  reject:\n';q.reject.forEach(a=>out+='  - '+y(a)+'\n')}
    if(q.final_answer)out+='  final_answer: '+y(q.final_answer)+'\n';
    if(q.tolerance!=null)out+='  tolerance: '+q.tolerance+'\n';
    if(q.rubric&&q.rubric.length){out+='  rubric:\n';
      q.rubric.forEach(b=>out+='  - band: '+y(b.band)+'\n    descriptor: '+y(b.descriptor)+'\n')}
    out+='  review_threshold: '+q.review_threshold+'\n';
  });
  return out;
}
function rubricMd(k){
  let md='# Marking key — '+k.test_id+'\nTotal: '+k.total_marks+' marks\n';
  k.questions.forEach(q=>{
    md+='\n## '+q.id+' ['+q.type+', '+q.marks+']\n';
    if(q.correct)md+='Correct: '+q.correct+'\n';
    if(q.distractor_notes)Object.keys(q.distractor_notes).forEach(o=>md+='- '+o+') '+q.distractor_notes[o]+'\n');
    (q.criteria||[]).forEach(c=>md+='- ['+c.marks+'] '+c.point+'\n');
    if(q.accept&&q.accept.length)md+='Accept: '+q.accept.join('; ')+'\n';
    if(q.reject&&q.reject.length)md+='Reject: '+q.reject.join('; ')+'\n';
    if(q.final_answer)md+='Final answer: '+q.final_answer+(q.tolerance!=null?' (±'+q.tolerance+')':'')+'\n';
    (q.rubric||[]).forEach(b=>md+='- '+b.band+': '+b.descriptor+'\n');
  });
  return md;
}


/* minimal parser for key.yaml files that Markable itself emits (keyYaml above):
   known keys, JSON-quoted scalars. Returns null if the shape isn't recognised. */
function parseKeyYaml(text){
  try{
    const lines=text.split('\n');const out={questions:[]};let q=null,list=null,item=null;
    for(const raw of lines){
      if(!raw.trim()||raw.trim().startsWith('#'))continue;
      let m;
      if((m=raw.match(/^test_id:\s*(.+)$/))){out.test_id=JSON.parse(m[1]);continue}
      if((m=raw.match(/^total_marks:\s*(\d+)/))){out.total_marks=+m[1];continue}
      if(/^questions:/.test(raw))continue;
      if((m=raw.match(/^- id:\s*(.+)$/))){q={id:JSON.parse(m[1])};out.questions.push(q);list=null;continue}
      if(!q)continue;
      if((m=raw.match(/^  type:\s*(\S+)/))){q.type=m[1];continue}
      if((m=raw.match(/^  marks:\s*(\d+)/))){q.marks=+m[1];continue}
      if((m=raw.match(/^  (criteria|accept|reject|rubric|distractor_notes):\s*$/))){list=m[1];q[list]=q[list]||(list==='distractor_notes'?{}:[]);continue}
      if(list==='criteria'&&(m=raw.match(/^  - point:\s*(.+)$/))){item={point:JSON.parse(m[1])};q.criteria.push(item);continue}
      if(list==='criteria'&&(m=raw.match(/^    marks:\s*(\d+)/))){if(item)item.marks=+m[1];continue}
      if((list==='accept'||list==='reject')&&(m=raw.match(/^  - (.+)$/))){q[list].push(JSON.parse(m[1]));continue}
      if(list==='rubric'&&(m=raw.match(/^  - band:\s*(.+)$/))){item={band:JSON.parse(m[1])};q.rubric.push(item);continue}
      if(list==='rubric'&&(m=raw.match(/^    descriptor:\s*(.+)$/))){if(item)item.descriptor=JSON.parse(m[1]);continue}
      if(list==='distractor_notes'&&(m=raw.match(/^    (.+?):\s*(.+)$/))){q.distractor_notes[JSON.parse(m[1])]=JSON.parse(m[2]);continue}
      if((m=raw.match(/^  correct:\s*(.+)$/))){q.correct=JSON.parse(m[1]);list=null;continue}
      if((m=raw.match(/^  final_answer:\s*(.+)$/))){q.final_answer=JSON.parse(m[1]);list=null;continue}
      if((m=raw.match(/^  tolerance:\s*(\S+)/))){q.tolerance=parseFloat(m[1]);list=null;continue}
      if((m=raw.match(/^  review_threshold:/))){list=null;continue}
    }
    return out.questions.length?out:null;
  }catch(e){return null}
}
function validateResult(r,structKey){
  r=validateCore(r);
  if(structKey&&Array.isArray(structKey.questions)&&Array.isArray(r.judgements)){
    const byId={};r.judgements.forEach(j=>byId[j.question]=j);
    structKey.questions.forEach(k=>{
      const j=byId[k.id];
      if(!j){r.judgements.push({question:k.id,marks_awarded:0,marks_available:k.marks||0,
        transcription:'',evidence:'',feedback:'',confidence:0,needs_review:true,
        review_reason:'missing from the AI response',
        _flags:['expected question '+k.id+' missing from the AI response'],_review:true});return}
      if(k.marks!=null&&j.marks_available!==k.marks){
        j._flags.push('marks_available '+j.marks_available+' ≠ key value '+k.marks+' — key value used');
        j.marks_available=k.marks;
        if(j.marks_awarded>k.marks){j._flags.push('awarded > key maximum — clamped');j.marks_awarded=k.marks}
        j._review=true;}
    });
    const known={};structKey.questions.forEach(k=>known[k.id]=1);
    r.judgements.forEach(j=>{if(!known[j.question]){
      j._flags=j._flags||[];j._flags.push('question '+j.question+' is not in the marking key');j._review=true}});
  }
  return r;
}
function validateCore(r){
  const flags=[];
  if(!Array.isArray(r.judgements)||!r.judgements.length){r._flags=['no judgements returned'];return r}
  const seen={};
  r.judgements.forEach(j=>{
    j._flags=[];
    j.marks_available=Number(j.marks_available)||0;
    j.marks_awarded=Number(j.marks_awarded)||0;
    if(seen[j.question])j._flags.push('duplicate question id '+j.question);
    seen[j.question]=true;
    if(j.marks_awarded<0){j._flags.push('negative mark clamped to 0');j.marks_awarded=0}
    if(j.marks_awarded>j.marks_available){
      j._flags.push('awarded '+j.marks_awarded+' > available '+j.marks_available+' — clamped');
      j.marks_awarded=j.marks_available}
    let c=Number(j.confidence);if(isNaN(c))c=0;
    j.confidence=Math.max(0,Math.min(1,c));
    if(j.confidence<REVIEW_CONF)j._flags.push('confidence '+j.confidence.toFixed(2)+' below '+REVIEW_CONF);
    if(!String(j.transcription||'').trim())j._flags.push('no transcription — possibly blank/illegible');
    if(j.needs_review)j._flags.push(j.review_reason||'model flagged for review');
    j._review=j._flags.length>0;   // OUR rule, not the model's field
  });
  r._flags=flags;
  return r;
}
if(typeof module!=='undefined'&&module.exports){
  module.exports={crc32,makeZip,xmlEsc,mdToDocx,pdfSan,mdToPdf,gridExtents,
    REVIEW_CONF,validateResult,validateCore,stripAnswerMarkers,detectAnswerLeaks,
    y,keyYaml,rubricMd,parseKeyYaml};
}
