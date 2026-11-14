const {chromium}=require(process.env.TEMP+'/ask-grandpa-qa-tools/node_modules/playwright');
const fs=require('fs'); const path=require('path'); const out=__dirname; const marker='QA-GOV-20261114';
const results=[]; const net=[]; const tokens={}; const created=[]; let browser;
function record(name,pass,detail){results.push({name,pass,detail}); console.log(JSON.stringify(results.at(-1)));fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({results,net,created},null,2));}
(async()=>{browser=await chromium.launch({executablePath:process.env.LOCALAPPDATA+'/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-win64/chrome-headless-shell.exe',headless:true});
const contexts={}; const pages={};
for(const [role,user] of Object.entries({senior:'u_expert',junior:'u_successor',intern:'u_outsider'})){
const c=await browser.newContext({viewport:{width:1440,height:1000}});contexts[role]=c; await c.addInitScript(u=>localStorage.setItem('handover_user',u),user);const p=await c.newPage();p.setDefaultNavigationTimeout(90000);pages[role]=p;
p.on('response',async r=>{const u=new URL(r.url());if(u.port!=='8000')return;net.push({role,path:u.pathname,status:r.status()});if(u.pathname==='/login'&&r.ok()){const j=await r.json();tokens[role]=j.token;}});
p.on('request',r=>{if(new URL(r.url()).port==='8000'&&r.headers().authorization)tokens[role]=r.headers().authorization.replace('Bearer ','');});
p.on('pageerror',e=>record(role+' pageerror',false,e.message)); await p.goto('http://localhost:3000/knows',{waitUntil:'domcontentloaded'}); await p.getByRole('heading',{name:'Desk ledger'}).waitFor();}
const p=pages.senior;
async function api(role,route,method='GET',body){const r=await contexts[role].request.fetch('http://localhost:8000'+route,{method,headers:{Authorization:'Bearer '+tokens[role]},...(body?{data:body}:{})});return {status:r.status(),body:await r.json()};}
for(let i=0;i<30&&!tokens.senior;i++)await p.waitForTimeout(500);await p.waitForTimeout(2000); const baseline=await api('senior','/gaps?owner_id=u_expert');
created.push(...JSON.parse(fs.readFileSync(path.join(out,'created.json'),'utf8'))); const loaded=await api('senior','/memories?owner_id=u_expert'); if(loaded.status!==200)throw new Error('Memory API '+JSON.stringify(loaded));const all=loaded.body; const target=all.find(m=>created.includes(m.id)&&m.kind==='procedure'&&m.status==='active'); if(!target)throw new Error('QA procedure missing'); let current=target.id; let row;
await p.goto('http://localhost:3000/under-the-hood',{waitUntil:'domcontentloaded'}); await p.locator('li').filter({hasText:target.text}).first().waitFor();
const getRow=()=>p.locator('li').filter({has:p.getByText(current,{exact:true})});row=getRow();
for(const scope of ['team','successor','never_transfer','team']){const pending=p.waitForResponse(r=>r.url().includes('/'+current+'/scope')&&r.request().method()==='PATCH');await row.getByLabel('Scope',{exact:true}).selectOption(scope);const r=await pending;await r.finished();await p.waitForTimeout(1300);const visibility={};for(const role of ['senior','junior','intern']){const ms=await api(role,'/memories?owner_id=u_expert');visibility[role]=ms.body.some(m=>m.id===current);}record('Scope '+scope+' enforces isolated-role visibility',r.ok()&&visibility.senior&&visibility.junior===(scope!=='never_transfer')&&visibility.intern===(scope==='team'),visibility);}
await pages.junior.goto('http://localhost:3000/under-the-hood',{waitUntil:'domcontentloaded'});await pages.intern.goto('http://localhost:3000/under-the-hood',{waitUntil:'domcontentloaded'});await p.screenshot({path:path.join(out,'02-scope-team.png')});
const rbBefore=await api('junior','/runbook');const step=rbBefore.body.find(s=>s.derived_from.includes(current));record('Interview procedure generates inherited runbook step',!!step,{step});
await row.getByRole('button',{name:'Correct',exact:true}).click();await row.getByRole('textbox',{name:'Corrected memory text'}).fill('');record('Empty correction cannot save',await row.getByRole('button',{name:/Save as/}).isDisabled(),{});
await row.getByRole('textbox',{name:'Corrected memory text'}).fill(marker+' CORRECTED synthetic QA training procedure: reconcile only the QA sandbox ledger total 947 and ask the QA duty manager to sign the training checklist. Never use for real payments.');const cp=p.waitForResponse(r=>r.url().includes('/'+current+'/correct')&&r.request().method()==='POST');await row.getByRole('button',{name:/Save as/}).click();const cr=await cp;const cj=await cr.json();record('Correct creates v2 and supersedes v1',cr.ok()&&cj.new?.version===2&&cj.old?.status==='corrected',cj);if(!cr.ok())throw new Error('Correction failed');current=cj.new.id;created.push(current);fs.writeFileSync(path.join(out,'created.json'),JSON.stringify(created));row=getRow();await p.waitForTimeout(1800);
const rbAfter=await api('junior','/runbook');record('Correction flags dependent runbook for review',!!rbAfter.body.find(s=>s.id===step?.id&&s.status==='needs_review'&&s.derived_from.includes(current)),{steps:rbAfter.body.filter(s=>s.derived_from.includes(current))});await p.screenshot({path:path.join(out,'03-corrected.png')});
const juniorVisible=pages.junior.locator('li').filter({hasText:marker});record('Junior receives correction live without refresh',(await juniorVisible.allTextContents()).some(t=>t.includes('947')),{texts:await juniorVisible.allTextContents()});
const forbidden=await api('intern','/memories/'+current+'/scope','PATCH',{scope:'never_transfer'});record('Nonowner cannot govern QA memory',forbidden.status===403,{status:forbidden.status});
await row.getByRole('button',{name:'Forget',exact:true}).click();await row.getByRole('button',{name:'No',exact:true}).click();record('Forget cancellation retains memory',!!(await api('senior','/memories?owner_id=u_expert')).body.find(m=>m.id===current&&m.status==='active'),{});
await row.getByRole('button',{name:'Forget',exact:true}).click();const fp=p.waitForResponse(r=>r.url().includes('/'+current+'/forget')&&r.request().method()==='POST');await row.getByRole('button',{name:'Yes',exact:true}).click();const fr=await fp;const fj=await fr.json();record('Forget cascades through both versions and runbook',fr.ok()&&fj.forgotten_ids.includes(target.id)&&fj.forgotten_ids.includes(current)&&fj.runbook_steps_removed.includes(step?.id),fj);for(let i=0;i<30&&!tokens.senior;i++)await p.waitForTimeout(500);await p.waitForTimeout(2000);
record('Junior live memory/runbook removed without refresh',!(await pages.junior.locator('li').allTextContents()).some(t=>t.includes(marker)),{});await pages.junior.screenshot({path:path.join(out,'04-junior-after-forget.png')});
for(const id of created){const ms=await api('senior','/memories?owner_id=u_expert');const m=ms.body.find(m=>m.id===id);if(m&&m.status!=='forgotten')record('Cleanup '+id,(await api('senior','/memories/'+id+'/forget','POST')).status===200,{});}
const after=await api('senior','/gaps?owner_id=u_expert');record('Original gaps unchanged',JSON.stringify(baseline.body)===JSON.stringify(after.body),{before:baseline.body,after:after.body});
record('Cleanup confirms no active QA memories',(await api('senior','/memories?owner_id=u_expert')).body.filter(m=>created.includes(m.id)&&m.status==='active').length===0,{tombstones:created});
})().catch(e=>record('RUN BLOCKER',false,{message:e.message,stack:e.stack})).finally(async()=>{fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({results,net,created},null,2));await browser?.close();});







