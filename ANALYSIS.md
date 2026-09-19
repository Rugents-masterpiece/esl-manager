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
