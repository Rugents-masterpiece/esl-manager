# OBERON ESL 2026 - Research Dokumentácia

## Prehľad
Systém pre správu elektronických cenoviek (E-ink) komunikuje cez HTTP/HTTPS API s serverom na IP adrese (napr. `192.168.16.251`). Základná URL je `/esls_new/`.

---

## API Endpointy

### 1. Získanie informácií o cenovkách
**GET** `/esls_new/associate/getTagsMsg`

**Response:** JSON array (alebo obalený string)
```json
[
  {
    "height": 128,
    "ido": 0,
    "mac": "92.91.87.80",
    "power": 100,
    "routerStatus": 1,
    "routerid": "1",
    "rssi": -54.0,
    "showStyle": "暂无",
    "status": 1,
    "styleId": 0,
    "sub": 0,
    "width": 296
  }
]
```

**Parametre:**
- `height` - výška tagu v pixeloch
- `ido` - interný identifikátor tagu
- `mac` - MAC adresa cenovky (formát: "92.81.05.82")
- `power` - stav batérie (0-100)
- `routerStatus` - status routera
- `routerid` - ID základnej stanice
- `rssi` - sila signálu (napr. -54.0)
- `showStyle` - zobrazený štýl
- `status` - status tagu:
  - 1 = Ready (pripravený)
  - 2 = Updating (aktualizuje sa)
  - 3 = Update failed (chyba)
  - 4 = Update successful (úspešné)
- `styleId` - ID použitej šablóny
- `sub` - substitute flag
- `width` - šírka tagu v pixeloch

---

### 2. Aktualizácia e-ink displeja
**POST** `/esls_new/associate/updateScreen`

**Request Body:** JSON array
```json
[
  {
    "mac": "99.99.33.35",
    "mappingtype": 1,
    "styleid": 10,
    "ABDisplayFlag": 163,
    "nfcdata": "dačo",
    "templateFieldName1": "hodnota",
    "templateFieldName2": "hodnota",
    "templateFieldName3": "hodnota"
  }
]
```

**Response:** `true` alebo `false`

**Parametre:**
- `mac` - **POVINNÝ** - MAC adresa cenovky
- `mappingtype` - typ mapovania polí
- `styleid` - **POVINNÝ** - ID šablóny
- `ABDisplayFlag` - **POVINNÝ** - A/B strana zobrazenia:
  - Side A: `0xa1` (161)
  - Side B: `0xa2` (162)
  - Double-sided: `0xa3` (163)
- `nfcdata` - NFC údaje (voliteľné, len pre tagy s NFC)
- `templateFieldName1`, `templateFieldName2`, ... - dynamické polia podľa šablóny

**Poznámky:**
- Najprv nakonfigurovať šablónu, potom odovzdať parametre podľa názvov polí šablóny
- NFC je vlastná funkcia - ak tag nemá NFC, pole sa nepoužíva
- `ABDisplayFlag` platí len pre tabuľkové tagy s obojstranným zobrazením
- Jednostranné tagy môžu mať `ABDisplayFlag=0xa3` (163)

**Chyby:**
- Server vracia HTTP 500 Internal Server Error aj pri úspešnom spracovaní (bug/feature)
- Ignorovať chyby obsahujúce "InternalServerError" alebo "required JSON"

---

### 3. Spätná väzba aktualizácie cenoviek
**POST** `/esls_new/associate/updateFeedback` (odhadované)

**Request Body:**
```json
[
  {
    "mac": "99.99.55.17",
    "power": 100,
    "result": true
  }
]
```

**Response:** prázdne

**Poznámka:** Endpoint nie je oficiálne zdokumentovaný, neznáme URL

---

### 4. Získanie informácií o základných staniciach (AP/Routroch)
**GET** `/esls_new/associate/getRoutersMsg`

**Response:** JSON array
```json
[
  {
    "freq": 437,
    "hardwareVersion": "1.0.0",
    "lastHeartbeatTime": 1579163376000,
    "routerID": 8,
    "routerIP": "172.17.28.20",
    "softwareVersion": "8.1.0",
    "state": 1,
    "tagQuanty": 20
  }
]
```

**Parametre:**
- `freq` - frekvencia základnej stanice
- `hardwareVersion` - verzia hardvéru
- `lastHeartbeatTime` - posledný heartbeat (timestamp v ms)
- `routerID` - identifikátor základnej stanice
- `routerIP` - IP adresa základnej stanice
- `softwareVersion` - verzia softvéru
- `state` - status stanice
- `tagQuanty` - počet e-ink tagov pripojených

**Poznámka:** Môže vrátiť Error 500 ak je len jedna stanica

---

### 5. Získanie informácií o šablónach/štýloch
**GET** `/esls_new/associate/getStylesMsg`

**Response:** JSON array
```json
[
  {
    "backgroundID": 0,
    "descriptor": "DefaultTemplate136",
    "height": 128,
    "id": 136,
    "mappingtype": 101,
    "name": "Default Template136",
    "type": 2,
    "updateTime": "16-Feb-2026 18:05:18",
    "width": 296
  }
]
```

**Parametre:**
- `backgroundID` - ID pozadia šablóny (na skladanie URL pre preview obrázok)
- `descriptor` - popis šablóny
- `height` - výška v pixeloch
- `id` - **identifikátor šablóny**
- `mappingtype` - typ mapovania polí
- `name` - názov šablóny
- `type` - typ obrazovky:
  - 1 = Čierno-biely e-ink displej
  - 2 = Čierno-bielo-červený trojfarebný e-ink displej
- `updateTime` - čas poslednej aktualizácie
- `width` - šírka v pixeloch

---

### 6. Získanie šablón so stránkovaním
**GET** `/esls_new/associate/getStyleMsgs`

**Response:** Paginovaný objekt
```json
{
  "datalist": [...],
  "page": {
    "currentPage": 0,
    "hasNext": true,
    "hasPrevious": false,
    "pageSize": 10,
    "startRow": 0,
    "totalPages": 0,
    "totalRows": 0
  },
  "resultCode": 10,
  "resultMsg": "成功"
}
```

**Poznámka:** Stránkovanie - oficiálna dokumentácia nešpecifikuje ako používať parametre

---

### 7. Získanie detailov šablóny podľa ID
**POST** `/esls_new/associate/getStyleMsgById?id={id}`

**Request Body:**
```json
{
  "id": 131
}
```

**Response:**
```json
{
  "datalist": [
    {
      "rotate": 0,
      "styleFileds": ["price", "name", "qr_code"],
      "mappingtype": 784,
      "name": "Default Template131",
      "width": 296,
      "id": 131,
      "descriptor": "Default Template131",
      "type": 2,
      "updatetime": "13-Feb-2026 21:06:54",
      "userid": 43,
      "backgroundId": 0,
      "height": 128
    }
  ],
  "page": {...},
  "resultCode": 10,
  "resultMsg": "成功"
}
```

**Poznámky:**
- ID môže byť v URL parametri aj v JSON body
- `styleFileds` - polia definované v šablóne (text, obrázky, QR kódy, ...)

---

### 8. Získanie preview obrázku šablóny
**GET** `/esls_new/{previewImgName}.png`

**Parameter:**
- `previewImgName` - `{názov šablóny}{id šablóny}.png`

**Response:** Base64 encoded string

**Príklad:** `GET /esls_new/CiernoBielyPrvy132.png`

---

### 9. Získanie zoznamu obrázkov
**GET** `/esls_new/associate/getPhotos`

**Response:** Paginovaný objekt s `datalist` obsahujúcim zoznam obrázkov

**Parametre obrázku:**
- `height` - výška v pixeloch
- `id` - identifikátor obrázku
- `name` - názov obrázku
- `width` - šírka v pixeloch

---

### 10. Získanie dát obrázku
**GET** `/esls_new/associate/getPhotoDataByName?photoName={photoName}`

**Parameter:**
- `photoName` - názov obrázku

**Response:**
```json
{
  "data": "STRING BASE64.....",
  "datalist": [],
  "page": {...},
  "resultCode": 10,
  "resultMsg": "成功",
  "t": "STRING BASE64"
}
```

**Poznámka:** Neštandardná response - obsahuje duplicitné Base64 dáta v `data` aj `t` poliach

---

### 11. Nahratie obrázku
**POST** `/esls_new/associate/uploadPhoto?photoName={name}&width={w}&height={h}`

**Poznámka:** Nebolo testované

---

### 12. Zmazanie obrázku
**GET** `/esls_new/associate/delPhoto?photoName={name}`

**Poznámka:** Nebolo testované

---

### 13. Zmazanie tagov podľa MAC
**POST** `/esls_new/associate/delTagsByMac`

**Request Body:** JSON array MAC adries
```json
["99.98.29.79", "99.98.30.22"]
```

**Response:** `true`

**Poznámka:** Nebolo testované

---

## Aktuálna Implementácia

### Implementované Endpointy:
✅ `getTagsMsg` - GetTagsMsg()  
✅ `getRoutersMsg` - GetRoutersMsg()  
✅ `getStylesMsg` - GetStylesMsg() (volá `getStyleMsgs`)  
✅ `getStyleMsgById` - GetStyleMsgById()  
✅ `getPhotos` - GetPhotos()  
✅ `getPhotoDataByName` - GetPhotoDataByName()  
✅ `updateScreen` - SendPriceTagAsync()  

### Chýbajúce Endpointy:
❌ `updateFeedback` - Spätná väzba aktualizácie  
❌ `uploadPhoto` - Nahratie obrázku  
❌ `delPhoto` - Zmazanie obrázku  
❌ `delTagsByMac` - Zmazanie tagov  
❌ Preview obrázok šablóny - Dynamic URL zostavovanie  

---

## Modely Dát

### TagInfo
- `height`, `ido`, `mac`, `power`, `routerStatus`, `routerid`, `rssi`, `showStyle`, `status`, `styleId`, `sub`, `width`

### PriceTagData (odosielacie dáta)
- `mac`, `mappingtype`, `styleid`, `ABDisplayFlag`, `nfcdata`
- Dynamické polia: `templateFieldName1`, `templateFieldName2`, ...

**Problém:** `PriceTagData` má fixné polia (`QRCode`, `Name`, `Mj`, `Price`, `ShowStyle`) ale API očakáva dynamické polia podľa šablóny.

### StyleInfo (dedí z BaseStyleInfo)
- `backgroundID`, `descriptor`, `height`, `id`, `mappingtype`, `name`, `type`, `updateTime`, `width`

### RouterInfo
- `freq`, `hardwareVersion`, `lastHeartbeatTime`, `routerID`, `routerIP`, `softwareVersion`, `state`, `tagQuanty`

### PhotoInfo
- `height`, `id`, `name`, `width`

---

## JSON Deserializácia

API vracia neštandardné JSON formáty:
1. **Escaped stringy** - JSON obalený v úvodzovkách: `"[{...}]"`
2. **Obalené objekty** - `{"datalist":[...], "page":{...}, "resultCode":10, "resultMsg":"成功"}`
3. **Priame array** - `[{...},{...}]`

Implementácia obsahuje `z_UnescapeJsonString()` na dekódovanie escaped JSON.

---

## Known Issues / Poznámky

1. **HTTP 500 pri úspechu** - `updateScreen` vracia 500 aj pri úspešnom spracovaní
2. **Čínske znaky v response** - `resultMsg: "成功"` znamená success
3. **Paginácia** - `page` objekt vrátený API, ale dokumentácia nešpecifikuje parametre
4. **Duplicitné dáta** - `getPhotoDataByName` vracia Base64 v `data` aj `t` poli
5. **Timeout** - HTTP klient má timeout 10s (10s na inicializáciu, 5s na operácie)
6. **ABDisplayFlag** - len pre obojstranné tagy, ale jednostranné môžu mať 0xa3

---

## Plán Vývoja

### Krátkodobé:
1. Pridať podporu dynamických polí v `PriceTagData`
2. Implementovať `updateFeedback` endpoint
3. Implementovať `uploadPhoto`, `delPhoto`, `delTagsByMac`
4. Pridať metódu na získanie preview obrázku šablóny

### Strednodobé:
1. Podpora paginácie pri veľkom počte šablón
2. Optimalizácia batch operácií (viac tagov v jednom requeste)
3. Re-try mechanizmus pre zlyhané operácie

### Dlhodobé:
1. Podpora pre viac typov tagov podľa `type` pola
2. Real-time monitoring statusu tagov
3. Cache šablón a obrázkov pre offline režim
