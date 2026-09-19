Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Photo message response containing array of photo information.
    ''' Returned by GET /esls_new/associate/getPhotos
    ''' </summary>
    Public Class PhotoMsg

        ' List of photo information
        Public Property datalist As List(Of PhotoInfo)

        ' Pagination information
        Public Property page As PageInfo

        ' Result code (10 = success)
        Public Property resultCode As Integer

        ' Result message (e.g., "成功" for success in Chinese)
        Public Property resultMsg As String

    End Class

End Namespace
