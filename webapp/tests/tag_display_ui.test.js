"use strict";
const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
const nodes={};class Node{constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.events={};this.classList={toggle(){}};this.value='';}append(...c){this.children.push(...c);}replaceChildren(...c){this.children=c;}setAttribute(){}addEventListener(n,f){this.events[n]=f;}}
for(const id of ['tag-display-load','tag-display-state','tag-display-summary','tag-display-preview','detail-id'])nodes[id]=new Node('div');
const context=vm.createContext({TemplateFamilies:{models:{}},CloneSubmissionGuard:class{},DetailLoadGuard:class{},DialogFocusManager:class{},DialogOperationGuard:class{},window:{EslDesigner:{create:()=>({})}},document:{getElementById:id=>nodes[id],createElement:tag=>new Node(tag)}});
vm.runInContext(fs.readFileSync(require.resolve('../static/app.js'),'utf8').replace(/bindEvents\(\);\s*loadInventory\(\);\s*navigate\(\);\s*$/,''),context);
const run=s=>vm.runInContext(s,context);
(async()=>{
assert.equal(run('typeof loadTagDisplay'),'function');
run(`state.detailTag={id:'t',mac:'92.80.88.48',staged:false};detailGuard.activeId='t';dialogOperationGuard.isBusy=()=>false;var calls=[];var resolve;api=async(path)=>{calls.push(path);return new Promise(r=>resolve=r);};`);nodes['detail-id'].value='t';
const pending=run('loadTagDisplay()');assert.equal(nodes['tag-display-load'].disabled,true);assert.equal(run('calls[0]'),'/api/tags/t/display');
run(`resolve({tag_id:'t',mac:'92.80.88.48',style_id:96,update_progress:5,native_update_progress:4,native_updated_at_ms:1791657409000,physical_screen_verified:false,preview_url:'/api/vendor/templates/96/preview?controller_id=default',read_at:'2026-10-10T12:00:00Z',updated_at_ms:0})`);await pending;
assert.match(nodes['tag-display-state'].textContent,/nie je.*fyzického displeja/);
assert.equal(nodes['tag-display-preview'].children[0].src,'/api/vendor/templates/96/preview?controller_id=default');
assert.equal(nodes['tag-display-load'].disabled,false);
const text=node=>[node.textContent||'',...(node.children||[]).map(text)].join(' ');
assert.match(text(nodes['tag-display-summary']),/Natívny prenos.*Prenos dokončený/);
assert.match(text(nodes['tag-display-summary']),/Uložené priradenie šablóny \(MMS\).*96/);
assert.match(nodes['tag-display-state'].textContent,/MMS.*nemusí.*natívn/);
const stale=run('loadTagDisplay()');run(`detailGuard.activeId='other';resolve({tag_id:'t',mac:'92.80.88.48',style_id:100,preview_url:'/wrong'})`);await stale;
assert.equal(nodes['tag-display-preview'].children[0].src,'/api/vendor/templates/96/preview?controller_id=default','stale reply never updates another tag');
console.log('PASS: read-only display request, controller source label, button locks and stale-response guard');
})().catch(e=>{console.error(e);process.exitCode=1;});
