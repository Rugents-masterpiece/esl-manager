(function () {
  "use strict";
  const M = window.EslDesignerModel, Media=window.EslDesignerMedia;
  const make = (tag, text, className) => { const n=document.createElement(tag); if(text!==undefined) n.textContent=text; if(className) n.className=className; return n; };
  window.EslDesigner = {create};
  function create({api,notify,root=document.getElementById("designer-root")}) {
    let history=new M.History(M.createDocument()), selected=null, record=null, baseline=JSON.stringify(history.document), pending=false, zoom=2, sampleInvalid=false, sampleRaw="{}", shown=false;
    const nodes={};
    let rawDirty=false;
    function message(text,error=false) { nodes.message.textContent=text; nodes.message.classList.toggle("error",error); }
    function dirty() { return rawDirty || sampleInvalid || JSON.stringify(history.document)!==baseline; }
    function mediaErrors(doc) {
      const errors=[];
      doc.elements.forEach(e=>{try {
        if(e.type==="barcode"||e.type==="qrcode") Media.codeLayout(e,M.renderText(e,doc.sample_data));
        if(e.type==="image"&&e.image_data&&!Media.isPngData(e.image_data)) throw new Error("Povolený je iba vložený PNG. Nahrajte obrázok znova.");
      } catch(error){errors.push(`${e.name}: ${error.message}`);} });
      return errors;
    }
    function guard() { return !pending && (!dirty() || window.confirm("Máte neuložené úpravy. Zahodiť ich?")); }
    function commit(doc) { rawDirty=false; history.set(doc); render(); const errors=[...M.validate(doc),...mediaErrors(doc)]; message(errors.join(" "),errors.length>0); }
    function run(action) { if(pending) return; try { Promise.resolve(action()).catch(e=>message(e.message,true)); } catch(e) { message(e.message,true); } }
    function button(text,action,primary=false) { const b=make("button",text,`button ${primary?"button-primary":"button-secondary"}`); b.type="button"; b.addEventListener("click",()=>run(action)); return b; }
    function field(label,control,parent) {
      // HTML maxlength counts UTF-16 units; canonical validation counts code points.
      if(control.maxLength>0 && label!=="Dátové pole") control.maxLength*=2;
      if(label==="Dátové pole" && history.document.schema_version===2) control.maxLength=200;
      const wrap=make("div",undefined,"field");
      const id=`designer-${Object.keys(nodes).length}-${label.replace(/[^a-zA-Z]/g,"")}`;
      control.id=id; const l=make("label",label); l.htmlFor=id;
      wrap.append(l,control); parent.append(wrap); return control;
    }
    function select(values) { const s=make("select"); values.forEach(([value,label])=>{ const o=make("option",label); o.value=value; s.append(o); }); return s; }
    function reset(doc,newRecord=null) {
      const errors=M.validate(doc); if(errors.length) throw new Error(errors.join(" "));
      rawDirty=false; history=new M.History(doc); record=newRecord; baseline=JSON.stringify(doc);
      selected=null; sampleInvalid=false; sampleRaw=JSON.stringify(doc.sample_data,null,2); render();
      message(newRecord?`Načítaná revízia ${record.revision}.`:"Nový lokálny návrh. Uložte ho alebo exportujte JSON.");
    }
    const heading=make("div",undefined,"designer-meta");
    nodes.name=field("Názov šablóny",make("input"),heading); nodes.name.maxLength=400;
    nodes.model=field("Model displeja",select(Object.entries(M.models).map(([id,m])=>[id,`${id} · ${m.width} × ${m.height}`])),heading);
    const actions=make("div",undefined,"designer-actions");
    nodes.new=button("Nová šablóna",()=>{ if(guard()) reset(M.createDocument()); });
    nodes.save=button("Uložiť návrh",save,true);
    nodes.export=button("Export JSON",()=>{ if(sampleInvalid) throw new Error("Opravte ukážkové dáta pred exportom."); const doc=history.document; const errors=M.validate(doc); if(errors.length) throw new Error(errors.join(" ")); const url=URL.createObjectURL(new Blob([JSON.stringify(doc,null,2)],{type:"application/json"})); const a=make("a"); a.href=url; a.download="esl-template.json"; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); });
    nodes.import=button("Import JSON",()=>nodes.file.click()); nodes.file=make("input"); nodes.file.type="file"; nodes.file.accept=".json,application/json"; nodes.file.hidden=true;
    actions.append(nodes.new,nodes.save,nodes.import,nodes.export,nodes.file);
    const library=make("div",undefined,"designer-library"); nodes.saved=field("Uložené lokálne návrhy",select([["","Vyberte návrh"]]),library);
    nodes.load=button("Načítať",()=>load(nodes.saved.value)); nodes.reload=button("Znovu načítať",()=>load(record?.id)); nodes.refresh=button("Obnoviť zoznam",refresh); nodes.deleteDraft=button("Zmazať návrh",deleteDraft); library.append(nodes.load,nodes.reload,nodes.refresh,nodes.deleteDraft);
    const sources=make("div",undefined,"designer-library designer-sources");
    sources.append(make("h2","Šablóny zo zariadenia"));
    nodes.controller=field("Controller",select([["","Vyberte controller"]]),sources);
    nodes.source=field("Zdrojová šablóna",select([["","Najprv vyberte controller"]]),sources);
    nodes.sourceLoad=button("Načítať kópiu",loadSource);
    nodes.sourceRefresh=button("Obnoviť zdroje",refreshSources);
    nodes.controllerRefresh=button("Obnoviť controllery",refreshControllers);
    nodes.sourceInfo=make("p","Načítanie vytvorí iba neuloženú lokálnu kópiu. Originál na zariadení sa nemení.","field-help");
    sources.append(nodes.sourceLoad,nodes.sourceRefresh,nodes.controllerRefresh,nodes.sourceInfo);
    nodes.controller.addEventListener("change",()=>run(refreshSources));
    nodes.source.addEventListener("change",renderButtons);
    nodes.message=make("div",undefined,"state-message"); nodes.message.setAttribute("role","status");
    nodes.status=make("p",undefined,"designer-status");
    const workspace=make("div",undefined,"designer-workspace");
    const left=make("aside",undefined,"designer-panel designer-palette"); left.append(make("h2","Prvky a vrstvy"));
    const palette=make("div",undefined,"designer-palette-buttons"); [["text","+ Text"],["rectangle","+ Obdĺžnik"],["line","+ Čiara"],["image","+ Obrázok"],["barcode","+ Čiarový kód"],["qrcode","+ QR kód"]].forEach(([type,label])=>palette.append(button(label,()=>{ const doc=M.add(history.document,type); selected=doc.elements.at(-1).id; commit(doc); }))); nodes.layers=make("div",undefined,"designer-layers"); left.append(palette,make("p","Posledná vrstva je vpredu.","field-help"),nodes.layers);
    const center=make("div",undefined,"designer-canvas-panel"); const toolbar=make("div",undefined,"designer-toolbar");
    function historyStep(direction) {
      history[direction]();
      if(!sampleInvalid) sampleRaw=JSON.stringify(history.document.sample_data,null,2);
      render();
      const errors=[...M.validate(history.document),...mediaErrors(history.document)];
      if(sampleInvalid)errors.unshift("Opravte ukážkový JSON.");
      message(errors.join(" "),errors.length>0);
    }
    nodes.undo=button("Späť",()=>historyStep("undo"));
    nodes.redo=button("Znova",()=>historyStep("redo"));
    nodes.zoom=field("Zväčšenie",select([["1","100 %"],["2","200 %"],["3","300 %"],["4","400 %"]]),toolbar); nodes.zoom.value="2"; nodes.zoom.addEventListener("change",()=>{ zoom=Number(nodes.zoom.value); renderStage(); }); toolbar.prepend(nodes.undo,nodes.redo);
    nodes.dimensions=make("span",undefined,"designer-dimensions"); toolbar.append(nodes.dimensions);
    const scroll=make("div",undefined,"designer-canvas-scroll"); nodes.stageWrap=make("div",undefined,"designer-stage-wrap"); nodes.stage=make("div",undefined,"designer-stage"); nodes.stage.tabIndex=0; nodes.stage.setAttribute("role","group"); nodes.stage.setAttribute("aria-label","Náhľad cenovky. Vyberte prvok, šípky posúvajú o pixel, Shift o 10 pixelov."); nodes.stageWrap.append(nodes.stage); scroll.append(nodes.stageWrap);
    center.append(toolbar,scroll,make("p","Ťahaním presúvajte prvok. Šípky: 1 px · Shift + šípky: 10 px · Delete: zmazať.","field-help"));
    const dataPanel=make("details",undefined,"designer-data"); dataPanel.open=true; dataPanel.append(make("summary","Ukážkové dáta a väzby polí")); nodes.sample=field("JSON objekt (napr. {\"price\": \"1,99\"})",make("textarea"),dataPanel); nodes.sample.rows=5; nodes.sample.spellcheck=false; dataPanel.append(make("p","Pole číta presný kľúč objektu, nie výraz. Importované návrhy podporujú aj názvy ako kod položky; medzery sú súčasťou názvu. Ak kľúč chýba, použije sa text prvku.","field-help")); center.append(dataPanel);
    const right=make("aside",undefined,"designer-panel designer-inspector"); right.append(make("h2","Vlastnosti prvku")); nodes.inspector=make("div"); right.append(nodes.inspector); workspace.append(left,center,right);
    nodes.controls=make("fieldset",undefined,"designer-controls"); nodes.controls.append(heading,actions,library,sources,workspace); root.append(nodes.status,nodes.message,nodes.controls);
    nodes.name.addEventListener("change",()=>run(()=>{const doc=history.document; doc.name=nodes.name.value; commit(doc);}));
    nodes.model.addEventListener("change",()=>run(()=>{const wanted=nodes.model.value; if(!guard()) { nodes.model.value=history.document.model_id; return; } reset(M.createDocument(nodes.name.value||"Nová cenovka",wanted)); }));
    nodes.sample.addEventListener("input",()=>{ sampleRaw=nodes.sample.value; sampleInvalid=true; nodes.status.textContent="Neuložené úpravy · ukážkové dáta čakajú na potvrdenie (opustite pole)."; });
    nodes.sample.addEventListener("change",()=>run(()=>{
      sampleRaw=nodes.sample.value; sampleInvalid=true; renderButtons();
      let data;
      try { data=JSON.parse(sampleRaw); }
      catch(e) { throw new Error("Ukážkové dáta: neplatný JSON. Úpravy zostali zachované."); }
      if(!data||Array.isArray(data)||typeof data!=="object") throw new Error("Ukážkové dáta musia byť JSON objekt.");
      const check=history.document; check.sample_data=data;
      const errors=M.validate(check).filter(text=>text.startsWith("Ukážkové")||text.startsWith("Dokument"));
      if(errors.length) throw new Error(errors.join(" "));
      sampleInvalid=false; commit(check); message("");
    }));
    nodes.file.addEventListener("change",async()=>{ const file=nodes.file.files[0]; nodes.file.value=""; if(!file||!guard()) return; if(file.size>1024*1024) { message("JSON súbor je príliš veľký (max. 1 MB).",true); return; } setPending(true); try { const doc=JSON.parse(await file.text()); reset(doc); baseline=""; render(); } catch(e) { message(`Import zlyhal: ${e.message}`,true); } finally { setPending(false); } });
    nodes.stage.addEventListener("keydown",event=>{ if(pending||!selected) return; const step=event.shiftKey?10:1, delta={ArrowLeft:[-step,0],ArrowRight:[step,0],ArrowUp:[0,-step],ArrowDown:[0,step]}[event.key]; if(delta) { event.preventDefault(); const e=history.document.elements.find(e=>e.id===selected); if(e) commit(M.move(history.document,selected,e.x+delta[0],e.y+delta[1])); } else if(event.key==="Delete") { event.preventDefault(); commit(M.remove(history.document,selected)); } });
    let drag=null;
    root.addEventListener("input",event=>{
      if(event.target===nodes.name || event.target===nodes.sample || nodes.inspector.contains(event.target)) rawDirty=true;
    });
    nodes.stage.addEventListener("pointerdown",event=>{ if(pending||event.button!==0) return; const target=event.target.closest("[data-element-id]"); selected=target?.dataset.elementId||null; renderInspector(); renderLayers(); renderStage(); if(!selected) return; const e=history.document.elements.find(e=>e.id===selected); drag={id:selected,x:event.clientX,y:event.clientY,start:M.clone(e),doc:history.document,next:null}; nodes.stage.setPointerCapture(event.pointerId); nodes.stage.focus(); event.preventDefault(); });
    nodes.stage.addEventListener("pointermove",event=>{ if(!drag) return; drag.next=M.move(drag.doc,drag.id,drag.start.x+(event.clientX-drag.x)/zoom,drag.start.y+(event.clientY-drag.y)/zoom); renderStage(drag.next); });
    const finish=()=>{
      if(!drag) return;
      const unchanged=JSON.stringify(drag.doc)===JSON.stringify(history.document);
      const next=drag.next; drag=null;
      if(next && unchanged) commit(next); else render();
    };
    nodes.stage.addEventListener("pointerup",finish); nodes.stage.addEventListener("pointercancel",()=>{drag=null;render();});
    window.addEventListener("beforeunload",event=>{ if(pending || dirty()) {event.preventDefault();event.returnValue="";} });
    function setPending(value) { pending=value; nodes.controls.disabled=value; nodes.stage.style.pointerEvents=value?"none":""; nodes.stage.setAttribute("aria-disabled",String(value)); renderButtons(); }
    function renderButtons() { const errors=[...M.validate(history.document),...mediaErrors(history.document)]; nodes.save.disabled=pending||sampleInvalid||errors.length>0; nodes.save.title=errors.length?errors.join(" "):sampleInvalid?"Opravte a potvrďte ukážkové dáta.":"Uložiť lokálne bez odoslania na hardvér"; nodes.save.textContent=pending?"Prebieha operácia…":"Uložiť návrh"; nodes.undo.disabled=pending||!history.canUndo; nodes.redo.disabled=pending||!history.canRedo; nodes.reload.disabled=pending||!record; nodes.deleteDraft.disabled=pending||!record; nodes.sourceLoad.disabled=pending||!nodes.source.value; nodes.sourceRefresh.disabled=pending||!nodes.controller.value; }
    function renderLayers() { nodes.layers.replaceChildren(); const doc=history.document; [...doc.elements].reverse().forEach(e=>{const b=button(`${e.name} · ${e.type}`,()=>{ selected=e.id; render(); }); b.className="designer-layer"; b.setAttribute("aria-pressed",String(e.id===selected)); nodes.layers.append(b);}); if(!doc.elements.length) nodes.layers.append(make("p","Začnite pridaním textu produktu alebo ceny.","field-help")); }
    function renderStage(doc=history.document) {
      const m=M.models[doc.model_id]; nodes.dimensions.textContent=`${m.width} × ${m.height} px`; Object.assign(nodes.stageWrap.style,{width:`${m.width*zoom}px`,height:`${m.height*zoom}px`}); Object.assign(nodes.stage.style,{width:`${m.width}px`,height:`${m.height}px`,transform:`scale(${zoom})`}); nodes.stage.replaceChildren();
      doc.elements.forEach(e=>{
        const box=make("div",undefined,`designer-object${e.id===selected?" selected":""}`);
        box.dataset.elementId=e.id; box.setAttribute("aria-label",e.name);
        Object.assign(box.style,{
          left:`${e.x}px`,top:`${e.y}px`,width:`${e.width}px`,height:`${e.height}px`,
          color:e.color,background:e.background,fontFamily:e.font_family,fontSize:`${e.font_size}px`,
          fontWeight:e.bold?"700":"400",fontStyle:e.italic?"italic":"normal",
          textAlign:e.align,border:`${e.border_width}px solid ${e.color}`
        });
        if(e.type==="text") box.textContent=M.renderText(e,doc.sample_data);
        if(e.type==="image") {
          box.classList.add("designer-media");
          if(!e.image_data) box.append(make("span","Bez obrázka · nahrajte PNG/JPEG/WebP/BMP","designer-media-empty"));
          else if(Media.isPngData(e.image_data)) { const img=make("img"); img.alt=e.name; img.src=e.image_data; img.draggable=false; img.style.objectFit=e.image_fit; box.append(img); }
          else box.append(make("span","Neplatný PNG · nahrajte obrázok znova","designer-media-error"));
        }
        if(e.type==="barcode"||e.type==="qrcode") {
          box.classList.add("designer-media");box.style.border="0";
          try { box.append(Media.codeSvg(Media.codeLayout(e,M.renderText(e,doc.sample_data)))); }
          catch(error) {box.append(make("span",error.message,"designer-media-error"));box.title=error.message;}
        }
        if(e.type==="line") {
          box.style.border="0";
          const ns="http://www.w3.org/2000/svg";
          const svg=document.createElementNS(ns,"svg"), line=document.createElementNS(ns,"line");
          svg.setAttribute("viewBox",`0 0 ${e.width} ${e.height}`);
          svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
          svg.setAttribute("aria-hidden","true");
          const dx=Math.min(e.width/2,e.border_width/2), dy=Math.min(e.height/2,e.border_width/2);
          const attributes={x1:dx,y1:dy,x2:e.width-dx,y2:e.height-dy,
            stroke:e.color,"stroke-width":e.border_width,"stroke-linecap":"butt"};
          Object.entries(attributes).forEach(([key,value])=>line.setAttribute(key,String(value)));
          svg.append(line); box.append(svg);
        }
        nodes.stage.append(box);
      });
    }
    function renderInspector() {
      nodes.inspector.replaceChildren(); const doc=history.document, e=doc.elements.find(e=>e.id===selected); if(!e) { selected=null; nodes.inspector.append(make("p","Vyberte prvok na plátne alebo v zozname vrstiev.","field-help")); return; }
      const tools=make("div",undefined,"designer-element-actions"); tools.append(button("Duplikovať",()=>{ const d=M.duplicate(history.document,selected); selected=d.elements.at(-1).id; commit(d); }),button("Zmazať",()=>commit(M.remove(history.document,selected))),button("Dozadu",()=>commit(M.layer(history.document,selected,-1))),button("Dopredu",()=>commit(M.layer(history.document,selected,1)))); nodes.inspector.append(tools);
      const grid=make("div",undefined,"designer-properties"); nodes.inspector.append(grid);
      const properties=[["id","ID (nemenné)"],["name","Názov prvku"],["type","Typ",["text","rectangle","line","image","barcode","qrcode"]],["x","X (px)"],["y","Y (px)"],["width","Šírka (px)"],["height","Výška (px)"],["text","Text / náhradná hodnota"],["field","Dátové pole"],["prefix","Predpona"],["suffix","Prípona"],["font_family","Písmo",["Arial","Verdana","Times New Roman","Courier New"]],["font_size","Veľkosť písma (px)"],["bold","Tučné"],["italic","Kurzíva"],["align","Zarovnanie",["left","center","right"]],["color","Farba",M.palette(doc.model_id)],["background","Pozadie",["transparent",...M.palette(doc.model_id)]],["border_width","Hrúbka čiary (px)"]];
      if(e.type==="image") properties.push(["image_fit","Prispôsobenie obrázka",["contain","cover","fill"]]);
      if(e.type==="barcode") properties.push(["barcode_format","Formát kódu",["CODE128"]]);
      if(e.type==="qrcode") properties.push(["error_correction","Korekcia QR chýb",["L","M","Q","H"]]);
      const applicable=properties.filter(([key])=>{
        if(!["image","barcode","qrcode"].includes(e.type)) return true;
        if(["font_family","font_size","bold","italic","align"].includes(key)) return false;
        if(e.type==="image"&&["text","field","prefix","suffix"].includes(key)) return false;
        if(["barcode","qrcode"].includes(e.type)&&["color","background","border_width"].includes(key)) return false;
        return true;
      });
      applicable.forEach(([key,label,values])=>{const numeric=["x","y","width","height","font_size","border_width"].includes(key), check=["bold","italic"].includes(key); const input=values?select(values.map(v=>[v,v])):make(key==="text"?"textarea":"input"); if(!values&&key!=="text") input.type=check?"checkbox":numeric?"number":"text"; if(check) input.checked=e[key]; else input.value=e[key]; if(key==="id") input.readOnly=true; if(numeric) { input.step="1"; input.min=["width","height"].includes(key)?"1":key==="font_size"?"4":"0"; input.max=key==="font_size"?"96":key==="border_width"?"8":String(["y","height"].includes(key)?M.models[doc.model_id].height:M.models[doc.model_id].width); } if(!numeric&&!check&&!values) input.maxLength=key==="text"?2000:key==="field"?64:200; field(label,input,grid); input.addEventListener("change",()=>run(()=>{const value=check?input.checked:numeric?Number(input.value):input.value; input.setCustomValidity(""); commit(M.update(history.document,selected,{[key]:value})); })); });
      if(e.type==="image") {
        const upload=make("input"); upload.type="file";upload.accept="image/png,image/jpeg,image/webp,image/bmp,.bmp";
        field("Nahrať obrázok",upload,grid);
        upload.addEventListener("change",async()=>{
          const file=upload.files[0],id=e.id;upload.value="";if(!file||pending)return;
          setPending(true);message("Spracúvam obrázok lokálne…");
          try { const png=await Media.normalizeImage(file,M.models[history.document.model_id]);
            const next=M.update(history.document,id,{image_data:png}),errors=M.validate(next);
            if(errors.length)throw new Error(errors.join(" "));commit(next);
          }catch(error){message(`Nahratie zlyhalo: ${error.message} Pôvodný návrh zostal zachovaný.`,true);}
          finally{setPending(false);}
        });
        grid.append(button("Odstrániť obrázok",()=>commit(M.update(history.document,e.id,{image_data:""}))));
        nodes.inspector.append(make("p","Obrázok sa spracuje lokálne na farby displeja a uloží ako vložený PNG. contain: celý obrázok · cover: orezanie · fill: natiahnutie.","field-help"));
      }
      if(e.type==="barcode"||e.type==="qrcode") {
        nodes.inspector.append(make("p","Kód používa text, dátové pole, predponu a príponu. Náhľad je čiernobiely s ochranným okrajom a celými pixelmi; zväčšenie nemení rozlíšenie cenovky.","field-help"));
        const errors=mediaErrors({...doc,elements:[e]});if(errors.length)nodes.inspector.append(make("p",errors.join(" "),"designer-media-error"));
      }
    }
    function render() {
      const doc=history.document;
      if(drag && JSON.stringify(drag.doc)!==JSON.stringify(doc)) drag=null;
      nodes.name.value=doc.name; nodes.model.value=doc.model_id; nodes.sample.value=sampleRaw;
      nodes.status.textContent=`${dirty()?"Neuložené úpravy":record?"Uložený stav":"Nový návrh"} · ${record?`revízia ${record.revision}`:"nový návrh"} · ${doc.elements.length}/100 prvkov`;
      renderLayers(); renderStage(); renderInspector(); renderButtons();
    }
    async function refresh() { const result=await api("/api/template-drafts"); const old=nodes.saved.value; nodes.saved.replaceChildren(); const empty=make("option",result.items.length?"Vyberte návrh":"Zatiaľ žiadne uložené návrhy"); empty.value=""; nodes.saved.append(empty); result.items.forEach(item=>{ const o=make("option",`${item.document.name} · revízia ${item.revision}`); o.value=item.id; nodes.saved.append(o); }); nodes.saved.value=result.items.some(i=>i.id===old)?old:""; }
    async function refreshControllers() {
      if(pending)return;setPending(true);
      try {
        const result=await api("/api/controllers",{authReturnTarget:nodes.controllerRefresh});
        const items=result.items.filter(item=>item.id!=="legacy");
        nodes.controller.replaceChildren();const empty=make("option",items.length?"Vyberte controller":"Žiadny dostupný controller");empty.value="";nodes.controller.append(empty);
        nodes.source.replaceChildren();const sourceEmpty=make("option","Najprv vyberte controller");sourceEmpty.value="";nodes.source.append(sourceEmpty);
        items.forEach(item=>{const option=make("option",item.name);option.value=item.id;nodes.controller.append(option);});
        nodes.sourceInfo.textContent=items.length?"Vyberte controller a načítajte zoznam zdrojových šablón. Originál zostáva nezmenený.":"Nie je dostupný controller. Lokálny editor funguje aj bez zdrojov.";
      }catch(error){nodes.sourceInfo.textContent=`Controllery sa nepodarilo načítať: ${error.message}`;}
      finally{setPending(false);}
    }
    async function refreshSources() {
      if(pending)return;
      const controller=nodes.controller.value;
      nodes.source.replaceChildren();const empty=make("option",controller?"Načítavam zdroje…":"Najprv vyberte controller");empty.value="";nodes.source.append(empty);renderButtons();
      if(!controller)return;setPending(true);
      try {
        const result=await api(`/api/template-draft-sources?controller_id=${encodeURIComponent(controller)}`,{authReturnTarget:nodes.sourceRefresh});
        if(result.controller_id!==controller)throw new Error("Odpoveď patrí inému controlleru. Obnovte zoznam.");
        const items=result.items.filter(item=>item.supported===true);
        empty.textContent=items.length?"Vyberte zdrojovú šablónu":"Controller nemá šablóny pre podporované modely";
        items.forEach(item=>{
          const option=make("option",`${item.name} · ${item.width} × ${item.height} · ${item.screen_type}`);
          option.value=String(item.id);nodes.source.append(option);
        });
        nodes.sourceInfo.textContent="Zobrazené sú iba šablóny pre podporované modely. Načítanie kópie nemení originál na zariadení.";
      }catch(error){empty.textContent="Zdroje sa nepodarilo načítať";nodes.sourceInfo.textContent=`Načítanie zdrojov zlyhalo: ${error.message}. Skúste Obnoviť zdroje.`;}
      finally{setPending(false);}
    }
    async function loadSource() {
      const id=nodes.source.value,controller=nodes.controller.value;
      if(!id||!controller||nodes.source.selectedOptions[0]?.disabled){message("Vyberte podporovanú zdrojovú šablónu.",true);return;}
      if(!guard())return;setPending(true);message("Načítavam a prevádzam lokálnu kópiu…");
      try {
        const result=await api(`/api/template-draft-sources/${encodeURIComponent(id)}?controller_id=${encodeURIComponent(controller)}`,{authReturnTarget:nodes.sourceLoad});
        if(!result.source||result.source.controller_id!==controller||String(result.source.id)!==id)throw new Error("Odpoveď nepatrí vybranému zdroju.");
        const errors=M.validate(result.document);if(errors.length)throw new Error(errors.join(" "));
        const warnings=Array.isArray(result.warnings)?result.warnings:[];
        if(warnings.length&&!window.confirm(`Konverzia šablóny vyžaduje kontrolu:\n\n${warnings.map(w=>`• ${w}`).join("\n")}\n\nNačítať túto lokálnu kópiu? Originál zostane nezmenený.`)) {
          message("Načítanie kópie bolo zrušené. Pôvodný návrh a úpravy zostali zachované.");return;
        }
        reset(result.document);baseline="";render();
        message(`Načítaná neuložená kópia: ${result.source.name}. Originál zostáva nezmenený.${warnings.length?` Upozornenia: ${warnings.join(" ")}`:""}${mediaErrors(result.document).length?` ${mediaErrors(result.document).join(" ")}`:""}`,warnings.length>0||mediaErrors(result.document).length>0);
      }catch(error){message(`Načítanie kópie zlyhalo: ${error.message}. Pôvodný návrh zostal zachovaný.`,true);}
      finally{setPending(false);}
    }
    async function load(id) { if(!id) {message("Vyberte uložený návrh.",true);return;} if(!guard()) return; setPending(true); try {const item=await api(`/api/template-drafts/${encodeURIComponent(id)}`); reset(item.document,item);} catch(e) {message(`Načítanie zlyhalo: ${e.message}`,true);} finally {setPending(false);} }
    async function save() {
      if(pending) return;
      const doc=history.document, errors=[...M.validate(doc),...mediaErrors(doc)]; if(sampleInvalid||errors.length) {message(sampleInvalid?"Opravte ukážkové dáta.":errors.join(" "),true);return;}
      setPending(true); message("Ukladám a overujem lokálny návrh…");
      try { const item=await api(record?`/api/template-drafts/${encodeURIComponent(record.id)}`:"/api/template-drafts",{method:record?"PUT":"POST",body:JSON.stringify(record?{revision:record.revision,document:doc}:doc),authReturnTarget:nodes.save}); record=item; const checked=await api(`/api/template-drafts/${encodeURIComponent(item.id)}`); if(checked.revision!==item.revision||JSON.stringify(checked.document)!==JSON.stringify(item.document)) throw new Error("Návrh sa po uložení zmenil. Exportujte úpravy a načítajte aktuálnu revíziu."); baseline=JSON.stringify(doc); record=checked; message(`Návrh uložený a overený · revízia ${checked.revision}. Bez odoslania na hardvér.`); notify("Lokálny návrh bol uložený. Bez fyzického odoslania."); try {await refresh(); nodes.saved.value=record.id;} catch(e) {message(`Návrh uložený, zoznam sa nepodarilo obnoviť: ${e.message}`,true);} }
      catch(e) {message(e.status===409?"Konflikt revízie: vaše úpravy zostali zachované. Exportujte JSON pred načítaním aktuálneho návrhu.":`Uloženie alebo overenie zlyhalo: ${e.message}. Úpravy zostali zachované.`,true);} finally {setPending(false);render();}
    }
    async function deleteDraft() { if(!record||!guard()||!window.confirm("Zmazať tento uložený lokálny návrh?")) return; setPending(true); try { const id=record.id; await api(`/api/template-drafts/${encodeURIComponent(id)}`,{method:"DELETE",body:JSON.stringify({revision:record.revision}),authReturnTarget:nodes.deleteDraft}); try {await api(`/api/template-drafts/${encodeURIComponent(id)}`); throw new Error("Návrh je stále dostupný.");} catch(e) {if(e.status!==404) throw e;} reset(M.createDocument()); await refresh(); message("Lokálny návrh bol zmazaný."); } catch(e) {message(`Zmazanie zlyhalo: ${e.message}. Úpravy zostali zachované.`,true);} finally {setPending(false);} }
    render();
    return {show() { if(shown) return; shown=true; refresh().catch(e=>message(`Zoznam návrhov sa nepodarilo načítať: ${e.message}. Editor a JSON export fungujú aj bez API.`,true)); refreshControllers(); },canLeave:guard,isDirty:dirty};
  }
})();
