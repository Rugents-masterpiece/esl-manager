(function(root,factory){
  "use strict";
  const value=factory(root);
  if(typeof module==="object"&&module.exports) module.exports=value;
  else root.EslDesignerMedia=value;
})(typeof globalThis!=="undefined"?globalThis:this,function(root){
  "use strict";
  const MAX_FILE=8*1024*1024, MAX_PNG=128*1024;
  function isPngData(value){
    const prefix="data:image/png;base64,";
    if(typeof value!=="string"||value.length>prefix.length+4*Math.ceil(MAX_PNG/3)||!/^data:image\/png;base64,iVBORw0KGgo[A-Za-z0-9+/]*={0,2}$/.test(value))return false;
    const encoded=value.slice(prefix.length),padding=encoded.endsWith("==")?2:encoded.endsWith("=")?1:0;
    return encoded.length%4===0&&encoded.length/4*3-padding<=MAX_PNG;
  }
  function codeLayout(e,text,deps=root){
    if(typeof text!=="string"||!text.length) throw new Error("Prázdny obsah kódu. Zadajte text alebo platné dátové pole.");
    if(Array.from(text).length>2000||/[\u0000-\u001f\u007f-\u009f]/.test(text)||Array.from(text).some(c=>c.codePointAt(0)>=0xd800&&c.codePointAt(0)<=0xdfff)) throw new Error("Neplatný obsah kódu. Použite najviac 2000 znakov bez riadiacich znakov.");
    const width=Math.floor(e.width),height=Math.floor(e.height);
    if(!Number.isFinite(width)||!Number.isFinite(height)||width<1||height<1) throw new Error("Neplatné rozmery kódu.");
    if(e.type==="qrcode"){
      if(!["L","M","Q","H"].includes(e.error_correction)) throw new Error("Neplatná korekcia QR kódu. Vyberte L, M, Q alebo H.");
      if(typeof deps.qrcode!=="function") throw new Error("Offline QR knižnica nie je dostupná. Obnovte stránku.");
      let qr;
      try { deps.qrcode.stringToBytes=deps.qrcode.stringToBytesFuncs['UTF-8']; qr=deps.qrcode(0,e.error_correction); qr.addData(text,"Byte"); qr.make(); }
      catch(_){throw new Error("QR obsah je príliš dlhý. Skráťte text alebo znížte korekciu chýb.");}
      const modules=qr.getModuleCount(),quiet=4,pitch=Math.floor(Math.min(width,height)/(modules+2*quiet));
      if(pitch<1) throw new Error(`QR rámček je príliš malý. Zväčšite ho aspoň na ${modules+8} × ${modules+8} px.`);
      const matrix=Array.from({length:modules},(_,y)=>Array.from({length:modules},(_,x)=>qr.isDark(y,x)));
      return {type:e.type,width,height,modules,quiet,pitch,x:Math.floor((width-modules*pitch)/2),y:Math.floor((height-modules*pitch)/2),matrix};
    }
    if(e.type!=="barcode"||e.barcode_format!=="CODE128") throw new Error("Podporovaný je iba čiarový kód CODE128.");
    if(!/^[\x20-\x7e]+$/.test(text)) throw new Error("CODE128 podporuje iba ASCII znaky. Odstráňte diakritiku alebo použite QR kód.");
    if(typeof deps.JsBarcode!=="function") throw new Error("Offline CODE128 knižnica nie je dostupná. Obnovte stránku.");
    const encoded={};
    try {deps.JsBarcode(encoded,text,{format:"CODE128",displayValue:false});}
    catch(_){throw new Error("Neplatný CODE128 obsah. Skontrolujte text alebo použite QR kód.");}
    const bits=encoded.encodings.map(part=>part.data).join(""),quiet=10,pitch=Math.floor(width/(bits.length+quiet*2));
    if(pitch<1) throw new Error(`CODE128 rámček je príliš malý. Zväčšite šírku aspoň na ${bits.length+20} px alebo skráťte obsah.`);
    if(height<16) throw new Error("CODE128 výška je príliš malá. Zväčšite ju aspoň na 16 px.");
    return {type:e.type,width,height,bits,quiet,pitch,x:Math.floor((width-bits.length*pitch)/2),y:0};
  }
  function codeSvg(layout,dom=root.document){
    const ns="http://www.w3.org/2000/svg",svg=dom.createElementNS(ns,"svg");
    const attrs=(n,values)=>Object.entries(values).forEach(([k,v])=>n.setAttribute(k,String(v)));
    attrs(svg,{viewBox:`0 0 ${layout.width} ${layout.height}`,width:layout.width,height:layout.height,"shape-rendering":"crispEdges","aria-hidden":"true"});
    const bg=dom.createElementNS(ns,"rect");attrs(bg,{width:layout.width,height:layout.height,fill:"#ffffff"});svg.append(bg);
    const path=dom.createElementNS(ns,"path");let d="";
    if(layout.type==="qrcode") layout.matrix.forEach((row,y)=>row.forEach((dark,x)=>{if(dark)d+=`M${layout.x+x*layout.pitch} ${layout.y+y*layout.pitch}h${layout.pitch}v${layout.pitch}h-${layout.pitch}z`; }));
    else for(let x=0;x<layout.bits.length;x++) if(layout.bits[x]==="1") d+=`M${layout.x+x*layout.pitch} 0h${layout.pitch}v${layout.height}h-${layout.pitch}z`;
    attrs(path,{d,fill:"#000000"});svg.append(path);return svg;
  }
  function quantizePixels(pixels,red){
    const result=new Uint8ClampedArray(pixels.length),palette=red?[[0,0,0],[255,255,255],[255,0,0]]:[[0,0,0],[255,255,255]];
    for(let i=0;i<pixels.length;i+=4){
      const a=pixels[i+3]/255, rgb=[0,1,2].map(c=>Math.round(pixels[i+c]*a+255*(1-a)));
      let best=palette[0],distance=Infinity;
      for(const color of palette){const d=rgb.reduce((sum,v,c)=>sum+(v-color[c])**2,0);if(d<distance){best=color;distance=d;}}
      result.set([...best,255],i);
    }return result;
  }
  async function normalizeImage(file,model){
    if(!file||!['image/png','image/jpeg','image/webp','image/bmp','image/x-ms-bmp'].includes(file.type)) throw new Error("Vyberte PNG, JPEG, WebP alebo BMP. SVG a externé obrázky nie sú povolené.");
    if(file.size>MAX_FILE) throw new Error("Obrázok je príliš veľký (max. 8 MB). Zmenšite súbor.");
    const head=new Uint8Array(await file.slice(0,16).arrayBuffer());
    const matches=(offset,bytes)=>bytes.every((byte,i)=>head[offset+i]===byte);
    const raster=matches(0,[137,80,78,71,13,10,26,10])||matches(0,[255,216,255])||matches(0,[66,77])||(matches(0,[82,73,70,70])&&matches(8,[87,69,66,80]));
    if(!raster)throw new Error("Súbor nie je PNG, JPEG, WebP ani BMP. SVG a externé obrázky nie sú povolené.");
    const url=URL.createObjectURL(file),img=new Image();
    try {
      await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error("Obrázok sa nepodarilo dekódovať. Vyberte platný obrazový súbor."));img.src=url;});
      if(!img.naturalWidth||!img.naturalHeight||img.naturalWidth*img.naturalHeight>40000000) throw new Error("Obrázok má príliš veľa pixelov (max. 40 MP). Zmenšite ho.");
      const ratio=Math.min(1,1024/img.naturalWidth,1024/img.naturalHeight,model.width/img.naturalWidth,model.height/img.naturalHeight);
      const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.naturalWidth*ratio));canvas.height=Math.max(1,Math.round(img.naturalHeight*ratio));
      const ctx=canvas.getContext('2d',{willReadFrequently:true});if(!ctx)throw new Error("Prehliadač nepodporuje spracovanie obrázkov.");
      ctx.fillStyle='#ffffff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
      const data=ctx.getImageData(0,0,canvas.width,canvas.height);data.data.set(quantizePixels(data.data,model.red));ctx.putImageData(data,0,0);
      const png=canvas.toDataURL('image/png');if(!isPngData(png))throw new Error("Spracovaný PNG presahuje 128 KiB. Zmenšite obrázok.");return png;
    }finally{img.src='';URL.revokeObjectURL(url);}
  }
  return {codeLayout,codeSvg,quantizePixels,isPngData,normalizeImage};
});
