(function (root, factory) {
  "use strict";
  const value = factory();
  if (typeof module === "object" && module.exports) module.exports = value;
  else root.EslDesignerModel = value;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const models = {"2.13TFT-BW":{width:250,height:132,red:false},"2.13EPD-BWR":{width:250,height:122,red:true},"2.9EPD-BWR":{width:296,height:128,red:true}};
  const clone = value => JSON.parse(JSON.stringify(value));
  const mediaDefaults = {image:{image_data:"",image_fit:"contain"},barcode:{barcode_format:"CODE128"},qrcode:{error_correction:"M"}};
  const types = ["text","rectangle","line","image","barcode","qrcode"];
  const isMedia = type => Object.prototype.hasOwnProperty.call(mediaDefaults,type);
  function createDocument(name = "Nová cenovka", model_id = "2.13EPD-BWR") {
    if (!Object.prototype.hasOwnProperty.call(models,model_id)) throw new Error("Nepodporovaný model.");
    return {schema_version:1,name,model_id,elements:[],sample_data:{}};
  }
  const integer = (value, low, high) => Math.max(low, Math.min(high, Math.round(Number(value) || 0)));
  function palette(model_id) { return models[model_id].red ? ["#000000","#ffffff","#ff0000"] : ["#000000","#ffffff"]; }
  function bounds(e, model_id) {
    const m = models[model_id];
    e.width = integer(e.width,1,m.width); e.height = integer(e.height,1,m.height);
    e.x = integer(e.x,0,m.width-e.width); e.y = integer(e.y,0,m.height-e.height);
    e.font_size = integer(e.font_size,4,96); e.border_width = integer(e.border_width,0,8);
    if (!palette(model_id).includes(e.color)) e.color="#000000";
    if (![...palette(model_id),"transparent"].includes(e.background)) e.background="transparent";
    return e;
  }
  function nextId(doc) { let n=1; while(doc.elements.some(e=>e.id===`element-${n}`)) n++; return `element-${n}`; }
  function add(doc,type) {
    if(doc.elements.length>=100) throw new Error("Najviac 100 prvkov.");
    if(!types.includes(type)) throw new Error("Neznámy typ.");
    const result=clone(doc);
    if(isMedia(type)) result.schema_version=2;
    result.elements.push(bounds({id:nextId(doc),name:{text:"Text",rectangle:"Obdĺžnik",line:"Čiara",image:"Obrázok",barcode:"Čiarový kód",qrcode:"QR kód"}[type],type,x:8,y:8,width:isMedia(type)?(type==="barcode"?200:80):120,height:type==="line"?1:type==="image"?60:type==="barcode"?48:type==="qrcode"?80:30,text:type==="text"?"Názov produktu":type==="barcode"?"123456789012":type==="qrcode"?"https://example.com":"",field:"",prefix:"",suffix:"",font_family:"Arial",font_size:18,bold:false,italic:false,align:"left",color:"#000000",background:isMedia(type)?"#ffffff":"transparent",border_width:type==="text"||isMedia(type)?0:1,...(isMedia(type)?mediaDefaults[type]:{})},doc.model_id));
    return result;
  }
  function update(doc,id,patch) {
    const result=clone(doc), e=result.elements.find(e=>e.id===id);
    if(e) {
      const {id:ignored,...rest}=patch;
      if(Object.prototype.hasOwnProperty.call(rest,"type") && rest.type!==e.type) {
        if(!types.includes(rest.type)) throw new Error("Neznámy typ.");
        for(const fields of Object.values(mediaDefaults)) for(const key of Object.keys(fields)) {
          delete e[key];
          if(!isMedia(rest.type)||!Object.prototype.hasOwnProperty.call(mediaDefaults[rest.type],key))delete rest[key];
        }
        if(isMedia(rest.type)) Object.assign(e,mediaDefaults[rest.type],{background:"#ffffff",color:"#000000"});
        if(!e.text&&!e.field&&!Object.prototype.hasOwnProperty.call(rest,"text")) {
          if(rest.type==="barcode")e.text="123456789012";
          if(rest.type==="qrcode")e.text="https://example.com";
        }
      }
      Object.assign(e,rest);
      if(isMedia(e.type)) result.schema_version=2;
      bounds(e,result.model_id);
    }
    return result;
  }
  function move(doc,id,x,y) { return update(doc,id,{x,y}); }
  function duplicate(doc,id) {
    if(doc.elements.length>=100) throw new Error("Najviac 100 prvkov.");
    const result=clone(doc), source=doc.elements.find(e=>e.id===id);
    if(source) result.elements.push(bounds({...clone(source),id:nextId(doc),name:Array.from(source.name).slice(0,192).join("")+" — kópia",x:source.x+8,y:source.y+8},doc.model_id));
    return result;
  }
  function remove(doc,id) { const result=clone(doc); result.elements=result.elements.filter(e=>e.id!==id); return result; }
  function layer(doc,id,direction) { const result=clone(doc), i=result.elements.findIndex(e=>e.id===id); if(i<0) return result; const target=integer(i+direction,0,result.elements.length-1); const [item]=result.elements.splice(i,1); result.elements.splice(target,0,item); return result; }
  class History {
    constructor(doc) { this.items=[clone(doc)]; this.index=0; }
    get document() { return clone(this.items[this.index]); }
    get canUndo() { return this.index>0; }
    get canRedo() { return this.index<this.items.length-1; }
    set(doc) { if(JSON.stringify(doc)===JSON.stringify(this.document)) return; this.items=this.items.slice(0,this.index+1); this.items.push(clone(doc)); if(this.items.length>101) this.items.shift(); this.index=this.items.length-1; }
    undo() { if(this.canUndo) this.index--; return this.document; }
    redo() { if(this.canRedo) this.index++; return this.document; }
  }
  function renderText(e,data) { const value=e.field && Object.prototype.hasOwnProperty.call(data,e.field) ? data[e.field] : e.text; return e.prefix+String(value==null?"":value)+e.suffix; }
  function validCode(value,type) {
    return typeof value==="string" && Array.from(value).length<=2000 &&
      Array.from(value).every(char=>{const n=char.codePointAt(0); return type==="barcode" ? n>=32&&n<=126 : n>=32 && !(n>=127&&n<=159) && !(n>=0xd800&&n<=0xdfff);});
  }
  const pngLimit=128*1024, pngPrefix="data:image/png;base64,";
  function crc32(data,start,end) {
    let crc=0xffffffff;
    for(let i=start;i<end;i++) {crc^=data[i];for(let bit=0;bit<8;bit++) crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
    return (crc^0xffffffff)>>>0;
  }
  const read32=(data,i)=>((data[i]*0x1000000)+(data[i+1]<<16)+(data[i+2]<<8)+data[i+3])>>>0;
  // Dependency-free bounded zlib/DEFLATE validation for real PNG raster data.
  // No DOM, async decompressor, or Node-only imports are needed by the model.
  function inflatePng(data,expected) {
    const bad=()=>{throw new Error("Invalid PNG deflate");};
    if(data.length<6||(data[0]&15)!==8||(data[0]>>>4)>7||((data[0]<<8)+data[1])%31||(data[1]&32)) bad();
    let bit=16, written=0;
    const limit=(data.length-4)*8, output=new Uint8Array(expected), window=1<<((data[0]>>>4)+8);
    const bits=n=>{if(bit+n>limit)bad();let v=0;for(let i=0;i<n;i++,bit++)v|=((data[bit>>>3]>>>(bit&7))&1)<<i;return v;};
    const put=value=>{if(written>=expected)bad();output[written++]=value;};
    function tree(lengths,complete=false) {
      const counts=new Array(16).fill(0), next=new Array(16).fill(0), maps=Array.from({length:16},()=>new Map());
      for(const n of lengths){if(n<0||n>15)bad();if(n)counts[n]++;}
      let left=1, code=0;
      for(let n=1;n<=15;n++){left=left*2-counts[n];if(left<0)bad();code=(code+counts[n-1])*2;next[n]=code;}
      const max=Math.max(...lengths);
      if(left && (complete || max>1))bad();
      lengths.forEach((n,symbol)=>{if(n){let c=next[n]++,rev=0;for(let i=0;i<n;i++){rev=(rev<<1)|(c&1);c>>>=1;}maps[n].set(rev,symbol);}});
      return ()=>{let c=0;for(let n=1;n<=max;n++){c|=bits(1)<<(n-1);if(maps[n].has(c))return maps[n].get(c);}bad();};
    }
    const lenBase=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258];
    const lenExtra=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0];
    const distBase=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577];
    const distExtra=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
    let final;
    do {
      final=bits(1);const kind=bits(2);
      if(kind===0) {
        bit=(bit+7)&~7;const n=bits(16);if((n^bits(16))!==65535)bad();
        for(let i=0;i<n;i++)put(bits(8));
        continue;
      }
      if(kind===3)bad();
      let litLengths,distLengths;
      if(kind===1) {
        litLengths=Array.from({length:288},(_,i)=>i<144?8:i<256?9:i<280?7:8);distLengths=new Array(32).fill(5);
      } else {
        const nl=bits(5)+257,nd=bits(5)+1,nc=bits(4)+4;
        if(nl>286||nd>30)bad();
        // RFC 1951 code-length alphabet order.
        const alphabet=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15], cl=new Array(19).fill(0);
        for(let i=0;i<nc;i++)cl[alphabet[i]]=bits(3);
        const decode=tree(cl,true), lengths=[];
        while(lengths.length<nl+nd) {
          const symbol=decode();
          if(symbol<16)lengths.push(symbol);
          else {
            if(symbol===16&&!lengths.length)bad();
            const repeat=symbol===16?bits(2)+3:symbol===17?bits(3)+3:bits(7)+11;
            const value=symbol===16?lengths[lengths.length-1]:0;
            if(lengths.length+repeat>nl+nd)bad();
            for(let i=0;i<repeat;i++)lengths.push(value);
          }
        }
        litLengths=lengths.slice(0,nl);distLengths=lengths.slice(nl);
        if(!litLengths[256])bad();
      }
      const literal=tree(litLengths),distance=tree(distLengths);
      while(true) {
        const symbol=literal();
        if(symbol<256)put(symbol);
        else if(symbol===256)break;
        else {
          if(symbol>285)bad();const n=lenBase[symbol-257]+bits(lenExtra[symbol-257]), ds=distance();
          if(ds>29)bad();const d=distBase[ds]+bits(distExtra[ds]);
          if(d>written||d>window||written+n>expected)bad();
          for(let i=0;i<n;i++)put(output[written-d]);
        }
      }
    } while(!final);
    if(written!==expected||Math.ceil(bit/8)!==data.length-4)bad();
    let a=1,b=0;for(const byte of output){a=(a+byte)%65521;b=(b+a)%65521;}
    if(((b*65536+a)>>>0)!==read32(data,data.length-4))bad();
    return output;
  }
  function validPng(value) {
    if(value==="")return true;
    if(typeof value!=="string"||!value.startsWith(pngPrefix)||value.length>pngPrefix.length+4*Math.ceil(pngLimit/3))return false;
    try {
      const encoded=value.slice(pngPrefix.length);
      if(!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded))return false;
      const binary=atob(encoded);if(btoa(binary)!==encoded||binary.length>pngLimit)return false;
      const data=Uint8Array.from(binary,c=>c.charCodeAt(0));
      if(data.length<8||![137,80,78,71,13,10,26,10].every((n,i)=>data[i]===n))return false;
      let offset=8,header=null,palette=false,ended=false,idatDone=false,idatStarted=false,total=0;const parts=[];
      while(offset<data.length) {
        if(offset+12>data.length)return false;
        const size=read32(data,offset),end=offset+12+size,kind=String.fromCharCode(...data.subarray(offset+4,offset+8));
        if(end>data.length||!/^[A-Za-z]{2}[A-Z][A-Za-z]$/.test(kind)||crc32(data,offset+4,end-4)!==read32(data,end-4)||(!header&&kind!=="IHDR"))return false;
        const payload=data.subarray(offset+8,end-4);
        if(kind==="IHDR") {
          if(header||size!==13)return false;
          header={width:read32(payload,0),height:read32(payload,4),depth:payload[8],color:payload[9],interlace:payload[12]};
          const depths={0:[1,2,4,8,16],2:[8,16],3:[1,2,4,8],4:[8,16],6:[8,16]};
          if(header.width<1||header.width>1024||header.height<1||header.height>1024||!depths[header.color]?.includes(header.depth)||payload[10]!==0||payload[11]!==0||header.interlace>1)return false;
        } else if(kind==="PLTE") {
          if(palette||idatStarted||!size||size%3||size>768||[0,4].includes(header.color)||(header.color===3&&size/3>2**header.depth))return false;
          palette=true;
        } else if(kind==="IDAT") {
          if(idatDone||(header.color===3&&!palette))return false;
          idatStarted=true;parts.push(payload);total+=size;
        } else if(kind==="IEND") {
          if(size||!total||end!==data.length)return false;ended=true;
        } else if(!(data[offset+4]&32)||["acTL","fcTL","fdAT"].includes(kind))return false;
        if(idatStarted&&kind!=="IDAT")idatDone=true;
        offset=end;
      }
      if(!ended||!header)return false;
      const channels={0:1,2:3,3:1,4:2,6:4}[header.color],rows=[];
      const passes=header.interlace?[[0,0,8,8],[4,0,8,8],[0,4,4,8],[2,0,4,4],[0,2,2,4],[1,0,2,2],[0,1,1,2]]:[[0,0,1,1]];
      for(const [x,y,dx,dy] of passes) {
        const pw=Math.max(0,Math.ceil((header.width-x)/dx)),ph=Math.max(0,Math.ceil((header.height-y)/dy));
        if(pw&&ph)for(let i=0;i<ph;i++)rows.push(1+Math.ceil(pw*channels*header.depth/8));
      }
      const compressed=new Uint8Array(total);let i=0;for(const part of parts){compressed.set(part,i);i+=part.length;}
      const raw=inflatePng(compressed,rows.reduce((a,b)=>a+b,0));i=0;
      for(const row of rows){if(raw[i]>4)return false;i+=row;}
      return true;
    } catch(error) {return false;}
  }
  function validFieldKey(value,version) {
    if(typeof value!=="string")return false;
    return version===1 ? /^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(value) :
      value.length>0&&Array.from(value).length<=100&&!/[\u0000-\u001f\u007f-\u009f\ud800-\udfff]/u.test(value);
  }
  function validate(doc) {
    const errors=[];
    const object=v=>v!==null&&typeof v==="object"&&!Array.isArray(v);
    const keys=(v,wanted)=>object(v)&&Object.keys(v).sort().join(",")===wanted.slice().sort().join(",");
    const string=(v,max)=>typeof v==="string"&&Array.from(v).length<=max;
    const int=(v,min,max)=>Number.isInteger(v)&&v>=min&&v<=max;
    if(!keys(doc,["schema_version","name","model_id","elements","sample_data"])||![1,2].includes(doc.schema_version)||!string(doc.name,200)||!doc.name.trim()||!Object.prototype.hasOwnProperty.call(models,doc.model_id)||!object(doc.sample_data)||!Array.isArray(doc.elements)||doc.elements.length>100) return ["Neplatný dokument šablóny (verzia, názov, model alebo dáta)."];
    const samples=Object.entries(doc.sample_data);
    const safeNumber=value=>typeof value==="number" && Number.isFinite(value) && Math.abs(value)<=Number.MAX_SAFE_INTEGER;
    if(samples.length>100||samples.some(([key,value])=>!validFieldKey(key,doc.schema_version)||!(value===null||typeof value==="boolean"||safeNumber(value)||string(value,2000)))) errors.push("Ukážkové dáta: najviac 100 platných polí; veľké čísla zadávajte ako text.");
    try { if(new TextEncoder().encode(JSON.stringify(doc)).length>256*1024) errors.push("Dokument presahuje 256 KiB."); } catch(e) {errors.push("Dokument nemožno previesť na JSON.");}
    const m=models[doc.model_id], ids=new Set();
    const fields=["id","name","type","x","y","width","height","text","field","prefix","suffix","font_family","font_size","bold","italic","align","color","background","border_width"];
    doc.elements.forEach((e,i)=>{
      if(!object(e)||!keys(e,[...fields,...(isMedia(e.type)?Object.keys(mediaDefaults[e.type]):[])])) { errors.push(`Prvok ${i+1}: neplatné polia.`); return; }
      if(isMedia(e.type) && (doc.schema_version!==2 || (e.type==="image" && !["contain","cover","fill"].includes(e.image_fit)) || (e.type==="barcode" && e.barcode_format!=="CODE128") || (e.type==="qrcode" && !["L","M","Q","H"].includes(e.error_correction)))) errors.push(`Prvok ${i+1}: neplatné nastavenie média.`);
      if(!string(e.id,64)||!e.id.trim()||ids.has(e.id)||!string(e.name,200)||!e.name.trim()||!types.includes(e.type)||!int(e.width,1,m.width)||!int(e.height,1,m.height)||!int(e.x,0,m.width-e.width)||!int(e.y,0,m.height-e.height)||!string(e.text,2000)||!(e.field===""||validFieldKey(e.field,doc.schema_version))||!string(e.prefix,200)||!string(e.suffix,200)||!["Arial","Verdana","Times New Roman","Courier New"].includes(e.font_family)||!int(e.font_size,4,96)||typeof e.bold!=="boolean"||typeof e.italic!=="boolean"||!["left","center","right"].includes(e.align)||!palette(doc.model_id).includes(e.color)||![...palette(doc.model_id),"transparent"].includes(e.background)||!int(e.border_width,0,8)) errors.push(`Prvok ${i+1}: skontrolujte názov, rozmery, farby a textové polia.`);
      ids.add(e.id);
      if(e.type==="image"&&!validPng(e.image_data)) errors.push(`Prvok ${i+1}: obrázok musí byť platný PNG do 128 KiB a 1024 × 1024 px.`);
      if(["barcode","qrcode"].includes(e.type) && (![e.text,e.prefix,e.suffix,e.prefix+e.text+e.suffix].every(value=>validCode(value,e.type)) || !validCode(renderText(e,doc.sample_data),e.type))) errors.push(`Prvok ${i+1}: neplatný obsah kódu (najviac 2000 znakov bez riadiacich znakov; CODE128 iba ASCII).`);
    });
    return errors;
  }
  return {models,clone,createDocument,palette,add,update,move,duplicate,remove,layer,History,renderText,validate};
});
