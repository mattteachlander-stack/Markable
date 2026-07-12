/* ---------- Live results views (VCE SACs / Years 7-10) + labelled demo data ----------
   These replace the old sibling-file result reports: the dashboard is rendered
   in-page from the uploaded workbook, so the standalone hub needs no files
   beside it. */
let IS_DEMO=false;
function paintResultsEmpty(){
  const el=$('results-empty');if(el)el.style.display=LAST_SACS?'none':'block';
}
function showResults(term,btn){
  if(term)LAST_TERM=term;
  show('results',btn||document.querySelector('.nav-item[data-nav='+(LAST_TERM==='Assessment'?'res710':'resvce')+']'));
  if(LAST_SACS){mountDash();$('xlsx-result').classList.add('active')}
  paintResultsEmpty();
}
function showFeedback(btn){
  show('feedback',btn||document.querySelector('.nav-item[data-nav=feedback]'));
  renderFeedback();
}
/* deterministic fictional cohort — clearly labelled DEMO, never real students */
function demoRand(seed){let s=seed>>>0;return function(){s=(s*1664525+1013904223)>>>0;return s/4294967296}}
function demoSacs(term){
  const first=['Ava','Ben','Chloe','Dev','Ella','Finn','Grace','Hugo','Isla','Jack','Kira','Liam'];
  const last=['Nguyen','Smith','Patel','OBrien','Kaur','Chen','Rossi','Brown','Silva','Khan','Ito','Jones'];
  const classes=term==='Assessment'?['8A','8B']:['11A','11B'];
  const defs=term==='Assessment'
    ?[{number:'1',topic:'Forces & motion (demo)',qs:[['Speed calculations',5],['Forces diagram',4],['Prac method',5],['Conclusions',6]]},
      {number:'2',topic:'Chemical reactions (demo)',qs:[['Word equations',4],['Observation table',5],['Variables',4],['Explanation',7]]}]
    :[{number:'1',topic:'Cells & membranes (demo)',qs:[['Microscopy',4],['Membrane transport',6],['Osmosis prac',5],['Data analysis',5]]},
      {number:'2',topic:'Enzymes & metabolism (demo)',qs:[['Enzyme structure',4],['Rates experiment',6],['Graphing',4],['Evaluation',6]]}];
  return defs.map((d,di)=>{
    const qs=d.qs.map(([id,max],i)=>({id,max,col:i}));
    const rnd=demoRand(42+di*7);
    const students=first.map((f,i)=>{
      const ability=.35+.6*(i/(first.length-1));
      const marks={};qs.forEach(q=>{const p=Math.min(1,Math.max(0,ability+(rnd()-.5)*.4));
        marks[q.id]=Math.round(p*q.max*2)/2});
      return {name:last[i]+', '+f,sid:'DEMO'+(100+i),cls:classes[i%2],marks};
    });
    return {number:d.number,topic:d.topic,total:qs.reduce((a,q)=>a+q.max,0),questions:qs,students,warnings:[]};
  });
}
function loadDemo(term){
  term=term||LAST_TERM||'SAC';
  LAST_SACS=demoSacs(term);LAST_TITLE='Demo data — fictional students';LAST_PACK='';LAST_TERM=term;IS_DEMO=true;
  showResults(term);
}
