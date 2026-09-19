Imports System.Threading.Tasks
Imports System.Web.ModelBinding
Imports System.Text.RegularExpressions
Imports Exalogic.Basic.NET.WebServiceClient.Models
Imports Newtonsoft.Json.Linq
Imports Newtonsoft.Json
Imports Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models


''' <summary>
''' HTTP klient pre komunikáciu s API elektronických cenoviek OBERON ESL 2026.
''' Dedí z WebServiceBaseClient a poskytuje metódy pre všetky API endpointy.
''' </summary>
''' <remarks>
''' Timeout HTTP požiadaviek je nastavený na 10 sekúnd (namiesto predvolených 60).
''' Všetky async metódy vracajú ExaException s Result = True pri úspechu.
''' JSON odpovede sú deserializované pomocou Newtonsoft.Json (JArray/JObject).
''' </remarks>
Namespace PriceLabels.OBERON_ESL_2026

    Public Class OBERON_ESL_2026Client
        Inherits Exalogic.Basic.NET.WebServiceClient.WebServiceBaseClient


        ' Základná URL adresa webovej služby elektronických cenoviek.
        Public prp_BaseUrl As String

        ''' <summary>
        ''' Konštruktor HTTP klienta pre komunikáciu s API cenoviek.
        ''' Nastavuje timeout na 10 sekúnd (namiesto predvolených 60 sekúnd).
        ''' </summary>
        Public Sub New()
            ' Nastaviť timeout na 10 sekúnd (namiesto predvolených 60 sekúnd)
            MyBase.New(10)
        End Sub

        ''' <summary>
        ''' Nastaví základnú URL adresu pre HTTP klienta.
        ''' Nastaví prp_BaseUrl aj HttpClient.BaseAddress v WebServiceBaseClient.
        ''' </summary>
        ''' <param name="BaseAddress">URL adresa webovej služby</param>
        Public Shadows Function SetBaseAddress(ByVal BaseAddress As String) As EXC.ExaException
            ' Volanie SetBaseAddress z rodičovskej triedy WebServiceBaseClient pre nastavenie HttpClient.BaseAddress
            ' Použijeme Try-Catch aby sme zachytili prípadné chyby z base metódy
            Try
                MyBase.SetBaseAddress(BaseAddress)
            Catch
                ' Ignorovať chyby z base metódy - prp_BaseUrl je nastavený
            End Try
            ' Nastaviť prp_BaseUrl PO volaní MyBase.SetBaseAddress pre istotu
            ' lebo base metóda môže prepísať interný stav
            prp_BaseUrl = BaseAddress
            Return EXC.GetDefault
        End Function


        ''' <summary>
        ''' Základná funkcia pre komunikačný test so zariadením.
        ''' Volá GET /esls_new/associate/getTagsMsg na overenie pripojenia.
        ''' </summary>
        ''' <param name="u_BaseUrl">Náhradná URL adresa (ak je prp_BaseUrl Nothing)</param>
        ''' <returns>
        ''' Task obsahujúci ExaException s výsledkom:
        '''   - Result = True: Komunikácia úspešná
        '''   - Result = False: Chyba komunikácie
        ''' </returns>
        Public Async Function CommunicationTest(Optional ByVal u_BaseUrl As String = Nothing) As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            ' Použiť u_BaseUrl ak prp_BaseUrl je Nothing
            Dim tmp_BaseUrl As String = If(prp_BaseUrl, u_BaseUrl)
            If String.IsNullOrEmpty(tmp_BaseUrl) Then
                Return EXC.Get("Nie je nastavená žiadna URL adresa (prp_BaseUrl aj u_BaseUrl sú Nothing).")
            End If

            Try
                ' HTTP GET požiadavka na endpoint getTagsMsg s timeoutom 5 sekúnd
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{tmp_BaseUrl}/esls_new/associate/getTagsMsg", 5)

                If result.Result = False Then
                    ' Zachytenie chyby z HTTP požiadavky (timeout, sieťová chyba)
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' Deserializácia JSON odpovede do zoznamu JObject pre ďalšie spracovanie
                Dim tmp_Templates As List(Of JObject) = z_DeserializeTagsMsg(result.Data)
                If tmp_Templates Is Nothing Then
                    ' Chyba ak API vrátilo prázdny zoznam cenoviek
                    myEx = EXC.Get($"Webová služba vrátila prázdny zoznam cenoviek.")
                    Return myEx
                End If

                ' Počítanie unikátnych MAC adries pre zistenie počtu rôznych zariadení
                Dim tmp_DifferentObjects As Integer = tmp_Templates.Select(Function(x) x("mac").ToString()).Distinct().Count()

                myEx.Result = True
                myEx.Description = $"Systém vrátil načítaných {tmp_Templates.Count} cenoviek."

            Catch ex As Exception
                ' Zachytenie všetkých nečakaných výnimiek (sieťové chyby, timeout)
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function


        ''' <summary>
        ''' Získava informácie o základných staniciach (AP/routroch) pre elektronické cenovky.
        ''' Volá GET /esls_new/associate/getRoutersMsg.
        ''' </summary>
        ''' <returns>Task obsahujúci ExaException s výsledkom</returns>
        Public Async Function GetRoutersMsg() As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' HTTP GET požiadavka na endpoint getRoutersMsg
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{prp_BaseUrl}/esls_new/associate/getRoutersMsg", 5)

                If result.Result = False Then
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' Deserializácia JSON odpovede do zoznamu JObject
                Dim tmp_Routers As List(Of JObject) = z_DeserializeRoutersMsg(result.Data)
                If tmp_Routers Is Nothing Then
                    myEx = EXC.Get($"Webová služba vrátila prázdny zoznam základných staníc.")
                    Return myEx
                End If

                myEx.Result = True
                myEx.Description = $"Systém vrátil načítaných {tmp_Routers.Count} základných staníc."

            Catch ex As Exception
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function


        ''' <summary>
        ''' Získava informácie o šablónach/styloch pre elektronické cenovky.
        ''' Volá GET /esls_new/associate/getStyleMsgs (Pozor: správne je getStyleMsgs, nie getStylesMsg!).
        ''' </summary>
        ''' <returns>Task obsahujúci ExaException s výsledkom</returns>
        Public Async Function GetStylesMsg() As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' HTTP GET požiadavka na endpoint getStyleMsgs (sloveso v množnom čísle - "Msgs" nie "Msg")
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{prp_BaseUrl}/esls_new/associate/getStyleMsgs", 5)

                If result.Result = False Then
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' Debug - vypíš prvých 300 znakov JSON odpovede
                If result.Data IsNot Nothing Then
                    Dim tmp_Preview As String = If(result.Data.Length > 300, result.Data.Substring(0, 300) & "...", result.Data)
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] GetStylesMsg - JSON preview: " & tmp_Preview, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

                ' Deserializácia JSON odpovede do zoznamu JObject
                ' API vracia {"datalist":[...]}, takže musíme extrahovať array z "datalist" kľúča
                Dim tmp_Styles As List(Of JObject) = z_DeserializeStylesMsg(result.Data)
                If tmp_Styles Is Nothing OrElse tmp_Styles.Count = 0 Then
                    myEx = EXC.Get($"Webová služba vrátila prázdny zoznam šablón. JSON input: {If(result.Data IsNot Nothing, result.Data.Substring(0, Math.Min(200, result.Data.Length)), "Nothing")}")
                    Return myEx
                End If

                myEx.Result = True
                ' Description obsahuje JSON pre deserializáciu vo forme
                myEx.Description = result.Data

            Catch ex As Exception
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function


        ''' <summary>
        ''' Získava informácie o šablóne podľa jej ID vrátane definície polí.
        ''' Volá POST /esls_new/associate/getStyleMsgById?id={id} s JSON body.
        ''' </summary>
        ''' <param name="u_StyleId">Identifikátor šablóny, ktorú chceme načítať</param>
        ''' <returns>Task obsahujúci ExaException s výsledkom, Description obsahuje JSON reprezentáciu JObject</returns>
        Public Async Function GetStyleMsgById(ByVal u_StyleId As Integer) As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' Vytvorenie JSON body pre POST požiadavku
                ' API očakáva JSON objekt s "id" polom
                Dim tmp_RequestBody As New Dictionary(Of String, Object)
                tmp_RequestBody.Add("id", u_StyleId)

                ' Konverzia na JSON string
                Dim tmp_JsonBody As String = JsonConvert.SerializeObject(tmp_RequestBody)

                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] GetStyleMsgById - POST body: " & tmp_JsonBody, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' HTTP POST požiadavka na endpoint getStyleMsgById s parametrom ID v URL a JSON body
                ' Použijeme PostAsyncEXC namiesto PostAsync, pretože ESL server vracia JSON formát,
                ' ktorý sa nedá deserializovať ako StyleMsgArray - PostAsyncEXC vracia raw Response string
                Dim result As Exalogic.Basic.Exceptions.ExaException = Await Me.PostAsyncEXC("descr", $"{prp_BaseUrl}/esls_new/associate/getStyleMsgById?id={u_StyleId}", u_TimeOut:=5)

                ' Kontrola result.Result - PostAsyncEXC vracia ExaException priamo
                ' .Result = True znamená úspech, .Result = False znamená chybu
                If result.Result = True Then
                    ' Skontrolovať či server vrátil dáta (data je v ExceptionData)
                    If String.IsNullOrWhiteSpace(result.ExceptionData) Then
                        myEx = EXC.Get($"Webová služba vrátila prázdnu odpoveď pre šablónu s ID {u_StyleId}.",
                                       u_ErrNumber:=CInt(Exalogic.Basic.Exceptions.enm_ErrNumbers.ValueOutOfRange))
                        Return myEx
                    End If

                    ' Deserializácia JSON odpovede do JObject pomocou existujúcej pomocnej metódy
                    Dim tmp_StyleObj As JObject = z_DeserializeStyleMsgById(result.ExceptionData)
                    If tmp_StyleObj Is Nothing Then
                        myEx = EXC.Get($"Webová služba vrátila neplatnú odpoveď pre šablónu s ID {u_StyleId}. JSON: {If(result.ExceptionData.Length > 200, result.ExceptionData.Substring(0, 200) & "...", result.Message)}")
                        Return myEx
                    End If

                    myEx.Result = True
                    ' Description obsahuje JSON JObject pre zobrazenie vo forme
                    myEx.Description = JsonConvert.SerializeObject(tmp_StyleObj, Formatting.Indented)
                Else
                    ' Chyba z PostAsyncEXC - result.Result = False
                    ' ExaException je vrátený priamo, nie cez result.Exception
                    myEx.Result = result.Result
                    myEx.Description = result.Message
                    myEx.ErrNumber = result.ErrNumber
                End If

            Catch ex As Exception
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function


        ''' <summary>
        ''' Získava zoznam obrázkov uložených v zariadení elektronických cenoviek.
        ''' Volá GET /esls_new/associate/getPhotos.
        ''' </summary>
        ''' <returns>Task obsahujúci ExaException s výsledkom</returns>
        Public Async Function GetPhotos() As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' HTTP GET požiadavka na endpoint getPhotos
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{prp_BaseUrl}/esls_new/associate/getPhotos", 5)

                If result.Result = False Then
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' Deserializácia JSON odpovede do zoznamu JObject
                Dim tmp_Photos As List(Of JObject) = z_DeserializePhotosMsg(result.Data)
                If tmp_Photos Is Nothing OrElse tmp_Photos.Count = 0 Then
                    myEx = EXC.Get($"Webová služba vrátila prázdny zoznam obrázkov.")
                    Return myEx
                End If

                myEx.Result = True
                ' Description obsahuje JSON pre deserializáciu volajúcou stranou
                myEx.Description = result.Data

            Catch ex As Exception
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function


        ''' <summary>
        ''' Získava údaje (dáta) obrázku podľa jeho názvu.
        ''' Volá GET /esls_new/associate/getPhotoDataByName?photoName={photoName}.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka, ktorý chceme načítať</param>
        ''' <returns>Task obsahujúci ExaException s výsledkom, Description alebo ExceptionData obsahuje Base64 string</returns>
        Public Async Function GetPhotoDataByName(ByVal u_PhotoName As String) As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' HTTP GET požiadavka na endpoint getPhotoDataByName s parametrom názvu
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{prp_BaseUrl}/esls_new/associate/getPhotoDataByName?photoName={u_PhotoName}", 5)

                If result.Result = False Then
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' API vracia JSON s Base64 dátami v poli "data"
                ' Formát: {"data": "BASE64STRING", "datalist": [], "page": {...}, "resultCode": 10, "resultMsg": "成功", "t": "BASE64STRING"}
                Dim json As String = result.Data.Trim()

                ' Odstrániť obalujúce úvodzovky ak sú prítomné
                If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                    json = json.Substring(1, json.Length - 2)
                End If

                ' Unescape JSON
                json = z_UnescapeJsonString(json)

                ' Parse JSON a extrahuj "data" pole
                Dim jObj As JObject = JObject.Parse(json)
                Dim tmp_Base64 As String = If(jObj("data") IsNot Nothing, jObj("data").ToString(), String.Empty)

                If String.IsNullOrWhiteSpace(tmp_Base64) Then
                    ' Skús alternatívne pole "t" (duplicitné dáta)
                    tmp_Base64 = If(jObj("t") IsNot Nothing, jObj("t").ToString(), String.Empty)
                End If

                If String.IsNullOrWhiteSpace(tmp_Base64) Then
                    myEx = EXC.Get($"API vrátilo prázdne dáta pre obrázok '{u_PhotoName}'.")
                    Return myEx
                End If

                myEx.Result = True
                ' Ulož Base64 dáta do ExceptionData pre prístup z vonku
                myEx.ExceptionData = tmp_Base64
                myEx.Description = $"Systém vrátil údaje pre obrázok '{u_PhotoName}'. Dĺžka Base64: {tmp_Base64.Length}."

                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] GetPhotoDataByName - Success, Base64 length: " & tmp_Base64.Length, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Catch ex As Exception
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function

''' <summary>
        ''' Nahraje obrázok do zariadenia elektronických cenoviek.
        ''' Volá POST /esls_new/associate/uploadPhoto s parametrami photoName, width, height.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        ''' <param name="u_Width">Šírka obrázka</param>
        ''' <param name="u_Height">Výška obrázka</param>
        ''' <param name="u_ImageData">Dáta obrázku (byte array)</param>
        Public Async Function UploadPhoto(ByVal u_PhotoName As String, ByVal u_Width As Integer, ByVal u_Height As Integer, ByVal u_ImageData As Byte()) As Threading.Tasks.Task(Of EXC.ExaException)
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If String.IsNullOrWhiteSpace(u_PhotoName) Then
                    Return EXC.Get("Názov obrázku nemôže byť prázdny.")
                End If

                If u_ImageData Is Nothing OrElse u_ImageData.Length = 0 Then
                    Return EXC.Get("Dáta obrázku nemôžu byť prázdne.")
                End If

                ' Konvertuj byte array na Base64 string
                Dim tmp_Base64 As String = Convert.ToBase64String(u_ImageData)

                ' Vytvor JSON body s Base64 dátami
                Dim tmp_JsonBody As String = JsonConvert.SerializeObject(New With {
                    .photoName = u_PhotoName,
                    .width = u_Width,
                    .height = u_Height,
                    .data = tmp_Base64
                })

                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] UploadPhoto - POST body: " & tmp_JsonBody, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' HTTP POST požiadavka - vytvoríme HttpRequestMessage s body a voláme RequestBaseAsync
                Dim tmp_Request As New Net.Http.HttpRequestMessage(Net.Http.HttpMethod.Post, $"{prp_BaseUrl}/esls_new/associate/uploadPhoto")
                If Not String.IsNullOrEmpty(Me.JWTToken) Then
                    tmp_Request.Headers.Authorization = New Net.Http.Headers.AuthenticationHeaderValue("Bearer", Me.JWTToken)
                End If
                tmp_Request.Content = New Net.Http.StringContent(tmp_JsonBody, Text.Encoding.UTF8, "application/json")

                Dim tmp_Result = Await Me.RequestBaseAsync("UploadPhoto", tmp_Request, 12)
                Dim tmp_Ex As Exalogic.Basic.Exceptions.ExaException = tmp_Result.Item1
                Dim tmp_Response As Net.Http.HttpResponseMessage = tmp_Result.Item2

                If tmp_Ex.Result = False Then
                    myEx.Result = False
                    myEx.Description = tmp_Ex.Message
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] UploadPhoto - Error: " & tmp_Ex.Message, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Exit Try
                End If

                If tmp_Response Is Nothing OrElse tmp_Response.Content Is Nothing Then
                    myEx.Result = False
                    myEx.Description = "Response je prázdny."
                    Exit Try
                End If

                Dim tmp_ResponseContent As String = Await tmp_Response.Content.ReadAsStringAsync()

                If String.Equals(tmp_ResponseContent, "true", StringComparison.OrdinalIgnoreCase) Then
                    myEx.Result = True
                    myEx.Description = $"Obrázok '{u_PhotoName}' bol úspešne nahraný."
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] UploadPhoto - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    myEx.Result = False
                    myEx.Description = $"Nepodarilo sa nahrať obrázok. Odpoveď: {tmp_ResponseContent}"
                    Exa.Basic.Debug.Console._Write($"[OBERON_ESL_2026Client] UploadPhoto - Failed: {tmp_ResponseContent}", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = z_GetException(ex, "Chyba pri nahrávaní obrázku")
            End Try

            Return myEx

        End Function

        ''' <summary>
        ''' Zmaže obrázok zo zariadenia elektronických cenoviek.
        ''' Volá GET /esls_new/associate/delPhoto?photoName={name}.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Public Async Function DeletePhoto(ByVal u_PhotoName As String) As Threading.Tasks.Task(Of EXC.ExaException)
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If String.IsNullOrWhiteSpace(u_PhotoName) Then
                    Return EXC.Get("Názov obrázku nemôže byť prázdny.")
                End If

                ' HTTP GET požiadavka
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{prp_BaseUrl}/esls_new/associate/delPhoto?photoName={u_PhotoName}", 5)

                If result.Result = False Then
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' Skontroluj odpoveď - server vracia "true" alebo "false"
                If String.Equals(result.Data, "true", StringComparison.OrdinalIgnoreCase) Then
                    myEx.Result = True
                    myEx.Description = $"Obrázok '{u_PhotoName}' bol úspešne zmazaný."
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] DeletePhoto - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    myEx.Result = False
                    myEx.Description = $"Obrázok '{u_PhotoName}' sa nepodarilo zmazať."
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] DeletePhoto - Failed: " & result.Data, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = z_GetException(ex, "Chyba pri zmazávaní obrázku")
            End Try

            Return myEx

        End Function

        ''' <summary>
        ''' Zmaže cenovky podľa MAC adries.
        ''' Volá POST /esls_new/associate/delTagsByMac s JSON array MAC adries.
        ''' </summary>
        ''' <param name="u_MacAddresses">Zoznam MAC adries</param>
        Public Async Function DeleteTagsByMac(ByVal u_MacAddresses As String()) As Threading.Tasks.Task(Of EXC.ExaException)
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If u_MacAddresses Is Nothing OrElse u_MacAddresses.Length = 0 Then
                    Return EXC.Get("MAC adresa nemôže byť prázdna.")
                End If

                ' Vytvor JSON array z MAC adries
                Dim tmp_JsonBody As String = JsonConvert.SerializeObject(u_MacAddresses)

                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] DeleteTagsByMac - POST body: " & tmp_JsonBody, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' HTTP POST požiadavka - vytvoríme HttpRequestMessage s body a voláme RequestBaseAsync
                Dim tmp_Request As New Net.Http.HttpRequestMessage(Net.Http.HttpMethod.Post, $"{prp_BaseUrl}/esls_new/associate/delTagsByMac")
                If Not String.IsNullOrEmpty(Me.JWTToken) Then
                    tmp_Request.Headers.Authorization = New Net.Http.Headers.AuthenticationHeaderValue("Bearer", Me.JWTToken)
                End If
                tmp_Request.Content = New Net.Http.StringContent(tmp_JsonBody, Text.Encoding.UTF8, "application/json")

                ' Volanie RequestBaseAsync - vráti (ExaException, HttpResponseMessage)
                Dim tmp_Result = Await Me.RequestBaseAsync("DeleteTagsByMac", tmp_Request, 12)
                Dim tmp_Ex As Exalogic.Basic.Exceptions.ExaException = tmp_Result.Item1
                Dim tmp_Response As Net.Http.HttpResponseMessage = tmp_Result.Item2

                ' Ak HTTP request zlyhal
                If tmp_Ex.Result = False Then
                    myEx = EXC.Get(tmp_Ex.Message, tmp_Ex.ErrNumber)
                    Exit Try
                End If

                ' Ak response je null
                If tmp_Response Is Nothing OrElse tmp_Response.Content Is Nothing Then
                    myEx = EXC.Get("Response je prázdny.")
                    Exit Try
                End If

                Dim tmp_ResponseContent As String = Await tmp_Response.Content.ReadAsStringAsync()

                ' Ak API vrátilo "true" - operácia úspešná
                If String.Equals(tmp_ResponseContent, "true", StringComparison.OrdinalIgnoreCase) Then
                    myEx.Result = True
                    myEx.Description = $"Cenovky s MAC adresami {String.Join(", ", u_MacAddresses)} boli úspešne zmazané."
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] DeleteTagsByMac - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    myEx.Result = False
                    myEx.Description = $"Nepodarilo sa zmazať cenovky. Odpoveď: {tmp_ResponseContent}"
                    Exa.Basic.Debug.Console._Write($"[OBERON_ESL_2026Client] DeleteTagsByMac - Failed: {tmp_ResponseContent}", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = z_GetException(ex, "Chyba pri zmazávaní cenoviek")
            End Try

            Return myEx

        End Function



#Region " Private Helper Methods "

        ''' <summary>
        ''' Unescape JSON reťazec - premení \" na ", \\ na \, \n na newline atď.
        ''' </summary>
        ''' <param name="u_EscapedJson">Escaped JSON reťazec z API</param>
        ''' <returns>Unescaped JSON reťazec pripravený na parsovanie</returns>
        Private Function z_UnescapeJsonString(ByVal u_EscapedJson As String) As String
            Dim result As New System.Text.StringBuilder()
            Dim i As Integer = 0

            While i < u_EscapedJson.Length
                If u_EscapedJson(i) = "\"c AndAlso i + 1 < u_EscapedJson.Length Then
                    Dim nextChar As Char = u_EscapedJson(i + 1)
                    Select Case nextChar
                        Case "\"c  ' backslash
                            result.Append("\"c)
                            i += 2
                        Case """"c  ' double quote
                            result.Append(""""c)
                            i += 2
                        Case "n"c  ' newline
                            result.Append(vbNewLine)
                            i += 2
                        Case "t"c  ' tab
                            result.Append(vbTab)
                            i += 2
                        Case "r"c  ' carriage return
                            result.Append(vbCr)
                            i += 2
                        Case "/"c  ' forward slash
                            result.Append("/"c)
                            i += 2
                        Case Else
                            ' Ak nie je escape sekvencia, pridaj znak ako je
                            result.Append(u_EscapedJson(i))
                            i += 1
                    End Select
                Else
                    result.Append(u_EscapedJson(i))
                    i += 1
                End If
            End While

            Return result.ToString()
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď pre TagInfo (getTagsMsg).
        ''' Formát: "[{\"mac\":\"...\",\"ido\":1,...},...]" alebo obalený string alebo JSON object
        ''' </summary>
        Private Function z_DeserializeTagsMsg(ByVal u_JsonData As String) As List(Of JObject)
            Dim tmp_Result As List(Of JObject) = Nothing

            If String.IsNullOrWhiteSpace(u_JsonData) Then Return Nothing

            Dim json As String = u_JsonData.Trim()

            ' Odstrániť obalujúce úvodzovky ak sú prítomné
            If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                json = json.Substring(1, json.Length - 2)
            End If

            ' Unescape JSON
            json = z_UnescapeJsonString(json)

            Try
                ' Skontroluj typ JSON - ak začína na {, skús najprv ako JObject
                If json.Trim().StartsWith("{"c) Then
                    ' JSON object - obal do listu
                    Dim jObj As JObject = JObject.Parse(json)
                    tmp_Result = New List(Of JObject) From {jObj}
                ElseIf json.Trim().StartsWith("["c) Then
                    ' JSON array - parse ako JArray
                    Dim jArray As JArray = JArray.Parse(json)
                    tmp_Result = jArray.ToObject(Of List(Of JObject))
                Else
                    ' Neznámy formát - skús JObject fallback
                    Dim jObj As JObject = JObject.Parse(json)
                    tmp_Result = New List(Of JObject) From {jObj}
                End If
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeTagsMsg - Failed: " & ex.Message, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            Return tmp_Result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď pre RouterInfo (getRoutersMsg).
        ''' Formát: "[{\"routerID\":1,...},...]" alebo obalený string alebo JSON object
        ''' </summary>
        Private Function z_DeserializeRoutersMsg(ByVal u_JsonData As String) As List(Of JObject)
            Dim tmp_Result As List(Of JObject) = Nothing

            If String.IsNullOrWhiteSpace(u_JsonData) Then Return Nothing

            Dim json As String = u_JsonData.Trim()

            ' Odstrániť obalujúce úvodzovky ak sú prítomné
            If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                json = json.Substring(1, json.Length - 2)
            End If

            ' Unescape JSON
            json = z_UnescapeJsonString(json)

            Try
                ' Skontroluj typ JSON - ak začína na {, skús najprv ako JObject
                If json.Trim().StartsWith("{"c) Then
                    Dim jObj As JObject = JObject.Parse(json)
                    tmp_Result = New List(Of JObject) From {jObj}
                ElseIf json.Trim().StartsWith("["c) Then
                    Dim jArray As JArray = JArray.Parse(json)
                    tmp_Result = jArray.ToObject(Of List(Of JObject))
                Else
                    Dim jObj As JObject = JObject.Parse(json)
                    tmp_Result = New List(Of JObject) From {jObj}
                End If
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeRoutersMsg - Failed: " & ex.Message, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            Return tmp_Result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď pre StyleInfo (getStylesMsg).
        ''' Formát: "[{\"id\":1,...},...]" alebo {"datalist":[...]} alebo obalený string
        ''' </summary>
        Private Function z_DeserializeStylesMsg(ByVal u_JsonData As String) As List(Of JObject)
            Dim tmp_Result As List(Of JObject) = Nothing

            If String.IsNullOrWhiteSpace(u_JsonData) Then Return Nothing

            Dim json As String = u_JsonData.Trim()

            ' Odstrániť obalujúce úvodzovky ak sú prítomné
            If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                json = json.Substring(1, json.Length - 2)
            End If

            ' Unescape JSON
            json = z_UnescapeJsonString(json)

            Try
                ' Skontroluj typ JSON - ak začína na {, skús ako JObject a extrahuj "datalist"
                If json.Trim().StartsWith("{"c) Then
                    Dim jObj As JObject = JObject.Parse(json)

                    ' Skontroluj či JObject obsahuje array v "datalist" kľúči
                    ' API vracia: {"datalist":[{...},{...},...]}
                    Dim tmp_ArrayValue As JToken = jObj("datalist")
                    If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                        ' Extrahuj array z datalist kľúča
                        Dim jArray As JArray = CType(tmp_ArrayValue, JArray)
                        tmp_Result = jArray.ToObject(Of List(Of JObject))
                    Else
                        ' Ak nie je datalist, skús známe array kľúče
                        For Each tmp_Key As String In New String() {"data", "result", "items", "list", "response", "value"}
                            tmp_ArrayValue = jObj(tmp_Key)
                            If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                                tmp_Result = CType(tmp_ArrayValue, JArray).ToObject(Of List(Of JObject))
                                Exit For
                            End If
                        Next

                        ' Ak žiadny array kľúč nebol nájdený, obal celý JObject do listu
                        If tmp_Result Is Nothing Then
                            tmp_Result = New List(Of JObject) From {jObj}
                        End If
                    End If
                ElseIf json.Trim().StartsWith("["c) Then
                    ' JSON array - parse ako JArray
                    Dim jArray As JArray = JArray.Parse(json)
                    tmp_Result = jArray.ToObject(Of List(Of JObject))
                Else
                    ' Neznámy formát - skús JObject fallback
                    Dim jObj As JObject = JObject.Parse(json)
                    tmp_Result = New List(Of JObject) From {jObj}
                End If
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStylesMsg - Failed: " & ex.Message, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            If tmp_Result IsNot Nothing Then
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStylesMsg - Success, count: " & tmp_Result.Count, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            End If

            Return tmp_Result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď pre StyleMsgById (getStyleMsgById).
        ''' Formát: JSON objekt s poliami šablóny, napr. {"id":131,"name":"...","fields":[...],...}
        ''' Vracia JObject ktorý obsahuje všetky dáta šablóny vrátane polí.
        ''' </summary>
        Private Function z_DeserializeStyleMsgById(ByVal u_JsonData As String) As JObject
            Dim tmp_Result As JObject = Nothing

            If String.IsNullOrWhiteSpace(u_JsonData) Then Return Nothing

            Dim json As String = u_JsonData.Trim()

            ' Debug - vypis prvej 300 znakov originálneho JSON
            Dim tmp_Preview As String = If(json.Length > 300, json.Substring(0, 300) & "...", json)
            Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - JSON preview: " & tmp_Preview, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            ' Odstrániť obalujúce úvodzovky ak sú prítomné
            If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                json = json.Substring(1, json.Length - 2)
            End If

            ' Unescape JSON
            json = z_UnescapeJsonString(json)

            Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - JSON after unescape: " & json, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Try
                ' API vracia JSON objekt - parse ako JObject
                If json.Trim().StartsWith("{"c) Then
                    tmp_Result = JObject.Parse(json)
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - Parsed JObject successfully, keys: " & String.Join(", ", tmp_Result.Properties().Select(Function(p) p.Name)), Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                ElseIf json.Trim().StartsWith("["c) Then
                    ' Ak je to array, extrahuj prvý prvok
                    Dim jArray As JArray = JArray.Parse(json)
                    If jArray.Count > 0 Then
                        tmp_Result = CType(jArray(0), JObject)
                        Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - Extracted first element from JArray", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    End If
                Else
                    ' Neznámy formát - skús JObject fallback
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - Unknown JSON format, trying JObject fallback...", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    tmp_Result = JObject.Parse(json)
                End If
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - Parse failed: " & ex.Message, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            If tmp_Result IsNot Nothing Then
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializeStyleMsgById - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            End If

            Return tmp_Result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď pre PhotoInfo (getPhotos).
        ''' Formát: {"datalist":[...],...} alebo "[{\"id\":1,...},...]" alebo obalený string
        ''' </summary>
        Private Function z_DeserializePhotosMsg(ByVal u_JsonData As String) As List(Of JObject)
            Dim tmp_Result As List(Of JObject) = Nothing

            If String.IsNullOrWhiteSpace(u_JsonData) Then Return Nothing

            Dim json As String = u_JsonData.Trim()

            ' Debug - vypis prvej 300 znakov originálneho JSON
            Dim tmp_Preview As String = If(json.Length > 300, json.Substring(0, 300) & "...", json)
            Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializePhotosMsg - JSON preview: " & tmp_Preview, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            ' Odstrániť obalujúce úvodzovky ak sú prítomné
            If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                json = json.Substring(1, json.Length - 2)
            End If

            ' Unescape JSON
            json = z_UnescapeJsonString(json)

            Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializePhotosMsg - JSON after unescape: " & json, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Try
                ' Skontroluj typ JSON - ak začína na {, skús ako JObject a extrahuj "datalist"
                If json.Trim().StartsWith("{"c) Then
                    Dim jObj As JObject = JObject.Parse(json)

                    ' ESL server vracia formát: {"datalist":[{...},{...},...], "page":{...}, "resultCode":..., "resultMsg":...}
                    ' Musíme extrahovať array z "datalist" kľúča
                    Dim tmp_ArrayValue As JToken = jObj("datalist")
                    If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                        ' Extrahuj array z datalist kľúča
                        Dim jArray As JArray = CType(tmp_ArrayValue, JArray)
                        tmp_Result = jArray.ToObject(Of List(Of JObject))
                    Else
                        ' Skontroluj aj iné možné array kľúče
                        For Each tmp_Key As String In New String() {"data", "result", "items", "list", "response", "value"}
                            tmp_ArrayValue = jObj(tmp_Key)
                            If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                                tmp_Result = CType(tmp_ArrayValue, JArray).ToObject(Of List(Of JObject))
                                Exit For
                            End If
                        Next

                        ' Ak žiadny array kľúč nebol nájdený, obal celý JObject do listu
                        If tmp_Result Is Nothing Then
                            tmp_Result = New List(Of JObject) From {jObj}
                        End If
                    End If
                ElseIf json.Trim().StartsWith("["c) Then
                    ' JSON array - parse ako JArray
                    Dim jArray As JArray = JArray.Parse(json)
                    tmp_Result = jArray.ToObject(Of List(Of JObject))
                Else
                    ' Neznámy formát - skús JObject fallback
                    Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializePhotosMsg - Unknown JSON format, trying JObject fallback...", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Dim jObj As JObject = JObject.Parse(json)
                    tmp_Result = New List(Of JObject) From {jObj}
                End If
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializePhotosMsg - Parse failed: " & ex.Message, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            If tmp_Result IsNot Nothing Then
                Exa.Basic.Debug.Console._Write("[OBERON_ESL_2026Client] z_DeserializePhotosMsg - Success, count: " & tmp_Result.Count, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            End If

            Return tmp_Result
        End Function

        ''' <summary>
        ''' Pomocná metóda pre získanie chybového objektu s optimalizovaným spracovaním výnimiek.
        ''' Extrahuje skutočnú chybovú správu z vnútorných výnimiek (InnerException).
        ''' </summary>
        ''' <param name="u_Exception">Výnimka, ktorú treba spracovať</param>
        ''' <param name="u_DefaultMessage">Predvolená správa ak sa zlyhá získanie detailov výnimky</param>
        ''' <returns>ExaException objekt s extrahovanou chybovou správou</returns>
        Private Function z_GetException(ByVal u_Exception As Exception, ByVal u_DefaultMessage As String) As EXC.ExaException

            Dim myEx As EXC.ExaException = EXC.GetDefault
            Dim tmp_ErrorMsg As String = u_DefaultMessage

            Try
                ' Extrakcia skutočnej výnimky z TargetInvocationException
                Dim tmp_ActualEx As Exception = u_Exception
                If TypeOf u_Exception Is System.Reflection.TargetInvocationException AndAlso u_Exception.InnerException IsNot Nothing Then
                    tmp_ActualEx = u_Exception.InnerException
                End If

                ' Získanie chybovej správy z reálnej výnimky
                If tmp_ActualEx IsNot Nothing Then
                    tmp_ErrorMsg = tmp_ActualEx.Message
                End If
            Catch
                ' Ak sa zlyží získanie chybového hlásenia, použi výchozí text
                tmp_ErrorMsg = u_DefaultMessage
            End Try

            If u_Exception IsNot Nothing Then
                ' Vytvorenie ExaException objektu s extrahovanou správou
                myEx = EXC.Get(tmp_ErrorMsg, u_Exception)
            Else
                myEx = EXC.Get(tmp_ErrorMsg)
            End If

            Return myEx

        End Function


#End Region


#Region " Tag Management Methods "

        ''' <summary>
        ''' Získava informácie o všetkých cenovkách pripojených k zariadeniu.
        ''' Volá GET /esls_new/associate/getTagsMsg.
        ''' </summary>
        ''' <returns>Task obsahujúci ExaException s výsledkom</returns>
        Public Async Function GetTagsMsg() As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' HTTP GET požiadavka na endpoint getTagsMsg
                Dim result As ResultModel(Of String) = Await Me.GetAsync("descr", $"{prp_BaseUrl}/esls_new/associate/getTagsMsg", 5)

                If result.Result = False Then
                    myEx = EXC.Get(result.Description, result.ErrNumber)
                    Exit Try
                End If

                ' Výsledok je JSON reťazec s dátami všetkých cenoviek
                myEx.Result = True
                myEx.Description = result.Data

            Catch ex As Exception
                myEx = z_GetException(ex, "Zariadenie neodpovedalo")
            End Try

            Return myEx

        End Function


        ''' <summary>
        ''' Async verzia metódy GetTagStatusByMac - získava status konkrétnej cenovky podľa MAC adresy.
        ''' </summary>
        ''' <param name="u_Mac">MAC adresa cenovky vo formáte "92.81.05.82"</param>
        ''' <returns>Task obsahujúci Integer status alebo Nothing</returns>
        Public Async Function GetTagStatusByMacAsync(u_Mac As String) As Task(Of Integer?)
            Dim result = Await GetTagsMsg()
            If result.Result = False Then Return Nothing

            ' Deserializácia JSON odpovede
            Dim tags As List(Of JObject) = z_DeserializeTagsMsg(result.Description)
            If tags Is Nothing Then Return Nothing

            ' Nájdenie cenovky s požadovanou MAC adresou
            Dim tag = tags.FirstOrDefault(Function(t) t("mac").ToString() = u_Mac)
            If tag Is Nothing Then Return Nothing

            ' Získanie status hodnoty z JSON objektu
            Dim statusValue As Integer? = Nothing
            If Integer.TryParse(tag("status").ToString(), statusValue) Then
                Return statusValue
            End If

            Return Nothing
        End Function

        ''' <summary>
        ''' Získava status konkrétnej cenovky podľa MAC adresy (synchronná verzia).
        ''' </summary>
        ''' <param name="u_Mac">MAC adresa cenovky vo formáte "92.81.05.82"</param>
        ''' <returns>Integer status alebo Nothing</returns>
        Public Function GetTagStatusByMac(ByVal u_Mac As String) As Integer?
            Try
                Dim resultTask = GetTagsMsg()
                resultTask.Wait()
                Dim myEx = resultTask.Result

                If myEx.Result = False Then Return Nothing

                ' Výsledok je JSON reťazec s dátami všetkých cenoviek
                Dim json As String = myEx.Description
                Dim tags As List(Of JObject) = z_DeserializeTagsMsg(json)
                If tags Is Nothing Then Return Nothing

                ' Nájdenie cenovky s požadovanou MAC adresou
                Dim tag = tags.FirstOrDefault(Function(t) t("mac").ToString() = u_Mac)
                If tag Is Nothing Then Return Nothing

                ' Získanie status hodnoty z JSON objektu
                Dim statusObj As Object = tag("status")
                If statusObj Is Nothing OrElse statusObj Is DBNull.Value Then Return Nothing

                Dim statusValue As Integer
                If Integer.TryParse(statusObj.ToString(), statusValue) Then
                    Return statusValue
                End If

            Catch ex As Exception
                ' Tiché ignorovanie výnimiek - vráti Nothing
            End Try

            Return Nothing
        End Function


        ''' <summary>
        ''' Odošle údaje pre aktualizáciu obrazovky elektronickej cenovky.
        ''' Volá POST /esls_new/associate/updateScreen.
        ''' </summary>
        ''' <param name="u_PriceTagData">List údajov pre cenovky, ktoré sa majú aktualizovať</param>
        ''' <returns>Task obsahujúci ExaException s výsledkom</returns>
        Public Async Function SendPriceTagAsync(ByVal u_PriceTagData As List(Of PriceLabels.OBERON_ESL_2026.Models.PriceTagData)) As Threading.Tasks.Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                Exa.Basic.Debug.Console._Write($"[SendPriceTagAsync] START - Počet cenoviek: {u_PriceTagData.Count}", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Vytvoríme jeden JSON array so všetkými cenovkami a pošleme naraz
                Dim jsonArray As New JArray()

                For Each tmp_Item As PriceLabels.OBERON_ESL_2026.Models.PriceTagData In u_PriceTagData
                    Dim jsonObject As New JObject()
                    jsonObject("mac") = tmp_Item.Mac
                    jsonObject("mappingtype") = tmp_Item.MappingType
                    jsonObject("styleid") = tmp_Item.StyleId

                    ' Pridať dynamické polia z Fields dictionary
                    If tmp_Item.Fields IsNot Nothing Then
                        For Each tmp_Kvp As KeyValuePair(Of String, Object) In tmp_Item.Fields
                            jsonObject(tmp_Kvp.Key) = JToken.FromObject(tmp_Kvp.Value)
                        Next
                    End If

                    jsonArray.Add(jsonObject)
                Next

                Dim jsonBody As String = JsonConvert.SerializeObject(jsonArray)
                Exa.Basic.Debug.Console._Write($"[SendPriceTagAsync] Batch JSON ({jsonArray.Count} items)", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                Dim request As New Net.Http.HttpRequestMessage(Net.Http.HttpMethod.Post, $"{prp_BaseUrl}/esls_new/associate/updateScreen")
                request.Content = New Net.Http.StringContent(jsonBody, Text.Encoding.UTF8, "application/json")
                Dim tmp_Result = Await Me.RequestBaseAsync("SendPriceTagAsync", request, 120)
                Dim tmp_Ex As Exalogic.Basic.Exceptions.ExaException = tmp_Result.Item1
                Dim tmp_Response As Net.Http.HttpResponseMessage = tmp_Result.Item2

                Dim responseContent As String = Await tmp_Response.Content.ReadAsStringAsync()
                Exa.Basic.Debug.Console._Write($"[SendPriceTagAsync] Response: {responseContent}", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If String.Equals(responseContent, "true", StringComparison.OrdinalIgnoreCase) Then
                    myEx.Result = True
                    myEx.Description = "Údaje boli úspešne odoslané na všetky cenovky."
                    Exa.Basic.Debug.Console._Write("[SendPriceTagAsync] SUCCESS", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    myEx = EXC.Get($"ESL server vrátil: {responseContent}", 0)
                    Exa.Basic.Debug.Console._Write($"[SendPriceTagAsync] FAILED: {responseContent}", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write($"[SendPriceTagAsync] EXCEPTION: {ex.Message}", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                myEx = z_GetException(ex, "Chyba pri odosielaní údajov na cenovky")
            End Try

            Return myEx

        End Function


#End Region


    End Class


End Namespace
