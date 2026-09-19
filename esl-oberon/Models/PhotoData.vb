Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Photo data response containing Base64 encoded image data.
    ''' Returned by GET /esls_new/associate/getPhotoDataByName
    ''' </summary>
    Public Class PhotoData

        ' Base64 encoded image data
        Public Property data As String

        ' List of photo information (empty in getPhotoDataByName response)
        Public Property datalist As List(Of PhotoInfo)

        ' Pagination information
        Public Property page As PageInfo

        ' Result code (10 = success)
        Public Property resultCode As Integer

        ' Result message (e.g., "成功" for success in Chinese)
        Public Property resultMsg As String

        ' Additional Base64 encoded data (not documented, but present in response)
        Public Property t As String

    End Class

End Namespace
