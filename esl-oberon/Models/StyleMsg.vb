Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Style message response containing template information with pagination.
    ''' Returned by GET /esls_new/associate/getStylesMsg and POST /esls_new/associate/getStyleMsgById
    ''' </summary>
    Public Class StyleMsg

        ' List of style/template information
        Public Property datalist As List(Of BaseStyleInfo)

        ' Pagination information
        Public Property page As PageInfo

        ' Result code (10 = success)
        Public Property resultCode As Integer

        ' Result message (e.g., "成功" for success in Chinese)
        Public Property resultMsg As String

    End Class

End Namespace
