Option Strict On
Option Explicit On
Option Infer Off

Imports System.Threading.Tasks
Imports Exa.OBERON.Devices.Base

Namespace PriceLabels

    ''' <summary>
    ''' Rozhranie pre device-specific driver elektronických cenoviek.
    ''' Definuje všetky metódy, ktoré musia byť implementované pre každý typ zariadenia.
    ''' </summary>
    Public Interface IPriceLabelsDriver
        Inherits IDisposable

        ''' <summary>Názov zariadenia.</summary>
        ReadOnly Property Name As String

        ''' <summary>Typ modelu zariadenia.</summary>
        ReadOnly Property PriceLabelsModel As enm_PriceLabelsModel

        ''' <summary>Komunikačné nastavenia.</summary>
        Property Communication As Device.cls_Communication

        ''' <summary>
        ''' Test komunikácie so zariadením (async verzia).
        ''' </summary>
        Function CommunicationTest() As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Otvorenie komunikácie.
        ''' </summary>
        Function CommunicationOpen() As EXC.ExaException

        ''' <summary>
        ''' Zatvorenie komunikácie.
        ''' </summary>
        Sub CommunicationClose()

        ''' <summary>
        ''' Nastavenie základnej adresy URL.
        ''' </summary>
        Function SetBaseAddress(BaseAddress As String) As EXC.ExaException

        ''' <summary>
        ''' Otestovanie pripojenia (synchronná verzia).
        ''' </summary>
        Function TestConnection() As EXC.ExaException

        ''' <summary>
        ''' Otestovanie pripojenia (async verzia).
        ''' </summary>
        Function TestConnection2() As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Získava informácie o všetkých cenovkách pripojených k zariadeniu.
        ''' </summary>
        Function GetTagsMsg() As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Získava informácie o základných staniciach (routroch).
        ''' </summary>
        Function GetRoutersMsg() As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Získava informácie o šablónach/styloch pre elektronické cenovky.
        ''' </summary>
        Function GetStylesMsg() As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Získava informácie o konkrétnej šablóne podľa jej ID vrátane definície polí.
        ''' </summary>
        ''' <param name="u_StyleId">Identifikátor šablóny</param>
        Function GetStyleMsgById(u_StyleId As Integer) As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Získava informácie o obrázkoch uložených v zariadení.
        ''' </summary>
        Function GetPhotos() As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Získava údaje (dáta) obrázku podľa jeho názvu.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Function GetPhotoDataByName(u_PhotoName As String) As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Nahraje obrázok do zariadenia.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        ''' <param name="u_Width">Šírka obrázka v pixeloch</param>
        ''' <param name="u_Height">Výška obrázka v pixeloch</param>
        ''' <param name="u_ImageData">Dáta obrázku (Base64 alebo byte array)</param>
        Function UploadPhoto(u_PhotoName As String, u_Width As Integer, u_Height As Integer, u_ImageData As Byte()) As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Zmaže obrázok zo zariadenia.
        ''' </summary>
        ''' <param name="u_PhotoName">Názov obrázka</param>
        Function DeletePhoto(u_PhotoName As String) As Task(Of EXC.ExaException)

        ''' <summary>
        ''' Zmaže cenovky podľa MAC adries.
        ''' </summary>
        ''' <param name="u_MacAddresses">Zoznam MAC adries</param>
        Function DeleteTagsByMac(u_MacAddresses As String()) As Task(Of EXC.ExaException)

        ''' <summary>Event pre logovanie JSON dát.</summary>
        Event JSONLog As Action(Of String)

    End Interface

End Namespace