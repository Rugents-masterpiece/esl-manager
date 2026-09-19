Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Photo/image information.
    ''' Returned by GET /esls_new/associate/getPhotos
    ''' </summary>
    Public Class PhotoInfo

        ''' <summary>
        ''' Height of the image in pixels.
        ''' </summary>
        Public Property height As Integer

        ''' <summary>
        ''' Unique identifier of the image.
        ''' </summary>
        Public Property id As Integer

        ''' <summary>
        ''' Name of the image (used for retrieving data).
        ''' </summary>
        Public Property name As String

        ''' <summary>
        ''' Width of the image in pixels.
        ''' </summary>
        Public Property width As Integer

    End Class

End Namespace
