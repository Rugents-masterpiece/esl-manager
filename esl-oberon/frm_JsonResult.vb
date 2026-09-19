Option Strict On
Option Explicit On
Option Infer Off

Namespace Forms

    ''' <summary>
    ''' Dialogové okno na zobrazenie formátovaného JSON dát.
    ''' </summary>
    Public Class frm_JsonResult
        Inherits Exa.Application.Forms.Form_Win32

        Private lc_JsonText As String = String.Empty
        Private lc_Title As String = String.Empty

        Private txt_JsonDisplay As TextBox = Nothing
        Private fro_btn_Zatvorit As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32 = Nothing

        ''' <summary>
        ''' Konštruktor dialogu pre zobrazenie JSON.
        ''' </summary>
        ''' <param name="u_JsonText">JSON text na zobrazenie</param>
        ''' <param name="u_Title">Názov okna</param>
        Public Sub New(ByVal u_JsonText As String, ByVal u_Title As String)
            MyBase.New()
            lc_JsonText = u_JsonText
            lc_Title = u_Title

            InitializeComponent()
            InitializeUI()
        End Sub

        ''' <summary>
        ''' Inicializácia komponentov formu.
        ''' </summary>
        Private Sub InitializeComponent()
            Me.Text = lc_Title
            Me.Size = New System.Drawing.Size(800, 600)
            Me.StartPosition = FormStartPosition.CenterParent
            Me.FormBorderStyle = FormBorderStyle.FixedDialog
            Me.MaximizeBox = False
            Me.MinimizeBox = False
        End Sub

        ''' <summary>
        ''' Inicializácia UI komponentov.
        ''' </summary>
        Private Sub InitializeUI()
            ' TextBox pre zobrazenie JSON
            txt_JsonDisplay = New TextBox()
            txt_JsonDisplay.Dock = DockStyle.Fill
            txt_JsonDisplay.Multiline = True
            txt_JsonDisplay.Font = New Font("Consolas", 9.0F)
            txt_JsonDisplay.Text = lc_JsonText
            txt_JsonDisplay.ReadOnly = True
            txt_JsonDisplay.ScrollBars = ScrollBars.Both
            txt_JsonDisplay.BackColor = Color.White
            txt_JsonDisplay.ForeColor = Color.Black

            ' Tlačidlo Zatvoriť
            fro_btn_Zatvorit = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            fro_btn_Zatvorit._Text = "Zatvoriť"
            fro_btn_Zatvorit.Anchor = AnchorStyles.Bottom Or AnchorStyles.Right
            fro_btn_Zatvorit.Location = New System.Drawing.Point(700, 8)
            fro_btn_Zatvorit.Size = New System.Drawing.Size(80, 28)
            fro_btn_Zatvorit.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.Cancel
            AddHandler fro_btn_Zatvorit.ev_Click, Sub(s As Object, e As EventArgs) Me.Close()

            ' Pridanie komponentov do formu
            Me.Controls.Add(txt_JsonDisplay)
            Me.Controls.Add(fro_btn_Zatvorit)
        End Sub

    End Class

End Namespace