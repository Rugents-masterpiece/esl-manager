# Editor šablón a prechod na vlastné ESL GUI

## Dodaný vertikálny celok

Navigácia **Editor šablón** (`/#designer`) je samostatný offline editor lokálnych návrhov. Návrhy nie sú vendor šablóny a zatiaľ ich nemožno priradiť fyzickej cenovke. Uloženie v tomto editore nevolá controller ani `updateScreen`.

Podporované displeje:

| Model | Rozmer | Paleta |
|---|---|---|
| 2.13TFT-BW | 250 × 132 | čierna, biela |
| 2.13EPD-BWR | 250 × 122 | čierna, biela, červená |
| 2.9EPD-BWR | 296 × 128 | čierna, biela, červená |

### Ovládanie

1. Zadajte názov a vyberte model. Pri zmene modelu vzniká nový prázdny návrh; existujúce prvky sa potichu nedeformujú.
2. Pridajte **Text**, **Obdĺžnik**, **Čiaru**, **Obrázok**, **Čiarový kód** alebo **QR kód**. Vyberte prvok na plátne alebo v zozname vrstiev.
3. V paneli vlastností nastavte názov, X/Y, šírku/výšku, text, predponu/príponu, písmo, veľkosť, tučné/kurzívu, zarovnanie, farbu, pozadie a hrúbku čiary. ID prvku je nemenné.
4. Presúvajte myšou alebo klávesmi: šípky 1 px, Shift + šípky 10 px, Delete odstráni vybraný prvok. Súradnice sú pixely displeja, nezávislé od zväčšenia náhľadu.
5. Duplikujte prvky, meňte poradie **Dozadu/Dopredu**, používajte **Späť/Znova**.
6. Pre dynamický obsah nastavte **Dátové pole** (napr. `price`) a ukážkový JSON (`{"price":"2,49"}`). Ak pole chýba, zobrazí sa náhradný text; predpona a prípona zostávajú zachované.
7. **Uložiť návrh** vytvorí/aktualizuje záznam v SQLite a následný GET overí uloženie. Pri tokenom chránenom serveri sa vyžaduje existujúce prihlásenie pre zápis.
8. **Export JSON** stiahne lokálny formát návrhu. **Import JSON** načíta ten istý formát ako nový návrh, nie ako aktualizáciu pôvodného záznamu.

Neuložené úpravy vyžadujú potvrdenie pri zahodení. Chyba alebo konflikt revízie nepovažuje návrh za úspešne uložený; používateľ môže exportovať svoje úpravy pred načítaním aktuálneho stavu.

### Obrázok, barcode a QR

- **Obrázok**: vyberte PNG/JPEG/WebP/BMP do 8 MiB. Prehliadač ho lokálne zmenší na rozmer displeja a prevedie na jeho čierno-bielu alebo čierno-bielo-červenú paletu. Uloží sa vložený statický PNG, nie externá URL ani SVG. Prispôsobenie: `contain` zachová celý obrázok, `cover` oreže, `fill` natiahne. PNG má limit 128 KiB dekódovaných bajtov, 1024 × 1024 px; celkový dokument stále 256 KiB. Prázdny obrázkový prvok je povolený a jasne označený.
- **Čiarový kód**: skutočný Code128 s kontrolným znakom, automatickým kódovaním a ochranným okrajom 10 modulov. Obsah používa tlačiteľné ASCII znaky; EAN/UPC a ďalšie symbologie nie sú v tomto celku implementované.
- **QR kód**: skutočná UTF-8 matica vrátane slovenčiny a emoji, korekcia L/M/Q/H, ochranný okraj 4 moduly.
- Oba kódy čítajú text alebo presne pomenované dátové pole s predponou/príponou. Generujú sa čierno-bielo v celých pixeloch natívneho displeja. Prázdny obsah alebo príliš malý rámček zobrazí konkrétnu chybu a blokuje uloženie; nejde o napodobeninu či rozmazané zmenšenie kódu. Zväčšenie plátna nemení natívne rozlíšenie.
- Generátory JsBarcode 3.11.6 a qrcode-generator 1.4.4 sú lokálne vendored MIT assets. Zdrojové URL, licencie a SHA-256 sú v `static/vendor/`; runtime nepotrebuje CDN. Backend zostáva Python stdlib.

### Načítanie existujúcich šablón

**Uložené lokálne návrhy** je výhradne SQLite knižnica nového editora; nenapĺňa sa automaticky vendor šablónami. Vedľa nej je samostatný výber **Šablóny zo zariadenia**:

1. Vyberte nakonfigurovaný controller; načíta sa aktuálny read-only katalóg. Výber zdrojovej šablóny zobrazuje iba kompatibilné modely; nepodporované a záznamy bez potvrdenej kompatibility sú odfiltrované. Pôvodný katalóg ani šablóny na controlleri sa nemenia.
2. Vyberte podporovanú šablónu a kliknite **Načítať kópiu**. Server iba prečíta pôvodný layout a prevedie ho na neuložený lokálny dokument. Nevytvára ani neprepisuje vendor šablónu a automaticky nič neukladá.
3. Pri náhrade fontu, orezaní presahu alebo neznámej pôvodnej symbologii/ECC sa zobrazia upozornenia a vyžaduje sa súhlas. Zrušenie aj chyba ponechávajú otvorený návrh nezmenený.
4. Doplňte ukážkové hodnoty dynamických polí, skontrolujte náhľad a **Uložiť návrh**. Až potom bude lokálna kópia dostupná v **Uložené lokálne návrhy**.

V2 zachováva názvy polí presne, vrátane diakritiky, čínskych znakov a medzier (`kod položky`, `价格`); sú to ploché kľúče JSON, nikdy vykonávané výrazy alebo cesty. Kľúč má najviac 100 Unicode code points, bez riadiacich znakov. Starý formát V1 má naďalej pôvodné ASCII limity. Pri importe sa nepodporovaný komponent, neoverené pozadie/rotácia či nebezpečná obrazová referencia nevynechá potichu — import sa odmietne s diagnostikou. Statické vendor fotografie sa získavajú iba známymi autentifikovanými read-only metódami; dynamické fotografie nie sú podporované.

### Pripojenie iba na čítanie šablón

`python3 run_live.py --templates-only` používa existujúcu chránenú konfiguráciu controllera, neseeduje demo dáta a vynúti `ESL_LIVE_WRITES=0`, aj keď uložená konfigurácia povoľuje zápisy. Klient má samostatný whitelist iba pre čítanie katalógu, metadát, layoutov a obrázkov šablón. Ostatné operácie vrátane načítania tagov/routerov, klonovania, uploadu a fyzického dispatchu sú blokované. Konfigurácia ani prihlasovacie údaje sa neprepisujú. Lokálne ukladanie je oddelené od zariadenia a používa existujúcu tokenovú autentifikáciu; čítanie šablón nevyžaduje write session.

### Presnosť náhľadu a limity

- Náhľad používa fonty prehliadača (Arial, Verdana, Times New Roman, Courier New). Nie je dôkazom presného rasterizovania na controlleri; systém môže chýbajúci font nahradiť.
- Neimplementované v tomto celku: upload fontov, vendor publikovanie a fyzický dispatch návrhu; import stále nie je dôkazom pixel-perfect vendor renderingu.
- Najviac 100 prvkov; dokument do 256 KiB; text do 2 000 znakov; font 4–96 px. Prvky musia byť v hraniciach displeja. Rozmery a súradnice sú celé čísla.
- Ukážkové dáta sú najviac 100 pomenovaných scalar hodnôt; nepodporujú vykonávanie výrazov alebo skriptov.
- Farby sú zámerne obmedzené na paletu modelu. Pri presune/zmene rozmerov editor obmedzí prvok na plátno; importované neplatné dokumenty odmietne.

## API lokálnych návrhov

| Metóda a cesta | Telo | Výsledok |
|---|---|---|
| GET `/api/template-drafts` | — | `{items:[record,...]}` |
| POST `/api/template-drafts` | dokument | HTTP 201 + record |
| GET `/api/template-drafts/{id}` | — | record alebo 404 |
| PUT `/api/template-drafts/{id}` | `{revision,document}` | nová revízia alebo 409 |
| DELETE `/api/template-drafts/{id}` | `{revision}` | 204 alebo 409 |
| GET `/api/template-draft-sources?controller_id={id}` | — | read-only živý katalóg `{items,controller_id}` |
| GET `/api/template-draft-sources/{vendor_id}?controller_id={id}` | — | neuložená kópia `{document,warnings,source}` |

`record` obsahuje `id`, `revision`, `document`, `created_at`, `updated_at`. Dokument obsahuje presne `schema_version` (1 alebo 2), `name`, `model_id`, `elements`, `sample_data`. V1 návrhy zostávajú čitateľné bez dátovej migrácie; pridanie média/prepnutie na médium automaticky používa V2. V2 obrázok má navyše `image_data,image_fit`, barcode `barcode_format:CODE128`, QR `error_correction`; nadbytočné/nesúvisiace polia sa odmietajú. Neznáme query parametre sa odmietajú. Každá mutácia má rovnaké session/Origin kontroly ako zvyšok aplikácie a transakčne pridáva audit udalosť. Ochrana revíziou bráni tichému prepisu z druhého okna. Tabuľka `template_drafts` je aditívna, inicializuje sa pri prvom použití draft API a nemení verziu existujúcej core schémy. Zdrojové GET API vyžaduje nakonfigurovaný non-legacy controller, je read-only a nevyžaduje write session.

Exportovaný dokument neobsahuje prihlasovacie údaje. ID importovaných prvkov sú stabilné lokálne menovky `vendor-{pôvodné_id}`, nie oprávnenie upravovať serverové komponenty. Je to prenosný lokálny formát, nie priamy vendor `orderJson`.

## Overené read-only discovery zariadenia

Na používateľom určenom `http://192.168.16.251/esls_new` bolo overené:

- prihlasovanie existujúcim vendor klientom cez `name` + MD5 `passwd`, session cookie a autentifikovaný probe;
- katalóg `/associate/getStyleMsgs`: 65 záznamov;
- `/style/getDispMsData?id=145`: 6 textových elementov;
- `/style/getStyleData?id=145`: autoritatívne metadata a komponenty.

Pri tomto prvom prieskume sa nevykonali vendor mutácie. Požiadavky boli sériové s minimálne 5 s odstupom; credentials/session sa nevypisovali. Používateľov lokálny `.env` má citované hodnoty vo formáte `username: ...`, `password: ...`, nie shell `KEY=VALUE`; bol prečítaný iba dátovým parserom a je ignorovaný Gitom. Nie je automaticky načítavaný aplikáciou. Následná aktivácia režimu `--templates-only` na webe overila živý katalóg 66 šablón, 13 kompatibilných; skutočný browser načítal šablónu 145 so šiestimi prvkami iba GET požiadavkami. Žiadne šablóny na zariadení sa nemenili.

Dôležité rozdiely oproti lokálnemu formátu:

- vendor identita mapovania je `mpname`, nie `feil` (pri textoch môže byť všade `text`);
- pozície a rozmery sú CSS reťazce (`left`, `top`, `width`, `height`), fonty sú vendor špecifické;
- živý layout používa aj historické `board-width`; nesmie sa potichu zameniť za ľubovoľnú CSS vlastnosť pri publikovaní;
- minimálne jeden zdrojový prvok presahuje šírku obrazovky. Import musí zobraziť konflikt alebo explicitne odsúhlasenú normalizáciu, nie tvrdiť bezstratový prenos.

## Matica pre ďalšie vertikálne celky

Verejné vzory pre UX:

- https://github.com/koosoli/ESPHomeDesigner — vizuálny editor E-Ink/OLED/LCD s drag-and-drop; README uvádza GPL 3.0.
- https://github.com/OpenEPaperLink/OpenEPaperLink/blob/master/ESP32_AP-Flasher/wwwroot/jsontemplate-demo-v2.html — JSON vstup a Canvas náhľad, nie kompletný drag-and-drop editor. Licencia repozitára je CC BY-NC-SA 4.0.

Ide iba o UX inšpiráciu; kód týchto ESL projektov ani ich renderer nebol prevzatý. Kompatibilita ich rádiového protokolu s kúpeným controllerom nie je preukázaná. Nové všeobecné MIT encodery kódov sú samostatne licencované v `static/vendor/`.

| Oblasť | Stav vlastnej aplikácie | Čo zostáva |
|---|---|---|
| Cenovky, telemetria, lokálny staging | existujúci backend + GUI | explicitné odoslanie konfigurácie, výsledky podľa MAC |
| Controllery a RF routery | registry + inventár | konfigurácia routerov podľa bezpečne overených route |
| Vendor šablóny a klonovanie | existujúci backend + GUI, read-only import kópie | presné vendor fonty a publikovanie vlastného layoutu |
| Vlastné návrhy | nový funkčný editor + SQLite/API | preklad do vendor formátu a publish workflow |
| Obrázky | lokálny upload, paleta, PNG persistence a statický import | vendor upload/delete a galéria |
| QR/barcode | offline UTF-8 QR a Code128, natívny SVG náhľad | ďalšie symbologie a vendor publish/read-back |
| Fonty | legacy upload route zdokumentovaná | licencie, zoznam dostupných fontov, bezpečný upload |
| Produkty/väzby/job/alerty | existujúci backend | účelové GUI a prepojenie jobu s overovaným dispatch |
| Meetingy, wake/register parametre | legacy route discovery | potvrdiť obchodný význam a riziká pred implementáciou |
| Fyzické delete/firmware | neprístupné | nenahrádzať API experimentom bez samostatného kontraktu |

Durable úlohy: ORB-00115 (parent), ORB-00116 (lokálny editor), ORB-00119 (médiá a read-only import), ORB-00117 (vendor publikovanie), ORB-00118 (zvyšné legacy workflows/QA). Lokálny editor nie je tvrdením o dokončenej náhrade všetkých funkcií starého systému.

## Testovanie

Z `webapp/`:

    python3 -m unittest discover -s tests -v
    python3 -m compileall -q esl_web tests
    node tests/designer_model.test.js
    node --check static/designer.js

Browser testy automaticky nájdu Chromium v Playwright cache alebo systémový Chromium; cestu možno explicitne zadať cez `ESL_CHROMIUM`. `designer_browser_flows.test.js` spúšťa Python fixture s disposable databázou a Chromium CDP, nie samotné `node --test tests/*.test.js` bez potrebných premenných. Artefakty: `webapp/test-artifacts/designer-browser/` (ignorované Gitom). Fyzický controller sa v automatických testoch nekontaktuje.
