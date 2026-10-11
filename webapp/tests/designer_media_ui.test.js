"use strict";
// DOM-free editor integration: exercise real controller/import state machine.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../static/designer-model.js'),Media=require('../static/designer-media.js');
class Node {
  constructor(tag){this.tagName=tag;this.children=[];this.listeners={};this.style={};this.dataset={};this.attributes={};this.value='';this.maxLength=-1;this.classList={add:()=>{},toggle:()=>{}};}
  append(...nodes){this.children.push(...nodes);}
  prepend(...nodes){this.children.unshift(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attributes[k]=v;}
  addEventListener(k,v){(this.listeners[k]??=[]).push(v);}
  contains(n){return this===n||this.children.some(c=>c.contains(n));}
  get selectedOptions(){return this.children.filter(c=>c.value===this.value);}
  setCustomValidity(){}
  async fire(type,event={}){for(const fn of this.listeners[type]||[])await fn({target:this,...event});await tick();}
}
const tick=()=>new Promise(r=>setImmediate(r));
const root=new Node('div'),unloads=[],confirms=[],calls=[];
let responseWarnings=['Prvok bol posunutý o 5 px.'],sourceResolve=null;
const initialSources=[{id:'145',name:'Source',width:250,height:122,screen_type:'BWR',supported:true},{id:'146',name:'Unknown',width:123,height:88,screen_type:'?',supported:false},{id:'147',name:'Missing compatibility',width:250,height:122,screen_type:'?'}];
let sourceItems=initialSources;
const copied=M.add(M.createDocument('Imported'), 'text');
async function api(path,options={}){
  calls.push({path,options});
  if(path==='/api/controllers')return {items:[{id:'legacy',name:'Legacy'},{id:'main',name:'Controller'}]};
  if(path==='/api/template-drafts')return {items:[]};
  if(path==='/api/template-draft-sources?controller_id=main')return {controller_id:'main',items:sourceItems};
  if(path==='/api/template-draft-sources/145?controller_id=main'){
    if(sourceResolve)await new Promise(resolve=>sourceResolve(resolve));
    return {document:copied,warnings:responseWarnings,source:{id:'145',controller_id:'main',name:'Source'}};
  }
  throw new Error('unexpected '+path);
}
const window={EslDesignerModel:M,EslDesignerMedia:Media,confirm:t=>{confirms.push(t);return answers.shift()??false;},addEventListener:(k,v)=>{if(k==='beforeunload')unloads.push(v);}};
const answers=[];
const context={window,document:{createElement:t=>new Node(t),createElementNS:(_,t)=>new Node(t),getElementById:()=>root},Promise,setTimeout,URL,Blob,console};
vm.createContext(context);vm.runInContext(fs.readFileSync(require.resolve('../static/designer.js'),'utf8'),context);
const editor=window.EslDesigner.create({api,notify:()=>{},root});
function all(n=root){return [n,...n.children.flatMap(c=>all(c))];}
function text(t){const n=all().find(n=>n.textContent===t);assert.ok(n,'find '+t);return n;}
function control(label){const l=text(label);return all().find(n=>n.id===l.htmlFor);}
async function click(label){await text(label).fire('click');}
(async()=>{
  editor.show();await tick();await tick();
  const controller=control('Controller');assert.equal(controller.children.some(n=>n.value==='legacy'),false);
  controller.value='main';await controller.fire('change');
  const source=control('Zdrojová šablóna');assert.deepEqual(source.children.map(n=>n.value),['','145'],'only explicitly supported sources are visible');
  sourceItems=initialSources.slice(1);await click('Obnoviť zdroje');
  assert.deepEqual(source.children.map(n=>n.value),['']);
  assert.equal(source.children[0].textContent,'Controller nemá šablóny pre podporované modely');
  assert.equal(text('Načítať kópiu').disabled,true);
  sourceItems=[];await click('Obnoviť zdroje');
  assert.equal(source.children[0].textContent,'Controller nemá šablóny pre podporované modely');
  sourceItems=initialSources;await click('Obnoviť zdroje');
  source.value='145';await source.fire('change');
  // Uncommitted input must survive warning cancellation and pending guard.
  const name=control('Názov šablóny');name.value='Typed but uncommitted';await root.fire('input',{target:name});assert.equal(editor.isDirty(),true);
  answers.push(true,false);await click('Načítať kópiu');
  assert.equal(name.value,'Typed but uncommitted');assert.equal(editor.isDirty(),true);assert.match(confirms.at(-1),/5 px/);
  let prevented=false;unloads[0]({preventDefault(){prevented=true;}});assert.equal(prevented,true);
  // Pending import disallows edits and navigation even for a clean canonical doc.
  let release;sourceResolve=resolve=>{release=resolve;};answers.push(true,true);
  await click('Načítať kópiu');assert.equal(editor.canLeave(),false);assert.equal(all().find(n=>n.tagName==='fieldset').disabled,true);
  release();await tick();await tick();sourceResolve=null;
  assert.equal(name.value,'Imported');assert.equal(editor.isDirty(),true);assert.equal(all().find(n=>n.tagName==='fieldset').disabled,false);
  assert.equal(text('Zmazať návrh').disabled,true,'import must not retain saved draft identity');
  assert.equal(calls.some(c=>c.options.method),false,'source loading must issue only GETs');
  // All media are editable and image upload affordances are scoped to image.
  await click('+ Obrázok');assert.ok(control('Nahrať obrázok'));assert.equal(control('Prispôsobenie obrázka').value,'contain');
  const type=control('Typ');type.value='qrcode';await type.fire('change');assert.ok(control('Korekcia QR chýb'));assert.equal(text('Uložiť návrh').disabled,true,'empty/invalid QR cannot save');
  console.log('designer media/source UI pending/dirty/warning guards: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
