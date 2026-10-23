const {chromium}=require('C:/Users/ritwi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'../..');
const SITE=process.env.PADDY_TEST_SITE||null;
(async()=>{
 const fixtures=JSON.parse(await fs.readFile(path.join(ROOT,'OTHER/ui-audit-fixture.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',err=>errors.push(err.message));
 await page.route('http://paddy.test/**',async route=>{
  const rel=decodeURIComponent(new URL(route.request().url()).pathname).slice(1)||'index.html';
  try{let body=await fs.readFile(SITE?path.join(SITE,rel):path.join(ROOT,rel.startsWith('desktop.')?'APP/desktop':'APP/prototype',rel));
   if(rel==='index.html'&&!body.toString().includes('src="desktop.js"'))body=Buffer.from(body.toString().replace('</head>','<link rel="stylesheet" href="desktop.css"><script defer src="desktop.js"></script></head>'));
   await route.fulfill({body,contentType:rel.endsWith('.html')?'text/html':rel.endsWith('.css')?'text/css':rel.endsWith('.js')?'application/javascript':rel.endsWith('.svg')?'image/svg+xml':undefined});
  }catch{await route.fulfill({status:404,body:''});}
 });
 await page.addInitScript(fixtures=>{
  window.testCalls={yield:[],health:[],export:[]};
  window.pywebview={api:{status:async()=>fixtures.status,predict_seasonal_yield:async request=>{window.testCalls.yield.push(request);return fixtures.yield;},classify_image:async()=>fixtures.health,export_pdf:async options=>{window.testCalls.export.push(options);return {ok:false,cancelled:true};}}};
 },fixtures);
 await page.goto('http://paddy.test/');await page.waitForFunction(()=>window.CropDesktop?.ready&&document.querySelector('#seq-stage-6'));
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.locator('#architecture .system-explorer').count(),0,'Legacy architecture must not be reinserted above neural diagrams');
 assert.doesNotMatch(await page.locator('#architecture-yield-panel').innerText(),/HistGradientBoosting|Residual MLP/);
 await page.locator('.state-surface[aria-label^="Andhra Pradesh,"]').press('Enter');
 await page.getByRole('button',{name:'Nellore, Andhra Pradesh. Select district.',exact:true}).press('Enter');
 await page.locator('#land-area').fill('15');await page.locator('#area').fill('12');
 await page.locator('.field-continue').click();
 await page.locator('#temperature').evaluate(el=>{el.value='27';el.dispatchEvent(new Event('input',{bubbles:true}));});
 await page.locator('#preview-button').click();await page.locator('#result').waitFor({state:'visible'});
 assert.match(await page.locator('#result').innerText(),/CNN–LSTM/);
 assert.doesNotMatch(await page.locator('#result').innerText(),/tree-path|boosted-tree|year trend/);
 await page.locator('#season-area').fill('6');await page.locator('#season-price').fill('20');
 assert.ok((await page.locator('#seq-production').innerText()).startsWith((fixtures.yield.yieldTPerHa*6).toLocaleString('en-IN',{maximumFractionDigits:3})));
 await page.locator('.prediction-audit > summary').click();
 assert.equal(await page.locator('.prediction-audit table').count(),5);
 assert.equal(await page.locator('.sequence-effect').count(),13);
 await page.locator('#export-pdf').click();
 await page.locator('#save-pdf').click();await page.waitForFunction(()=>window.testCalls.export.length===1);
 assert.equal(await page.evaluate(()=>window.testCalls.export[0].scenario.areaHa),6);
 await page.locator('.pdf-close').click();
 await fs.mkdir(path.join(ROOT,'OTHER/sequence-ui-qa'),{recursive:true});
 await page.screenshot({path:path.join(ROOT,'OTHER/sequence-ui-qa/result.png')});
 await page.locator('nav[aria-label="Main"] a[href="#architecture"]').click();
 assert.equal(await page.locator('#architecture [role="tabpanel"]:visible').count(),1);
 assert.equal(await page.locator('#architecture-yield-panel .sequence-stage').count(),7);
 await page.getByRole('button',{name:'4. LSTM',exact:true}).click();
 assert.equal(await page.locator('#architecture').isVisible(),true);
 await page.locator('#seq-stage-4').screenshot({path:path.join(ROOT,'OTHER/sequence-ui-qa/lstm-stage.png')});
 await page.getByRole('tab',{name:/Disease/}).click();
 assert.equal(await page.locator('#architecture [role="tabpanel"]:visible').count(),1);
 assert.equal(await page.locator('.sequence-image-stages .sequence-stage').count(),4);
 await page.locator('nav[aria-label="Main"] a[href="#health"]').click();
 await page.locator('#crop-photo').setInputFiles(path.join(ROOT,'APP/prototype/assets/brown-spot-real.jpg'));
 await page.locator('#prepare-screening').click();await page.locator('#image-result').waitFor({state:'visible'});
 assert.equal(await page.locator('.health-score-track').count(),10);
 await page.locator('nav[aria-label="Main"] a[href="#architecture"]').click();
 await page.getByRole('tab',{name:/Disease/}).click();
 assert.equal(await page.locator('[data-image-stage]').count(),14);
 for(let i=0;i<14;i++){await page.locator('[data-image-stage="'+i+'"]').click();assert.ok((await page.locator('.image-stage-inspector').innerText()).length>40);}
 await page.locator('[data-image-stage="5"]').click();
 await page.locator('.image-stage-inspector').screenshot({path:path.join(ROOT,'OTHER/sequence-ui-qa/image-stage.png')});
 await page.getByRole('tab',{name:/Yield Prediction/}).click();
 await page.getByRole('button',{name:'4. LSTM',exact:true}).click();
 assert.equal(await page.locator('#seq-stage-4 .last-sequence-run').getAttribute('open'),'');
 await page.locator('.detailed-sequence-graph').screenshot({path:path.join(ROOT,'OTHER/sequence-ui-qa/detailed-graph.png')});
 assert.deepEqual(errors,[]);
 console.log('PASS: map, CNN-LSTM output, 13 sensitivities, arithmetic, PDF export, tensor stages, exclusive tabs and ten health scores; no JS errors.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
