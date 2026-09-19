Namespace Forms.DeviceSettings.PriceLabels

    <Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
    Partial Class frm_OBERON_ESL_2026
        Inherits Exa.Application.Forms.Form_Win32

        'Form overrides dispose to clean up the component list.
        <System.Diagnostics.DebuggerNonUserCode()>
        Protected Overrides Sub Dispose(ByVal disposing As Boolean)
            Try
                If disposing AndAlso components IsNot Nothing Then
                    components.Dispose()
                End If
            Finally
                MyBase.Dispose(disposing)
            End Try
        End Sub

        'Required by the Windows Form Designer
        Private components As System.ComponentModel.IContainer

        'NOTE: The following procedure is required by the Windows Form Designer
        'It can be modified using the Windows Form Designer.  
        'Do not modify it using the code editor.
        <System.Diagnostics.DebuggerStepThrough()>
        Private Sub InitializeComponent()
            Dim resources As System.ComponentModel.ComponentResourceManager = New System.ComponentModel.ComponentResourceManager(GetType(frm_OBERON_ESL_2026))
            Me.fro_btn_OK = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.fro_btn_Zatvorit = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.S_ButtonsGroupPanel_Win321 = New Exa.Application.Controls.Simple.S_ButtonsGroupPanel.BaseControls.S_ButtonsGroupPanel_Win32()
            Me.S_PictureBox_Win321 = New Exa.Application.Controls.Simple.S_PictureBox.BaseControls.S_PictureBox_Win32()
            Me.fro_txt_IP = New Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32()
            Me.S_Label_Win322 = New Exa.Application.Controls.Simple.S_Label.BaseControls.S_Label_Win32()
            Me.S_Label_Win321 = New Exa.Application.Controls.Simple.S_Label.BaseControls.S_Label_Win32()
            Me.fro_btn_Test = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.S_ButtonsGroupPanel_Win321.SuspendLayout()
            Me.SuspendLayout()
            '
            'fro_btn_OK
            '
            Me.fro_btn_OK._Text = "O&K"
            Me.fro_btn_OK.AcceptButton = True
            Me.fro_btn_OK.Anchor = CType((System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right), System.Windows.Forms.AnchorStyles)
            Me.fro_btn_OK.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.OK
            Me.fro_btn_OK.Location = New System.Drawing.Point(255, 10)
            Me.fro_btn_OK.Name = "fro_btn_OK"
            Me.fro_btn_OK.Size = New System.Drawing.Size(90, 25)
            Me.fro_btn_OK.TabIndex = 100
            '
            'fro_btn_Zatvorit
            '
            Me.fro_btn_Zatvorit._DialogResult = System.Windows.Forms.DialogResult.Cancel
            Me.fro_btn_Zatvorit._Text = "Zatvoriť"
            Me.fro_btn_Zatvorit.Anchor = CType((System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right), System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Zatvorit.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.Cancel
            Me.fro_btn_Zatvorit.Location = New System.Drawing.Point(351, 10)
            Me.fro_btn_Zatvorit.Name = "fro_btn_Zatvorit"
            Me.fro_btn_Zatvorit.Size = New System.Drawing.Size(90, 25)
            Me.fro_btn_Zatvorit.TabIndex = 101
            '
            'S_ButtonsGroupPanel_Win321
            '
            Me.S_ButtonsGroupPanel_Win321.BorderLinesSettings.LineShow_Top = True
            Me.S_ButtonsGroupPanel_Win321.Controls.Add(Me.fro_btn_OK)
            Me.S_ButtonsGroupPanel_Win321.Controls.Add(Me.fro_btn_Zatvorit)
            Me.S_ButtonsGroupPanel_Win321.Dock = System.Windows.Forms.DockStyle.Bottom
            Me.S_ButtonsGroupPanel_Win321.Location = New System.Drawing.Point(0, 275)
            Me.S_ButtonsGroupPanel_Win321.Name = "S_ButtonsGroupPanel_Win321"
            Me.S_ButtonsGroupPanel_Win321.Size = New System.Drawing.Size(453, 43)
            Me.S_ButtonsGroupPanel_Win321.TabIndex = 102
            '
            'S_PictureBox_Win321
            '
            Me.S_PictureBox_Win321._Image = CType(resources.GetObject("S_PictureBox_Win321._Image"), System.Drawing.Image)
            Me.S_PictureBox_Win321.Location = New System.Drawing.Point(12, 12)
            Me.S_PictureBox_Win321.Name = "S_PictureBox_Win321"
            Me.S_PictureBox_Win321.Size = New System.Drawing.Size(32, 32)
            '
            'fro_txt_IP
            '
            Me.fro_txt_IP.CaptionSettings.Text = "IP adresa:"
            Me.fro_txt_IP.CaptionSettings.Width = 130
            Me.fro_txt_IP.Hightlight = True
            Me.fro_txt_IP.Location = New System.Drawing.Point(12, 105)
            Me.fro_txt_IP.Name = "fro_txt_IP"
            Me.fro_txt_IP.Size = New System.Drawing.Size(429, 22)
            Me.fro_txt_IP.TabIndex = 0
            Me.fro_txt_IP.ValueSettings.Format_Custom = Nothing
            '
            'S_Label_Win322
            '
            Me.S_Label_Win322._Text = "'OBERON ESL 2026' predstavuje zariadenie, ktoré komunikuje s elektronickými cenov" &
    "kami."
            Me.S_Label_Win322.AutoSize = False
            Me.S_Label_Win322.Location = New System.Drawing.Point(56, 12)
            Me.S_Label_Win322.Name = "S_Label_Win322"
            Me.S_Label_Win322.Size = New System.Drawing.Size(385, 47)
            '
            'S_Label_Win321
            '
            Me.S_Label_Win321._Text = "Zadajte IP adresu zariadenia OBERON ESL 2026."
            Me.S_Label_Win321.AutoSize = False
            Me.S_Label_Win321.Location = New System.Drawing.Point(12, 68)
            Me.S_Label_Win321.Name = "S_Label_Win321"
            Me.S_Label_Win321.Size = New System.Drawing.Size(429, 25)
            '
            'fro_btn_Test
            '
            Me.fro_btn_Test._Text = "Otestovať"
            Me.fro_btn_Test.Anchor = CType((System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right), System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Test.Location = New System.Drawing.Point(341, 138)
            Me.fro_btn_Test.Name = "fro_btn_Test"
            Me.fro_btn_Test.Size = New System.Drawing.Size(100, 25)
            Me.fro_btn_Test.TabIndex = 3
            '
            'frm_OBERON_ESL_2026
            '
            Me.AutoScaleDimensions = New System.Drawing.SizeF(96.0!, 96.0!)
            Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Dpi
            Me.ClientSize = New System.Drawing.Size(453, 318)
            Me.Controls.Add(Me.fro_btn_Test)
            Me.Controls.Add(Me.S_Label_Win321)
            Me.Controls.Add(Me.S_Label_Win322)
            Me.Controls.Add(Me.fro_txt_IP)
            Me.Controls.Add(Me.S_ButtonsGroupPanel_Win321)
            Me.Controls.Add(Me.S_PictureBox_Win321)
            Me.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog
            Me.MaximizeBox = False
            Me.MinimizeBox = False
            Me.Name = "frm_OBERON_ESL_2026"
            Me.ShowIcon = False
            Me.ShowInTaskbar = False
            Me.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
            Me.Text = "OBERON Electronic Shelf Labels"
            Me.S_ButtonsGroupPanel_Win321.ResumeLayout(False)
            Me.ResumeLayout(False)

        End Sub
        Friend WithEvents fro_btn_OK As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
        Friend WithEvents fro_btn_Zatvorit As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
        Friend WithEvents S_PictureBox_Win321 As Exa.Application.Controls.Simple.S_PictureBox.BaseControls.S_PictureBox_Win32
        Friend WithEvents S_ButtonsGroupPanel_Win321 As Exa.Application.Controls.Simple.S_ButtonsGroupPanel.BaseControls.S_ButtonsGroupPanel_Win32
        Friend WithEvents fro_txt_IP As Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32
        Friend WithEvents S_Label_Win322 As Application.Controls.Simple.S_Label.BaseControls.S_Label_Win32
        Friend WithEvents S_Label_Win321 As Application.Controls.Simple.S_Label.BaseControls.S_Label_Win32
        Friend WithEvents fro_btn_Test As Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
    End Class

End Namespace