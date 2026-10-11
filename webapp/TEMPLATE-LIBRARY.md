# Knižnica lokálnych ESL návrhov

Knižnica má 30 návrhov: 10 účelov pre každý z modelov `2.13TFT-BW` (250 × 132),
`2.13EPD-BWR` (250 × 122) a `2.9EPD-BWR` (296 × 128). Pôvodných 9 návrhov bolo
zachovaných; pribudlo 21. Varianty majú odlišné kompozície aj dátové kontrakty.

## Varianty a zamýšľané zdroje

| Variant | Rozloženie / použitie | Polia a budúci zdroj |
|---|---|---|
| `standard` | Regálová cena, Code128 a SKU | ERP/POS: názov, cena, SKU; katalóg: balenie; výpočet jednotkovej ceny |
| `promotion` | Akciový pás, cena a porovnávacia história | Cenová kampaň: označenie a platnosť; overená história: najnižšia cena za 30 dní |
| `details` | Cena vľavo, QR vpravo | Produktový katalóg/PIM: balenie, pôvod a skutočný odkaz na detail |
| `minimal` | Centrovaná veľká cena, minimum informácií | ERP/POS: `product_name`, `price`; PIM: `package_info`; výpočet: `unit_price` |
| `loyalty` | Dvojstĺpcová bežná a klubová cena | ERP/POS: `regular_price`; CRM: `member_price`, `membership_condition`; obe jednotkové ceny |
| `weighed` | Dominantná cena za kg, pôvod, trieda a PLU | ERP/POS: `price_per_kg`; PIM: `origin`, `quality_class`; katalóg váh: `plu_code` |
| `deposit` | Cena tovaru a záloh vľavo, celková platba vpravo | ERP/POS: `product_price`; politika obalov: `deposit_amount`; výpočet: `total_price` |
| `batch` | Cena a dátum vedľa seba, kontrastný pás šarže | Šaržový systém: `batch_code`, `date_label`, `expiry_date` |
| `technical` | Obrázok, značka, model, parametre a cena | PIM: `brand`, `model_code`, `specs`, `warranty_text` a obrázok; ERP/POS: cena |
| `warehouse` | Interná pozícia, množstvo, pokyn a Code128 | WMS: `stock_qty`, `stock_unit`, `pick_location`, `replenishment_status`; ERP: SKU |

## Čo je skutočne pripojené

Aktuálny zdroj všetkých textových a kódových bindingov je `document.sample_data`.
Hodnoty sú editovateľné lokálne ukážky uložené spolu s návrhom v SQLite.
Obrázok technického variantu je vlastné schematické monochromatické PNG v
`element.image_data`, nie fotografia konkrétneho produktu.

ERP/POS, CRM, váhy, história cien, PIM, šaržový systém a WMS NIE SÚ pripojené.
CSV/JSON/API sú navrhované vstupy budúcich adaptérov, nie hotové importéry.
Ani lokálne `/api/products` sa automaticky neviaže na tieto návrhy: obsahuje
najmä `name`, `sku`, `ean`, numerické `price`, `currency` a väzby, ale nie nové
špecializované údaje. Budúci adaptér musí mapovať `name → product_name`,
formátovať cenu a odmietnuť nekompatibilnú menu; ukážky používajú EUR.

Presná mapa každého bindingu, jeho významu a nepripojeného upstreamu je v
`template-presets/data-sources.json`. Názvy polí sa nemenia podľa modelu.

## Významové pravidlá

- Klubová bežná cena nie je zákonná predchádzajúca cena. Členstvo musí byť
  zrozumiteľné; klubový layout sám nepreukazuje cenovú ani právnu správnosť.
- Vážený predaj zobrazuje €/kg, nie cenu ľubovoľného balenia. PLU musí pochádzať
  z používaného katalógu váh. Jednotkové ceny vychádzajú z čistého množstva.
- Celková platba = cena výrobku + vratný záloh. Jednotková cena nezahŕňa záloh.
  Ukážkových 0,15 € nie je univerzálna sadzba pre všetky vratné obaly.
- Šarža a dátum musia patriť konkrétnemu tovaru. „Min. trvanlivosť“ a
  „spotrebujte do“ nie sú zameniteľné. Návrh nenahrádza povinné údaje na obale.
- Skladový variant je označený „SKLAD – LEN PRE PERSONÁL“, nemá predajnú cenu
  a nie je náhradou zákazníckej cenovky. Množstvo znamená dostupné ks na pozícii.
- Technické parametre a deklarovaná záruka musia byť overené u dodávateľa.
- Code128 nesie interné SKU, nie automaticky EAN-13. QR example.com je ukážka.
- Fonty a paleta sú otestované pre ukážkové hodnoty; po zmene dĺžky textu či
  ceny treba preveriť geometriu a čitateľnosť znovu pri natívnom rozlíšení.

## Súbory a overenie

Pôvodné návrhy: `template-presets/retail-sk/`; nové: `template-presets/extended-sk/`.
Výskum a právne zdroje pôvodných návrhov: `RETAIL-TEMPLATES.md`.

V editore otvorte „Uložené lokálne návrhy“ a obnovte zoznam. Reštart nie je
potrebný: nové lokálne záznamy sa načítajú cez existujúce draft API.

`test-artifacts/extended-presets/catalog.html` je samostatný offline prehľad
všetkých 30 skutočných náhľadov; pri každom sa dajú rozbaliť polia a zdroje.
V tom istom adresári sú overenia presného API read-backu, browserového renderu,
nezávislého dekódovania 9 natívnych Code128/QR a tri modelové obrázkové prehľady.

Nebolo vykonané publikovanie na controller, dispatch na cenovky ani reštart.
