Option Strict On
Option Explicit On
Option Infer Off

Imports System.Threading.Tasks
Imports Exa.Basic.Debug
Imports Exa.Basic.Exceptions
Imports Exa.Basic.Exceptions.ExaException
Imports Exa.Basic.Helpers
Imports Exa.OBERON.Devices.Base

Namespace PriceLabels

    ''' <summary>
    ''' Systém na elektronické cenovky (Price Labels).
    ''' Factory trieda, ktorá vytvára a spravuje konkrétny driver pre daný model elektronických cenoviek.
    ''' Podporuje nasledujúce modely:
    '''   - OBERON_ESL_2026: Najnovší systém OBERON ESL 2026 pre komunikáciu cez HTTP/HTTPS API
    ''' </summary>
    ''' <remarks>
    ''' Táto trieda slúži ako abstrakčná vrstva medzi hlavnou aplikáciou a konkrétnymi implementáciami driverov.
    ''' Používa factory pattern na vytvorenie správneho driveru na základe typu zariadenia.
    ''' </remarks>
    Public Class Driver_Common
        Implements IDisposable


#Region " Properties "

        ''' <summary>
        ''' Získava konkrétny typ/model zariadenia - presný typ cenoviek.
        ''' Deleguje sa na podkladový driver.
        ''' </summary>
        Public ReadOnly Property PriceLabelsModel() As Main.enm_PriceLabelsModel
            Get
                Return CType(lc_Base_PriceLabels, IPriceLabelsDriver).PriceLabelsModel
            End Get
        End Property

        ''' <summary>
        ''' Nastavenia komunikácie so zariadením.
        ''' Obsahuje IP adresu, port a ďalšie komunikačné parametre.
        ''' </summary>
        Public Property Communication As Exa.OBERON.Devices.Base.Device.cls_Communication
            Get
                Return CType(lc_Base_PriceLabels, IPriceLabelsDriver).Communication
            End Get
            Set(ByVal value As Exa.OBERON.Devices.Base.Device.cls_Communication)
                CType(lc_Base_PriceLabels, IPriceLabelsDriver).Communication = value
            End Set
        End Property


#End Region


#Region " Function "

        ''' <summary>
        ''' Konštruktor factory triedy pre elektronické cenovky.
        ''' Na základe čísla modelu zariadenia vytvára príslušný driver.
        ''' </summary>
        ''' <param name="u_Device">Objekt zariadenia s definovaným typom modelu</param>
        Public Sub New(ByVal u_Device As Exa.OBERON.Devices.Base.Device)

            On Error Resume Next

            Dim tmp_Model As enm_PriceLabelsModel
            tmp_Model = CType(u_Device.Device_Model_Num, enm_PriceLabelsModel)

            '--- Ak nie je model nastavený (0 = None), použi predvolený OBERON_ESL_2026
            If tmp_Model = enm_PriceLabelsModel.None Then
                tmp_Model = enm_PriceLabelsModel.OBERON_ESL_2026
            End If

            Select Case tmp_Model

                Case enm_PriceLabelsModel.OBERON_ESL_2026
                    ' Vytvorí driver pre model OBERON_ESL_2026 (komunikácia cez HTTP/HTTPS API)
                    lc_Base_PriceLabels = New Driver_OBERON_ESL_2026(tmp_Model,
                                                                      u_DeviceName:=u_Device.Device_Name)

                Case Else
                    ' Pre nepodporované modely vyhodí výnimku s chybovým kódom 1000999
                    EXC.Throw("Nepodporovaný model elektronickej cenovky.", 1000999)
                    lc_Base_PriceLabels = Nothing
                    Exit Sub
            End Select

        End Sub

        ''' <summary>
        ''' Testuje komunikáciu so zariadením elektronických cenoviek.
        ''' Async metóda, ktorá deleguje volanie na konkrétny driver.
        ''' </summary>
        ''' <returns>Task obsahujúci výsledok testu (EXC.ExaException.Result = True = úspech)</returns>
        Public Async Function CommunicationTest() As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                ' Podkladový driver nie je inicializovaný
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).CommunicationTest()

        End Function

        ''' <summary>
        ''' Získava informácie o všetkých cenovkách pripojených k zariadeniu.
        ''' </summary>
        Public Async Function GetTagsMsg() As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).GetTagsMsg()

        End Function

        ''' <summary>
        ''' Získava informácie o základných staniciach (routroch).
        ''' </summary>
        Public Async Function GetRoutersMsg() As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).GetRoutersMsg()

        End Function

        ''' <summary>
        ''' Získava informácie o šablónach/styloch pre elektronické cenovky.
        ''' </summary>
        Public Async Function GetStylesMsg() As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).GetStylesMsg()

        End Function

        ''' <summary>
        ''' Získava informácie o konkrétnej šablóne podľa jej ID vrátane definície polí.
        ''' </summary>
        ''' <param name="u_StyleId">Identifikátor šablóny</param>
        Public Async Function GetStyleMsgById(ByVal u_StyleId As Integer) As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).GetStyleMsgById(u_StyleId)

        End Function

        ''' <summary>
        ''' Získava informácie o obrázkoch uložených v zariadení.
        ''' </summary>
        Public Async Function GetPhotos() As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).GetPhotos()

        End Function

        ''' <summary>
        ''' Získava údaje (dáta) obrázku podľa jeho názvu.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Public Async Function GetPhotoDataByName(ByVal u_PhotoName As String) As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).GetPhotoDataByName(u_PhotoName)

        End Function

        ''' <summary>
        ''' Nahraje obrázok do zariadenia.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        ''' <param name="u_Width">Šírka obrázka</param>
        ''' <param name="u_Height">Výška obrázka</param>
        ''' <param name="u_ImageData">Dáta obrázku (byte array)</param>
        Public Async Function UploadPhoto(ByVal u_PhotoName As String, ByVal u_Width As Integer, ByVal u_Height As Integer, ByVal u_ImageData As Byte()) As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).UploadPhoto(u_PhotoName, u_Width, u_Height, u_ImageData)

        End Function

        ''' <summary>
        ''' Zmaže obrázok zo zariadenia.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Public Async Function DeletePhoto(ByVal u_PhotoName As String) As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).DeletePhoto(u_PhotoName)

        End Function

        ''' <summary>
        ''' Zmaže cenovky podľa MAC adries.
        ''' </summary>
        ''' <param name="u_MacAddresses">Zoznam MAC adries</param>
        Public Async Function DeleteTagsByMac(ByVal u_MacAddresses As String()) As Task(Of EXC.ExaException)

            If lc_Base_PriceLabels Is Nothing Then
                Return EXC.Get("Objekt elektronickej cenovky nie je inicializovaný.")
            End If

            Return Await CType(lc_Base_PriceLabels, IPriceLabelsDriver).DeleteTagsByMac(u_MacAddresses)

        End Function



#End Region


#Region " Private "

        ' Základný objekt elektronickej cenovky - konkrétna implementácia driveru.
        ' Inicializuje sa v konštruktore na základe typu modelu.
        ' Hodnota Nothing znamená, že driver ešte nebol vytvorený.
        Private lc_Base_PriceLabels As Object = Nothing


#End Region


#Region " IDisposable "

        ' Označuje, či už bola trieda uvoľnená.
        Private _IsDisposed As Boolean = False

        ''' <summary>
        ''' Uvoľňuje prostriedky použité driverom elektronických cenoviek.
        ''' </summary>
        ''' <param name="disposing">True ak je volané z Dispose(), false z finalizeru</param>
        Protected Overridable Sub Dispose(ByVal disposing As Boolean)
            If Not _IsDisposed Then
                If disposing Then
                    If lc_Base_PriceLabels IsNot Nothing Then
                        Try
                            ' Bezpečne uvoľní podkladový driver cez IDisposable rozhranie
                            CType(lc_Base_PriceLabels, IDisposable).Dispose()
                        Catch
                        End Try
                        lc_Base_PriceLabels = Nothing
                    End If
                End If
                _IsDisposed = True
            End If
        End Sub

        ''' <summary>
        ''' Verejné rozhranie pre uvoľnenie prostriedkov.
        ''' Zaviera Dispose(True) a potláča finalizáciu.
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
