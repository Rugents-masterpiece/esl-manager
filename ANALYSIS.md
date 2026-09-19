# Analýza zdrojov a návrh ESL Managera

## Inventár

- `esl-manager/`: 104 súborov, prevažne Python pokusy reverzného inžinierstva; hlavný znovupoužiteľný klient je `scripts/esl_manager.py`.
- `esl-oberon/`: 30 súborov (28 VB.NET, 2 Markdown), 991 734 B; obsahuje dátové modely, OBERON driver a dokumentáciu protokolu, ale nemá solution/project manifest ani samostatné testy.
- `esl/`: 38 zachytených frontend súborov, z toho väčšina staré vendor/theme assety; vlastné workflow sú hlavne v `component.js` a `DocUtil.js`.

## Overené schopnosti zdrojov

Čítacie endpointy zdokumentované vo viacerých nezávislých zdrojoch:

- `GET /esls_new/associate/getTagsMsg`
- `GET /esls_new/associate/getRoutersMsg`
- `GET /esls_new/associate/getStyleMsgs`
- `POST /esls_new/associate/getStyleMsgById?id={id}`
- `GET /esls_new/associate/getPhotos`
- `GET /esls_new/associate/getPhotoDataByName?photoName={name}`

Zápisové operácie:

- `POST /esls_new/associate/updateScreen` — dávková aktualizácia displejov.
- `POST /esls_new/associate/delTagsByMac` — deštruktívne odstránenie cenoviek.
- upload/delete obrázkov a úpravy štýlov existujú, ale ich správanie je nekonzistentné.

Dátové polia cenovky: MAC, rozmery, batéria (`power`), RSSI, router, status 1 ready / 2 updating / 3 failed / 4 success, `styleId`. Update payload obsahuje `mac`, `styleid`, `mappingtype`, `ABDisplayFlag` (161 A, 162 B, 163 obe), voliteľné NFC a dynamické polia šablóny.

## Riziká pôvodného kódu

- Natvrdo uložené IP, heslo admin/admin a session cookie v experimentálnych skriptoch.
- Response formáty sú nekonzistentné: priamy JSON, JSON zakódovaný ako string, `datalist` envelope aj HTML/plain text.
- Niektoré zápisy vracajú HTTP 500 napriek možnému úspechu; úspech sa musí overovať read-backom, nie iba statusom.
- `updateDispMData` je podľa opakovaných pokusov nedôveryhodný; klonovanie môže prepísať originál.
- Starý frontend používa nepodporovaný jQuery 1.10/Bootstrap 3/Metronic mix a nejasné licenčné pokrytie. Nová aplikácia tieto assety nekopíruje.
- Jeden historický Python pokus má syntax error; legacy adresáre nie sú súčasťou runtime novej app.
- Firmware workflow a `updateFeedback` nie sú dostatočne zdokumentované a nebudú implementované ako live operácie.

## Architektúra novej aplikácie

Nová aplikácia bude samostatná v `webapp/` a použije iba Python štandardnú knižnicu:

- `esl_web/storage.py` — SQLite schema, seed, repository a transakcie.
- `esl_web/service.py` — validácia a use-cases pre produkty, tagy, binding, joby, retry, alarmy a audit.
- `esl_web/vendor.py` — izolovaný ESL HTTP adapter, robustný decoder, read-only sync a dvojitá poistka live zápisov.
- `esl_web/server.py` — ThreadingHTTPServer, JSON REST API a statické súbory.
- `static/` — offline, responzívny slovenský frontend bez CDN.
- `tests/` — unittest testy repository, API, vendor adaptera a DOM markerov.

Predvolený režim je `demo/simulation`. Živé zápisy vyžadujú súčasne `ESL_LIVE_WRITES=1` a explicitnú potvrdzovaciu frázu v requeste. Deštruktívne operácie na fyzickom ESL serveri nová verzia nevykonáva.

## Funkčný rozsah

Základné funkcie:

- KPI dashboard a inventár cenoviek/routerov/šablón.
- Produkty, ceny, SKU/EAN a väzba produktu na cenovku.
- Vyhľadávanie, filtre, detail a lokálne CRUD operácie.

Pokročilé funkcie:

- Dávkové update joby, položky jobu, retry zlyhaných položiek a stavový prehľad.
- Alerty nízkej batérie, slabého signálu, offline routera a failed update.
- Audit log všetkých mutácií.
- CSV export, bezpečný read-only sync a simulovaný dispatch.
- Offline-first UI v IBM Carbon-inšpirovanom dizajne.

## Bezpečnostné hranice

- Žiadne credentialy v repozitári; všetko cez environment premenné.
- Browser nikdy nekomunikuje priamo s ESL zariadením.
- Vendor host je validovaný, timeouts sú povinné a testy používajú iba loopback fake server.
- API vracia jednoznačné 4xx chyby pri neplatných vstupoch.
- Fyzické DELETE endpointy sa neexponujú.

## Live read-only discovery dokumentovaných endpointov

Sekvenčný probe proti produkčnému controlleru používal autentifikovanú session a minimálny odstup 5,2 s medzi požiadavkami. Zaznamenaná bola iba HTTP odpoveď, tvar dát, názvy polí a počty; prihlasovacie údaje, cookie, hodnoty položiek ani Base64 obsah sa nevypisovali. Endpointy `updateScreen`, `uploadPhoto`, `delPhoto` a `delTagsByMac` neboli volané.

| Operácia | Metóda a cesta | Live výsledok | Tvar a rozhodnutie |
|---|---|---:|---|
| Cenovky | `GET /associate/getTagsMsg` | HTTP 200 | Priamy zoznam, 13 položiek. Polia: `height`, `ido`, `mac`, `power`, `routerStatus`, `routerid`, `rssi`, `showStyle`, `status`, `styleId`, `sub`, `width`. Použiteľný zdroj rozšírených read-only metadát. |
| Stanice, legacy | `GET /associate/getRoutersMsg` | HTTP 500 | Nepoužívať. Zachovať fungujúci fallback `GET /mms/queryRouters?currentPage=0&routerId=0`, ktorý vrátil 1 stanicu. |
| Šablóny, jednoduchý zoznam | `GET /associate/getStylesMsg` | HTTP 200 | Priamy zoznam, 62 položiek. Obsahuje `backgroundID`, `descriptor`, rozmery, `id`, `mappingtype`, `name`, `type`, `updateTime`. |
| Šablóny, envelope | `GET /associate/getStyleMsgs` | HTTP 200 | Objekt s `datalist`, `page`, `resultCode`, `resultMsg`; 62 položiek. Preferovaný endpoint, lebo zachováva vendor status. |
| Detail šablóny | `POST /associate/getStyleMsgById?id={id}` s JSON telom `{"id": id}` | HTTP 200 | `datalist` s 1 položkou; navyše `styleFileds`, `rotate`, `userid` a detailné metadáta. Operácia je read-only napriek metóde POST. |
| Zoznam obrázkov | `GET /associate/getPhotos` | HTTP 200 | Envelope s 47 položkami; polia `height`, `id`, `name`, `width`. |
| Dáta obrázka | `GET /associate/getPhotoDataByName?photoName={name}` | HTTP 200 | Base64 je duplicitne v `data` a `t`; pri probe obe polia mali 45 036 znakov. Backend musí mať tvrdý limit veľkosti a nesmie logovať payload. |
| Preview šablóny | `GET /{urlencoded(name + id + '.png')}` | HTTP 200 `image/png` | Overený dynamicky odvodený názov. Backend má validovať názov a proxyovať len obrázok z rovnakého controller originu. |

Implementačné dôsledky:

- Pre stanice zostáva autoritatívny MMS endpoint; legacy route zlyháva.
- Rozšírené tag metadata sa môžu zlúčiť s existujúcim stránkovaným MMS inventárom podľa MAC; strata alebo konflikt MAC musí zlyhať bezpečne.
- `getStyleMsgs` poskytuje podstatne širší zoznam než aktuálny MMS sync (62 oproti 4), preto sa nové read-only zobrazenie nemá tváriť ako náhrada existujúceho synchronizovaného inventára bez explicitného zlučovacieho pravidla.
- Detail šablóny, zoznam obrázkov, obrázkové dáta a preview možno implementovať ako read-through GET API aplikácie bez fyzickej mutácie controlleru.
- V tejto etape sa nepridajú upload, update displeja ani žiadne DELETE ovládacie prvky.

## Kompletný reverse engineering vendor UI a template editora (ORB-00049)

Používateľ následne výslovne povolil create/update/delete konfiguračných objektov a určil tri zdrojové šablóny. Táto discovery etapa zostala zámerne read-only: fyzické `updateScreen`/`delTagsByMac` ani template mutácie neboli volané. Všetky požiadavky boli autentifikované, serializované a oddelené najmenej 5 sekundami.

### Zachytený živý frontend

Z controlleru sa načítali hlavné menu fragmenty `mms/index`, `mms/meeting`, `mms/tag`, `mms/router`, `mms/chooseStyle`, `mms/getHelpDoc`, tri editory `mms/getDispMs?id=145|147|149` a 37 ich same-origin JS/CSS assetov. Relevantné živé first-party assety:

- `/app/js/DocUtil.js`, SHA-256 `43260b93a5db03c022487a61b2d52848c861843474a982f8808a5d7dbd690c57`
- `/app/js/RouterUtil.js`, SHA-256 `ae42c141ed36bcb263bbc38b78ed02911ea94485052c704ab15950a88ffaae96`
- `/app/js/component_v2/component/js/component.js`, SHA-256 `1270f754c9ed60b96e9355b81ef48d7b81fe9fdfb3ad641142556894a63a3806`
- `/app/js/index.js`, SHA-256 `892f82928731f352490b0f9f9087af7e065e08cd9a49a2f070379bdc5180428e`

Raw capture ostáva iba v dočasnom adresári `/tmp/esl-orb-00049-capture` s módom `0700`; cookies, credentials a Base64 obrázky nie sú v Git ani v tejto dokumentácii.

### Frontendom preukázané backendové route

| Oblasť | Metóda a route | Parametre / body | Zdroj | Riziko a stav |
|---|---|---|---|---|
| navigácia | `GET /mms/menu`, `/mms/index`, `/mms/meeting`, `/mms/tag`, `/mms/router`, `/mms/chooseStyle`, `/mms/getHelpDoc` | bez tela | live HTML | read-only, live 200 |
| inventár tagov | `GET /mms/queryTags` | `currentPage`, `tagMac`, `routerMac`, `startTime`, `endTime`, `templateType` | `RouterUtil.js:95` | read-only, live overené |
| inventár routerov | `GET /mms/queryRouters` | `currentPage`, `routerId` | `RouterUtil.js:184` | read-only, live overené |
| meetingy | `GET /mms/queryMeetings`, `GET /mms/queryTagsByMeeting` | stránka, názov alebo `mid`/`mac` | `RouterUtil.js:24,218,245` | read-only; mimo clone workflow |
| šablóny | `GET /mms/queryStyles` | `currentPage`, `templateType` | `RouterUtil.js:282` | read-only, live overené |
| typy displejov | `POST /mms/queryStyleAlign` | prázdne JSON telo | `DocUtil.js:1492`, `component.js:505` | read-only; live envelope, 18 typov |
| editor | `GET /mms/getDispMs?id={id}` | ID šablóny | `DocUtil.js:910` | read-only pre existujúce ID; live 200 |
| komponenty | `POST /style/getDispMsData?id={id}` | prázdne/form telo | `component.js:727` | read-only; JSON zakódovaný ako string |
| úplný detail | `GET /style/getStyleData?id={id}` | ID šablóny | live/historické zdroje | read-only; metadata + `dispMs` |
| obrázky editora | `POST /style/getPhotoName`, `/style/getBgMsg`, `/style/getBgImg` | `stylealignId`, `styleid` alebo `ImgId` | `component.js:108,196,228` | read-only; Base64 musí byť bounded |
| použitá schéma | `GET /mms/queryUsingColumn` | `tid`, `mappingtype` | `DocUtil.js:103` | read-only |
| preview návrhu | `POST /style/previewImg?id={id}` | form `orderJson=<JSON>` | `component.js:1315` | generuje preview; nie je dôkazom uloženia |
| create | `GET /mms/addStyles?id=0&stylealignId={id}` | typ displeja | `DocUtil.js:925` | mutujúci GET; vytvorí default šablónu a serverové ID |
| názov/typ | `POST /style/updateStyleAlign` | query `styleid`, `stylealign`, `styleName`; prázdne JSON telo | `component.js:383,410,1161` | template update; `0` fail, `1` success, `2` duplicate name |
| layout | `POST /mms/updateDispMData?id={id}` | form `orderJson=<JSON>` | `component.js:360,1189` | autoritatívny live UI save endpoint; vyžaduje read-back |
| starý layout | `POST /style/updateDispMData?id={id}` | form `orderJson=<JSON>` | `component.js:1125` | legacy varianta; historicky 200 bez uloženia, nepoužiť |
| pridať pole | `POST /style/addColumnAndGood` | query `columnName`, `mappingText`, `mappingtype`, `styleid` | `component.js:334` | template update; vytvára serverový component ID |
| zmazať pole | `POST /style/delDismp` | JSON scalar component ID | `component.js:841` | deštruktívne iba pre jeden komponent |
| zmazať šablónu | `GET /style/deleteStyles?styleid={id}` | ID šablóny | `DocUtil.js:975` | deštruktívny GET; úspech je envelope `resultCode=10` |
| pozadie | `POST /style/removeBackground` | `mappingtype`, `styleid` | `component.js:243` | mutácia šablóny |
| upload obrázka | `POST /style/uploadPhoto` | multipart form: `name`, `width`, `height`, `photo`, voliteľne `redphoto` | `component.js:461,479` | upload; nie JSON/form-urlencoded |
| upload fontu | `POST /mms/uploadFont` | multipart + query `filePath`, `fontName` | `component.js:30` | systémová mutácia, mimo clone workflow |
| meeting väzba | `POST /mms/selectStyleById` | form `mid`, `styleid` | `RouterUtil.js:362` | mutácia meetingu, mimo rozsahu |
| ostatné UI mutácie | `POST /mms/saveColumnContent`, `/mms/delMeeting`, `/mms/deleteTag`, `/mms/deleteAllTag`, `/mms/deleteRouter`; `POST /router/updateRouterDescription`, `/router/updateTagRegisterEN`; default GET `/associate/tagWakePeriod` | podľa `DocUtil.js` | `DocUtil.js:1249-1550` | nesúvisia s klonovaním; nevolať |

Naďalej platia zdokumentované `/associate` route: `getTagsMsg`, `getRoutersMsg`, `getStyleMsgs`, `getStyleMsgById`, `getPhotos`, `getPhotoDataByName`, `updateScreen`, `uploadPhoto`, `delPhoto`, `delTagsByMac`. Aktívny MMS inventár zostáva autoritatívny. Fyzické tag mutácie sú oddelené od template CRUD a nie sú súčasťou vytvorenia klonov.

### Presné zdrojové snapshoty

| ID | Názov | Rozmer | style align / screen type | mappingtype | Komponenty | Texty už bold / spolu | Layout SHA-256 | Preview SHA-256 |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 145 | `S21BasePriceTag_V1` | 250x122 | 9 / 2 | 291 | 6 text | 2 / 6 | `c73b93bc475d556b1f0085c454ecc6cd9f01f44d59b4a735bd7d636c2eca7b2f` | `82d9f6b5d825f23748508ddc640c3c10ce684f25f580aa355a97540d21a47284` |
| 147 | `SF21BasePriceTag_V1` | 250x132 | 8 / 1 | 502 | 6 text | 2 / 6 | `afe9c492de7acbbd4395113bac1255fb99fa6df9321e5bf99a78c045cfab5c99` | `76691154e487a3ce5dd291ea86cdfc45d94c8b61f27c84e8e61e4cb3489614cb` |
| 149 | `Default Template149` | 296x128 | 2 / 2 | 620 | 6 text | 4 / 6 | `9b7581218f7975135e704be9a5fb3541e2d73009d0918d28eaf0dab175e4fc3e` | `358af8b167d1bb7fd0d2479a3009a2e72c2d8dff3b996892093e91c33e965366` |

Všetkých 18 komponentov troch zdrojov má `type="text"`. Editor zapisuje tučné písmo ako `style["font-weight"] = "700"`; read-back `/style/getStyleData` ho reprezentuje ako `fontBold="bold"`. Transformácia klonu preto mení iba `font-weight` na `700` pre každý textový komponent. Rozmery, pozícia, farby, text, prefix/suffix, dátové mapovanie a netextové polia sa nemenia.

### Bezpečný clone kontrakt

1. Tesne pred create načítať a hashovať katalóg, metadata, `getDispMsData`, `getStyleData` a preview zdroja.
2. Overiť, že cieľový názov ešte neexistuje. Predvolené rozlíšiteľné názvy budú `S21BasePriceTag_V1_BOLD`, `SF21BasePriceTag_V1_BOLD` a `Default Template149_BOLD`.
3. `GET /mms/addStyles?id=0&stylealignId={9|8|2}` vykonať presne raz. Aj keď ide o GET, považovať ho za create. Nové ID identifikovať porovnaním katalógu a z HTML odpovede; nikdy ho nehádzať ani opakovane nevolať pri nejasnom statuse.
4. Nová default šablóna má vlastný `mappingtype` a serverové component IDs. Zdrojové component IDs sa nesmú poslať do cieľovej šablóny, lebo by mohli prepísať alebo presunúť zdroj.
5. Pre každé chýbajúce dynamické pole zavolať `addColumnAndGood` najviac raz, potom znovu načítať cieľ a spárovať nové serverové IDs podľa stabilných field identít. Až potom zostaviť cieľový `orderJson` so zachovaným layoutom a `font-weight=700`.
6. Aktualizovať jedinečný názov cez `updateStyleAlign`, uložiť layout cez autoritatívny `/mms/updateDispMData`, potom vykonať detail/layout/preview read-back. HTTP status ani preview bez detailu nie sú dôkaz uloženia.
7. Zdroj musí mať po každom klone rovnaký normalizovaný layout hash a metadata. Pri nejasnom výsledku mutáciu neopakovať; najprv znovu načítať katalóg a presný objekt.
8. Rollback smie použiť `GET /style/deleteStyles?styleid={new_id}` iba pre ID vytvorené týmto workflow, po fresh read-backu identity. Zdrojové ID 145/147/149 sa nikdy nemažú ani neupravujú.

Live katalóg mal počas discovery 62 položiek a maximálne ID 153. Existujú aj staršie testovacie objekty 150 a 151; nie sú vytvorené touto úlohou a preto sa automaticky nemažú. Zachytený historický `addStyles` objekt 151 potvrdzuje, že create route pridelila nový ID, nový `mappingtype` a jeden default textový komponent. Žiadny fyzický tag nebol počas discovery zmenený.

### Live vytvorené bold klony (ORB-00052)

Finálny katalógový read-back obsahuje 65 položiek, teda presne tri nové objekty oproti preflight počtu 62. Jediné nové ID nad pôvodným maximom 153, ktoré vo finálnom katalógu existujú, sú 158, 159 a 160.

| Nové ID | Zdroj | Názov | Rozmer | style align / screen type | mappingtype | Text bold editor/native | Layout SHA-256 | Preview SHA-256 |
|---:|---:|---|---:|---:|---:|---:|---|---|
| 158 | 145 | `S21BasePriceTag_V1_BOLD` | 250x122 | 9 / 2 | 282 | 6/6 / 6/6 | `9c13c9be7e61f99ed6cf482b7a22866b619a911ab313b9bed9799193fcbf895c` | `ee840a4b2e7f1fbcaf689b866ad3ec9ecac741aea69d977c9505d9d0e4f285e7` |
| 159 | 147 | `SF21BasePriceTag_V1_BOLD` | 250x132 | 8 / 1 | 773 | 6/6 / 6/6 | `74b50a3c8888f8e47256082a7137eedfbf170d713242bb1c4eece7b67ea67a07` | `74fbad7dc8c25176c83b5f26adafe5017032c168763527149a5acb0aa00f58f1` |
| 160 | 149 | `Default Template149_BOLD` | 296x128 | 2 / 2 | 318 | 6/6 / 6/6 | `b5156de7a39fc4e0fa435ed777986de1ec4471162b941a4162e3b79f84307479` | `ba6face1251801f872bcc48d5916c70d674d5b2e894be74834ca8d1c63311f9f` |

Editorový read-back overil `font-weight=700` na všetkých 18 textoch. Nezávislý native read-back `/style/getStyleData` overil `fontBold="bold"` na rovnakých 18 textoch. Server pri uložení normalizuje poradie komponentov, číselný/string tvar `font-weight` a `mpname`; dynamické polia sa preto overujú autoritatívnym `styleFileds` setom a native komponenty podľa serverových ID a interného `name`, pričom všetky ostatné native polia musia zostať zhodné so zdrojom.

Počas sprísňovania live read-back kontraktu vznikli štyri dočasné kandidáty v rozsahu ID 154–157. Každý zlyhal na fail-closed verifikácii, bol identifikovaný ako objekt vlastnený konkrétnym create volaním, rollback-zmazaný a jeho neprítomnosť bola overená čerstvým katalógom. Zdrojové layout a preview hashe ID 145, 147 a 149 po všetkých operáciách zostali presne zhodné s preflight hodnotami uvedenými vyššie. Fyzické operácie `updateScreen` a `delTagsByMac` sa nevolali.
