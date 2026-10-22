/* Shared, deterministic class-score display; never modifies model scores. */
(function(root){
 'use strict';
 const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fraction=value=>Number.isFinite(Number(value))?Math.max(0,Math.min(1,Number(value))):0;
 function percentage(value){
  const percent=fraction(value)*100;
  if(percent===0||percent===100)return percent+'%';
  if(percent<.1)return '<0.1%';
  if(percent>99.9)return '>99.9%';
  return percent.toLocaleString('en-IN',{maximumFractionDigits:1})+'%';
 }
 function renderRows(scores,labels){
  const highest=Math.max(0,...scores.map(row=>fraction(row.score)));
  return scores.map(row=>{
   const value=fraction(row.score),percent=value*100,label=labels[row.label]||row.label;
   return `<div class="score-row${highest>0&&value===highest?' score-row-leading':''}"><span>${escape(label)}</span><b>${escape(percentage(value))}</b><span class="health-score-track" role="meter" aria-label="${escape(label)} model score" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" aria-valuetext="${escape(percentage(value))}"><span class="health-score-fill" style="width:${percent}%" aria-hidden="true"></span></span></div>`;
  }).join('');
 }
 const api={renderRows,percentage};
 root.HealthScoreBars=api;
 if(typeof module==='object'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
