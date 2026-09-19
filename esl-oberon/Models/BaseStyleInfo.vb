Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Base model for style/template information.
    ''' Contains common fields for template/style definitions.
    ''' </summary>
    Public Class BaseStyleInfo

        ' Identifier of the background image for the template
        Public Property backgroundID As Integer

        ' Descriptor/description of the template (often contains version or timestamp info)
        Public Property descriptor As String

        ' Height of the template in pixels
        Public Property height As Integer

        ' Unique identifier of the template
        Public Property id As Integer

        ' Field mapping type for updating the screen interface
        Public Property mappingtype As Integer

        ' Name of the template
        Public Property name As String

        ' Type of screen that uses this template:
        ' 1 = Black and white e-ink screen
        ' 2 = Black, white, and red tri-color e-ink screen
        Public Property type As Integer

        ' Last update time of the template
        Public Property updateTime As String

        ' Width of the template in pixels
        Public Property width As Integer

    End Class

End Namespace
