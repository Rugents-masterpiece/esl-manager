"use strict";
const assert=require('node:assert/strict'), M=require('../static/designer-model.js');
for(const key of ['价格','商品名','pozadie názvu','kod položky','test ','a.b','__proto__','constructor','toString','😀'.repeat(100)]) {
  const doc=M.add(M.createDocument(),'text');doc.schema_version=2;doc.elements[0].field=key;
  doc.sample_data=JSON.parse(JSON.stringify({[key]:'hodnota'}));
  assert.deepEqual(M.validate(doc),[],`literal native key: ${key}`);
  assert.equal(M.renderText(doc.elements[0],doc.sample_data),'hodnota');
  const cloned=M.clone(doc);assert.deepEqual(cloned,doc);assert.equal(Object.getPrototypeOf(cloned.sample_data),Object.prototype);
  delete cloned.sample_data[key];assert.equal(M.renderText(cloned.elements[0],cloned.sample_data),'Názov produktu','inherited prototype properties are never bindings');
}
for(const [version,keys] of [[1,['价格','kod položky','a.b','x'.repeat(65)]],[2,['x'.repeat(101),'😀'.repeat(101),'bad\n','bad\x00','bad\x7f','bad\x85','\ud800']]]) {
  for(const key of keys)for(const place of ['field','sample']) {
    const doc=M.add(M.createDocument(),'text');doc.schema_version=version;
    if(place==='field')doc.elements[0].field=key;else doc.sample_data={[key]:'value'};
    assert.ok(M.validate(doc).length,`invalid ${version}/${place}/${JSON.stringify(key)}`);
  }
}
const doc=M.add(M.createDocument(),'text');doc.schema_version=2;assert.deepEqual(M.validate(doc),[]);
doc.sample_data={'':'value'};assert.ok(M.validate(doc).length);
console.log('designer v1/v2 literal fields, Unicode and prototype safety: PASS');
for(const type of ['text','image'])for(const name of ['a'.repeat(191)+'😀','😀'.repeat(200)]) {
  const original=M.add(M.createDocument(),type);original.elements[0].name=name;
  const copied=M.duplicate(original,original.elements[0].id);
  assert.equal(copied.elements[1].name,Array.from(name).slice(0,192).join('')+' — kópia','duplicate truncates code points, not UTF-16 surrogate halves');
  assert.deepEqual(M.validate(copied),[]);
}
console.log('designer duplicate Unicode name boundaries: PASS');
