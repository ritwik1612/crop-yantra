/* Accessible SVG views of arithmetic scenarios and recorded observations. */
(function(root){
 'use strict';
 const n=(v,d=1)=>Number(v).toLocaleString('en-IN',{maximumFractionDigits:d});
 const svg=(label,body)=>`<svg class="result-chart harvest-chart" viewBox="0 0 560 250" role="img" aria-label="${label}"><title>${label}</title>${body}</svg>`;
 function comparison(s){
  const observed=s.reference?Number(s.reference.YIELD):null;
  const ceiling=Math.max(s.yieldTPerHa,observed||0,1)*1.15;
  const rows=[{label:'Your demo assumption',value:s.yieldTPerHa,kind:'demo-bar',y:62},{label:'Recorded district yield',value:observed,kind:'observed-bar',y:153}];
  return svg('Demo assumption versus recorded yield, in tonnes per hectare. Not a model evaluation.',
   rows.map(r=>`<text x="24" y="${r.y-13}" class="chart-row-label">${r.label}</text><rect x="24" y="${r.y}" width="512" height="24" rx="12" class="chart-track"/>${r.value===null?`<text x="24" y="${r.y+53}" class="chart-note">No matching observation · not treated as zero</text>`:`<rect x="24" y="${r.y}" width="${Math.max(0,r.value/ceiling*512)}" height="24" rx="12" class="${r.kind}"/><text x="536" y="${r.y-13}" text-anchor="end" class="chart-value">${n(r.value,2)} t/ha</text>`}`).join('')+
   `<text x="24" y="237" class="chart-note">Same unit, different evidence: illustrative vs observed.</text>`);
 }
 function scenario(s,factor=1){
  const p=s.productionTonnes,area=s.areaHa,max=Math.max(p*1.5,1),x=f=>52+(f-.5)*456,y=v=>198-v/max*142;
  const fx=x(factor),fy=y(p*factor);
  return svg(`Area scenario: ${n(area*factor,2)} hectares gives ${n(p*factor,2)} tonnes at fixed demo yield. Not uncertainty.`,
   [0,.5,1].map(f=>`<line x1="52" y1="${198-f*142}" x2="508" y2="${198-f*142}" class="chart-grid"/><text x="42" y="${203-f*142}" text-anchor="end">${n(max*f)}</text>`).join('')+
   `<text x="52" y="24" class="chart-note">PRODUCTION · TONNES</text><path d="M52 198 L52 ${y(p*.5)} L508 ${y(p*1.5)} L508 198 Z" class="scenario-fill"/><path d="M52 ${y(p*.5)} L508 ${y(p*1.5)}" class="scenario-line"/>`+
   [.5,1,1.5].map(f=>`<circle cx="${x(f)}" cy="${y(p*f)}" r="4" class="history-point"/><text x="${x(f)}" y="225" text-anchor="middle">${n(area*f)} ha</text>`).join('')+
   `<g class="scenario-marker"><line x1="${fx}" y1="42" x2="${fx}" y2="198" class="scenario-highlight"/><circle cx="${fx}" cy="${fy}" r="11" class="scenario-halo"/><circle cx="${fx}" cy="${fy}" r="5" class="scenario-dot"/></g><text x="508" y="24" text-anchor="end" class="chart-value">${n(p*factor,2)} t</text>`);
 }
 function history(s){
  if(!s.trend.length)return null;
  const points=s.trend,max=Math.max(...points.map(p=>p.yield),1)*1.15,min=points[0].year,last=points.at(-1).year;
  const x=year=>52+(year-min)/Math.max(last-min,1)*456,y=v=>198-v/max*142;
  const coords=points.map(p=>`${x(p.year)},${y(p.yield)}`).join(' ');
  const ticks=[...new Set([min,points[Math.floor((points.length-1)/2)].year,last])];
  return svg('Recorded same-season district yield history. Hover or focus an observation for its value. Not a forecast.',
   [0,.5,1].map(f=>`<line x1="52" y1="${198-f*142}" x2="508" y2="${198-f*142}" class="chart-grid"/><text x="42" y="${203-f*142}" text-anchor="end">${n(max*f)}</text>`).join('')+
   `<text x="52" y="24" class="chart-note">OBSERVED YIELD · t/ha</text>${points.length>1?`<polygon points="${x(min)},198 ${coords} ${x(last)},198" class="history-fill"/><polyline points="${coords}" class="history-line"/>`:''}`+
   points.map(p=>`<g class="history-observation" tabindex="0" role="img" aria-label="${p.year}: ${n(p.yield,3)} tonnes per hectare"><circle cx="${x(p.year)}" cy="${y(p.yield)}" r="12" fill="transparent"/><circle cx="${x(p.year)}" cy="${y(p.yield)}" r="4" class="history-point"/><title>${p.year}: ${n(p.yield,3)} t/ha</title><g class="point-callout" transform="translate(${Math.max(70,Math.min(490,x(p.year)))},${Math.max(48,y(p.yield)-18)})"><rect x="-66" y="-24" width="132" height="28" rx="6"/><text x="0" y="-6" text-anchor="middle">${p.year} · ${n(p.yield,2)} t/ha</text></g></g>`).join('')+
   ticks.map(year=>`<text x="${x(year)}" y="226" text-anchor="middle">${year}</text>`).join(''));
 }
 root.CropCharts={comparison,scenario,history};
 if(typeof module!=='undefined'&&module.exports)module.exports=root.CropCharts;
})(typeof window!=='undefined'?window:globalThis);
