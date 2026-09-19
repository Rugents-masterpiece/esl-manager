Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Router message response containing array of router information.
    ''' Returned by GET /esls_new/associate/getRoutersMsg
    ''' </summary>
    Public Class RouterMsg

        ' List of router information
        Public Property datalist As List(Of RouterInfo)

        ' Pagination information
        Public Property page As PageInfo

        ' Result code (10 = success)
        Public Property resultCode As Integer

        ' Result message (e.g., "成功" for success in Chinese)
        Public Property resultMsg As String

    End Class

End Namespace
