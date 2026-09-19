Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Style message with fields information for a specific template.
    ''' Returned by POST /esls_new/associate/getStyleMsgById
    ''' </summary>
    Public Class StyleMsgById

        ' List of style information including field names
        Public Property datalist As List(Of StyleInfoWithFields)

        ' Pagination information
        Public Property page As PageInfo

        ' Result code (10 = success)
        Public Property resultCode As Integer

        ' Result message (e.g., "成功" for success in Chinese)
        Public Property resultMsg As String

    End Class

    ''' <summary>
    ''' Style information with fields array containing field names.
    ''' </summary>
    Public Class StyleInfoWithFields
        Inherits BaseStyleInfo

        ' Array of field names defined in the template
        Public Property styleFileds As List(Of String)

        ' Rotate value (default 0)
        Public Property rotate As Integer

        ' User ID who created/modified the template
        Public Property userid As Integer

    End Class

End Namespace
