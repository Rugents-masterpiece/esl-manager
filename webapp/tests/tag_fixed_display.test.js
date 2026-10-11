"use strict";
const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
const nodes={};class Node{constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.value='';this.disabled=false;this.dataset={};}set id(v){this._id=v;nodes[v]=this;}get id(){return this._id;}append(...c){this.children.push(...c);}replaceChildren(...c){this.children=c;}setAttribute(){}}
for(const id of ['detail-model','detail-controller','detail-router','detail-template','detail-mac','detail-label','tag-test-data'])nodes[id]=new Node('select');
const context=vm.createContext({TemplateFamilies:require('../static/template-family.js'),CloneSubmissionGuard:class{},DetailLoadGuard:class{},DialogFocusManager:class{},DialogOperationGuard:class{},window:{EslDesigner:{create:()=>({})}},document:{getElementById:id=>nodes[id],createElement:tag=>new Node(tag)}});
vm.runInContext(fs.readFileSync(require.resolve('../static/app.js'),'utf8').replace(/bindEvents\(\);\s*loadInventory\(\);\s*navigate\(\);\s*$/,''),context);
const run=s=>vm.runInContext(s,context);
assert.equal(run('typeof fixedTagDisplay'),'function','existing tags must have fixed display controls');
run(`state.detailTag={id:'t',controller_id:'c',device_model_id:'2.13EPD-BWR',width:250,height:122};fixedTagDisplay(state.detailTag);`);
assert.equal(nodes['detail-model'].disabled,true);assert.equal(nodes['detail-model'].children.length,1);assert.match(nodes['detail-model'].children[0].textContent,/250 × 122 px/);
run(`state.controllers=[{id:'c'}];state.routers=[{id:'r',controller_id:'c'}];state.templates=[{id:'good',controller_id:'c',name:'Retail',width:250,height:122,screen_type:2},{id:'wrong-size',controller_id:'c',name:'Wrong',width:296,height:128,screen_type:2},{id:'wrong-type',controller_id:'c',name:'Wrong type',width:250,height:122,screen_type:1}];dependentOptions('detail','c',state.detailTag.device_model_id,'r','good');`);
assert.equal(nodes['detail-template'].children.length,2,'only compatible template plus placeholder');assert.equal(nodes['detail-template'].children[1].textContent,'Retail · 250 × 122 px');
nodes['detail-model'].value='2.9EPD-BWR';nodes['detail-controller'].value='c';nodes['detail-router'].value='r';nodes['detail-template'].value='good';nodes['detail-mac'].value='92.80.88.48';nodes['tag-test-data'].value='{}';
assert.deepEqual(JSON.parse(run(`JSON.stringify(tagPayload('detail','tag-test-data'))`)),{controller_id:'c',router_id:'r',device_model_id:'2.13EPD-BWR',width:250,height:122,template_id:'good',mac:'92.80.88.48',label:null,test_data:{}},'DOM tampering must not change stored display dimensions');
assert.equal(run(`templateDisplayName({name:'Design',width:296,height:128})`),'Design · 296 × 128 px');
run(`fixedTagDisplay({device_model_id:null,width:800,height:480})`);assert.equal(nodes['detail-model'].disabled,true);assert.match(nodes['detail-model'].children[0].textContent,/800 × 480 px/);
console.log('PASS: immutable display UI/payload, template dimension labels, exact size/type filtering, historical display read-only');
