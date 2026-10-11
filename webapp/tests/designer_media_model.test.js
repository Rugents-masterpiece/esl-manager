"use strict";
const assert = require('node:assert/strict');
const M = require('../static/designer-model.js');
const extras = {image:{image_data:'',image_fit:'contain'},barcode:{barcode_format:'CODE128'},qrcode:{error_correction:'M'}};
for (const model of Object.keys(M.models)) {
  for (const type of Object.keys(extras)) {
    const original=M.createDocument('Media',model), doc=M.add(original,type), e=doc.elements[0];
    assert.equal(original.schema_version,1);
    assert.equal(doc.schema_version,2);
    assert.deepEqual(M.validate(doc),[]);
    assert.equal(e.background,'#ffffff'); assert.equal(e.color,'#000000');
    assert.equal(e.width,type==='barcode'?200:80);
    assert.equal(e.height,type==='barcode'?48:type==='image'?60:80);
    assert.equal(e.text,type==='barcode'?'123456789012':type==='qrcode'?'https://example.com':'');
    for(const [key,value] of Object.entries(extras[type])) assert.equal(e[key],value);
    assert.ok(M.validate({...doc,schema_version:1}).length);
    for(const key of Object.keys(extras[type])) { const bad=M.clone(doc); delete bad.elements[0][key]; assert.ok(M.validate(bad).length); }
    const bad=M.clone(doc); bad.elements[0].irrelevant=''; assert.ok(M.validate(bad).length);
  }
}
let doc=M.add(M.createDocument(),'text'), id=doc.elements[0].id;
doc=M.update(doc,id,{text:'Keep',field:'sku',prefix:'[',suffix:']',type:'image'});
assert.equal(doc.schema_version,2); assert.equal(doc.elements[0].image_fit,'contain');
assert.equal(doc.elements[0].text,'Keep'); assert.equal(doc.elements[0].field,'sku');
for(const type of ['barcode','qrcode','text']) {
  doc=M.update(doc,id,{type});
  assert.deepEqual(M.validate(doc),[]);
  const e=doc.elements[0];
  for(const [other,fields] of Object.entries(extras)) for(const key of Object.keys(fields)) assert.equal(Object.hasOwn(e,key),type===other);
}
assert.deepEqual(M.validate({...M.add(M.createDocument(),'text'),schema_version:2}),[]);
assert.throws(()=>M.update(doc,id,{type:'html'}));
console.log('designer media schemas, defaults and transitions: OK');
for(const type of ['barcode','qrcode']) {
  const base=M.add(M.createDocument(),type), id=base.elements[0].id;
  for(const text of ['', ' !~', 'x'.repeat(2000)]) assert.deepEqual(M.validate(M.update(base,id,{text})),[]);
  assert.ok(M.validate(M.update(base,id,{text:'x'.repeat(2000),prefix:'x'})).length);
  for(const text of ['\x00','\n','\x7f','\x85',...(type==='barcode'?['é']:[])]) {
    for(const key of ['text','prefix','suffix','sample']) {
      const bad=M.clone(base);
      if(key==='sample') {bad.elements[0].field='sku';bad.sample_data.sku=text;} else bad.elements[0][key]=text;
      assert.ok(M.validate(bad).length, `${type} ${key} rejects controls / non-ASCII`);
    }
  }
  for(const value of [null,false,123,'']) {
    const bound=M.update(base,id,{field:'sku'}); bound.sample_data.sku=value;
    assert.deepEqual(M.validate(bound),[]);
    assert.equal(M.renderText(bound.elements[0],bound.sample_data),value==null?'':String(value));
  }
}
assert.deepEqual(M.validate(M.update(M.add(M.createDocument(),'qrcode'),'element-1',{text:'雪😀'.repeat(1000)})),[]);
console.log('designer code content and bindings: OK');
const zlib=require('node:zlib');
function crc32(data) {let crc=0xffffffff;for(const byte of data){crc^=byte;for(let i=0;i<8;i++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return (crc^0xffffffff)>>>0;}
function chunk(type,data=Buffer.alloc(0)) {const kind=Buffer.from(type), len=Buffer.alloc(4), crc=Buffer.alloc(4);len.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([kind,data])));return Buffer.concat([len,kind,data,crc]);}
function png({width=1,height=1,depth=8,color=6,compression=0,filtering=0,interlace=0,raw}={}) {
  const h=Buffer.alloc(13);h.writeUInt32BE(width);h.writeUInt32BE(height,4);h.set([depth,color,compression,filtering,interlace],8);
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',h),chunk('IDAT',zlib.deflateSync(raw??Buffer.alloc((1+width*4)*height))),chunk('IEND')]);
}
const url=data=>'data:image/png;base64,'+data.toString('base64'), valid=png();
for(const image_data of ['',url(valid),url(png({width:1024})),url(png({interlace:1})),url(png({depth:1,color:0,raw:Buffer.alloc(2)}))]) {
  const doc=M.add(M.createDocument(),'image');doc.elements[0].image_data=image_data;assert.deepEqual(M.validate(doc),[]);
}
const corrupt=Buffer.from(valid);corrupt[29]^=1;
for(const image_data of [null,'https://example.com/image.png','data:image/svg+xml;base64,AAAA','data:image/png;base64,!!!!',url(valid)+'\n',url(valid).slice(0,-1),url(Buffer.from('not png')),url(valid.subarray(0,-1)),url(Buffer.concat([valid,Buffer.from('junk')])),url(corrupt),...[
  {width:0},{width:1025},{height:1025},{depth:3},{compression:1},{filtering:1},{interlace:2},{raw:Buffer.from([5,0,0,0,0])},{raw:Buffer.alloc(0)},{raw:Buffer.alloc(10000)}
].map(options=>url(png(options))),url(Buffer.concat([valid.subarray(0,33),chunk('IDAT',Buffer.from('not zlib')),chunk('IEND')])),url(Buffer.concat([valid.subarray(0,33),chunk('ABCD'),valid.subarray(33)])),url(Buffer.concat([valid.subarray(0,33),chunk('IHDR',valid.subarray(16,29)),valid.subarray(33)])),url(Buffer.concat([valid.subarray(0,33),chunk('tEXt',Buffer.alloc(128*1024)),valid.subarray(33)]))]) {
  const doc=M.add(M.createDocument(),'image');doc.elements[0].image_data=image_data;assert.ok(M.validate(doc).length,`reject malformed PNG ${String(image_data).slice(0,60)}`);
}
console.log('designer PNG validation: OK');
const bounded=Buffer.concat([valid.subarray(0,33),chunk('tEXt',Buffer.alloc(128*1024-valid.length-12,120)),valid.subarray(33)]);
let indexed=png({depth:1,color:3,raw:Buffer.alloc(2)}); indexed=Buffer.concat([indexed.subarray(0,33),chunk('PLTE',Buffer.alloc(3)),indexed.subarray(33)]);
for(const data of [bounded,indexed]) {const doc=M.add(M.createDocument(),'image');doc.elements[0].image_data=url(data);assert.deepEqual(M.validate(doc),[]);}
for(const data of [png({depth:1,color:3,raw:Buffer.alloc(2)}),Buffer.concat([valid.subarray(0,33),chunk('IDAT'),chunk('tEXt'),valid.subarray(33)]),Buffer.concat([valid.subarray(0,33),chunk('IDAT'),chunk('PLTE',Buffer.alloc(3)),valid.subarray(33)]),Buffer.concat([valid.subarray(0,33),chunk('acTL',Buffer.alloc(8)),valid.subarray(33)])]) {
  const doc=M.add(M.createDocument(),'image');doc.elements[0].image_data=url(data);assert.ok(M.validate(doc).length,'reject PNG chunk ordering');
}
const transition=M.update(M.add(M.createDocument(),'image'),'element-1',{type:'barcode',image_data:'',image_fit:'contain'});
assert.equal(transition.elements[0].text,'123456789012');assert.deepEqual(M.validate(transition),[]);
console.log('designer PNG boundaries, palettes and transitions: OK');
for(const type of Object.keys(extras)) for(const patch of [{font_size:97},{x:999,width:1},{text:'x'.repeat(2001)},{field:'bad\x00field'}]) {
  const doc=M.add(M.createDocument(),type);Object.assign(doc.elements[0],patch);assert.ok(M.validate(doc).length);
}
const over=M.add(M.createDocument(),'image');over.elements[0].image_data=url(bounded);over.elements.push({...over.elements[0],id:'second'});assert.ok(M.validate(over).length);
const raw=Buffer.alloc(65*16);for(let row=0;row<16;row++)for(let x=0;x<64;x++)raw[row*65+x+1]=x;
for(const strategy of [zlib.constants.Z_DEFAULT_STRATEGY,zlib.constants.Z_FIXED,zlib.constants.Z_HUFFMAN_ONLY])for(const level of [0,1,9]) {
  const compressed=zlib.deflateSync(raw,{strategy,level}), data=Buffer.concat([png({width:16,height:16}).subarray(0,33),chunk('IDAT',compressed.subarray(0,3)),chunk('IDAT',compressed.subarray(3)),chunk('IEND')]);
  const doc=M.add(M.createDocument(),'image');doc.elements[0].image_data=url(data);assert.deepEqual(M.validate(doc),[],`strategy ${strategy} level ${level}`);
}
const max=M.add(M.createDocument(),'image');max.elements[0].image_data=url(png({width:1024,height:1024}));assert.deepEqual(M.validate(max),[]);
const compressed=zlib.deflateSync(Buffer.alloc(5)), altered=Buffer.from(compressed);altered[altered.length-1]^=1;
for(const data of [Buffer.concat([valid.subarray(0,33),chunk('IDAT',altered),chunk('IEND')]),Buffer.concat([valid.subarray(0,33),chunk('IDAT',Buffer.concat([compressed,Buffer.from('extra')])),chunk('IEND')]),Buffer.concat([valid.subarray(0,33),chunk('IDAT',compressed.subarray(0,-1)),chunk('IEND')]),Buffer.concat([valid.subarray(0,33),chunk('IEND')]),valid.subarray(0,-12)]) {
  const doc=M.add(M.createDocument(),'image');doc.elements[0].image_data=url(data);assert.ok(M.validate(doc).length);
}
console.log('designer media limits and bounded deflate strategies: OK');
