/* Interactive, source-backed dataset explorer. No generated observations. */
(function(root){
 'use strict';
 const sources=[
  {name:'Crop records',provider:'UPAg / DES',description:'District-season crop area and production provide the observed yield labels.',features:['Crop year','State & district','Season','Crop area','Production','Yield = production / area'],url:'https://ckandev.indiadataportal.com/dataset/area-production-yield-apy',icon:'<path d="M7 19V7h12v12H7Zm4-8h4m-4 4h4M4 4h12"/>'},
  {name:'District boundaries',provider:'GADM 4.1',description:'Exact same-state district matching connects crop records to representative coordinates.',features:['District geometry','State & district matching','CENTROID_X','CENTROID_Y'],url:'https://gadm.org/data.html',icon:'<path d="m4 7 5-3 6 3 5-3v15l-5 3-6-3-5 3V7Zm5-3v15m6-12v15"/>'},
  {name:'Seasonal weather',provider:'NASA POWER',description:'Daily weather is aggregated over complete crop-season windows. Rabi and Winter cross the agricultural-year boundary.',features:['Temperature','Rainfall','Relative humidity','Wind speed','Solar radiation','Evaporation','Pressure','Growing degree days'],url:'https://power.larc.nasa.gov/docs/services/api/temporal/daily/',icon:'<circle cx="10" cy="9" r="4"/><path d="M10 1v2m-8 6h2m12 0h2M4 3l2 2m9-2-2 2M7 18h12a3 3 0 0 0-1-6 5 5 0 0 0-9 1 3 3 0 0 0-2 5Z"/>'}
 ];
 root.PaddyPipeline={mount(dataset){
  const host=document.getElementById('sources-section');if(!host||host.querySelector('.pipeline-workbench'))return;
  const details=host.querySelector('.source-details');
  const work=document.createElement('div');work.className='pipeline-workbench';
  work.innerHTML='<div class="pipeline-sources" aria-label="Explore data sources">'+sources.map((s,i)=>`<button type="button" class="pipeline-source" aria-pressed="${i===0}" data-source="${i}"><svg viewBox="0 0 24 26" aria-hidden="true">${s.icon}</svg><span><b>${s.name}</b><small>${s.provider}</small></span><span class="source-arrow" aria-hidden="true">↗</span></button>`).join('')+'</div><div class="pipeline-inspector"><div class="pipeline-network"><svg viewBox="0 0 660 230" role="img" aria-label="Crop records, district boundaries and seasonal weather merge into the rice dataset"><defs><pattern id="pipeline-dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".7" fill="#343434"/></pattern></defs><rect width="660" height="230" fill="url(#pipeline-dots)"/><g class="network-lines" fill="none"><path data-branch="0" d="M168 43H250Q270 43 270 63V95Q270 115 300 115H382"/><path data-branch="1" d="M168 115H382"/><path data-branch="2" d="M168 187H250Q270 187 270 167V135Q270 115 300 115H382"/></g><g class="network-input" data-node="0"><rect x="18" y="23" width="150" height="40" rx="6"/><text x="93" y="48" text-anchor="middle">Crop records</text></g><g class="network-input" data-node="1"><rect x="18" y="95" width="150" height="40" rx="6"/><text x="93" y="120" text-anchor="middle">Boundaries</text></g><g class="network-input" data-node="2"><rect x="18" y="167" width="150" height="40" rx="6"/><text x="93" y="192" text-anchor="middle">Weather</text></g><circle cx="332" cy="115" r="5" fill="#c8ee86"/><rect x="382" y="73" width="258" height="84" rx="8" class="network-output"/><text x="404" y="102" class="network-output-title">Rice dataset</text><text x="404" y="132" id="pipeline-shape"></text></svg></div><div class="pipeline-detail" aria-live="polite"><h3 id="pipeline-title"></h3><p id="pipeline-description"></p><div id="pipeline-features" class="pipeline-features"></div><a id="pipeline-link" target="_blank" rel="noopener">View original source ↗</a></div></div>';
  const title=document.createElement('h2');title.textContent='Data pipeline';host.replaceChildren(title,work);if(details)host.append(details);
  work.querySelector('#pipeline-shape').textContent=Number(dataset.rows).toLocaleString('en-IN')+' rows · 30 columns';
  const choose=index=>{
   const s=sources[index];work.querySelector('#pipeline-title').textContent=s.name;work.querySelector('#pipeline-description').textContent=s.description;
   const features=work.querySelector('#pipeline-features');features.replaceChildren(...s.features.map(name=>{const tag=document.createElement('span');tag.textContent=name;return tag;}));
   work.querySelector('#pipeline-link').href=s.url;
   work.querySelectorAll('[data-source]').forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
   work.querySelectorAll('[data-branch]').forEach((path,i)=>path.classList.toggle('is-active',i===index));
   work.querySelectorAll('[data-node]').forEach((node,i)=>node.classList.toggle('is-active',i===index));
  };
  work.querySelectorAll('[data-source]').forEach((button,i)=>button.addEventListener('click',()=>choose(i)));choose(0);
 }};
})(window);
