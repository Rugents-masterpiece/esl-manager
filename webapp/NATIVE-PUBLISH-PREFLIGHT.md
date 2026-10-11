# Natívne nasadenie lokálnych návrhov — overený preflight

Stav: nenasadené; žiadna nová šablóna, priradenie ani displej na controlleri
sa počas tohto preflightu nemenili. Súhlas s publikovaním používateľ už dal;
nový súhlas s reštartom ESL webu ešte neprišiel. Timeout otázky nie je súhlas.

## Doložené výsledky

- Aktívny cieľ: `default`, `http://192.168.16.251/esls_new`.
- ESL web na porte 10050 je aktívny, v režime `read_only`; launcher používa
  `--templates-only` a obmedzuje klienta na čítanie šablón/obrázkov.
- Reálne autentifikované čítanie katalógu: 66 pôvodných šablón, 13 v troch
  presných podporovaných rodinách. Knižnica 30 nových návrhov je stále lokálna.
- Reálne čítanie existujúcej šablóny 145 potvrdilo rozdiel medzi screen type
  (catalog `type=2`) a alignment (`getStyleData.type=9`). Rozmer je 250 × 122.
- `POST /style/getDispMsData?id=145`, telo `{}`, vrátilo natívne komponenty
  s `mpname`, `feil`, pridelenými číselnými ID a CSS štýlom. Toto nie je náš
  draft JSON. Endpoint `getStyleData` obsahuje inú schému `dispMs`.
- `GET /mms/getDispMs?id=145` potvrdilo natívne ovládanie textu, photo, barcode
  a qrcode; fontový výber uvádza HuaweiSans, nie lokálny Arial/Courier New.
  Prítomnosť položky v UI sama nepotvrdzuje pixelovú ani diakritickú zhodu.
- Upload formuláre používajú multipart súbory `photo` a `redphoto`.
- Read-only diagnostika zachovala päťsekundové rozostupy vendor klienta.

## Rozdelenie implementácie

1. Overený preflight a kontrakty: tento dokument + artefakty.
2. Natívny prekladač a publikovanie: oddelený adaptér, explicitné mapovanie
   field/element ID, zachovanie dynamických dát a natívne fonty. Zvlášť overiť
   24 obdĺžnikov, 3 PNG, 6 Code128 a 3 QR, vrátane ochranných okrajov a ECC.
   Najprv jeden kontrolovaný nový návrh, potom ostatné; žiadne prepisovanie
   existujúcich šablón, žiadne slepé opakovanie nejednoznačnej mutácie.
3. Ručný výber a integrácia: uložiť overené vendor ID/model/mappingtype do
   lokálneho katalógu, zosúladiť ručný výber a payload polí; oddeliť uloženie
   priradenia od fyzického dispatchu. Zmenu režimu webu nasadiť len po výslovnom
   súhlase s reštartom. Nikdy automaticky neposlať aktualizáciu žiadnej cenovke.

## Kontrakty a riziká

Existujúci `VendorClient` má create/add-field/rename/layout primitíva, nie
publisher lokálnych návrhov. Clone API nie je náhradou prekladača. Natívne
pole sa identifikuje `mpname`, nie `feil`; rovnaký binding vo viacerých prvkoch
vyžaduje explicitné aliasy a odpovedajúce mapovanie dispatch payloadu.

Captured `esl/component.js:1135` ukladá cez `POST /style/updateDispMData`, kým
`:1191` a aktuálny `vendor.py:461` používajú `/mms/updateDispMData`. Staršie
pozorovania uvádzajú prijaté, ale ignorované uloženie. Pred hromadným zápisom
musí nový vlastnený cieľ prejsť read-backom celého layoutu a natívneho náhľadu;
HTTP 200 ani meno v katalógu nestačia. Natívne rectangle/line, fonty, PNG fit,
barcode symbologia a QR ECC sa nesmú iba predpokladať alebo ticho vynechať.
Celý návrh nesmie byť ticho sploštený na obrázok so stratou dynamických polí.

Ručné lokálne priradenie už existuje, ale nemení okamžite controller/displej.
`GET /api/templates` číta SQLite. Nové controller šablóny preto potrebujú
explicitne importované overené metadáta, nie len vzdialený create.

## Artefakty

`test-artifacts/publish-preflight/catalog.json`, `145.json` a
`native-form-contract.json` zachytávajú skutočné odpovede, bez hesiel/cookies.
Diagnostické skripty `/tmp/esl-publish-preflight.py` a
`/tmp/esl-native-form-contract.py` sú read-only; nejde o hotový publisher.

Publikovanie 30/30, ručné priraďovanie z nového katalógu a fyzická použiteľnosť
zatiaľ nie sú overené. Controller ani web sa nereštartovali.
