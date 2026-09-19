# OBERON ESL 2026 - API Integration Patterns

## Prehľad
Dokumentácia patternov a riešení pre HTTP komunikáciu s API elektronických cenoviek OBERON ESL 2026.

## Použité triedy a objekty

### Hlavné triedy
- **OBERON_ESL_2026Client** - HTTP klient pre komunikáciu s ESL API (dedí z `WebServiceBaseClient`)
- **Driver_OBERON_ESL_2026** - Driver pre prácu s ESL zariadeniami (implementuje `IPriceLabelsDriver`)
- **Driver_Common** - Common driver factory (vracia `IPriceLabelsDriver` podľa konfigurácie)
- **IPriceLabelsDriver** - Interface pre price label driver

### HTTP triedy (.NET Framework)
- `System.Net.Http.HttpClient` - HTTP klient
- `System.Net.Http.HttpRequestMessage` - HTTP požiadavka
- `System.Net.Http.HttpResponseMessage` - HTTP odpoveď
- `System.Net.Http.StringContent` - HTTP content s JSON body
- `System.Net.Http.Headers.AuthenticationHeaderValue` - Bearer token authorization

### Serializácia
- **Newtonsoft.Json.JsonConvert** - JSON serializácia/deserializácia
- **Newtonsoft.Json.Linq.JObject** - JSON objekt pre dynamické dáta
- **Newtonsoft.Json.Linq.JArray** - JSON pole pre zoznamy

### Ostatné
- **Exalogic.Basic.Exceptions.ExaException** - Exception handler (Result, Message, Description, ErrNumber, ExceptionData)
- **Exalogic.Basic.NET.WebServiceClient.Models.ResultModel<T>** - Response model (Result, Data, Description, ErrNumber)
- **Exa.Basic.Debug.Console._Write** - Logging

## WebServiceBaseClient - Funkcie a ich použitie

### `PostAsync<T>(u_Description, u_ApiPath, u_Request, u_TimeOut)`
- **Čo robí**: HTTP POST s JSON body + automatická deserializácia response do `ResultModel<T>`
- **Volá**: `RequestAsync` → **kontroluje `Content-Type` response → musí obsahovať `/json`**
- **Kedy použiť**: Keď server vracia validný JSON response s `Content-Type: application/json`
- **Kedy nepoužiť**: Keď server NEVRÁTA JSON content-type (ESL server)
- **Problém**: Ak server vracia response bez JSON content-type, zlyhá s errorom `"RequestAsync 'descr' error (required JSON)"`
- **Príklad použitia**: `GetTagsMsg()`, `GetPhotosList()` - endpointy ktoré vracajú JSON

### `PostAsyncEXC(u_Description, u_ApiPath, u_TimeOut)`
- **Čo robí**: HTTP POST **BEZ request body** → vracia `ExaException` priamo
- **Volá**: `RequestBaseAsync` → **žiadna kontrola JSON content-type**
- **Response body**: Uložený v `result.ExceptionData`
- **Kedy použiť**: Keď nepotrebuješ poslať request body (len GET-like POST)
- **Pozor**: 3. parameter je `u_TimeOut` (UInteger), **nie request body**!
- **Príklad použitia**: `GetStyleMsgById()` - volá endpoint s params v URL, body nie je potrebné

### `RequestAsync(u_Description, u_Request, u_TimeOut)`
- **Čo robí**: Spracuje HTTP response → **kontroluje `Content-Type` response → musí obsahovať `/json`** → deserializuje JSON
- **Kontrola**: `!m_MediaType.Contains("/json")` → error ak content-type neobsahuje `/json`
- **Vracia**: `(ExaException, JObject)` tuple
- **Pozor**: **Nepoužívať priamo** - vždy cez `PostAsync` alebo `PostAsyncEXC`

### `RequestBaseAsync(u_Description, u_Request, u_TimeOut)`
- **Čo robí**: Spracuje HTTP response → **žiadna kontrola JSON content-type**
- **Vracia**: `(ExaException, HttpResponseMessage)` tuple
- **Kedy použiť**: Keď potrebuješ poslať request body A server vracia response bez JSON content-type
- **Prístup**: Chránená metóda - volateľná len z dedených tried (`OBERON_ESL_2026Client`)
- **Použitie pri ESL**: `DeleteTagsByMac()`, `UploadPhoto()` - ESL server vracia response bez JSON content-type

## Patterny a riešenia

### Pattern 1: POST s JSON body (keď server vracia JSON content-type)
```vb
' Použi PostAsync<T> - server vracia JSON response s Content-Type: application/json
Dim result As ResultModel(Of String) = Await Me.PostAsync(Of String)("descr", url, requestBody)
If result.Result = False Then
    ' Error handling - result.Description obsahuje error message
End If
If String.Equals(result.Data, "true", StringComparison.OrdinalIgnoreCase) Then
    ' Success - result.Data obsahuje odpoveď
End If
```

### Pattern 2: POST bez request body (GET-like POST)
```vb
' Použi PostAsyncEXC - body nie je potrebné, params sú v URL
' POZOR: 3. parameter je u_TimeOut (UInteger), NIE request body!
Dim result As ExaException = Await Me.PostAsyncEXC("descr", url, u_TimeOut:=5)
If result.Result = True Then
    Dim responseContent As String = result.ExceptionData
    ' Work with response
End If
```

### Pattern 3: POST s JSON body (keď server NEVRÁTA JSON content-type)
```vb
' Vytvor HttpRequestMessage s body
Dim tmp_Request As New Net.Http.HttpRequestMessage(Net.Http.HttpMethod.Post, url)
tmp_Request.Content = New Net.Http.StringContent(jsonBody, Text.Encoding.UTF8, "application/json")

' Volaj RequestBaseAsync priamo (chránená metóda z base class)
Dim tmp_Result = Await Me.RequestBaseAsync("description", tmp_Request, 12)
Dim tmp_Ex As ExaException = tmp_Result.Item1
Dim tmp_Response As HttpResponseMessage = tmp_Result.Item2

' Spracuj response
If tmp_Ex.Result = False Then
    ' Error handling
End If
Dim tmp_ResponseContent As String = Await tmp_Response.Content.ReadAsStringAsync()
```

### Pattern 4: GET request
```vb
' Použi GetAsync
Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", url, u_TimeOut:=5)
If result.Result = False Then
    ' Error handling
End If
' Work with result.Data
```

## Časté chyby a riešenia

### Chyba 1: `RequestAsync 'descr' error (required JSON)`
- **Príčina**: Server vracia response bez `Content-Type: application/json`
- **Riešenie**: Použi `RequestBaseAsync` namiesto `PostAsync`
- **Kde vznikla**: `DeleteTagsByMac()` - ESL server vracia response bez JSON content-type

### Chyba 2: `InvalidCastException` pri konverzii JSON na UInteger
- **Príčina**: `PostAsyncEXC` berie 3. parameter ako `u_TimeOut` (UInteger), nie ako request body
- **Riešenie**: Použi `RequestBaseAsync` s vlastným `HttpRequestMessage`
- **Kde vznikla**: `UploadPhoto()` - snaha poslať JSON body cez `PostAsyncEXC`

### Chyba 3: `MissingMemberException` - `.exc` alebo `.rsp` na ValueTuple
- **Príčina**: VB.NET ValueTuple používa `.Item1` a `.Item2`, nie named properties
- **Riešenie**: Použi `.Item1` a `.Item2` pre access na tuple elements
- **Kde vznikla**: `DeleteTagsByMac()` - snaha použiť `.exc` a `.rsp`

### Chyba 4: `Cannot read "image.png" (this model does not support image input)`
- **Príčina**: API vracia warning v `Description` aj keď operácia zlyhala
- **Riešenie**: Kontroluj `result.Data` (true/false) namiesto `result.Result` (bool)
- **Poznámka**: `Data` má vyššiu prioritu - ak `Data="true"`, operácia prebehla OK aj keď `Description` obsahuje warning

## Dôležité poznámky

1. **`PostAsyncEXC` neposiela request body** - má len 3 parametre (`u_Description`, `u_ApiPath`, `u_TimeOut`), 3. parameter je `UInteger` pre timeout
2. **`RequestBaseAsync` nekontroluje JSON content-type** - používať keď server vracia neštandardný content-type
3. **VB.NET ValueTuple** - používa `.Item1`, `.Item2`, nie named properties
4. **`RequestAsync` kontroluje JSON content-type** - zlyháva ak server vracia response bez `/json` v content-type
5. **`ResultModel<T>`** - `Result` je bool (HTTP success), `Data` je T (response body)
6. **`ExaException`** - `Result` je bool, `Message` je error message, `ExceptionData` je extra data
7. **`PostAsync` VOLÁ `RequestAsync`** → kontroluje JSON content-type → **nepoužiť pre ESL server**
8. **`PostAsyncEXC` neprijíma request body** → použiť len pre GET-like POST (params v URL)
9. **`RequestBaseAsync` je pre ESL server** → pošle body + nekontroluje content-type

## Súbory modulu

- `OBERON_ESL_2026Client.vb` - HTTP klient (main API methods)
- `Driver_OBERON_ESL_2026.vb` - Driver implementation
- `Driver_Common.vb` - Common driver factory
- `IPriceLabelsDriver.vb` - Interface definition
- `PriceTagStatusMonitor.vb` - Background status monitor

## API Endpointy

- `POST /esls_new/associate/getTagsMsg` - Získať zoznam cenoviek
- `POST /esls_new/associate/getStyleMsgById` - Získať štýl podľa ID
- `GET /esls_new/associate/getPhotos` - Získať zoznam fotiek
- `GET /esls_new/associate/getPhotoDataByName` - Získať dáta fotky
- `POST /esls_new/associate/uploadPhoto` - Nahrať fotku
- `GET /esls_new/associate/delPhoto` - Zmazať fotku
- `POST /esls_new/associate/delTagsByMac` - Zmazať cenovky podľa MAC
