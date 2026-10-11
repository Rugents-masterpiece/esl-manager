"use strict";
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const nodes = {};
class Node {
  constructor(tag) { this.tagName=tag.toUpperCase(); this.children=[]; this.events={}; this.value=''; this.dataset={}; }
  set id(id) {this._id=id; nodes[id]=this;} get id(){return this._id;}
  append(...children){this.children.push(...children);} replaceChildren(...children){this.children=children;}
  setAttribute(){} addEventListener(name, fn){this.events[name]=fn;}
}
const context=vm.createContext({TemplateFamilies:{models:{}},CloneSubmissionGuard:class{},DetailLoadGuard:class{},DialogFocusManager:class{},DialogOperationGuard:class{},window:{EslDesigner:{create:()=>({})}},document:{getElementById:id=>nodes[id],createElement:tag=>new Node(tag)}});
const source=fs.readFileSync(require.resolve('../static/app.js'),'utf8').replace(/bindEvents\(\);\s*loadInventory\(\);\s*navigate\(\);\s*$/,'');
vm.runInContext(source,context);
const run=code=>vm.runInContext(code,context);
for(const id of ['tag-content-fields','tag-test-data','detail-template']) {nodes[id]=new Node('div');}
run(`state.detailTag={controller_id:'c',device_model_id:'m',management_supported:true};
state.templates=[{id:'t',controller_id:'c',vendor_id:10}];
state.publications=[{controller_id:'c',vendor_id:10,model_id:'m',bindings:{a:{field:'Name'},b:{field:'Price'},c:{field:'Price'},d:{field:'Enabled'},fixed:{field:''}}}];`);
nodes['detail-template'].value='t';
nodes['tag-test-data'].value=JSON.stringify({Name:'Žemľa',Price:0,Enabled:false,Extra:'preserve'});
assert.equal(run('typeof renderTagContentFields'),'function','editable content form must exist');
run('renderTagContentFields()');
assert.equal(nodes['tag-content-fields'].children.length,3,'one input per dynamic field, no static/demo values');
nodes['tag-content-0'].value='Chlieb <b>'; nodes['tag-content-0'].events.input();
nodes['tag-content-1'].value='1.25'; nodes['tag-content-1'].events.input();
nodes['tag-content-2'].value='true'; nodes['tag-content-2'].events.input();
assert.deepEqual(JSON.parse(nodes['tag-test-data'].value),{Name:'Chlieb <b>',Price:1.25,Enabled:true,Extra:'preserve'});
nodes['tag-test-data'].value='{'; run('renderTagContentFields()');
assert.equal(nodes['tag-content-fields'].children.length,1,'invalid JSON produces an explanatory message, never overwrites it');
assert.equal(nodes['tag-test-data'].value,'{');
nodes['tag-test-data'].value='{}'; run('renderTagContentFields()');
assert.equal(nodes['tag-content-0'].value,'','missing values must not be filled with sample data');
assert.equal(nodes['tag-content-0'].required,true);
console.log('PASS: content fields, typed scalar edits, preserved extras, invalid JSON, no samples');
