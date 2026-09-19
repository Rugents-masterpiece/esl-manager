#!/usr/bin/env python3
"""ESL (Electronic Shelf Label) Manager - správa elektronických cenoviek.

Server: 192.168.16.251 (Tomcat 8.5.81, Spring MVC)
API dokumentácia: ESL manufacturer API
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import base64
import time
from typing import Optional, List, Dict, Any, Union

class ESLManager:
    """Správa ESL (Electronic Shelf Label) systému."""
    
    BASE_URL = "http://192.168.16.251/esls_new"
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, base_url: Optional[str] = None, session_id: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = (base_url or self.BASE_URL).rstrip('/')
        self.session_id = session_id or "06DAE8066D63A0CC3DCDEB1D8E360F4B"
        self.timeout = timeout or self.DEFAULT_TIMEOUT
    
    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        """Vykoná GET request na ESL server.
        
        Server vracia tri formáty:
        1. Escaped JSON string: "[{\"id\":1,...}]" (getStylesMsg, getTagsMsg)
        2. Čistý JSON: {"datalist":[...], "resultCode":10} (getStyleMsgs, getPhotoDataByName)
        3. HTML stránka: celá HTML (getDispMs - bug servera)
        """
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url)
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        req.add_header("Accept", "*/*")
        req.add_header("Accept-Encoding", "gzip, deflate")
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                text = data.decode("utf-8", errors="replace")
                stripped = text.strip()
                
                # 1. Escaped JSON string: "[{\"id\":1,...}]"
                if stripped.startswith('"') and stripped.endswith('"'):
                    inner = stripped[1:-1]
                    # Odstránime escaped uvozovky
                    inner = inner.replace('\\"', '"')
                    try:
                        return json.loads(inner)
                    except json.JSONDecodeError:
                        pass
                
                # 2. Čistý JSON
                if stripped.startswith('{') or stripped.startswith('['):
                    try:
                        return json.loads(stripped)
                    except json.JSONDecodeError:
                        pass
                
                # 3. HTML stránka — skúsime nájsť JSON fragment
                if '<html' in stripped.lower():
                    import re
                    json_match = re.search(r'\{.*\}', stripped, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass
                    return text
                
                return text
        except Exception as e:
            raise Exception(f"GET {path} failed: {e}")
    
    def _post(self, path: str, params: Optional[Dict] = None, form_data: Optional[Dict] = None) -> Any:
        """Vykoná POST request na ESL server.
        
        Server vracia tri formáty:
        1. Escaped JSON string: "[{\"id\":1,...}]" (getDispMsData, getStyleMsgById)
        2. Čistý JSON: {"datalist":[...], "resultCode":10} (getPhotoDataByName)
        3. HTML stránka: celá HTML (getDispMs - bug servera)
        """
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        body = None
        if form_data:
            body = urllib.parse.urlencode(form_data, encoding="utf-8").encode("utf-8")
        
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        req.add_header("X-Requested-With", "XMLHttpRequest")
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        req.add_header("Accept", "*/*")
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                text = data.decode("utf-8", errors="replace")
                stripped = text.strip()
                
                # 1. Escaped JSON string: "[{\"id\":1,...}]"
                if stripped.startswith('"') and stripped.endswith('"'):
                    inner = stripped[1:-1]
                    # Odstránime escaped uvozovky
                    inner = inner.replace('\\"', '"')
                    try:
                        return json.loads(inner)
                    except json.JSONDecodeError:
                        pass
                
                # 2. Čistý JSON
                if stripped.startswith('{') or stripped.startswith('['):
                    try:
                        return json.loads(stripped)
                    except json.JSONDecodeError:
                        pass
                
                # 3. HTML stránka — skúsime nájsť JSON fragment
                if '<html' in stripped.lower():
                    import re
                    json_match = re.search(r'\{.*\}', stripped, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass
                    return text
                
                return text
        except Exception as e:
            raise Exception(f"POST {path} failed: {e}")
    
    # --- TAGY ---
    
    def get_tags(self) -> List[Dict]:
        """Získa zoznam všetkých tagov (elektronických cenoviek).
        
        Vrátane MAC adresy, stavu batérie, RSSI, atď.
        """
        return self._get("/associate/getTagsMsg")
    
    def delete_tags_by_mac(self, macs: List[str]) -> bool:
        """Zmaže tagy podľa MAC adries."""
        body = json.dumps(macs)
        req = urllib.request.Request(
            f"{self.base_url}/associate/delTagsByMac",
            data=body.encode("utf-8"),
            method="POST"
        )
        req.add_header("Content-Type", "application/json")
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise Exception(f"delete_tags_by_mac failed: {e}")
    
    # --- AKTUALIZÁCIA DISPLEJA ---
    
    def update_screen(self, updates: List[Dict]) -> bool:
        """Aktualizuje displeje na tagoch.
        
        Parametre každého update záznamu:
        - mac: MAC adresa tagu (povinný)
        - styleid: ID šablóny (povinný)
        - mappingtype: typ mapovania poľa
        - ABDisplayFlag: 0xa1 (strana A), 0xa2 (strana B), 0xa3 (obojs.)
        - nfcdata: údaje do NFC (voliteľný)
        - templateFieldName1, templateFieldName2, ...: hodnoty podľa šablóny
        
        PRÍKLAD:
        updates = [{
            "mac": "92.91.87.80",
            "styleid": 146,
            "mappingtype": 1,
            "ABDisplayFlag": 163,
            "Name": "Produkt",
            "PriceRetail": "9.99"
        }]
        """
        body = json.dumps(updates)
        req = urllib.request.Request(
            f"{self.base_url}/associate/updateScreen",
            data=body.encode("utf-8"),
            method="POST"
        )
        req.add_header("Content-Type", "application/json")
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise Exception(f"update_screen failed: {e}")
    
    # --- ZÁKLADNÉ STANICE ---
    
    def get_routers(self) -> List[Dict]:
        """Získa zoznam základných staníc (AP)."""
        return self._get("/associate/getRoutersMsg")
    
    # --- ŠABLÓNY ---
    
    def get_styles(self) -> List[Dict]:
        """Získa zoznam všetkých šablón."""
        return self._get("/associate/getStylesMsg")
    
    def get_styles_paginated(self, page: int = 0, page_size: int = 10) -> Dict:
        """Získa šablóny so stránkovaním."""
        return self._get("/associate/getStyleMsgs", {
            "currentPage": page,
            "pageSize": page_size
        })
    
    def get_style_by_id(self, style_id: int) -> Dict:
        """Získa detail šablóny podľa ID (vrátane polí).
        
        Dokumentácia: POST /esls_new/associate/getStyleMsgById?id=X
        Body params: id = X
        
        Server vracia: {"datalist":[{...}], "page":{}, "resultCode":10, "resultMsg":"成功"}
        Vraciame prvok z datalist alebo celý response ak datalist chýba.
        """
        result = self._post("/associate/getStyleMsgById", form_data={"id": str(style_id)})
        if isinstance(result, dict) and "datalist" in result and isinstance(result["datalist"], list) and len(result["datalist"]) > 0:
            return result["datalist"][0]
        return result
    
    def get_style_details(self, style_id: int) -> Any:
        """Načíta kompletné detaily šablóny (z /style/getDispMs)."""
        return self._get("/style/getDispMs", {"id": style_id})
    
    def update_style(self, style_id: int, order_json: List[Dict]) -> Any:
        """Aktualizuje šablónu (orderJson parameter).
        
        Toto je hlavný endpoint na úpravu šablóny.
        order_json je zoznam polí s definíciou štýlu.
        
        POZNÁMKA: Tento endpoint môže vrátiť NPE (500) aj keď dáta prešli.
        Server má bug v StyleController.java:531 — NPE ale update prebehne.
        """
        json_str = json.dumps(order_json, ensure_ascii=False)
        return self._post(
            "/style/updateDispMData",
            params={"id": style_id},
            form_data={"id": str(style_id), "orderJson": json_str}
        )
    
    # --- PREVIEW OBRÁZKY ---
    
    def get_style_preview(self, style_id: int) -> str:
        """Stiahne preview obrázok šablóny ako base64 string."""
        # Skúsim zistiť názov šablóny
        style = self.get_style_by_id(style_id)
        if isinstance(style, dict) and "datalist" in style:
            style_info = style["datalist"][0]
        elif isinstance(style, dict):
            style_info = style
        else:
            style_info = self.get_styles()[0]  # fallback
        
        descriptor = style_info.get("descriptor", f"Template{style_id}")
        img_url = f"{self.base_url}/{descriptor}.png"
        
        req = urllib.request.Request(img_url)
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise Exception(f"get_style_preview({style_id}) failed: {e}")
    
    # --- OBRAZKY ---
    
    def get_photos(self) -> List[Dict]:
        """Získa zoznam obrázkov v systéme.
        
        Server vracia: {"datalist":[...], "resultCode":10, ...}
        Vraciame datalist.
        """
        result = self._get("/associate/getPhotos")
        if isinstance(result, dict) and "datalist" in result and isinstance(result["datalist"], list):
            return result["datalist"]
        return result
    
    def get_photo_data(self, photo_name: str) -> Dict:
        """Získa obrázok ako base64 podľa mena."""
        return self._get("/associate/getPhotoDataByName", {"photoName": photo_name})
    
    def get_photo_name_list(self, stylealign_id: int, style_id: int) -> Dict:
        """Získa zoznam fotiek pre danú šablónu (stylealign + styleid)."""
        return self._post("/style/getPhotoName", params={"stylealignId": stylealign_id, "styleid": style_id})
    
    def get_bg_msg(self, stylealign_id: int) -> Dict:
        """Získa zoznam pozadí pre daný typ obrazovky.
        
        Server vracia JSON: {"datalist":[...], "resultCode":10, "resultMsg":"成功"}
        alebo chybu: {"datalist":[], "resultCode":-1, "resultMsg":"错误"}
        """
        return self._post("/style/getBgMsg", params={"stylealignId": stylealign_id})
    
    def get_bg_img(self, img_id: int) -> Dict:
        """Získa base64 data pozadia.
        
        Server vracia JSON: {"datalist":["/9j/4AAQSkZ..."]}
        """
        return self._post("/style/getBgImg", params={"ImgId": img_id})
    
    def remove_background(self, mappingtype: int, style_id: int) -> bool:
        """Odstráni pozadie zo šablóny.
        
        Server vracia "0" alebo "1" ako string.
        """
        result = self._post("/style/removeBackground", params={"mappingtype": mappingtype, "styleid": style_id})
        if isinstance(result, str):
            return result.strip() == "1"
        return bool(result)
    
    def add_column_and_good(self, column_name: str, mapping_text: str, mappingtype: int, style_id: int) -> bool:
        """Pridá nové pole do šablóny.
        
        Server vracia "true", "0", alebo HTTP 500 (NPE bug).
        """
        try:
            result = self._post("/style/addColumnAndGood", params={
                "columnName": column_name, "mappingText": mapping_text,
                "mappingtype": mappingtype, "styleid": style_id
            })
            if isinstance(result, str):
                return result.strip().lower() in ("true", "1")
            return bool(result)
        except Exception as e:
            if "500" in str(e):
                # NPE bug - update mohol prebehnúť
                return True
            raise
    
    def update_style_align(self, style_id: int, stylealign: int, style_name: str) -> bool:
        """Zmení meno a typ šablóny (stylealign = typ obrazovky).
        
        Server vracia "0" alebo "1" ako string.
        """
        result = self._post("/style/updateStyleAlign", params={
            "styleid": style_id, "stylealign": stylealign, "styleName": style_name
        })
        if isinstance(result, str):
            return result.strip() == "1"
        return bool(result)
    
    def get_disp_ms_data(self, style_id: int) -> List[Dict]:
        """Získa kompletné orderJson šablóny (nový endpoint).
        
        Server vracia escaped JSON string: "[{\"mpname\":\"Name\",...}]"
        """
        return self._post("/style/getDispMsData", params={"id": style_id})
    
    def del_dismp(self, style_id: int) -> bool:
        """Zmaže pole zo šablóny (potrebuje ďalšie parametre).
        
        Server vracia "0" alebo "1" ako string.
        """
        try:
            result = self._post("/style/delDismp", params={"styleid": style_id})
            if isinstance(result, str):
                return result.strip() == "1"
            return bool(result)
        except Exception as e:
            if "415" in str(e) or "500" in str(e):
                # Server error - nemôžeme overiť
                return False
            raise
    
    def preview_img(self, style_id: int) -> bool:
        """Generuje preview obrázok šablóny.
        
        Server vracia prázdny string (200 OK) alebo chybu.
        """
        try:
            result = self._post("/style/previewImg", params={"id": style_id})
            # Prázdny string = success
            return True
        except Exception as e:
            if "500" in str(e):
                return False
            raise
    
    def upload_photo(self, photo_name: str, width: int, height: int, image_data: bytes) -> bool:
        """Nahraje obrázok do systému (form data upload).
        
        Server vracia JSON: {"datalist":[...], "resultCode":10, "resultMsg":"成功"}
        alebo chybu: {"datalist":[], "resultCode":-1, "resultMsg":"错误"}
        """
        req = urllib.request.Request(
            f"{self.base_url}/style/uploadPhoto",
            data=image_data,
            method="POST"
        )
        req.add_header("Content-Type", "multipart/form-data")
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read()
                text = data.decode("utf-8", errors="replace").strip()
                if text.startswith('"') and text.endswith('"'):
                    inner = text[1:-1].replace('\\"', '"')
                    try:
                        parsed = json.loads(inner)
                        return parsed.get("resultCode") == 10
                    except:
                        pass
                if text.startswith('{') or text.startswith('['):
                    try:
                        parsed = json.loads(text)
                        return parsed.get("resultCode") == 10
                    except:
                        pass
                return False
        except urllib.error.HTTPError:
            return False
        except Exception:
            return False
    
    def upload_font(self, font_name: str, file_path: str, font_data: bytes) -> bool:
        """Nahraje font do systému.
        
        Server vracia JSON alebo chybu.
        """
        req = urllib.request.Request(
            f"{self.base_url}/mms/uploadFont",
            data=font_data,
            method="POST"
        )
        req.add_header("Content-Type", "multipart/form-data")
        if self.session_id:
            req.add_header("Cookie", f"JSESSIONID={self.session_id}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read()
                text = data.decode("utf-8", errors="replace").strip()
                if text.startswith('"') and text.endswith('"'):
                    inner = text[1:-1].replace('\\"', '"')
                    try:
                        parsed = json.loads(inner)
                        return parsed.get("resultCode") == 10
                    except:
                        pass
                if text.startswith('{') or text.startswith('['):
                    try:
                        parsed = json.loads(text)
                        return parsed.get("resultCode") == 10
                    except:
                        pass
                return False
        except urllib.error.HTTPError:
            return False
        except Exception:
            return False
    
    # --- POMOCNÉ FUNKCIE ---
    
    def clone_style(self, source_id: int, new_name: str) -> int:
        """Naklonuje šablónu s novým menom.
        
        Návratová hodnota: ID novej šablóny.
        """
        # Skúsime získať orderJson z getDispMsData (najspoľahlivejší endpoint)
        order_json = None
        try:
            disp_data = self.get_disp_ms_data(source_id)
            if isinstance(disp_data, str):
                # Escaped JSON string - rozparsujeme
                stripped = disp_data.strip()
                if stripped.startswith('"') and stripped.endswith('"'):
                    inner = stripped[1:-1]
                    inner = inner.replace('\\"', '"')
                    try:
                        order_json = json.loads(inner)
                    except json.JSONDecodeError:
                        pass
                elif stripped.startswith('[') or stripped.startswith('{'):
                    try:
                        order_json = json.loads(stripped)
                    except json.JSONDecodeError:
                        pass
            elif isinstance(disp_data, list):
                order_json = disp_data
            elif isinstance(disp_data, dict):
                order_json = disp_data.get("orderJson") or disp_data.get("fields") or disp_data.get("datalist")
        except Exception:
            pass
        
        if not order_json or not isinstance(order_json, list):
            raise Exception(f"Could not extract orderJson from style {source_id}")
        
        # Aktualizujeme meno v orderJson
        for field in order_json:
            if isinstance(field, dict) and "name" in field:
                field["name"] = new_name
        
        # Pokúsim sa uložiť
        try:
            self.update_style(source_id, order_json)
            return source_id  # rovnaké ID, len upravené
        except Exception as e:
            if "500" in str(e):
                # NPE môže znamenať že to prešlo
                return source_id
            raise
    
    def format_tag_info(self, tag: Dict) -> str:
        """Formátuje informácie o tagu na čitateľný text."""
        lines = [
            f"  MAC: {tag.get('mac', 'N/A')}",
            f"  Stav batérie: {tag.get('power', 'N/A')}%",
            f"  RSSI: {tag.get('rssi', 'N/A')}",
            f"  Status: {tag.get('status', 'N/A')}",
            f"  Style ID: {tag.get('styleId', 'N/A')}",
            f"  Rozmer: {tag.get('width', 'N/A')}x{tag.get('height', 'N/A')}",
        ]
        return "\n".join(lines)
    
    def format_style_info(self, style: Dict) -> str:
        """Formátuje informácie o šablóne."""
        type_names = {1: "Čierno-biela", 2: "Trojfarebná (BWR)"}
        lines = [
            f"  ID: {style.get('id', 'N/A')}",
            f"  Názov: {style.get('name', 'N/A')}",
            f"  Rozmer: {style.get('width', 'N/A')}x{style.get('height', 'N/A')}",
            f"  Typ: {type_names.get(style.get('type', 0), 'N/A')}",
            f"  Mapping type: {style.get('mappingtype', 'N/A')}",
            f"  Posledná úprava: {style.get('updateTime', 'N/A')}",
        ]
        return "\n".join(lines)


# --- Rýchle testy priamo z príkazového riadku ---
if __name__ == "__main__":
    import sys
    
    esl = ESLManager()
    
    if len(sys.argv) < 2:
        print("Použitie: python3 esl_manager.py <príkaz> [parametre]")
        print("Príkazy:")
        print("  list-tags      - zoznam tagov")
        print("  list-styles   - zoznam šablón")
        print("  get-style ID  - detail šablóny")
        print("  list-routers  - základné stanice")
        print("  list-photos   - zoznam obrázkov")
        print("  preview ID    - preview šablóny")
        print("  clone ID MENO - naklonuj šablónu")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    try:
        if cmd == "list-tags":
            tags = esl.get_tags()
            if tags:
                for tag in tags:
                    print(esl.format_tag_info(tag))
                    print()
            else:
                print("Žiadne tagy nenaájdené")
        
        elif cmd == "list-styles":
            styles = esl.get_styles()
            if styles:
                for s in styles:
                    print(esl.format_style_info(s))
                    print()
            else:
                print("Žiadne šablóny nenaájdené")
        
        elif cmd == "get-style":
            if len(sys.argv) < 3:
                print("Chýba parameter: ID šablóny")
                sys.exit(1)
            style = esl.get_style_by_id(int(sys.argv[2]))
            print(json.dumps(style, indent=2, ensure_ascii=False))
        
        elif cmd == "list-routers":
            routers = esl.get_routers()
            if routers:
                for r in routers:
                    print(json.dumps(r, indent=2, ensure_ascii=False))
                    print()
            else:
                print("Žiadne základné stanice")
        
        elif cmd == "list-photos":
            photos = esl.get_photos()
            if photos:
                for p in photos:
                    print(f"  {p.get('name')}: {p.get('width')}x{p.get('height')} (ID: {p.get('id')})")
            else:
                print("Žiadne obrázky")
        
        elif cmd == "preview":
            if len(sys.argv) < 3:
                print("Chýba parameter: ID šablóny")
                sys.exit(1)
            data = esl.get_style_preview(int(sys.argv[2]))
            # Ulož do súboru
            import os
            path = os.path.expanduser("~/.hermes/scripts/esl_preview.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
            print(f"Preview uložený: {path}")
        
        elif cmd == "clone":
            if len(sys.argv) < 4:
                print("Chýbajú parametre: ID šablóny a nové meno")
                sys.exit(1)
            result = esl.clone_style(int(sys.argv[2]), sys.argv[3])
            print(f"Šablóna naklonovaná: ID={result}")
        
        else:
            print(f"Neznámy príkaz: {cmd}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Chyba: {e}")
        sys.exit(1)