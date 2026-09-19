Option Strict On
Option Explicit On
Option Infer Off

Imports System.Threading.Tasks
Imports Exa.Basic.Debug
Imports Exa.Basic.Exceptions
Imports Exa.Basic.Exceptions.ExaException
Imports Exa.Basic.Helpers
Imports Exa.OBERON.Devices.Base
Imports Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026

Namespace PriceLabels

    ''' <summary>
    ''' OBERON ESL (Electronic Price Label) 2026 - Systém na elektronické cenovky.
    ''' Komunikuje cez HTTP/HTTPS webovú službu pre správu cenoviek.
    ''' </summary>
    ''' <remarks>
    ''' Trieda implementuje rozhranie IPriceLabels a Driver_Common.IPriceLabels.
    ''' Používa OBERON_ESL_2026Client na HTTP komunikáciu s zariadením.
    ''' Predvolená adresa: http://192.168.16.251:80
    ''' </remarks>
    Friend Class Driver_OBERON_ESL_2026
        Implements IDisposable
        Implements IPriceLabelsDriver

#Region " Declaration "

        ''' <summary>Event pre logovanie JSON dát z API.</summary>
        Public Event JSONLog As Action(Of String) Implements IPriceLabelsDriver.JSONLog

        ' Názov aplikácie pre logovanie a chybové hlásenia.
        Private Const CONST_ESLAppName As String = "OBERON ESL 2026"

        ' Verzia drivera elektronických cenoviek.
        Private Const CONST_ESLAppVersion As String = "1.0.0"

        ' Objekt na synchronizáciu prístupu k zdieľaným zdrojom.
        ' Používa sa na ochranu pred viacvláknovým prístupom.
        Private lc_SyncLockObj As New Object

        ' Klient pre HTTP/HTTPS komunikáciu s webovou službou elektronických cenoviek.
        ' Dedí z WebServiceBaseClient a poskytuje metódy pre API volania.
        Private lc_OBERON_ESL_2026Client As OBERON_ESL_2026Client = Nothing

        ' Základná URL adresa webovej služby elektronických cenoviek.
        ' Formát: http://IP_ADRESA alebo https://IP_ADRESA
        Private prp_BaseUrl As String


#End Region


#Region " Properties "

        ''' <summary>
        ''' Pomenovanie cenoviek v systéme OBERON (zoznam zariadení).
        ''' </summary>
        Public ReadOnly Property Name As String Implements IPriceLabelsDriver.Name
            Get
                Return prp_DeviceName
            End Get
        End Property

        ''' <summary>
        ''' Získava konkrétny typ/model zariadenia - presný typ cenoviek.
        ''' </summary>
        Public ReadOnly Property PriceLabelsModel() As Main.enm_PriceLabelsModel Implements IPriceLabelsDriver.PriceLabelsModel

        ''' <summary>
        ''' Interné úložisko komunikačných nastavení.
        ''' </summary>
        Private prp_Communication As Exa.OBERON.Devices.Base.Device.cls_Communication

        ''' <summary>
        ''' Nastavenia komunikácie so zariadením elektronických cenoviek.
        ''' </summary>
        Public Property Communication As Exa.OBERON.Devices.Base.Device.cls_Communication Implements IPriceLabelsDriver.Communication
            Get
                Return prp_Communication
            End Get
            Set(ByVal value As Exa.OBERON.Devices.Base.Device.cls_Communication)
                ' Pri nastavení sa vytvorí kópia komunikačného objektu (Clone) pre izoláciu
                prp_Communication = value.Clone
            End Set
        End Property

        ''' <summary>
        ''' Interné úložisko názvu zariadenia.
        ''' </summary>
        Private prp_DeviceName As String


#End Region


#Region " Constructor "

        ''' <summary>
        ''' Konštruktor drivera elektronických cenoviek OBERON ESL 2026.
        ''' Inicializuje typ zariadenia, komunikačné nastavenia a HTTP klienta.
        ''' </summary>
        ''' <param name="u_PriceLabelsModel">Typ modelu zariadenia (musí byť OBERON_ESL_2026)</param>
        ''' <param name="u_DeviceName">Pomenovanie zariadenia v systéme OBERON</param>
        Public Sub New(ByVal u_PriceLabelsModel As enm_PriceLabelsModel,
                       ByVal u_DeviceName As String)

            On Error Resume Next
            PriceLabelsModel = u_PriceLabelsModel

            ' Vytvorí predvolené komunikačné nastavenia
            prp_Communication = New Exa.OBERON.Devices.Base.Device.cls_Communication
            prp_Communication.TCP_HostName = "http://192.168.16.251"
            prp_Communication.TCP_Port = 80

            ' Vytvorí HTTP klienta pre komunikáciu s API cenoviek (timeout 10 sekúnd)
            lc_OBERON_ESL_2026Client = New OBERON_ESL_2026Client()

            prp_DeviceName = u_DeviceName
            prp_BaseUrl = prp_Communication.TCP_HostName

        End Sub


#End Region


#Region " Public Methods "

        ''' <summary>
        ''' Otvorenie komunikácie so zariadením.
        ''' </summary>
        Public Function CommunicationOpen() As EXC.ExaException Implements IPriceLabelsDriver.CommunicationOpen
            Dim myEx As EXC.ExaException = EXC.GetDefault
            Try
                ' Zatvorí staré spojenie a vytvorí nové
                z_CommunicationClose()
                lc_OBERON_ESL_2026Client = New OBERON_ESL_2026Client
                myEx = z_SetBaseAddress(Me.Communication.TCP_HostName)
                If myEx.Result = True Then
                    myEx = z_TestConnection2().GetAwaiter().GetResult()
                End If
            Catch ex As Exception
                myEx = EXC.Get($"CommunicationOpen error: {ex.Message}", ex)
            End Try
            Return myEx
        End Function

        ''' <summary>
        ''' Zatvorenie komunikácie so zariadením.
        ''' </summary>
        Public Sub CommunicationClose() Implements IPriceLabelsDriver.CommunicationClose
            z_CommunicationClose()
        End Sub

        ''' <summary>
        ''' Nastavenie základnej adresy URL.
        ''' </summary>
        Public Function SetBaseAddress(BaseAddress As String) As EXC.ExaException Implements IPriceLabelsDriver.SetBaseAddress
            Return z_SetBaseAddress(BaseAddress)
        End Function

        ''' <summary>
        ''' Otestovanie pripojenia (synchronná verzia).
        ''' </summary>
        Public Function TestConnection() As EXC.ExaException Implements IPriceLabelsDriver.TestConnection
            Dim myEx As EXC.ExaException = EXC.GetDefault
            Try
                myEx = z_TestConnection2().GetAwaiter().GetResult()
            Catch ex As Exception
                myEx = EXC.Get($"TestConnection error: {ex.Message}", ex)
            End Try
            Return myEx
        End Function

        ''' <summary>
        ''' Testuje komunikáciu so zariadením elektronických cenoviek.
        ''' </summary>
        ''' <returns>
        ''' Task obsahujúci ExaException s výsledkom:
        '''   - Result = True: Komunikácia úspešná
        '''   - Result = False: Chyba komunikácie
        ''' </returns>
        Public Async Function CommunicationTest() As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.CommunicationTest

            Dim myEx As EXC.ExaException = EXC.GetDefault


            Try
                ' Krok 1: Zatvorenie starého spojenia a vytvorenie nového klienta
                z_CommunicationClose()
                lc_OBERON_ESL_2026Client = New OBERON_ESL_2026Client

                ' Krok 2: Validácia URL adresy webovej služby
                If String.IsNullOrWhiteSpace(Me.Communication.TCP_HostName) = True Then
                    myEx = EXC.Get($"URL (IP adresa) webovej služby nie je zadaná.")
                    myEx.ExceptionType = enm_ExceptionTypes.Validation
                    Return myEx
                End If

                ' Krok 3: Nastavenie základnej URL adresy pre HTTP klienta
                myEx = z_SetBaseAddress(Me.Communication.TCP_HostName)
                If myEx.Result = False Then
                    Return myEx
                End If

                ' Krok 4: Priamo nastaviť prp_BaseUrl na client pre istotu (pred volaním CommunicationTest)
                ' Toto zabezpečí, že prp_BaseUrl nie je Nothing keď CommunicationTest() začne konštruovať URL
                If lc_OBERON_ESL_2026Client IsNot Nothing Then
                    lc_OBERON_ESL_2026Client.prp_BaseUrl = prp_BaseUrl
                End If

                ' Krok 5: Otestovanie pripojenia cez async metódu
                myEx = Await z_TestConnection2()
                If myEx.Result = False Then
                    Return myEx
                End If

                ' Krok 5: Nastavenie výsledku ako úspešného
                myEx.Result = True

            Catch ex As Exception
                ' Zachytenie všetkých nečakaných výnimiek a vrátenie chybového výsledku
                myEx = EXC.Get($"'{CONST_ESLAppName}' connection error: {ex.Message}", ex)
            End Try

            Return myEx

        End Function

        ''' <summary>
        ''' Získava informácie o všetkých cenovkách pripojenovaných k zariadeniu.
        ''' </summary>
        Public Async Function GetTagsMsg() As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.GetTagsMsg
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                myEx = Await lc_OBERON_ESL_2026Client.GetTagsMsg()
            Catch ex As Exception
                myEx = EXC.Get($"GetTagsMsg error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Získava informácie o základných staniciach (routroch).
        ''' </summary>
        Public Async Function GetRoutersMsg() As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.GetRoutersMsg
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                myEx = Await lc_OBERON_ESL_2026Client.GetRoutersMsg()
            Catch ex As Exception
                myEx = EXC.Get($"GetRoutersMsg error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Získava informácie o šablónach/styloch pre elektronické cenovky.
        ''' </summary>
        Public Async Function GetStylesMsg() As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.GetStylesMsg
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                myEx = Await lc_OBERON_ESL_2026Client.GetStylesMsg()
            Catch ex As Exception
                myEx = EXC.Get($"GetStylesMsg error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Získava informácie o konkrétnej šablóne podľa jej ID vrátane definície polí.
        ''' </summary>
        ''' <param name="u_StyleId">Identifikátor šablóny</param>
        Public Async Function GetStyleMsgById(ByVal u_StyleId As Integer) As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.GetStyleMsgById
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                myEx = Await lc_OBERON_ESL_2026Client.GetStyleMsgById(u_StyleId)
            Catch ex As Exception
                myEx = EXC.Get($"GetStyleMsgById({u_StyleId}) error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Získava informácie o obrázkoch uložených v zariadení.
        ''' </summary>
        Public Async Function GetPhotos() As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.GetPhotos
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                myEx = Await lc_OBERON_ESL_2026Client.GetPhotos()
            Catch ex As Exception
                myEx = EXC.Get($"GetPhotos error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Získava údaje (dáta) obrázku podľa jeho názvu.
        ''' Volá GET /esls_new/associate/getPhotoDataByName?photoName={name}.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Public Async Function GetPhotoDataByName(ByVal u_PhotoName As String) As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.GetPhotoDataByName
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If String.IsNullOrWhiteSpace(u_PhotoName) Then
                    Return EXC.Get("Názov obrázku nemôže byť prázdny.")
                End If

                Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] GetPhotoDataByName - Getting photo data for: " & u_PhotoName, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Volanie API klienta
                myEx = Await lc_OBERON_ESL_2026Client.GetPhotoDataByName(u_PhotoName)

                If myEx.Result = True Then
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] GetPhotoDataByName - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] GetPhotoDataByName - Error: " & myEx.Description, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = EXC.Get($"GetPhotoDataByName error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Nahraje obrázok do zariadenia elektronických cenoviek.
        ''' Volá POST /esls_new/associate/uploadPhoto s parametrami photoName, width, height.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        ''' <param name="u_Width">Šírka obrázka v pixeloch</param>
        ''' <param name="u_Height">Výška obrázka v pixeloch</param>
        ''' <param name="u_ImageData">Dáta obrázku (Base64 alebo byte array)</param>
        Public Async Function UploadPhoto(ByVal u_PhotoName As String, ByVal u_Width As Integer, ByVal u_Height As Integer, ByVal u_ImageData As Byte()) As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.UploadPhoto
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If String.IsNullOrWhiteSpace(u_PhotoName) Then
                    Return EXC.Get("Názov obrázku nemôže byť prázdny.")
                End If

                If u_ImageData Is Nothing OrElse u_ImageData.Length = 0 Then
                    Return EXC.Get("Dáta obrázku nemôžu byť prázdne.")
                End If

                Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] UploadPhoto - Uploading photo: " & u_PhotoName & " (" & u_Width & "x" & u_Height & ", " & u_ImageData.Length & " bytes)", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Volanie API klienta
                myEx = Await lc_OBERON_ESL_2026Client.UploadPhoto(u_PhotoName, u_Width, u_Height, u_ImageData)

                If myEx.Result = True Then
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] UploadPhoto - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] UploadPhoto - Error: " & myEx.Description, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = EXC.Get($"UploadPhoto error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Zmaže obrázok zo zariadenia elektronických cenoviek.
        ''' Volá GET /esls_new/associate/delPhoto?photoName={name}.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Public Async Function DeletePhoto(ByVal u_PhotoName As String) As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.DeletePhoto
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If String.IsNullOrWhiteSpace(u_PhotoName) Then
                    Return EXC.Get("Názov obrázku nemôže byť prázdny.")
                End If

                Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] DeletePhoto - Deleting photo: " & u_PhotoName, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Volanie API klienta
                myEx = Await lc_OBERON_ESL_2026Client.DeletePhoto(u_PhotoName)

                If myEx.Result = True Then
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] DeletePhoto - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] DeletePhoto - Error: " & myEx.Description, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = EXC.Get($"DeletePhoto error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function

        ''' <summary>
        ''' Zmaže cenovky podľa MAC adries.
        ''' Volá POST /esls_new/associate/delTagsByMac s JSON array MAC adries.
        ''' </summary>
        ''' <param name="u_MacAddresses">Zoznam MAC adries</param>
        Public Async Function DeleteTagsByMac(ByVal u_MacAddresses As String()) As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.DeleteTagsByMac
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                If u_MacAddresses Is Nothing OrElse u_MacAddresses.Length = 0 Then
                    Return EXC.Get("MAC adresa nemôže byť prázdna.")
                End If

                Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] DeleteTagsByMac - Deleting tags: " & String.Join(", ", u_MacAddresses), Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Volanie API klienta
                myEx = Await lc_OBERON_ESL_2026Client.DeleteTagsByMac(u_MacAddresses)

                If myEx.Result = True Then
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] DeleteTagsByMac - Success", Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    Exa.Basic.Debug.Console._Write("[Driver_OBERON_ESL_2026] DeleteTagsByMac - Error: " & myEx.Description, Nothing, "OBERON_ESL_2026", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                myEx = EXC.Get($"DeleteTagsByMac error: {ex.Message}", ex)
            End Try

            Return myEx
        End Function



#End Region


#Region " Private Methods "

        ''' <summary>
        ''' Zatvorí aktívne komunikačné spojenie so zariadením.
        ''' </summary>
        Private Sub z_CommunicationClose()
            ' V súčasnosti prázdna metóda - pripravená pre budúce rozšírenie
        End Sub

        ''' <summary>
        ''' Nastavuje základnú URL adresu pre HTTP klienta.
        ''' </summary>
        ''' <param name="u_BaseAddress">URL adresa webovej služby (napr. http://192.168.16.251)</param>
        ''' <returns>ExaException s výsledkom nastavenia URL</returns>
        Private Function z_SetBaseAddress(ByVal u_BaseAddress As String) As EXC.ExaException

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' Validácia vstupného parametra - URL nesmie byť prázdna
                If String.IsNullOrWhiteSpace(u_BaseAddress) = True Then
                    myEx = EXC.Get($"URL adresa nie je zadaná.")
                    myEx.ExceptionType = enm_ExceptionTypes.Validation
                    Return myEx
                End If

                ' Uloženie URL adresy a odstránenie bielych priestorov
                Dim tmp_BaseAddress As String = u_BaseAddress.Trim().TrimEnd("/"c)

                ' Skontrolovať, či URL už obsahuje port (obsahuje vzor : číslo po hostname)
                Dim tmp_HasPort As Boolean = False
                If tmp_BaseAddress.Contains("://") Then
                    Dim tmp_AfterProtocol As String = tmp_BaseAddress.Substring(tmp_BaseAddress.IndexOf("://") + 3)
                    Dim tmp_HostEndIndex As Integer = tmp_AfterProtocol.IndexOf("/")
                    If tmp_HostEndIndex > 0 Then
                        tmp_AfterProtocol = tmp_AfterProtocol.Substring(0, tmp_HostEndIndex)
                    End If
                    If tmp_AfterProtocol.Contains(":") Then
                        tmp_HasPort = True
                    End If
                End If

                ' Ak URL neobsahuje port a Communication má nastavený port, pridať ho
                Dim tmp_FullBaseUrl As String = tmp_BaseAddress
                If Not tmp_HasPort AndAlso Me.Communication IsNot Nothing AndAlso Me.Communication.TCP_Port > 0 Then
                    tmp_FullBaseUrl = tmp_BaseAddress & ":" & Me.Communication.TCP_Port.ToString()
                End If

                prp_BaseUrl = tmp_FullBaseUrl

                ' Inicializácia klienta ak ešte neexistuje
                If lc_OBERON_ESL_2026Client Is Nothing Then
                    lc_OBERON_ESL_2026Client = New OBERON_ESL_2026Client
                End If

                ' Predanie URL adresy HTTP klientovi (vrátane portu) - nastaviť prp_BaseUrl aj HttpClient.BaseAddress
                ' Nastaviť prp_BaseUrl priamo na client pre istotu
                lc_OBERON_ESL_2026Client.prp_BaseUrl = tmp_FullBaseUrl
                ' Volanie SetBaseAddress pre nastavenie HttpClient.BaseAddress v WebServiceBaseClient
                lc_OBERON_ESL_2026Client.SetBaseAddress(tmp_FullBaseUrl)
                ' Nastaviť prp_BaseUrl na driveri
                prp_BaseUrl = tmp_FullBaseUrl

                myEx.Result = True

            Catch ex As Exception
                ' Zachytenie výnimiek pri nastavovaní URL
                myEx = EXC.Get($"z_SetBaseAddress error: {ex.Message}", ex)
            End Try

            Return myEx

        End Function

        ''' <summary>
        ''' Otestovanie pripojenia (async verzia).
        ''' </summary>
        Public Async Function TestConnection2() As Task(Of EXC.ExaException) Implements IPriceLabelsDriver.TestConnection2
            Return Await z_TestConnection2()
        End Function

        ''' <summary>
        ''' Async testovanie pripojenia k zariadeniu.
        ''' Volá metódu CommunicationTest() HTTP klienta s prp_BaseUrl ako parameter.
        ''' </summary>
        ''' <returns>Task obsahujúci ExaException s výsledkom testu</returns>
        Private Async Function z_TestConnection2() As Task(Of EXC.ExaException)

            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                ' Volanie async testu pripojenia cez HTTP klienta s prp_BaseUrl ako parameter
                ' Toto zabezpečí, že URL adresa je vždy správna aj keď je prp_BaseUrl v klientovi Nothing
                myEx = Await lc_OBERON_ESL_2026Client.CommunicationTest(u_BaseUrl:=prp_BaseUrl)
                Return myEx

            Catch ex As Exception
                ' Zachytenie výnimiek pri teste pripojenia
                myEx = EXC.Get($"z_TestConnection error: {ex.Message}", ex)
            End Try

            Return myEx

        End Function


#End Region


#Region " IDisposable "

        ' Označuje, či už bola trieda uvoľnená.
        Private _IsDisposed As Boolean = False

        ''' <summary>
        ''' Uvoľňuje prostriedky použité HTTP klientom.
        ''' </summary>
        ''' <param name="disposing">True ak je volané z Dispose(), false z finalizeru</param>
        Protected Overridable Sub Dispose(ByVal disposing As Boolean)
            If Not _IsDisposed Then
                If disposing Then
                    If lc_OBERON_ESL_2026Client IsNot Nothing Then
                        ' Nastaví lc_OBERON_ESL_2026Client na Nothing pre uvoľnenie pamäte
                        lc_OBERON_ESL_2026Client = Nothing
                    End If
                End If
                _IsDisposed = True
            End If
        End Sub

        ''' <summary>
        ''' Verejné rozhranie pre uvoľnenie prostriedkov.
        ''' </summary>
        Public Sub Dispose() Implements IDisposable.Dispose
            Dispose(True)
            GC.SuppressFinalize(Me)
        End Sub

        ''' <summary>
        ''' Finalizer - záložné uvoľnenie prostriedkov pri nevolaní Dispose().
        ''' </summary>
        Protected Overrides Sub Finalize()
            Dispose(False)
            MyBase.Finalize()
        End Sub


#End Region


    End Class

End Namespace
