Imports System.Drawing
Imports System.Windows.Forms
Imports Exa.Application.Forms

Namespace Forms

    ''' <summary>
    ''' Form na zobrazenie obrázku s možnosťou zavretia.
    ''' </summary>
    Public Class frm_ImageDisplay
    Inherits Form

    Private PictureBox_Image As PictureBox
    Private components As System.ComponentModel.IContainer

    ''' <summary>
    ''' Konštruktor formu na zobrazenie obrázku.
    ''' </summary>
    ''' <param name="u_Image">Obrázok na zobrazenie</param>
    ''' <param name="u_Title">Názov formu</param>
    Public Sub New(u_Image As Bitmap, u_Title As String)
        InitializeComponent()

        Me.Text = u_Title
        Me.MinimumSize = New Size(300, 200)
        Me.Size = New Size(Math.Max(600, u_Image.Width + 40), Math.Max(400, u_Image.Height + 40))
        Me.StartPosition = FormStartPosition.CenterParent

        ' Nastav PictureBox na vyplnenie celého formu
        PictureBox_Image = New PictureBox()
        PictureBox_Image.Image = u_Image
        PictureBox_Image.SizeMode = PictureBoxSizeMode.Zoom
        PictureBox_Image.Dock = DockStyle.Fill
        PictureBox_Image.BackColor = Color.Black
        PictureBox_Image.Name = "PictureBox_Image"
        PictureBox_Image.TabStop = False

        Me.Controls.Add(PictureBox_Image)
    End Sub

    Protected Overrides Sub Dispose(ByVal disposing As Boolean)
        If disposing Then
            If components IsNot Nothing Then
                components.Dispose()
            End If
            If PictureBox_Image IsNot Nothing Then
                PictureBox_Image.Dispose()
            End If
        End If
        MyBase.Dispose(disposing)
    End Sub

    Private Sub InitializeComponent()
        Me.components = New System.ComponentModel.Container()
        Me.SuspendLayout()
        Me.ClientSize = New Size(600, 400)
        Me.Name = "frm_ImageDisplay"
        Me.Text = "Obrázok"
        Me.ResumeLayout(False)
    End Sub

    End Class

End Namespace

