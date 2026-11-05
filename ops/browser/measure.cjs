const {chromium} = require('playwright');
const fs = require('fs');
const crypto = require('crypto');
const [base, output, phase, countText = '10'] = process.argv.slice(2);
const write = row => fs.appendFileSync(output, JSON.stringify(row) + '\n', 'utf8');
const ready = async page => {
  await page.waitForFunction(() => document.querySelectorAll('.herb-row').length === 601 && document.querySelector('h1')?.textContent.includes('괴화'), {timeout: 20000});
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
};
(async () => {
 const browser = await chromium.launch({headless:true});
 let failures=0;
 try {
  for (let i=0;i<Number(countText);i++) {
   const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'ko-KR'});
   const page=await context.newPage();
   page.setDefaultTimeout(20000);
   const row={phase,sample:i,started_at:new Date().toISOString(),browser:browser.version(),playwright:require('playwright/package.json').version,ok:false,checks:{},errors:[]};
   page.on('pageerror',e=>row.errors.push(e.message));
   try {
    // Fresh context per sample: browser HTTP cache and localStorage are cold.
    const begin=performance.now();
    const response=await page.goto(base+'/?herb=sophorae-flos',{waitUntil:'load'});
    if(response.status()!==200)throw Error('Page HTTP '+response.status());
    await ready(page);
    row.initial_ready_ms=performance.now()-begin;
    row.navigation=await page.evaluate(()=>{const n=performance.getEntriesByType('navigation')[0];return {load_ms:n.loadEventEnd,dom_content_loaded_ms:n.domContentLoadedEventEnd};});
    const dataResponse=await context.request.get(base+'/herbs.json');
    const records=await dataResponse.json();
    row.data_sha256=crypto.createHash('sha256').update(JSON.stringify(records)).digest('hex');
    row.deployment_sha=(await (await context.request.get(base+'/api/health')).json()).deployment_sha||null;
    row.checks.sophora=(await page.locator('h1').innerText()).includes('괴화') && (await page.locator('#basic').innerText()).includes('회화나무');
    if(!row.checks.sophora)throw Error('Sophora detail not rendered');
    await page.evaluate(()=>{
      window.__searchTiming=null;
      document.querySelector('#search').addEventListener('input',()=>{
        const start=performance.now();
        requestAnimationFrame(()=>requestAnimationFrame(()=>window.__searchTiming=performance.now()-start));
      },{once:true,capture:true});
    });
    await page.locator('#search').fill('감초');
    await page.waitForFunction(()=>window.__searchTiming!==null);
    row.search_ms=await page.evaluate(()=>window.__searchTiming);
    const expected=records.filter(r=>[r.name,r.hanja,r.english,r.latin,r.plant,...(r.detail?.aliases||[]).map(a=>a.value)].join(' ').toLowerCase().includes('감초')).map(r=>r.name+' '+r.hanja);
    const actual=await page.locator('.herb-row strong').allTextContents();
    row.checks.search=expected.length>0 && JSON.stringify(expected)===JSON.stringify(actual);
    if(!row.checks.search)throw Error('Search result mismatch');
    await page.locator('#search').fill('괴화');
    await page.locator('.herb-row').filter({hasText:'괴화'}).first().click();
    if(!(await page.locator('h1').innerText()).includes('괴화'))throw Error('Detail navigation failed');
    await page.locator('#bookmark').click();
    await page.reload({waitUntil:'load'});
    await ready(page);
    row.checks.bookmark_reload=await page.locator('#bookmark').getAttribute('aria-pressed')==='true';
    if(!row.checks.bookmark_reload)throw Error('Bookmark did not survive reload');
    row.ok=row.errors.length===0;
    if(!row.ok)throw Error('Browser console errors');
   } catch(e) {row.errors.push(String(e));failures++;}
   finally {
    row.ended_at=new Date().toISOString();write(row);
    if(i===0)await page.screenshot({path:output+'.'+phase+'.png'}).catch(()=>{});
    await context.close();
   }
  }
 } finally {await browser.close();}
 if(failures)process.exitCode=1;
})().catch(e=>{write({phase,ok:false,fatal:String(e),ended_at:new Date().toISOString()});process.exitCode=1;});
