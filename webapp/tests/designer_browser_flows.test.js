"use strict";
// A real Chromium flow against a disposable local database, never live hardware.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = process.env.ESL_BROWSER_BASE, cdp = process.env.ESL_BROWSER_CDP;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  assert.ok(base && cdp, "Run via Python BrowserDomIntegrationTests (provides local fixture and Chromium)");
  const watchdog = setTimeout(() => { console.error("designer browser watchdog"); process.exit(2); }, 25000);
  const target = await (await fetch(`${cdp}/json/new?about:blank`, {method:"PUT"})).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let sequence = 0;
  const pending = new Map(), errors = [];
  ws.onmessage = event => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) { const cb=pending.get(msg.id); pending.delete(msg.id); msg.error?cb.reject(msg.error):cb.resolve(msg.result); }
    else if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params);
  };
  await new Promise((resolve,reject) => { ws.onopen=resolve; ws.onerror=reject; });
  const call = (method,params={}) => new Promise((resolve,reject)=>{const id=++sequence; pending.set(id,{resolve,reject}); ws.send(JSON.stringify({id,method,params}));});
  const evaluate = async expression => { const r=await call("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true}); if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value; };
  const wait = async expr => { for(let i=0;i<160;i++){ try {if(await evaluate(expr)) return;} catch(_){} await delay(25); } throw new Error(`Timed out: ${expr}`); };
  const button = name => `[...document.querySelectorAll('#view-designer button')].find(b=>b.textContent===${JSON.stringify(name)})`;
  const input = label => `document.getElementById([...document.querySelectorAll('#view-designer label')].find(l=>l.textContent===${JSON.stringify(label)}).htmlFor)`;
  const box = async expr => evaluate(`(()=>{const n=(${expr}); if(!n) throw new Error('Missing target'); n.scrollIntoView({block:'center',inline:'center'}); const r=n.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
  const click = async expr => {const {x,y}=await box(expr); await call("Input.dispatchMouseEvent",{type:"mousePressed",x,y,button:"left",clickCount:1}); await call("Input.dispatchMouseEvent",{type:"mouseReleased",x,y,button:"left",clickCount:1});};
  const change = (label,value) => evaluate(`(()=>{const n=(${input(label)}); n.value=${JSON.stringify(value)}; n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  const count = () => evaluate("document.querySelectorAll('.designer-object').length");
  const artifact = path.resolve("test-artifacts/designer-browser"); fs.mkdirSync(artifact,{recursive:true});
  const download = path.join(artifact,"esl-template.json"); if(fs.existsSync(download)) fs.unlinkSync(download);
  await call("Page.enable"); await call("Runtime.enable");
  await call("Emulation.setDeviceMetricsOverride",{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await call("Page.navigate",{url:base+"/#designer"});
  await wait("document.querySelector('#view-designer') && !document.querySelector('#view-designer').hidden && document.querySelector('.designer-stage') && document.querySelector('#app-status').textContent==='API pripojené' && !document.querySelector('.designer-controls').disabled");
  await change("Názov šablóny","Browser návrh");
  await click(button("+ Čiara"));
  await change("Šírka (px)","100");
  await change("Výška (px)","101");
  const segment=await evaluate(`(() => {
    const line=document.querySelector('.designer-object svg line');
    if(!line) return null;
    return ['x1','y1','x2','y2','stroke-width'].map(key=>Number(line.getAttribute(key)));
  })()`);
  assert.deepEqual(segment,[0.5,0.5,99.5,100.5,1],"line reaches its configured box");
  await change("Hrúbka čiary (px)","0");
  assert.equal(await evaluate("document.querySelector('.designer-object svg line').getAttribute('stroke-width')"),"0");
  await click(button("Zmazať"));
  await click(button("+ Text"));
  assert.equal(await count(),1);
  await change("Názov prvku","Cena");
  await change("Text / náhradná hodnota","9,99");
  await change("Dátové pole","price");
  await change("Dátové pole","invalid.field");
  assert.equal(await evaluate(`${button("Uložiť návrh")}.disabled`),true,
    "invalid visible property must block saving the old hidden value");
  await change("Dátové pole","price");
  await change("Prípona"," €");
  await change('JSON objekt (napr. {"price": "1,99"})','{"price":"2,49"}');
  assert.equal(await evaluate("document.querySelector('.designer-object').textContent"),"2,49 €");
  // Real drag at 200% zoom followed by keyboard movement.
  const rawJson='{"price":"partially typed';
  await change('JSON objekt (napr. {"price": "1,99"})',rawJson);
  await click(button("Späť"));
  assert.equal(await evaluate(`${input('JSON objekt (napr. {"price": "1,99"})')}.value`),rawJson);
  await click(button("Znova"));
  assert.equal(await evaluate(`${input('JSON objekt (napr. {"price": "1,99"})')}.value`),rawJson);
  await change('JSON objekt (napr. {"price": "1,99"})','{"price":"2,49"}');

  const layout = await evaluate("getComputedStyle(document.querySelector('.designer-workspace')).display");
  assert.equal(layout, "grid", "editor CSS is active");
  let position=await box("document.querySelector('.designer-object')");
  await call("Input.dispatchMouseEvent",{type:"mousePressed",...position,button:"left",clickCount:1});
  await call("Input.dispatchMouseEvent",{type:"mouseMoved",x:position.x+20,y:position.y+10,button:"left",buttons:1});
  await call("Input.dispatchMouseEvent",{type:"mouseReleased",x:position.x+20,y:position.y+10,button:"left",clickCount:1});
  assert.equal(await evaluate(`${input("X (px)")}.value`),"18");
  assert.equal(await evaluate(`${input("Y (px)")}.value`),"13");
  await call("Input.dispatchKeyEvent",{type:"keyDown",key:"ArrowRight",code:"ArrowRight"});
  await call("Input.dispatchKeyEvent",{type:"keyUp",key:"ArrowRight",code:"ArrowRight"});
  assert.equal(await evaluate(`${input("X (px)")}.value`),"19");
  await click(button("Späť")); assert.equal(await evaluate(`${input("X (px)")}.value`),"18");
  await click(button("Znova")); assert.equal(await evaluate(`${input("X (px)")}.value`),"19");
  const held=await box("document.querySelector('.designer-object')");
  await call("Input.dispatchMouseEvent",{type:"mousePressed",...held,button:"left",clickCount:1});
  await call("Input.dispatchMouseEvent",{type:"mouseMoved",x:held.x+4,y:held.y+4,button:"left",buttons:1});
  await call("Input.dispatchKeyEvent",{type:"keyDown",key:"Delete",code:"Delete"});
  await call("Input.dispatchMouseEvent",{type:"mouseReleased",...held,button:"left",clickCount:1});
  assert.equal(await evaluate("document.querySelectorAll('.designer-object').length"),0,"drag must not resurrect deleted elements");
  await click(button("Späť"));
  await click("document.querySelector('.designer-layer')");
  await click(button("Duplikovať")); assert.equal(await count(),2);
  await click(button("Zmazať")); assert.equal(await count(),1);
  // Re-select retained text using layer button and save via 401/login UI.
  await click("document.querySelector('.designer-layer')");
  await click(button("Uložiť návrh"));
  await wait("document.querySelector('#auth-modal').open");
  await evaluate("document.querySelector('#auth-token').value='A'.repeat(64)");
  await click("document.querySelector('#auth-submit')");
  await wait("!document.querySelector('#auth-modal').open");
  assert.equal(await evaluate("document.querySelector('#auth-token').value"),"");
  // Hold one POST response; repeated real clicks must not issue extra writes.
  await evaluate(`(()=>{window.__realFetch=window.fetch.bind(window); window.__posts=0; window.fetch=(url,opts={})=>{const response=window.__realFetch(url,opts); if(url==='/api/template-drafts'&&opts.method==='POST'){window.__posts++;return new Promise((res,rej)=>{window.__release=()=>response.then(res,rej);});} return response;};})()`);
  await click(button("Uložiť návrh"));
  await wait("window.__release && document.querySelector('.designer-controls').disabled");
  const savePoint=await box("document.querySelector('.designer-actions .button-primary')");
  for(let i=0;i<2;i++){await call("Input.dispatchMouseEvent",{type:"mousePressed",...savePoint,button:"left",clickCount:1});await call("Input.dispatchMouseEvent",{type:"mouseReleased",...savePoint,button:"left",clickCount:1});}
  assert.equal(await evaluate("window.__posts"),1);

  await evaluate("window.__release()");
  await wait("document.querySelector('#designer-root .state-message').textContent.includes('uložený a overený') && !document.querySelector('.designer-controls').disabled");
  await evaluate("window.fetch=window.__realFetch");
  const listed=await evaluate("fetch('/api/template-drafts').then(r=>r.json())");
  assert.equal(listed.items.length,1);
  const saved=listed.items[0]; assert.equal(saved.revision,1); assert.equal(saved.document.elements[0].x,19); assert.equal(saved.document.elements[0].field,"price");
  // Undo local change then reload actual persisted state.
  const protectsRawInput = await evaluate(`(() => {
    const field=${input("Názov šablóny")}; field.value='Rozpísaný názov';
    field.dispatchEvent(new Event('input',{bubbles:true}));
    const event=new Event('beforeunload',{cancelable:true}); window.dispatchEvent(event);
    return event.defaultPrevented;
  })()`);
  assert.equal(protectsRawInput,true,"unblurred edits of saved drafts must be protected");
  await change("Názov šablóny","Browser návrh");
  await change("X (px)","22");
  // Accept the dirty confirmation after clicking reload, without waiting for dialog-blocked evaluation.
  ws.addEventListener("message",event=>{const msg=JSON.parse(event.data);if(msg.method==='Page.javascriptDialogOpening') call('Page.handleJavaScriptDialog',{accept:true});});
  await click(button("Znovu načítať"));
  await wait("document.querySelector('#designer-root .state-message').textContent.includes('Načítaná revízia') && !document.querySelector('.designer-controls').disabled");
  // Reload clears selection; choose retained element.
  await click("document.querySelector('.designer-layer')");
  assert.equal(await evaluate(`${input("X (px)")}.value`),"19");
  // Export actual downloaded JSON and import through a real file input.
  await call("Browser.setDownloadBehavior",{behavior:"allow",downloadPath:artifact});
  await click(button("Export JSON"));
  for(let i=0;i<80&&!fs.existsSync(download);i++) await delay(25);
  assert.ok(fs.existsSync(download),"export must create a downloadable JSON file");
  assert.deepEqual(JSON.parse(fs.readFileSync(download,"utf8")),saved.document);
  const importFile=path.join(artifact,"import.json");
  fs.writeFileSync(importFile,JSON.stringify({...saved.document,name:"Importovaný návrh"}));
  const {root}=await call("DOM.getDocument");
  const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#designer-root input[type=file]"});
  await call("DOM.setFileInputFiles",{nodeId,files:[importFile]});
  await wait(`${input("Názov šablóny")}.value==='Importovaný návrh'`);
  await click(button("Uložiť návrh"));
  await wait("document.querySelector('#designer-root .state-message').textContent.includes('uložený a overený') && !document.querySelector('.designer-controls').disabled");
  const reloaded=await evaluate("fetch('/api/template-drafts').then(r=>r.json())");
  assert.equal(reloaded.items.length,2);
  // Desktop/mobile screenshots and document-overflow contract.
  // A backend-valid draft must also load/edit/save at Unicode code-point limits.
  const unicode=await evaluate(`(async()=>{
    const doc=EslDesignerModel.add(EslDesignerModel.createDocument('😀'.repeat(200)),'text');
    doc.elements[0].id='😀'.repeat(64); doc.elements[0].name='😀'.repeat(200);
    doc.elements[0].text='😀'.repeat(2000); doc.sample_data={code:'😀'.repeat(2000)};
    const response=await fetch('/api/template-drafts',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(doc)});
    if(response.status!==201) throw new Error('Unicode draft create failed');
    return response.json();
  })()`);
  await click(button("Obnoviť zoznam"));
  await wait(`${input("Uložené lokálne návrhy")}.querySelector('option[value="${unicode.id}"]')`);
  await change("Uložené lokálne návrhy",unicode.id);
  await click(button("Načítať"));
  await wait(`${input("Názov šablóny")}.value===${JSON.stringify(unicode.document.name)}`);
  await click("document.querySelector('.designer-layer')");
  const nameCapacity=await evaluate(`${input("Názov šablóny")}.maxLength`);
  const textCapacity=await evaluate(`${input("Text / náhradná hodnota")}.maxLength`);
  assert.ok(nameCapacity<0 || nameCapacity>=unicode.document.name.length,"native input must allow a valid Unicode name");
  assert.ok(textCapacity<0 || textCapacity>=unicode.document.elements[0].text.length,"native textarea must allow valid Unicode text");
  const unicodeName='😀'.repeat(199)+'A', unicodeText='😀'.repeat(1999)+'X';
  await change("Názov šablóny",unicodeName);
  await change("Text / náhradná hodnota",unicodeText);
  await click(button("Uložiť návrh"));
  await wait("document.querySelector('#designer-root .state-message').textContent.includes('uložený a overený') && !document.querySelector('.designer-controls').disabled");
  const unicodeSaved=await evaluate(`fetch('/api/template-drafts/${unicode.id}').then(r=>r.json())`);
  assert.equal(unicodeSaved.document.name,unicodeName);
  assert.equal(unicodeSaved.document.elements[0].text,unicodeText);
  const normal=reloaded.items.find(item=>item.document.name==='Importovaný návrh');
  await change("Uložené lokálne návrhy",normal.id);
  await click(button("Načítať"));
  await wait(`${input("Názov šablóny")}.value==='Importovaný návrh'`);
  await click("document.querySelector('.designer-layer')");
  await evaluate("document.activeElement.blur(); window.scrollTo(0,0); new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))");
  const desktop=await call("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});
  fs.writeFileSync(path.join(artifact,"desktop.png"),Buffer.from(desktop.data,"base64"));
  await call("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate("window.scrollTo(0,0); new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))");
  await wait("document.querySelector('#primary-nav').getBoundingClientRect().right<=0");
  assert.equal(await evaluate("document.documentElement.scrollWidth<=window.innerWidth"),true,"mobile page must not overflow horizontally");
  const mobile=await call("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});
  fs.writeFileSync(path.join(artifact,"mobile.png"),Buffer.from(mobile.data,"base64"));
  assert.deepEqual(errors,[],"no uncaught runtime exceptions");
  const finalDraftCount=await evaluate("fetch('/api/template-drafts').then(r=>r.json()).then(v=>v.items.length)");
  console.log(JSON.stringify({designer:"PASS",drag_keyboard_history:"PASS",authentication:"PASS",save_readback:"PASS",duplicate_post_prevention:"PASS",import_export:"PASS",unicode:"PASS",mobile:"PASS",draft_count:finalDraftCount,artifacts:artifact}));
  await call("Page.close"); ws.close(); clearTimeout(watchdog);
})().catch(error=>{console.error(error);process.exit(1);});
