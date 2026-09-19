Option Strict On
Option Explicit On
Option Infer Off

Imports System.Threading.Tasks
Imports Exa.OBERON.Devices.PriceLabels
Imports Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026
Imports Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models
Imports Newtonsoft.Json.Linq
Imports Newtonsoft.Json

Namespace Forms

    ''' <summary>
    ''' Form pre správu elektronických cenoviek cez API.
    ''' Používa Driver_Common factory pre komunikáciu s ESL zariadením.
    ''' Každá záložka zobrazuje dáta z iného API endpointu.
    ''' </summary>
    Public Class frm_ElectronicPriceTags_List
        Inherits Exa.Application.Forms.Form_Win32

        ' Privates
        Private lc_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration = Nothing
        Private lc_Driver_Common As Driver_Common = Nothing

#Region " CONSTRUCTOR "

        ''' <summary>
        ''' Konštruktor formu pre správu elektronických cenoviek.
        ''' Vytvára Driver_Common factory s predvolenými nastaveniami pre OBERON ESL 2026.
        ''' </summary>
        ''' <param name="u_AppConfiguration">Aplikačná konfigurácia pre prístup k nastaveniam</param>
        Public Sub New(u_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration)
            MyBase.New()
            InitializeComponent()
            lc_AppConfiguration = u_AppConfiguration

            ' Vytvor Driver_Common s predvoleným zariadením pre OBERON ESL 2026
            Dim tmp_DefaultDevice As New Exa.OBERON.Devices.Base.Device(u_AppConfiguration)
            tmp_DefaultDevice.Device_Model_Num = CInt(enm_PriceLabelsModel.OBERON_ESL_2026)
            tmp_DefaultDevice.Device_Name = "OBERON ESL 2026"

            lc_Driver_Common = New Driver_Common(tmp_DefaultDevice)

            ' Nastav predvolenú URL adresu ESL servera
            lc_Driver_Common.Communication.TCP_HostName = "http://192.168.16.251"
            lc_Driver_Common.Communication.TCP_Port = 80

            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] Form constructor initialized with Driver_Common", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
        End Sub

#End Region

#Region " PUBLIC METHODS "

        ''' <summary>
        ''' Načíta a inicializuje dáta pre form.
        ''' </summary>
        ''' <returns>ExaException s výsledkom operácie</returns>
        Public Function _LoadData() As EXC.ExaException
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] _LoadData - Form data loading", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                myEx.Result = True
                myEx.Description = "Form inicializovaný."
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] _LoadData - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                myEx = EXC.Get("Chyba pri inicializácii formu.", ex)
            End Try

            Return myEx
        End Function

#End Region

#Region " DATA STORAGE "

        ' Úložisko pre načítané dáta z API
        Private prp_PriceTagData As List(Of TagInfo)
        Private prp_RouterData As List(Of RouterInfo)
        Private prp_StyleData As List(Of BaseStyleInfo)
        Private prp_PhotoData As List(Of PhotoInfo)

#End Region

        ''' <summary>
        ''' Event handler pre tlačidlo "Načítať cenovky" - Tab PriceTagData
        ''' </summary>
        Private Async Sub fro_btn_Load_PriceTagData_Click(sender As Object, e As EventArgs) Handles fro_btn_Load_PriceTagData.ev_Click
            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PriceTagData_Click - Button clicked START", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Test - či je Driver_Common inicializovaný
                If lc_Driver_Common Is Nothing Then
                    MessageBox.Show("ERROR: lc_Driver_Common je Nothing!", "Debug", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PriceTagData_Click - ERROR: lc_Driver_Common is Nothing!", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return
                End If

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PriceTagData_Click - lc_Driver_Common initialized, Communication: " & lc_Driver_Common.Communication.TCP_HostName, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                Await z_LoadPriceTagDataAsync()

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PriceTagData_Click - z_LoadPriceTagDataAsync completed", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PriceTagData_Click - Items.Count after load: " & Me.fro_dgv_PriceTagData.Items.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PriceTagData_Click - Exception: " & ex.ToString(), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                MessageBox.Show("Exception: " & ex.ToString(), "Debug Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
            End Try
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Načítať routre" - Tab RouterInfo
        ''' </summary>
        Private Async Sub fro_btn_Load_RouterInfo_Click(sender As Object, e As EventArgs) Handles fro_btn_Load_RouterInfo.ev_Click
            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_RouterInfo_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            Await z_LoadRouterInfoAsync()
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Načítať šablóny" - Tab StyleMsgArray
        ''' </summary>
        Private Async Sub fro_btn_Load_StyleMsgArray_Click(sender As Object, e As EventArgs) Handles fro_btn_Load_StyleMsgArray.ev_Click
            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_StyleMsgArray_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            Await z_LoadStyleMsgArrayAsync()
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Detail šablóny" - získa detail šablóny podľa ID vybraného riadku
        ''' </summary>
        Private Async Sub fro_btn_Load_StyleMsgById_Click(sender As Object, e As EventArgs) Handles fro_btn_Load_StyleMsgById.ev_Click
            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_StyleMsgById_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Skontroluj či sú dáta a či je vybraný riadok
                If prp_StyleData Is Nothing OrElse prp_StyleData.Count = 0 Then
                    MessageBox.Show("Tabuľka šablón je prázdna.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Získaj SelectedRowIndex z gridu
                Dim selectedIndex As Integer = Me.fro_dgv_StyleMsgArray._Selected_RowIndex
                If selectedIndex < 0 OrElse selectedIndex >= prp_StyleData.Count Then
                    MessageBox.Show("Prosím vyberte šablónu z tabuľky.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Získaj BaseStyleInfo podľa SelectedIndex
                Dim style As BaseStyleInfo = prp_StyleData(selectedIndex)
                If style Is Nothing Then
                    MessageBox.Show("Nie je možné extrahovať ID šablóny.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Return
                End If

                Dim styleId As Integer = style.id
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_StyleMsgById_Click - Loading style details for ID: " & styleId, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Disable button during load
                fro_btn_Load_StyleMsgById.Enabled = False
                Me.z_UpdateStatus("Načítavam detail šablóny...")
                Exa.Application.Cursor_Wait()

                ' Volanie API pre získanie detailu šablóny
                Dim myEx As EXC.ExaException = Await lc_Driver_Common.GetStyleMsgById(styleId)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_StyleMsgById_Click - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    MessageBox.Show("Nie je možné načítať detail šablóny.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                Else
                    ' Zobraziť JSON odpoveď (už naformátovanú z clientu) v novom okne
                    Dim tmp_Json As String = myEx.Description
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_StyleMsgById_Click - JSON length: " & If(tmp_Json IsNot Nothing, tmp_Json.Length, 0), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    ' Zobraziť v novom okne
                    Dim frm_Result As New frm_JsonResult(tmp_Json, "Detail šablóny (ID: " & styleId & ")")
                    frm_Result.ShowDialog(Me)
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_StyleMsgById_Click - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                MessageBox.Show("Chyba pri načítavaní detailu šablóny.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Finally
                fro_btn_Load_StyleMsgById.Enabled = True
                Me.z_UpdateStatus("Pripravené")
                Exa.Application.Cursor_Default()
            End Try
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Načítať obrázky" - Tab PhotoInfo
        ''' </summary>
        Private Async Sub fro_btn_Load_PhotoInfo_Click(sender As Object, e As EventArgs) Handles fro_btn_Load_PhotoInfo.ev_Click
            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PhotoInfo_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            Await z_LoadPhotoInfoAsync()
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Načítať obrázok" - získa a zobrazí obrázok podľa vybraného riadku
        ''' </summary>
        Private Async Sub fro_btn_Load_PhotoImage_Click(sender As Object, e As EventArgs) Handles fro_btn_Load_PhotoImage.ev_Click
            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PhotoImage_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Skontroluj či sú dáta a či je vybraný riadok
                If prp_PhotoData Is Nothing OrElse prp_PhotoData.Count = 0 Then
                    MessageBox.Show("Tabuľka obrázkov je prázdna. Najprv načítajte obrázky.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Získaj SelectedRowIndex z gridu
                Dim selectedIndex As Integer = Me.fro_dgv_PhotoInfo._Selected_RowIndex
                If selectedIndex < 0 OrElse selectedIndex >= prp_PhotoData.Count Then
                    MessageBox.Show("Prosím vyberte obrázok z tabuľky.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Získaj PhotoInfo podľa SelectedIndex
                Dim photo As PhotoInfo = prp_PhotoData(selectedIndex)
                If photo Is Nothing OrElse String.IsNullOrEmpty(photo.name) Then
                    MessageBox.Show("Nie je možné extrahovať názov obrázku.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Return
                End If

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PhotoImage_Click - Loading photo: " & photo.name & " (ID: " & photo.id & ")", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Disable button during load
                fro_btn_Load_PhotoImage.Enabled = False
                Me.z_UpdateStatus("Načítavam obrázok...")
                Exa.Application.Cursor_Wait()

                ' Volanie API pre získanie dát obrázku
                Dim myEx As EXC.ExaException = Await lc_Driver_Common.GetPhotoDataByName(photo.name)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PhotoImage_Click - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    MessageBox.Show("Nie je možné načítať obrázok.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                Else
                    ' Získaj Base64 dátá z ExceptionData
                    Dim tmp_Base64 As String = If(myEx.ExceptionData IsNot Nothing, myEx.ExceptionData, myEx.Description)
                    
                    If String.IsNullOrWhiteSpace(tmp_Base64) Then
                        MessageBox.Show("Obrázok bol načítaný, ale dáta sú prázdne.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                        Return
                    End If

                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PhotoImage_Click - Base64 data length: " & tmp_Base64.Length, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    ' Konvertuj Base64 na Bitmap a zobraz
                    Dim bmp As System.Drawing.Bitmap = z_Base64ToBitmap(tmp_Base64)
                    If bmp IsNot Nothing Then
                        Dim frm_Image As New frm_ImageDisplay(bmp, "Obrázok: " & photo.name)
                        frm_Image.ShowDialog(Me)
                    Else
                        MessageBox.Show("Nie je možné konvertovať obrázok.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    End If
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Load_PhotoImage_Click - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                MessageBox.Show("Chyba pri načítavaní obrázku: " & ex.Message, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Finally
                fro_btn_Load_PhotoImage.Enabled = True
                Me.z_UpdateStatus("Pripravené")
                Exa.Application.Cursor_Default()
            End Try
        End Sub


        ''' <summary>
        ''' Event handler pre tlačidlo "Zatvoriť"
        ''' </summary>
        Private Sub fro_btn_Zatvorit_Click(sender As Object, e As EventArgs) Handles fro_btn_Zatvorit.ev_Click
            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_Zatvorit_Click - Closing form", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            Me.Close()
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Nahrať obrázok"
        ''' </summary>
        Private Async Sub fro_btn_UploadPhoto_Click(sender As Object, e As EventArgs) Handles fro_btn_UploadPhoto.ev_Click
            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Open file dialog to select image
                Using frm_OpenFile As New OpenFileDialog()
                    frm_OpenFile.Filter = "Obrázky|*.png;*.jpg;*.jpeg;*.bmp|Všetky|*.*"
                    frm_OpenFile.Title = "Vybrať obrázok"

                    If frm_OpenFile.ShowDialog() <> DialogResult.OK Then
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - No file selected", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Return
                    End If

                    Dim tmp_FilePath As String = frm_OpenFile.FileName
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - Selected file: " & tmp_FilePath, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    ' Read file bytes
                    Dim tmp_FileBytes As Byte() = IO.File.ReadAllBytes(tmp_FilePath)
                    Dim tmp_FileName As String = IO.Path.GetFileNameWithoutExtension(tmp_FilePath)

                    ' Get image dimensions
                    Dim tmp_Width As Integer = 0
                    Dim tmp_Height As Integer = 0
                    Using tmp_Image As New System.Drawing.Bitmap(tmp_FilePath)
                        tmp_Width = tmp_Image.Width
                        tmp_Height = tmp_Image.Height
                    End Using

                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - Image: " & tmp_FileName & ", Size: " & tmp_Width & "x" & tmp_Height & ", Bytes: " & tmp_FileBytes.Length, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    ' Disable button during upload
                    fro_btn_UploadPhoto.Enabled = False
                    Me.z_UpdateStatus("Nahrávam obrázok...")
                    Exa.Application.Cursor_Wait()

                    ' Call API to upload photo
                    Dim myEx As EXC.ExaException = Await lc_Driver_Common.UploadPhoto(tmp_FileName, tmp_Width, tmp_Height, tmp_FileBytes)

                    If myEx.Result = False Then
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        MessageBox.Show("Nie je možné nahráť obrázok: " & myEx.Description, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Else
                        MessageBox.Show(myEx.Description, "Úspech", MessageBoxButtons.OK, MessageBoxIcon.Information)
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - Success", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    End If

                End Using

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_UploadPhoto_Click - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                MessageBox.Show("Chyba pri nahrávaní obrázku: " & ex.Message, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Finally
                fro_btn_UploadPhoto.Enabled = True
                Me.z_UpdateStatus("Pripravené")
                Exa.Application.Cursor_Default()
            End Try
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Vymazať obrázok"
        ''' </summary>
        Private Async Sub fro_btn_DeletePhoto_Click(sender As Object, e As EventArgs) Handles fro_btn_DeletePhoto.ev_Click
            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeletePhoto_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Check if data is loaded and a row is selected
                If prp_PhotoData Is Nothing OrElse prp_PhotoData.Count = 0 Then
                    MessageBox.Show("Tabuľka obrázkov je prázdna.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Get SelectedRowIndex from grid
                Dim selectedIndex As Integer = Me.fro_dgv_PhotoInfo._Selected_RowIndex
                If selectedIndex < 0 OrElse selectedIndex >= prp_PhotoData.Count Then
                    MessageBox.Show("Prosím vyberte obrázok z tabuľky.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Get PhotoInfo according to SelectedIndex
                Dim photo As PhotoInfo = prp_PhotoData(selectedIndex)
                If photo Is Nothing OrElse String.IsNullOrEmpty(photo.name) Then
                    MessageBox.Show("Nie je možné extrahovať názov obrázku.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Return
                End If

                ' Confirm deletion
                Dim tmp_Message As String = $"Naozaj chcete zmazať obrázok '{photo.name}'?"
                If MessageBox.Show(tmp_Message, "Potvrdenie", MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
                    Return
                End If

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeletePhoto_Click - Deleting photo: " & photo.name & " (ID: " & photo.id & ")", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Disable button during delete
                fro_btn_DeletePhoto.Enabled = False
                Me.z_UpdateStatus("Mazem obrázok...")
                Exa.Application.Cursor_Wait()

                ' Call API to delete photo
                Dim myEx As EXC.ExaException = Await lc_Driver_Common.DeletePhoto(photo.name)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeletePhoto_Click - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    MessageBox.Show("Nie je možné zmazať obrázok: " & myEx.Description, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                Else
                    MessageBox.Show(myEx.Description, "Úspech", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeletePhoto_Click - Success", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeletePhoto_Click - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                MessageBox.Show("Chyba pri zmazávaní obrázku: " & ex.Message, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Finally
                fro_btn_DeletePhoto.Enabled = True
                Me.z_UpdateStatus("Pripravené")
                Exa.Application.Cursor_Default()
            End Try
        End Sub

        ''' <summary>
        ''' Event handler pre tlačidlo "Zmazať cenovky"
        ''' </summary>
        Private Async Sub fro_btn_DeleteTagsByMac_Click(sender As Object, e As EventArgs) Handles fro_btn_DeleteTagsByMac.ev_Click
            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeleteTagsByMac_Click - Button clicked", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Check if data is loaded
                If prp_PriceTagData Is Nothing OrElse prp_PriceTagData.Count = 0 Then
                    MessageBox.Show("Tabuľka cenoviek je prázdna.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                ' Get selected row from grid
                Dim selectedIndex As Integer = Me.fro_dgv_PriceTagData._Selected_RowIndex
                If selectedIndex < 0 Then
                    MessageBox.Show("Prosím vyberte cenovku, ktorú chcete zmazať.", "Informácia", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Return
                End If

                If selectedIndex >= prp_PriceTagData.Count Then
                    MessageBox.Show("Neplatný výber riadku.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Return
                End If

                ' Get MAC address of selected tag
                Dim tmp_Tag As TagInfo = prp_PriceTagData(selectedIndex)
                If tmp_Tag Is Nothing OrElse String.IsNullOrEmpty(tmp_Tag.mac) Then
                    MessageBox.Show("Nie je možné extrahovať MAC adresu.", "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                    Return
                End If

                ' Confirm deletion
                Dim tmp_Message As String = $"Naozaj chcete zmazať cenovku s MAC adresou '{tmp_Tag.mac}'?"
                If MessageBox.Show(tmp_Message, "Potvrdenie", MessageBoxButtons.YesNo, MessageBoxIcon.Question) <> DialogResult.Yes Then
                    Return
                End If

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeleteTagsByMac_Click - Deleting tag: " & tmp_Tag.mac, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Disable button during delete
                fro_btn_DeleteTagsByMac.Enabled = False
                Me.z_UpdateStatus("Mazem cenovku...")
                Exa.Application.Cursor_Wait()

                ' Call API to delete tag
                Dim myEx As EXC.ExaException = Await lc_Driver_Common.DeleteTagsByMac(New String() {tmp_Tag.mac})

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeleteTagsByMac_Click - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    MessageBox.Show("Nie je možné zmazať cenovku: " & myEx.Description, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
                Else
                    ' Odstráňte záznam zo zoznamu a gridu
                    prp_PriceTagData.RemoveAt(selectedIndex)
                    Me.fro_dgv_PriceTagData.Items.RemoveAt(selectedIndex)
                    Me.fro_dgv_PriceTagData._RowsCount = prp_PriceTagData.Count
                    
                    MessageBox.Show(myEx.Description, "Úspech", MessageBoxButtons.OK, MessageBoxIcon.Information)
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeleteTagsByMac_Click - Success - tag removed from grid", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] fro_btn_DeleteTagsByMac_Click - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                MessageBox.Show("Chyba pri zmazávaní cenoviek: " & ex.Message, "Chyba", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Finally
                If fro_btn_DeleteTagsByMac IsNot Nothing Then
                    fro_btn_DeleteTagsByMac.Enabled = True
                End If
                Me.z_UpdateStatus("Pripravené")
                Exa.Application.Cursor_Default()
            End Try
        End Sub



#Region " EVENT HANDLERS - CELL VALUE NEEDED "

        ''' <summary>
        ''' Naplni hodnoty buniek pre PriceTagData grid (virtual mode).
        ''' </summary>
        Private Sub fro_dgv_PriceTagData_ev_Cell_ValueNeeded(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_CellValueNeededEventArgs) Handles fro_dgv_PriceTagData.ev_Cell_ValueNeeded
            If prp_PriceTagData Is Nothing OrElse e.RowIndex < 0 Then Return

            ' Nájdi TagInfo podľa RowIndex
            If e.RowIndex < prp_PriceTagData.Count Then
                Dim tag As TagInfo = prp_PriceTagData(e.RowIndex)
                Select Case e.Column_VisibleIndex
                    Case cln_PriceTag_mac.VisibleIndex : e.Value = tag.mac
                    Case cln_PriceTag_ido.VisibleIndex : e.Value = tag.ido
                    Case cln_PriceTag_routerid.VisibleIndex : e.Value = tag.routerid
                    Case cln_PriceTag_status.VisibleIndex : e.Value = tag.status
                    Case cln_PriceTag_rssi.VisibleIndex : e.Value = tag.rssi
                    Case cln_PriceTag_power.VisibleIndex : e.Value = tag.power
                    Case cln_PriceTag_styleId.VisibleIndex : e.Value = tag.styleId
                    Case cln_PriceTag_width.VisibleIndex : e.Value = tag.width
                    Case cln_PriceTag_height.VisibleIndex : e.Value = tag.height
                End Select
            End If
        End Sub

        ''' <summary>
        ''' Naplni hodnoty buniek pre RouterInfo grid (virtual mode).
        ''' </summary>
        Private Sub fro_dgv_RouterInfo_ev_Cell_ValueNeeded(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_CellValueNeededEventArgs) Handles fro_dgv_RouterInfo.ev_Cell_ValueNeeded
            If prp_RouterData Is Nothing OrElse e.RowIndex < 0 Then Return

            ' Nájdi RouterInfo podľa RowIndex
            If e.RowIndex < prp_RouterData.Count Then
                Dim router As RouterInfo = prp_RouterData(e.RowIndex)
                Select Case e.Column_VisibleIndex
                    Case cln_Router_routerID.VisibleIndex : e.Value = router.routerID
                    Case cln_Router_routerIP.VisibleIndex : e.Value = router.routerIP
                    Case cln_Router_hardwareVersion.VisibleIndex : e.Value = router.hardwareVersion
                    Case cln_Router_softwareVersion.VisibleIndex : e.Value = router.softwareVersion
                    Case cln_Router_freq.VisibleIndex : e.Value = router.freq
                    Case cln_Router_state.VisibleIndex : e.Value = router.state
                    Case cln_Router_tagQuanty.VisibleIndex : e.Value = router.tagQuanty
                    Case cln_Router_lastHeartbeatTime.VisibleIndex : e.Value = router.lastHeartbeatTime
                End Select
            End If
        End Sub

        ''' <summary>
        ''' Naplni hodnoty buniek pre StyleMsgArray grid (virtual mode).
        ''' </summary>
        Private Sub fro_dgv_StyleMsgArray_ev_Cell_ValueNeeded(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_CellValueNeededEventArgs) Handles fro_dgv_StyleMsgArray.ev_Cell_ValueNeeded
            If prp_StyleData Is Nothing OrElse e.RowIndex < 0 Then Return

            ' Nájdi BaseStyleInfo podľa RowIndex
            If e.RowIndex < prp_StyleData.Count Then
                Dim style As BaseStyleInfo = prp_StyleData(e.RowIndex)
                Select Case e.Column_VisibleIndex
                    Case cln_Style_id.VisibleIndex : e.Value = style.id
                    Case cln_Style_name.VisibleIndex : e.Value = style.name
                    Case cln_Style_type.VisibleIndex : e.Value = style.type
                    Case cln_Style_width.VisibleIndex : e.Value = style.width
                    Case cln_Style_height.VisibleIndex : e.Value = style.height
                    Case cln_Style_backgroundID.VisibleIndex : e.Value = style.backgroundID
                    Case cln_Style_updateTime.VisibleIndex : e.Value = style.updateTime
                End Select
            End If
        End Sub

        ''' <summary>
        ''' Naplni hodnoty buniek pre PhotoInfo grid (virtual mode).
        ''' </summary>
        Private Sub fro_dgv_PhotoInfo_ev_Cell_ValueNeeded(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_CellValueNeededEventArgs) Handles fro_dgv_PhotoInfo.ev_Cell_ValueNeeded
            If prp_PhotoData Is Nothing OrElse e.RowIndex < 0 Then Return

            ' Nájdi PhotoInfo podľa RowIndex
            If e.RowIndex < prp_PhotoData.Count Then
                Dim photo As PhotoInfo = prp_PhotoData(e.RowIndex)
                Select Case e.Column_VisibleIndex
                    Case cln_Photo_id.VisibleIndex : e.Value = photo.id
                    Case cln_Photo_name.VisibleIndex : e.Value = photo.name
                    Case cln_Photo_width.VisibleIndex : e.Value = photo.width
                    Case cln_Photo_height.VisibleIndex : e.Value = photo.height
                End Select
            End If
        End Sub

#End Region

#Region " PRIVATE METHODS - DATA LOADING "

        ''' <summary>
        ''' Načíta dáta cenoviek (TagInfo) z API cez Driver_Common.
        ''' </summary>
        Private Async Function z_LoadPriceTagDataAsync() As Task
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Starting data load...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Driver Communication: " & lc_Driver_Common.Communication.TCP_HostName, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Try
                Me.z_SetLoadingState(True)
                Me.fro_btn_Load_PriceTagData.Enabled = False
                Me.z_UpdateStatus("Načítavam cenovky...")

                ' Najprv otestovať pripojenie a nastaviť URL do klienta
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Testing connection and setting URL...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                myEx = Await lc_Driver_Common.CommunicationTest()
                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Connection test failed: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Me.z_UpdateStatus($"Chyba pripojenia: {myEx.Description}")
                    Exa.Application.MsgBox("Nie je možné nadviazať spojenie s ESL zariadením.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                    Return
                End If

                ' Potom načítať dáta cenoviek
                myEx = Await lc_Driver_Common.GetTagsMsg()

                Dim tmp_DescPreview As String = If(myEx.Description IsNot Nothing, myEx.Description.Substring(0, Math.Min(100, myEx.Description.Length)), "Nothing")
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - GetTagsMsg() returned - Result: " & myEx.Result & ", Description: " & tmp_DescPreview, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Me.z_UpdateStatus($"Chyba: {myEx.Description}")
                    Exa.Application.MsgBox("Nie je možné načítať cenovky.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Else
                    ' Deserializácia JSON odpovede do TagInfo listu
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Deserializing JSON response...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Dim lst_Tags As List(Of TagInfo) = z_DeserializeTagsMsg(myEx.Description)

                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Deserialization result: " & If(lst_Tags IsNot Nothing, "Count=" & lst_Tags.Count, "Nothing"), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    If lst_Tags IsNot Nothing Then
                        ' Vymaz existujuce polozky
                        Me.fro_dgv_PriceTagData.Items.Clear()

                        ' Pridaj nove polozky do DataGridu - Cell_ValueNeeded pouzije RowIndex
                        For Each tag As TagInfo In lst_Tags
                            Me.fro_dgv_PriceTagData.Items.Add(
                                tag.mac,
                                u_Tag:=tag
                            )
                        Next

                        ' DULEZITE: Nastavit pocet riadkov pre grid!
                        ' Cell_ValueNeeded event sa vola iba ak grid viem kolko ma riadkov
                        Me.fro_dgv_PriceTagData._RowsCount = lst_Tags.Count

                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Successfully loaded " & lst_Tags.Count & " tags, _RowsCount=" & Me.fro_dgv_PriceTagData._RowsCount, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        ' Ulož dáta do property pre Cell_ValueNeeded event
                        prp_PriceTagData = lst_Tags

                        Me.z_UpdateStatus($"Načítaných {lst_Tags.Count} cenoviek.")
                    Else
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - No tags found in response", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Me.z_UpdateStatus("Žiadne cenovky nenájdené.")
                    End If
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPriceTagDataAsync - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Dim ex_Local As EXC.ExaException = EXC.Get("Chyba pri načítavaní cenoviek.", ex)
                Me.z_UpdateStatus($"Chyba: {ex_Local.Description}")
                Exa.Application.MsgBox("Nie je možné načítať cenovky.", ex_Local, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Finally
                Me.z_SetLoadingState(False)
            End Try
        End Function

        ''' <summary>
        ''' Načíta dáta routerov (RouterInfo) z API cez Driver_Common.
        ''' </summary>
        Private Async Function z_LoadRouterInfoAsync() As Task
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - Starting data load...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Try
                Me.z_SetLoadingState(True)
                Me.fro_btn_Load_RouterInfo.Enabled = False
                Me.z_UpdateStatus("Načítavam routre...")

                ' Volanie API pre získanie routerov cez Driver_Common
                myEx = Await lc_Driver_Common.GetRoutersMsg()

                Dim tmp_DescPreview As String = If(myEx.Description IsNot Nothing, myEx.Description.Substring(0, Math.Min(100, myEx.Description.Length)), "Nothing")
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - GetRoutersMsg() returned - Result: " & myEx.Result & ", Description: " & tmp_DescPreview, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Me.z_UpdateStatus($"Chyba: {myEx.Description}")
                    Exa.Application.MsgBox("Nie je možné načítať routre.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Else
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - Deserializing JSON response...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Dim lst_Routers As List(Of RouterInfo) = z_DeserializeRouterMsg(myEx.Description)

                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - Deserialization result: " & If(lst_Routers IsNot Nothing, "Count=" & lst_Routers.Count, "Nothing"), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    If lst_Routers IsNot Nothing Then
                        Me.fro_dgv_RouterInfo.Items.Clear()

                        For Each router As RouterInfo In lst_Routers
                            Me.fro_dgv_RouterInfo.Items.Add(
                                router.routerID.ToString(),
                                u_Tag:=router
                            )
                        Next

                        ' DULEZITE: Nastavit pocet riadkov pre grid!
                        Me.fro_dgv_RouterInfo._RowsCount = lst_Routers.Count

                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - Successfully loaded " & lst_Routers.Count & " routers, _RowsCount=" & Me.fro_dgv_RouterInfo._RowsCount, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        ' Ulož dáta do property pre Cell_ValueNeeded event
                        prp_RouterData = lst_Routers

                        Me.z_UpdateStatus($"Načítaných {lst_Routers.Count} routerov.")
                    Else
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - No routers found in response", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Me.z_UpdateStatus("Žiadne routre nenájdené.")
                    End If
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadRouterInfoAsync - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Dim ex_Local As EXC.ExaException = EXC.Get("Chyba pri načítavaní routerov.", ex)
                Me.z_UpdateStatus($"Chyba: {ex_Local.Description}")
                Exa.Application.MsgBox("Nie je možné načítať routre.", ex_Local, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Finally
                Me.z_SetLoadingState(False)
            End Try
        End Function

        ''' <summary>
        ''' Načíta dáta šablón (StyleInfo) z API cez Driver_Common.
        ''' </summary>
        Private Async Function z_LoadStyleMsgArrayAsync() As Task
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - Starting data load...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Try
                Me.z_SetLoadingState(True)
                Me.fro_btn_Load_StyleMsgArray.Enabled = False
                Me.z_UpdateStatus("Načítavam šablóny...")

                ' Volanie API pre získanie šablón cez Driver_Common
                myEx = Await lc_Driver_Common.GetStylesMsg()

                Dim tmp_DescPreview As String = If(myEx.Description IsNot Nothing, myEx.Description.Substring(0, Math.Min(100, myEx.Description.Length)), "Nothing")
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - GetStylesMsg() returned - Result: " & myEx.Result & ", Description: " & tmp_DescPreview, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Me.z_UpdateStatus($"Chyba: {myEx.Description}")
                    Exa.Application.MsgBox("Nie je možné načítať šablóny.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Else
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - Deserializing JSON response...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Dim lst_Styles As List(Of BaseStyleInfo) = z_DeserializeStyleMsg(myEx.Description)

                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - Deserialization result: " & If(lst_Styles IsNot Nothing, "Count=" & lst_Styles.Count, "Nothing"), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    If lst_Styles IsNot Nothing Then
                        Me.fro_dgv_StyleMsgArray.Items.Clear()

                        For Each style As BaseStyleInfo In lst_Styles
                            Me.fro_dgv_StyleMsgArray.Items.Add(
                                style.id.ToString(),
                                u_Tag:=style
                            )
                        Next

                        ' DULEZITE: Nastavit pocet riadkov pre grid!
                        Me.fro_dgv_StyleMsgArray._RowsCount = lst_Styles.Count

                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - Successfully loaded " & lst_Styles.Count & " styles, _RowsCount=" & Me.fro_dgv_StyleMsgArray._RowsCount, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        ' Ulož dáta do property pre Cell_ValueNeeded event
                        prp_StyleData = lst_Styles

                        Me.z_UpdateStatus($"Načítaných {lst_Styles.Count} šablón.")
                    Else
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - No styles found in response", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Me.z_UpdateStatus("Žiadne šablóny nenájdené.")
                    End If
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadStyleMsgArrayAsync - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Dim ex_Local As EXC.ExaException = EXC.Get("Chyba pri načítavaní šablón.", ex)
                Me.z_UpdateStatus($"Chyba: {ex_Local.Description}")
                Exa.Application.MsgBox("Nie je možné načítať šablóny.", ex_Local, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Finally
                Me.z_SetLoadingState(False)
            End Try
        End Function

        ''' <summary>
        ''' Načíta dáta obrázkov (PhotoInfo) z API cez Driver_Common.
        ''' </summary>
        Private Async Function z_LoadPhotoInfoAsync() As Task
            Dim myEx As EXC.ExaException = EXC.GetDefault

            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - Starting data load...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Try
                Me.z_SetLoadingState(True)
                Me.fro_btn_Load_PhotoInfo.Enabled = False
                Me.z_UpdateStatus("Načítavam obrázky...")

                ' Volanie API pre získanie obrázkov cez Driver_Common
                myEx = Await lc_Driver_Common.GetPhotos()

                Dim tmp_DescPreview As String = If(myEx.Description IsNot Nothing, myEx.Description.Substring(0, Math.Min(100, myEx.Description.Length)), "Nothing")
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - GetPhotos() returned - Result: " & myEx.Result & ", Description: " & tmp_DescPreview, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If myEx.Result = False Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - API returned error: " & myEx.Description, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Me.z_UpdateStatus($"Chyba: {myEx.Description}")
                    Exa.Application.MsgBox("Nie je možné načítať obrázky.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Else
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - Deserializing JSON response...", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Dim lst_Photos As List(Of PhotoInfo) = z_DeserializePhotoMsg(myEx.Description)

                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - Deserialization result: " & If(lst_Photos IsNot Nothing, "Count=" & lst_Photos.Count, "Nothing"), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                    If lst_Photos IsNot Nothing Then
                        Me.fro_dgv_PhotoInfo.Items.Clear()

                        For Each photo As PhotoInfo In lst_Photos
                            Me.fro_dgv_PhotoInfo.Items.Add(
                                photo.id.ToString(),
                                u_Tag:=photo
                            )
                        Next

                        ' DULEZITE: Nastavit pocet riadkov pre grid!
                        Me.fro_dgv_PhotoInfo._RowsCount = lst_Photos.Count

                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - Successfully loaded " & lst_Photos.Count & " photos, _RowsCount=" & Me.fro_dgv_PhotoInfo._RowsCount, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        ' Ulož dáta do property pre Cell_ValueNeeded event
                        prp_PhotoData = lst_Photos

                        Me.z_UpdateStatus($"Načítaných {lst_Photos.Count} obrázkov.")
                    Else
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - No photos found in response", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Me.z_UpdateStatus("Žiadne obrázky nenájdené.")
                    End If
                End If

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_LoadPhotoInfoAsync - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Dim ex_Local As EXC.ExaException = EXC.Get("Chyba pri načítavaní obrázkov.", ex)
                Me.z_UpdateStatus($"Chyba: {ex_Local.Description}")
                Exa.Application.MsgBox("Nie je možné načítať obrázky.", ex_Local, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Finally
                Me.z_SetLoadingState(False)
            End Try
        End Function

#End Region

#Region " PRIVATE METHODS - JSON DESERIALIZATION "

        ''' <summary>
        ''' Deserializuje JSON odpoveď z getTagsMsg endpointu do TagInfo listu.
        ''' </summary>
        Private Function z_DeserializeTagsMsg(ByVal u_JsonData As String) As List(Of TagInfo)
            Dim result As New List(Of TagInfo)()

            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - Input JSON length: " & If(u_JsonData IsNot Nothing, u_JsonData.Length, 0), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If String.IsNullOrWhiteSpace(u_JsonData) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - Input JSON is null or empty", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' API vracia JSON obalený v úvodzovkách s escaped úvodzovkami vnútri
                ' Napr: "[{\"mac\":\"92.96.43.22\",...}]"
                Dim json As String = u_JsonData.Trim()

                ' Odstrániť obalujúce úvodzovky
                If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                    json = json.Substring(1, json.Length - 2)
                End If

                ' Unescape JSON reťazec - premeniť \" na " a \\ na \ a \n na newline atď.
                ' Toto je potrebné pretože ESL server vracia JSON s escaped úvodzovkami
                ' Použijeme JavaScriptSerializer alebo jednoduchý manuálny parser
                json = z_UnescapeJsonString(json)

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - JSON after unescaping, length: " & json.Length, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Parsovanie JSON
                Dim jArray As JArray = JArray.Parse(json)
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - JArray parsed, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Konverzia na TagInfo objekty
                For Each jToken As JToken In jArray
                    Dim jObj As JObject = CType(jToken, JObject)
                    If jObj IsNot Nothing Then
                        ' Debug - vypíš všetky kľúče v JSON objekte
                        Dim tmp_KeyNames As String = String.Join(", ", jObj.Properties().Select(Function(p) p.Name))
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - JSON keys: " & tmp_KeyNames, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                        Dim info As New TagInfo()
                        info.mac = If(jObj("mac") IsNot Nothing, jObj("mac").ToString(), String.Empty)
                        info.ido = If(jObj("ido") IsNot Nothing, CInt(jObj("ido")), 0)
                        info.routerid = If(jObj("routerid") IsNot Nothing, jObj("routerid").ToString(), String.Empty)
                        info.status = If(jObj("status") IsNot Nothing, CInt(jObj("status")), 0)
                        info.rssi = If(jObj("rssi") IsNot Nothing, CDbl(jObj("rssi")), 0.0)
                        info.power = If(jObj("power") IsNot Nothing, CInt(jObj("power")), 0)
                        info.styleId = If(jObj("styleid") IsNot Nothing, CInt(jObj("styleid")), 0)
                        info.width = If(jObj("width") IsNot Nothing, CInt(jObj("width")), 0)
                        info.height = If(jObj("height") IsNot Nothing, CInt(jObj("height")), 0)

                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - Parsed: mac=" & info.mac & ", ido=" & info.ido & ", routerid=" & info.routerid & ", status=" & info.status, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                        result.Add(info)
                    End If
                Next

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - Deserialization complete, result count: " & result.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeTagsMsg - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                ' Chyba pri deserializácii - vráti Nothing
                Return Nothing
            End Try

            Return result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď z getRoutersMsg endpointu do RouterInfo listu.
        ''' </summary>
        Private Function z_DeserializeRouterMsg(ByVal u_JsonData As String) As List(Of RouterInfo)
            Dim result As New List(Of RouterInfo)()

            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - Input JSON length: " & If(u_JsonData IsNot Nothing, u_JsonData.Length, 0), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If String.IsNullOrWhiteSpace(u_JsonData) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - Input JSON is null or empty", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' SKONTROLUJ CI TO NIE JE TEXTOVA ODPOVED (napr. "Success", "Error", etc.)
                ' JSON musi zaciat na [ alebo {
                Dim json As String = u_JsonData.Trim()
                If json.Length > 0 AndAlso Not (json.StartsWith("[") OrElse json.StartsWith("{") OrElse json.StartsWith("""")) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - NOT JSON, text response: " & json, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' Odstrániť obalujúce úvodzovky ak sú prítomné
                If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                    json = json.Substring(1, json.Length - 2)
                End If

                ' Po odstránení úvodzoviek skontroluj znova
                If json.Length > 0 AndAlso Not (json.StartsWith("[") OrElse json.StartsWith("{")) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - After stripping quotes, NOT JSON: " & json, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                json = z_UnescapeJsonString(json)

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - JSON after unescaping, length: " & json.Length, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                Dim jArray As JArray = JArray.Parse(json)
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - JArray parsed, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Konverzia na RouterInfo objekty
                For Each jToken As JToken In jArray
                    Dim jObj As JObject = CType(jToken, JObject)
                    If jObj IsNot Nothing Then
                        Dim info As New RouterInfo()
                        info.routerID = If(jObj("routerID") IsNot Nothing, CInt(jObj("routerID")), 0)
                        info.routerIP = If(jObj("routerIP") IsNot Nothing, jObj("routerIP").ToString(), String.Empty)
                        info.hardwareVersion = If(jObj("hardwareVersion") IsNot Nothing, jObj("hardwareVersion").ToString(), String.Empty)
                        info.softwareVersion = If(jObj("softwareVersion") IsNot Nothing, jObj("softwareVersion").ToString(), String.Empty)
                        info.freq = If(jObj("freq") IsNot Nothing, CInt(jObj("freq")), 0)
                        info.state = If(jObj("state") IsNot Nothing, CInt(jObj("state")), 0)
                        info.tagQuanty = If(jObj("tagQuanty") IsNot Nothing, CInt(jObj("tagQuanty")), 0)
                        info.lastHeartbeatTime = If(jObj("lastHeartbeatTime") IsNot Nothing, CLng(jObj("lastHeartbeatTime")), 0L)
                        result.Add(info)
                    End If
                Next

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - Deserialization complete, result count: " & result.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeRouterMsg - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            Return result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď z getStylesMsg endpointu do BaseStyleInfo listu.
        ''' </summary>
        Private Function z_DeserializeStyleMsg(ByVal u_JsonData As String) As List(Of BaseStyleInfo)
            Dim result As New List(Of BaseStyleInfo)()

            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Input JSON length: " & If(u_JsonData IsNot Nothing, u_JsonData.Length, 0), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If String.IsNullOrWhiteSpace(u_JsonData) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Input JSON is null or empty", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' Debug: vypis prvej 200 znakov originálneho JSON
                Dim tmp_Preview As String = u_JsonData.Substring(0, Math.Min(200, u_JsonData.Length))
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - JSON preview: " & tmp_Preview, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' SKONTROLUJ CI TO NIE JE TEXTOVA ODPOVED (napr. "Success", "Error", etc.)
                ' JSON musi zaciat na [ alebo {
                Dim json As String = u_JsonData.Trim()
                If json.Length > 0 AndAlso Not (json.StartsWith("[") OrElse json.StartsWith("{") OrElse json.StartsWith("""")) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - NOT JSON, text response: " & json, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' Odstrániť obalujúce úvodzovky ak sú prítomné
                If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                    json = json.Substring(1, json.Length - 2)
                End If

                ' Po odstránení úvodzoviek skontroluj znova
                If json.Length > 0 AndAlso Not (json.StartsWith("[") OrElse json.StartsWith("{")) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - After stripping quotes, NOT JSON: " & json, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                json = z_UnescapeJsonString(json)

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - JSON after unescaping, length: " & json.Length, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Skontroluj typ JSON - ESL server vracia {"datalist":[...]}
                Dim jArray As JArray = Nothing

                ' Skús parse podľa typu JSON
                If json.Trim().StartsWith("{"c) Then
                    ' JSON object - extrahuj "datalist" array
                    Dim jObj As JObject = JObject.Parse(json)

                    ' Skontroluj či JObject obsahuje array v "datalist" kľúči
                    ' API vracia: {"datalist":[{...},{...},...]}
                    Dim tmp_ArrayValue As JToken = jObj("datalist")
                    If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                        ' Extrahuj array z datalist kľúča
                        jArray = CType(tmp_ArrayValue, JArray)
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Extracted array from 'datalist' key, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Else
                        ' Skús známe array kľúče
                        For Each tmp_Key As String In New String() {"data", "result", "items", "list", "response", "value"}
                            tmp_ArrayValue = jObj(tmp_Key)
                            If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                                jArray = CType(tmp_ArrayValue, JArray)
                                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Extracted array from '" & tmp_Key & "' key, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                                Exit For
                            End If
                        Next

                        ' Ak žiadny array kľúč nebol nájdený, obal celý JObject do array
                        If jArray Is Nothing Then
                            jArray = New JArray(jObj)
                            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - No array key found, wrapping JObject into array", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        End If
                    End If
                ElseIf json.Trim().StartsWith("["c) Then
                    ' JSON array - parse priamo
                    jArray = JArray.Parse(json)
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Parsed JArray directly, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    ' Neznámy formát - skús JObject fallback
                    Try
                        jArray = New JArray(JObject.Parse(json))
                    Catch jsonEx2 As Exception
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Unknown JSON format, fallback failed: " & jsonEx2.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Return Nothing
                    End Try
                End If

                If jArray Is Nothing Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - jArray is Nothing after parsing", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - JArray parsed, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Konverzia na BaseStyleInfo objekty
                For Each jToken As JToken In jArray
                    Dim jObj As JObject = CType(jToken, JObject)
                    If jObj IsNot Nothing Then
                        Dim info As New BaseStyleInfo()
                        info.id = If(jObj("id") IsNot Nothing, CInt(jObj("id")), 0)
                        info.name = If(jObj("name") IsNot Nothing, jObj("name").ToString(), String.Empty)
                        info.type = If(jObj("type") IsNot Nothing, CInt(jObj("type")), 0)
                        info.width = If(jObj("width") IsNot Nothing, CInt(jObj("width")), 0)
                        info.height = If(jObj("height") IsNot Nothing, CInt(jObj("height")), 0)
                        info.backgroundID = If(jObj("backgroundID") IsNot Nothing, CInt(jObj("backgroundID")), 0)
                        info.updateTime = If(jObj("updateTime") IsNot Nothing, jObj("updateTime").ToString(), String.Empty)
                        info.descriptor = If(jObj("descriptor") IsNot Nothing, jObj("descriptor").ToString(), String.Empty)
                        info.mappingtype = If(jObj("mappingtype") IsNot Nothing, CInt(jObj("mappingtype")), 0)
                        result.Add(info)
                    End If
                Next

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Deserialization complete, result count: " & result.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializeStyleMsg - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            Return result
        End Function

        ''' <summary>
        ''' Deserializuje JSON odpoveď z getPhotos endpointu do PhotoInfo listu.
        ''' </summary>
        Private Function z_DeserializePhotoMsg(ByVal u_JsonData As String) As List(Of PhotoInfo)
            Dim result As New List(Of PhotoInfo)()

            Try
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Input JSON length: " & If(u_JsonData IsNot Nothing, u_JsonData.Length, 0), Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                If String.IsNullOrWhiteSpace(u_JsonData) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Input JSON is null or empty", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' SKONTROLUJ CI TO NIE JE TEXTOVA ODPOVED (napr. "Success", "Error", etc.)
                ' JSON musi zaciat na [ alebo {
                Dim json As String = u_JsonData.Trim()
                If json.Length > 0 AndAlso Not (json.StartsWith("[") OrElse json.StartsWith("{") OrElse json.StartsWith("""")) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - NOT JSON, text response: " & json, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                ' Odstrániť obalujúce úvodzovky ak sú prítomné
                If json.Length >= 2 AndAlso json.StartsWith("""") AndAlso json.EndsWith("""") Then
                    json = json.Substring(1, json.Length - 2)
                End If

                ' Po odstránení úvodzoviek skontroluj znova
                If json.Length > 0 AndAlso Not (json.StartsWith("[") OrElse json.StartsWith("{")) Then
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - After stripping quotes, NOT JSON: " & json, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Return Nothing
                End If

                json = z_UnescapeJsonString(json)

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - JSON after unescaping, length: " & json.Length, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Skontroluj typ JSON pred parsovaním - ESL server vracia {"datalist":[...],...}
                Dim jArray As JArray = Nothing

                If json.Trim().StartsWith("{"c) Then
                    ' JSON object - extrahuj "datalist" array
                    Dim jObj As JObject = JObject.Parse(json)

                    ' Skontroluj či JObject obsahuje array v "datalist" kľúči
                    ' API vracia: {"datalist":[{...},{...},...], "page":{...}, "resultCode":..., "resultMsg":...}
                    Dim tmp_ArrayValue As JToken = jObj("datalist")
                    If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                        ' Extrahuj array z datalist kľúča
                        jArray = CType(tmp_ArrayValue, JArray)
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Extracted array from 'datalist' key, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Else
                        ' Skús iné bežné array kľúče
                        For Each tmp_Key As String In New String() {"data", "result", "items", "list", "response", "value"}
                            tmp_ArrayValue = jObj(tmp_Key)
                            If tmp_ArrayValue IsNot Nothing AndAlso tmp_ArrayValue.Type = JTokenType.Array Then
                                jArray = CType(tmp_ArrayValue, JArray)
                                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Extracted array from '" & tmp_Key & "' key, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                                Exit For
                            End If
                        Next

                        ' Ak žiadny array kľúč nebol nájdený, obal celý JObject do listu
                        If jArray Is Nothing Then
                            jArray = New JArray(jObj)
                            Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - No array key found, wrapping JObject into array", Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        End If
                    End If
                ElseIf json.Trim().StartsWith("["c) Then
                    ' JSON array - parse priamo
                    jArray = JArray.Parse(json)
                    Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Parsed JArray directly, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Else
                    ' Neznámy formát - skús JObject fallback
                    Try
                        jArray = New JArray(JObject.Parse(json))
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Unknown JSON format, fallback to JObject, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Warning, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                    Catch jsonEx2 As Exception
                        Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Unknown JSON format, fallback failed: " & jsonEx2.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                        Return Nothing
                    End Try
                End If
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - JArray parsed, count: " & jArray.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' Konverzia na PhotoInfo objekty
                For Each jToken As JToken In jArray
                    Dim jObj As JObject = CType(jToken, JObject)
                    If jObj IsNot Nothing Then
                        Dim info As New PhotoInfo()
                        info.id = If(jObj("id") IsNot Nothing, CInt(jObj("id")), 0)
                        info.name = If(jObj("name") IsNot Nothing, jObj("name").ToString(), String.Empty)
                        info.width = If(jObj("width") IsNot Nothing, CInt(jObj("width")), 0)
                        info.height = If(jObj("height") IsNot Nothing, CInt(jObj("height")), 0)
                        result.Add(info)
                    End If
                Next

                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Deserialization complete, result count: " & result.Count, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_DeserializePhotoMsg - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try

            Return result
        End Function

#End Region

#Region " PRIVATE METHODS - HELPERS "

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
        ''' Nastaví loading stav UI (enable/disable tlačidiel).
        ''' </summary>
        Private Sub z_SetLoadingState(ByVal u_IsLoading As Boolean)
            fro_btn_Load_PriceTagData.Enabled = Not u_IsLoading
            fro_btn_DeleteTagsByMac.Enabled = Not u_IsLoading
            fro_btn_Load_RouterInfo.Enabled = Not u_IsLoading
            fro_btn_Load_StyleMsgArray.Enabled = Not u_IsLoading
            fro_btn_Load_PhotoInfo.Enabled = Not u_IsLoading
            fro_btn_Load_PhotoImage.Enabled = Not u_IsLoading
            fro_btn_UploadPhoto.Enabled = Not u_IsLoading
            fro_btn_DeletePhoto.Enabled = Not u_IsLoading
            fro_btn_Zatvorit.Enabled = Not u_IsLoading

            If u_IsLoading Then
                Exa.Application.Cursor_Wait()
            Else
                Exa.Application.Cursor_Default()
            End If
        End Sub

        ''' <summary>
        ''' Aktualizuje status label v status bare.
        ''' </summary>
        Private Sub z_UpdateStatus(ByVal u_Message As String)
            If fro_lbl_Status.InvokeRequired Then
                fro_lbl_Status.Invoke(New Action(Sub() fro_lbl_Status.Text = u_Message))
            Else
                fro_lbl_Status.Text = u_Message
            End If
        End Sub

        ''' <summary>
        ''' Konvertuje Base64 string na Bitmap.
        ''' </summary>
        ''' <param name="u_Base64String">Base64 encoded image string</param>
        ''' <returns>Bitmap alebo Nothing pri chybe</returns>
        Private Function z_Base64ToBitmap(ByVal u_Base64String As String) As System.Drawing.Bitmap
            Try
                ' Odstrániť prefix ak je prítomný (napr. "data:image/png;base64,")
                Dim tmp_Base64 As String = u_Base64String
                If tmp_Base64.Contains(",") Then
                    tmp_Base64 = tmp_Base64.Substring(tmp_Base64.IndexOf(",") + 1)
                End If

                ' Konvertuj Base64 na byte array
                Dim tmp_Bytes As Byte() = Convert.FromBase64String(tmp_Base64)

                ' Vytvor Bitmap z byte array
                Using ms As New System.IO.MemoryStream(tmp_Bytes)
                    Return New System.Drawing.Bitmap(ms)
                End Using
            Catch ex As Exception
                Exa.Basic.Debug.Console._Write("[frm_ElectronicPriceTags] z_Base64ToBitmap - Exception: " & ex.Message, Nothing, "ElectronicPriceTags", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)
                Return Nothing
            End Try
        End Function


#End Region

    End Class

End Namespace