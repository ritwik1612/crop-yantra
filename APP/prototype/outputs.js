/* Transparent derived outputs. No inference, agronomic scoring or fabricated data. */
(function(root){
 'use strict';
 function summarize(request,records,price=null,factor=1){
  const yieldValue=Number(request.illustrativeYieldTPerHa),area=Number(request.areaHa);
  if(!Number.isFinite(yieldValue)||yieldValue<0||!Number.isFinite(area)||area<=0)throw new Error('Invalid yield or area');
  if(!Number.isFinite(factor)||factor<.5||factor>1.5)throw new Error('Scenario factor outside 0.5–1.5');
  if(price!==null&&(!Number.isFinite(price)||price<0))throw new Error('Invalid price');
  const seasonRows=records.filter(r=>r.SEASON===request.season&&Number(r.FYEAR)<=request.year);
  const byYear=new Map();seasonRows.forEach(r=>{const year=Number(r.FYEAR);byYear.set(year,[...(byYear.get(year)||[]),r]);});
  const trend=[...byYear].filter(([,rows])=>rows.length===1).map(([year,rows])=>({year,yield:Number(rows[0].YIELD)})).filter(p=>Number.isFinite(p.yield)).sort((a,b)=>a.year-b.year);
  const matched=records.filter(r=>r.SEASON===request.season&&Number(r.FYEAR)===request.year);
  const reference=matched.length===1?matched[0]:null;
  const tonnes=yieldValue*area,kg=tonnes*1000;
  return {mode:'interface_demo',yieldTPerHa:yieldValue,areaHa:area,productionTonnes:tonnes,productionKg:kg,
          grossValueINR:price===null?null:kg*price,priceINRPerKg:price,
          scenario:{areaFactor:factor,areaHa:area*factor,productionTonnes:tonnes*factor},
          reference,trend,ambiguousYears:[...byYear].filter(([,rows])=>rows.length!==1).map(([year])=>year),
          observedMeanYield:trend.length?trend.reduce((sum,p)=>sum+p.yield,0)/trend.length:null,
          observedMinYield:trend.length?Math.min(...trend.map(p=>p.yield)):null,
          observedMaxYield:trend.length?Math.max(...trend.map(p=>p.yield)):null,
          demoGapTPerHa:reference?yieldValue-Number(reference.YIELD):null,
          modelTrained:false};
 }
 root.RYPOutputs={summarize};
 if(typeof module!=='undefined'&&module.exports)module.exports=root.RYPOutputs;
})(typeof window!=='undefined'?window:globalThis);
