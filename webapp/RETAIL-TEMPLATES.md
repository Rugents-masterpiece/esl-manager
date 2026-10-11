# Slovenské maloobchodné šablóny ESL

## Výsledok

Tento dokument opisuje pôvodných 9 návrhov z internetového prieskumu.
Rozšírená knižnica má teraz 30 návrhov, po 10 pre každý model; ďalšie účely,
dátové polia a stav zdrojov opisuje [TEMPLATE-LIBRARY.md](TEMPLATE-LIBRARY.md).

Pre každý podporovaný model sú pripravené tri editovateľné lokálne návrhy:

| Model | Natívne rozmery | Paleta | Varianty |
|---|---|---|---|
| `2.13TFT-BW` | 250 × 132 px | čierna/biela | Základná, Akcia, Produkt s QR |
| `2.13EPD-BWR` | 250 × 122 px | čierna/biela/červená | Základná, Akcia, Produkt s QR |
| `2.9EPD-BWR` | 296 × 128 px | čierna/biela/červená | Základná, Akcia, Produkt s QR |

Deväť JSON dokumentov v `template-presets/retail-sk/` používa existujúcu schému návrhov v2. Kópie sú uložené v lokálnej databáze a dostupné cez „Uložené lokálne návrhy“. Nie sú to publikované vendor šablóny ani export určený priamo pre fyzické zariadenia.

## Internetový prieskum a prioritizácia údajov

Ide o kvalitatívny prieskum stránok výrobcov a slovenských právnych pravidiel, nie štatistiku celého trhu. Z týchto zdrojov nemožno vyvodiť percentá používania ani presné poradie najčastejších požiadaviek.

Praktický základ cenovky je identifikácia produktu a jasná cena. Zvolená hierarchia je:

1. **Názov produktu a balenie/variant.** Zákazník musí vedieť, ktorému tovaru cena patrí. Ukážky cenoviek na stránkach Hanshow predstavujú produktové a cenové informácie; výrobca zdôrazňuje čitateľnosť a flexibilné produktové/promo zobrazenie [1, 2].
2. **Výrazná predajná cena a mena.** Ceny sú väčšie než pomocné údaje. Predajná cena v slovenskom zákone znamená konečnú cenu vrátane DPH a ostatných daní [4, § 2 písm. g)].
3. **Jednotková cena, napríklad €/kg alebo €/l.** Umožňuje porovnanie rôznych balení. Nie je len dizajnový doplnok: slovenský zákon rieši jej zobrazenie a výnimky [4, § 2 písm. h), § 6].
4. **Akciové označenie, aktuálna cena a predchádzajúca referenčná cena.** Farba podporuje odlíšenie akcie [1, 2]. Pri oznámení zníženia na Slovensku treba pracovať s právnou definíciou predchádzajúcej ceny, nie ľubovoľnou katalógovou cenou [4, § 7].
5. **Čiarový kód ako identifikátor.** Je užitočný pri práci s položkami. V tomto projekte ide o existujúci CODE128 s interným SKU; samostatný text SKU je praktický doplnok našich návrhov, nie doložená univerzálna požiadavka trhu.
6. **QR odkaz na rozšírené produktové informácie.** Pricer výslovne opisuje QR na cenovke ako cestu k údajom o pôvode, výrobcovi, bio/vegan vlastnostiach, receptoch alebo recyklácii [3]. Na malom displeji je vhodnejší odkaz než pokus zobraziť všetky informácie naraz.

Údaje o sklade, regálovej pozícii, dodávateľovi či internom workflow môžu byť užitočné pre personál, ale na týchto malých zákazníckych cenovkách by konkurovali názvu, cene a jednotkovej cene. Preto nie sú predvolene zobrazené. Dlhé zloženie, alergény a výživové údaje patria v QR variante na odkazovanú produktovú stránku; QR nesmie automaticky nahrádzať povinné označenia na výrobku.

## Tri varianty

### Základná – cena a kód

Názov, balenie/pôvod, veľká cena s DPH, jednotková cena, CODE128 a textové SKU. Ukážka: extra panenský olivový olej 500 ml, 4,99 €, 9,98 €/l.

### Akcia – porovnanie ceny

Kontrastný pás „AKCIA“, dátum platnosti, názov, balenie, veľká akciová cena, jednotková cena a samostatný riadok „Najnižšia cena za 30 dní“. BWR modely používajú červený pás a cenu; BW model čierny pás a biely nápis. Ukážka: olej 500 ml, 3,49 €, 6,98 €/l, referenčná cena 4,99 €.

Nezobrazujeme automaticky percento zľavy. Bez overenej cenovej histórie by percento alebo prečiarknutá „bežná cena“ mohli zavádzať. Dátum platnosti je dátové pole, nie plánovač automatického skončenia akcie.

### Produkt – detaily cez QR

Názov, balenie/pôvod/trieda, veľká cena, jednotková cena, SKU a QR na produktové detaily. Ukážka: BIO jablká Gala v balení 1 kg, 2,49 €, 2,49 €/kg. Označenie BIO a pôvod sú len ukážkové hodnoty, nie overené tvrdenia o skutočnom výrobku.

## Dátové polia

| Pole | Význam | Použitie |
|---|---|---|
| `product_name` | Názov a prípadný variant | všetky |
| `package_info` | Balenie, množstvo, prípadne pôvod/trieda | všetky |
| `price` | Formátovaná predajná cena bez meny, napr. `4,99` | všetky; element pridáva ` €` |
| `unit_price` | Kompletná jednotková cena, napr. `9,98 €/l` | všetky |
| `sku` | Interné číslo položky | základná a QR |
| `promotion_label` | Napr. `AKCIA` | akcia |
| `promotion_validity` | Text platnosti, napr. `Do 31. 12. 2026` | akcia |
| `lowest_30d_price` | Overená predchádzajúca cena podľa vhodného pravidla | akcia |
| `product_url` | Krátky HTTPS odkaz na produkt | QR |

Polia sa čítajú zo `sample_data` existujúcim literal bindingom. Tieto šablóny nevytvárajú integráciu s ERP, nezisťujú sklad a nepočítajú cenovú históriu. Cena, jednotková cena aj referenčná cena musia pochádzať zo správneho dátového zdroja. Ukážkové údaje, SKU, ceny a platnosť sú fiktívne. QR `https://example.com/p/10001` je výslovne zástupný odkaz, nie fungujúca produktová stránka.

## Právne rozlíšenie

Overený zdroj: zákon č. 108/2024 Z. z., časová verzia účinná od 27. 9. 2026 [4].

- § 6 ods. 1 vyžaduje jednoznačné a ľahko čitateľné označenie predajnou a jednotkovou cenou. Jednotková cena nemusí byť osobitne vyznačená, ak je zhodná s predajnou; tovar predávaný na množstvo sa označuje len jednotkovou cenou. Odseky 2–4 uvádzajú ďalšie výnimky a osobitosti; nevzťahovať požiadavku bez rozdielu na každý produkt.
- § 7 ods. 1–2 pri oznámení zníženia ceny stanovuje predchádzajúcu cenu ako najnižšiu cenu počas 30 dní pred znížením, alebo od začiatku predaja, ak je výrobok v predaji kratšie. Odsek 3 upravuje postupné znižovanie a odsek 4 výnimku pre rýchlo sa kaziaci tovar.
- Akciový variant predvolene predpokladá štandardný prípad tovaru predávaného aspoň 30 dní. Pri inom režime treba zmeniť obsah/popis referenčnej ceny a overiť použiteľnosť. Samotná existencia riadka nepreukazuje zákonnosť akcie.

Toto je podklad pre vývoj šablón, nie právne schválenie reálneho nasadenia.

## Technické hranice a overenie

- Rozmery a palety striktne zodpovedajú existujúcim trom rodinám v aplikácii.
- Čiarový kód je **CODE128**, nie EAN-13 ani GS1-128. Hodnota je interné 12-miestne SKU. Neoznačovať ho za pokladničný EAN; kompatibilita s konkrétnou pokladnicou nie je overená.
- QR používa korekciu M a plochu 76 × 76 px. Dlhší URL môže vyžadovať väčšiu plochu alebo krátky odkaz; existujúci editor odmieta príliš malý kód.
- Názov má rezervu pre dva riadky. Reálny Chromium test skúša aj dlhší slovenský názov. Neexistuje automatické zmenšovanie písma: pri výrazne dlhších hodnotách treba upraviť font alebo rozmery.
- Všetkých deväť návrhov má presný read-back z bežiaceho GET API a načítanie cez skutočné UI editora. Kontroluje sa orezanie textu, médium, paleta a JavaScript chyby.
- Tri CODE128 a tri QR boli nezávisle dekódované pomocou ZXing z natívneho rastra SVG vykresleného editorom. Nie je to test fyzického displeja alebo reálnej čítačky.
- Unit regresie kontrolujú presné modely, deväť súborov, schému, dátové polia, nekolidujúce prvky, jednotkové ceny ukážok a CRUD na disposable SQLite.
- Prehľad náhľadov a doklady sú v `test-artifacts/retail-presets/`. Tieto runtime artifacts sa necommitujú.
- Controller zostáva v režime iba čítania šablón. Vytvorenie lokálnych návrhov nevyžadovalo vendor zápis ani reštart služby.

## Zdroje

[1] Hanshow, Nebular — čitateľnosť produktových informácií a flexibilná prezentácia promo údajov: https://www.hanshow.com/en/nebular

[2] Hanshow, Polaris Pro — produktové detaily na kompaktných cenovkách a cenové aktualizácie: https://www.hanshow.com/en/polaris-pro

[3] Pricer, Mobile Product Information — výslovná podpora QR na detaily a pôvod produktu: https://www.pricer.com/use-cases/shopper-engagement/mobile-product-information

[4] Slov-Lex, zákon č. 108/2024 Z. z., záväzné PDF, účinné od 27. 9. 2026, najmä § 2, § 6 a § 7: https://static.slov-lex.sk/pdf/SK/ZZ/2024/108/ZZ_2024_108_20260927.pdf
