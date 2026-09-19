Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Style message response containing array of style information.
    ''' Returned by GET /esls_new/associate/getStylesMsg
    ''' </summary>
    Public Class StyleMsgArray

        ''' <summary>
        ''' List of style information.
        ''' </summary>
        Public Property datalist As List(Of StyleInfo)

        ''' <summary>
        ''' Pagination information.
        ''' </summary>
        Public Property page As PageInfo

        ''' <summary>
        ''' Result code (10 = success).
        ''' </summary>
        Public Property resultCode As Integer

        ''' <summary>
        ''' Result message (e.g., "成功" for success in Chinese).
        ''' </summary>
        Public Property resultMsg As String

    End Class

End Namespace
