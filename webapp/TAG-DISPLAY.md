# Stav displeja z controllera

## Pevný rozmer a kompatibilita

Rozmer v pixeloch a model existujúcej cenovky sú nemenné v editácii aj cez
API lokálnej konfigurácie. Detail zobrazuje jediný uzamknutý model s rozmermi;
výber modelu je možný iba pri vytvorení nového lokálneho staging záznamu.
Názvy šablón v zozname, výbere, klonovaní a potvrdení odoslania zobrazujú
`šírka × výška px`; uložené vendor názvy sa neprepisujú.
Výber a fyzické použitie vyžadujú zhodu šírky, výšky aj typu displeja.
Ani rovnaké rozmery s iným farebným typom nie sú kompatibilné.

## Controllerový náhľad

`GET /api/tags/{local_tag_id}/display` bez query a bez tela načíta aktuálne
controllerové údaje. Controller sa vyberá zo záznamu cenovky, nie z klientskych
parametrov. Lokálny staging nemá fyzický displej. Operácia nemení inventár,
audit ani cenovku a nikdy neopakuje dispatch.

Backend najprv kanonicky porovná identitu v MMS inventári (číselná uint32 MAC
oproti lokálnej bodkovanej MAC), potom načíta presné interné ID cez
`GET /tag/getTagById?id={id}`. Odpoveď musí mať rovnaké ID a MAC. Výstup obsahuje
`style_id`, `update_progress`, `updated_at_ms`, `read_at`, rozmery a
`physical_screen_verified: false`. `preview_url` smeruje na existujúcu
same-origin proxy PNG aktuálne priradenej natívnej šablóny.

Obrázok je náhľad šablóny na controlleri. Nie je fotografiou ani pixelovým
read-backom fyzického displeja a nemusí obsahovať konkrétne produktové dáta
cenovky. API na čítanie obrazových bodov fyzickej cenovky nebolo v dostupných
aktívach preukázané. Živý stav 4 je údaj controllera, nie automatický dôkaz
úspechu historického neovereného pokusu.

V detaile cenovky otvorte „Stav displeja na controlleri“ a kliknite na
„Načítať stav a náhľad z controllera“. Načítanie je ručné, bez automatického
pollingu. Neskorá odpoveď nesmie prekresliť inú cenovku; chyba obrázku musí byť
viditeľná a nikdy sa nenahrádza novou vybranou šablónou ani demo obrázkom.

Overenie nasadenia: 337 testov PASS; živý GET a PNG HTTP 200; Chromium LAN
flow s používateľským kliknutím, bez mutácií/runtime chýb. Pre 92.80.88.48
controller v čase overenia vrátil interné ID 8, priradenú šablónu 96 a stav 5
(neaktualizovaná). Vybraný pokus na šablónu 166 sa neopakoval. Reštartovaná bola
iba webová služba. Inventár aj audit ostali nezmenené.

Dispatch preflight/read-back používa rovnakú kanonizáciu MAC, ale zachováva
zdokumentovaný bodkovaný formát `/associate/updateScreen` v odosielanom tele.
Oprava bola overená offline vrátane duplicít, stale-success a no-retry brán;
nový fyzický dispatch počas tejto práce nebol vykonaný.

## Natívny prenos verzus staré MMS priradenie

Natívny editor controllera (`app/js/component-v2/component/js/component.js`,
`setUpdateScreenCode`) generuje pole JSON s `mac`, `mappingtype`, `styleid`
a všetkými aliasmi prvkov, bez `ABDisplayFlag`. Staršie konferenčné GUI
`meetingRefresh.js` používa odlišné telo: JSON reťazec a `ABDisplayFlag`.
Tieto protokoly nemožno miešať. Kontrola presného modelu, potvrdenie, dvojitá
write brána a durable attempted audit ostávajú pred každým prenosom.

Pri natívnom prenose je relevantný stav z `/associate/getTagsMsg` a čerstvý
`tag.tagAndGood.status`/`timestamp` z identity-overeného detailu.
Samotný starý `tag.updateProgress`, uložené `tag.styleid`, `showStyle` ani
náhľad `/style/getStylePreview` nepotvrdzujú obsah posledného natívneho
prenosu. Staré MMS priradenie môže zostať nezmenené. Status 4 bez čerstvého
časového dôkazu tiež nepotvrdzuje konkrétny nový pokus.

Display API zachováva pôvodné MMS polia a pridáva `native_update_progress`
a `native_updated_at_ms`. GUI tieto dve vetvy označuje oddelene; starý MMS
obrázok nikdy nepremenuje na čítanie fyzickej obrazovky.

Živý kontrastný test na 92.81.10.37 odoslal šablónu 182 a dáta TEST 03
Ovsené vločky podľa natívneho príkladu. Čas `tag.updatetime` sa zmenil z
1779717034000 na 1791657431000 a natívny detail zaznamenal status 4 s novým
`tagAndGood.timestamp` 1791657409000; MMS ostalo šablóna 98 / stav 5.
Doslovné produktové dáta ani pixely nového obrazu však detail nevracia.
`test-artifacts/manual-live-20261010/expected-content-scoped-tag-10.png`
je výslovne označená lokálna vizualizácia odoslaných údajov, nie read-back.
