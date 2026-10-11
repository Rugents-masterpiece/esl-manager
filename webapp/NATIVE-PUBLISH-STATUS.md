# Natívne publikovanie — integračný checkpoint

## Overené pred spustením knižnice

- Používateľ potvrdil publikovanie a reštart iba `esl-manager.service`.
- Fyzické odoslanie ostáva samostatnou ručnou akciou s presným potvrdením;
  nasadzovací proces nikdy nevolá `update_screen` ani nemení priradenia.
- Kompletná Python sada: 317 testov PASS. Compile, JS syntax a diff check PASS.
- Compiler → publication registry: všetkých 30 dokumentov má kompatibilné
  aliasy/bindingy; offline publikácia aj spätné načítanie evidencie PASS.
- Čerstvý vlastný pilot ID 164 má overený editor, `dispMs`, model, mapping,
  foto bajty a natívny PNG. Nejde o finálnu knižničnú šablónu.
- Skutočný pilot PNG: Code128 `123456789012` decoded; QR
  `DEMO-QR-SK-123456` decoded s ECLevel M; ikona prítomná; slovenské znaky
  a biely text na červenom pozadí vizuálne overené.

## Príčina chýbajúceho QR/ikony a oprava

Nesprávne `table=tb_tagsandgoods` na komponentoch `photo` umožnilo uloženie
layoutu a spätné načítanie PNG bajtov, ale renderer obrázky vynechal.
Natívne vytvorený obrázkový komponent používa `table=tb_photos`.
Prekladač teraz zachováva správny zdroj aj pre odvodené obdĺžniky a QR.
Regresia kontroluje source table vo všetkých 30 návrhoch; fake controller
teraz vracia skutočný zdroj komponentu namiesto pevnej produktovej tabuľky.

Ďalšie overené obmedzenia controllera: z-index 0, border width 1, natívny QR L.
Statické dekorácie používajú RGBA masky, dynamické texty vlastné rovnomerné
pozadie a QR štandardný offline PNG renderer s presnou korekciou M.
Runtime aplikácie ostáva bez Pillow/ZXing; tie sú iba izolované QA nástroje.

## Natívne metriky fontov

Prvé reálne knižničné náhľady odhalili orezanie ceny pri päte a zalomenie
symbolu eura. Pevná veľkosť fontu na controlleri nezodpovedá metrikám
lokálneho Arialu. Natívny text teraz používa `autoReacting=true`
(jednoriadkové prispôsobenie). Táto adaptácia je uvedená v diagnostike;
zdrojové dokumenty sa nemenia. Controller môže zmeniť aj zdanlivý rez fontu,
preto sa netvrdí pixelová zhoda s lokálnym editorom.

Beh sa po náleze zastavil. Iba preukázateľne vlastné ID 165–168 a pilot 164
sa opravili bez vytvárania duplikátov; editor, komponenty, model a skutočný
PNG sa znovu overili. Journaly opravy sú pri jednotlivých návrhoch.

## Dokončená knižnica

`/tmp/esl-publish-library.py --run` dokončil sériové publikovanie, s odstupom
aspoň 5 sekúnd po každej controllerovej požiadavke. Nejasné mutácie sa
neopakujú. Každý návrh má vlastný journal, natívny readback a PNG; kódy
v PNG sa dekódujú pred registráciou. PNG ikony nesmú byť prázdne.

Autoritatívny priebeh: `test-artifacts/native-deployment/library/progress.json`.
`status=verified` môže vzniknúť iba po 30 rôznych vendor ID, presnom
SQLite/readbacke a kontrole nezmenených pôvodných šablón, tagov a draftov.
Samotné spustenie procesu nie je potvrdením dokončenia.

Checkpoint/SQLite backup: `test-artifacts/native-deployment/library/`.
Overený pilot: `test-artifacts/native-deployment/verified-pilot/`.

## Nasadený web a posledný checkpoint

`esl-manager.service` bol reštartovaný iba pre web. Aktívny launcher:
`--template-publish --allow-confirmed-dispatch`; LAN health `live_enabled`.
Manuálne odoslanie na jeden MAC stále vyžaduje autentifikáciu, explicitné
dáta a presnú potvrdzovaciu frázu. Pôvodný hromadný dispatch je blokovaný.

Živý API smoke PASS: anonymný apply 401; cudzí Origin, nesprávne potvrdenie
a pôvodný batch dispatch 403. Skutočný Chromium na LAN overil výber
kompatibilnej publikovanej šablóny a ručný dialóg; bez potvrdenia je submit
zakázaný. Nulový počet browserových mutácií a runtime chýb.

Finálny checkpoint je `status=verified`: 30/30 knižničných šablón, ID 165–194,
presne desať pre každý model. Všetkých 30 má natívny readback, skutočný PNG,
QA kontrolu kódov/obrázkov a evidenciu v SQLite. Čerstvé živé API vrátilo
rovnakých 30 dvojíc draft/vendor ID a rozdelenie 10/10/10.
Pôvodných 66 natívnych šablón, všetky tagy/priradenia a lokálne návrhy
zostali nezmenené. Finálne galérie všetkých 30 skutočných náhľadov sú
`library/gallery-{model}.png`; nejde o lokálne simulované náhľady.

Dôkazy: `test-artifacts/native-deployment/live-acceptance.json`,
`browser-acceptance.json`, `manual-apply-dialog.png` a
`library/latest-readback.json`. Worker `proc_2862f7bd6d99` skončil s exit 0;
predošlý hromadný `proc_a4f37ae4bfa5` je zastavený, nesmie sa opakovať naslepo.
Controller/router sa nereštartuje. Bez commitov/pushov.
