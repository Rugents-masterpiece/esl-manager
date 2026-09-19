# ESL Manager - Index pokusov

## Prehľad

Tento adresár obsahuje všetky pokusy o komunikáciu s ESL serverom na adrese `192.168.16.251`.

## Kategórie

### login/ - Prihlásenie
- `esl_login_update.py` - Programmatic login s http.cookiejar (hlavný)
- `esl_login.py` - Základný login pokus
- `esl_login_main.py` - Login a stiahnutie main.js
- `esl_login_index.py` - Login a stiahnutie index.html
- `esl_index_after_login.py` - Analýza index.html po prihlásení
- `esl_index_after_login2.py` - Re-analýza index.html po prihlásení
- `esl_analyze_login.py` - Analýza login endpointu

### styles/ - Štýly
- `esl_inspect_style.py` - Inspekcia štruktúry štýlu 146
- `esl_analyze_style_js.py` - Analýza style.js
- `esl_download_style_js.py` - Stiahnutie style.js
- `esl_find_style_js.py` - Nájdenie style.js
- `esl_update_style.py` - Test updateStyle endpointu
- `esl_verify_updatestyle.py` - Overenie updateStyle zmien
- `esl_debug_addstyle.py` - Debug addStyle formátu
- `esl_debug_updatestyle.py` - Debug updateStyle formátu
- `esl_debug_updatestyle2.py` - Re-debug updateStyle formátu

### create/ - Vytváranie
- `esl_create_and_populate.py` - Vytvorenie nového štýlu s dátami z 146
- `esl_create_and_populate2.py` - Aktualizovaná verzia (addStyle s JSON)
- `esl_create_new.py` - Vytvorenie nového štýlu s novým ID
- `esl_clone_red.py` - Klonovanie štýlu 146 s červenými farbami
- `esl_find_create_endpoint.py` - Nájdenie endpointu pre vytváranie

### update/ - Aktualizácia
- `esl_change_colors.py` - Priama zmena farieb na štýle 146
- `esl_debug_updatedisp.py` - Debug updateDispMData formátu
- `esl_update_test.py` - Test updateDispMData s unchanged orderJson
- `esl_update_json.py` - Test updateDispMData s JSON body
- `esl_update_headers.py` - Test updateDispMData s presnými hlavičkami
- `esl_find_updatedisp_in_html.py` - Nájdenie updateDispMData v HTML

### debug/ - Debugovanie
- `esl_debug_app_js.py` - Analýza app.js a test updateDispMData
- `esl_debug_params.py` - Debug parametrov a updateStyle s JSON
- `esl_debug_params2.py` - Re-debug parametrov
- `esl_json_body.py` - Test updateStyle s JSON body

### analysis/ - Analýzy
- `esl_analyze_app.py` - Analýza app.js pre updateDispMData
- `esl_analyze_app2.py` - Re-analýza app.js
- `esl_analyze_endpoints.py` - Analýza tag/update a style/styleId
- `esl_analyze_endpoints2.py` - Re-analýza endpointov
- `esl_analyze_html.py` - Analýza ESL dashboard HTML
- `esl_analyze_index.py` - Analýza index/index.html
- `esl_analyze_index_js.py` - Analýza app/js/index.js pre updateDispMData
- `esl_analyze_main_index.py` - Analýza main/index.html
- `esl_download_and_analyze.py` - Stiahnutie a analýza app.js

### js/ - JavaScript analýzy
- `esl_all_js.py` - Nájdenie všetkých JS súborov v app/js/
- `esl_download_app.py` - Stiahnutie app.js
- `esl_download_index_js.py` - Stiahnutie index.js
- `esl_dump_main_index.py` - Dump main/index a hľadanie inline JS
- `esl_find_all_js.py` - Hľadanie updateDispMData vo všetkých JS
- `esl_find_js2.py` - Nájdenie main JS súboru z HTML
- `esl_find_js3.py` - Nájdenie JSP/HTML linkov v dashboard
- `esl_find_js.py` - Nájdenie JS súborov z dashboardu
- `esl_json_body.py` - Test updateStyle s JSON body
- `esl_main_index.py` - Stiahnutie main/index HTML

### tags/ - Tagy
- `esl_analyze_tag.py` - Analýza tag.js pre updateDispMData
- `esl_analyze_tag2.py` - Re-analýza tag.js a app.js
- `esl_analyze_tag_js.py` - Analýza tag.js pre updateDispMData
- `esl_analyze_tag_js2.py` - Analýza tag.js pre všetky endpointy
- `esl_analyze_tag_update.py` - Analýza tag/update endpointu v tag.js
- `esl_download_tag.py` - Stiahnutie a analýza tag.js
- `esl_download_tag_js.py` - Stiahnutie tag.js (30KB)

### test/ - Testy
- `esl_test.py` - Základný test
- `esl_test_all.py` - Kompletný testovací suite
- `esl_test_all_endpoints.py` - Test všetkých endpointov
- `esl_tester.py` - Testovací skript pre live server validáciu
- `esl_test_targeted.py` - Cielený test
- `esl_test_v2.py` - Verzia 2 testovacieho skriptu

### misc/ - Ostatné
- `esl_cli.py` - CLI rozhranie
- `esl_dump_html.py` - Dump main/index a hľadanie inline JS
- `esl_inline_scripts.py` - Analýza inline skriptov v HTML
- `esl_manager.py` - Hlavná knižnica
- `esl_organize.py` - Organizácia skriptov
- `esl_setup_workspace.py` - Nastavenie workspace

## Kľúčové zistenia

1. `addStyle` vracia 500 ale štýl sa vytvorí (NPE bug)
2. `updateStyle` funguje len pre meta-dáta (nie orderJson)
3. `updateDispMData` vracia 200 OK ale dáta sa neukladajú
4. Endpoint pre `orderJson` nie je v statických JS súboroch
5. Browser automatizácia nie je dostupná
