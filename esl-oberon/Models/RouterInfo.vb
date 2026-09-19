Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Information about a base station (AP/router).
    ''' Returned by GET /esls_new/associate/getRoutersMsg
    ''' </summary>
    Public Class RouterInfo

        ' Frequency of the base station
        Public Property freq As Integer

        ' Hardware version of the base station
        Public Property hardwareVersion As String

        ' Last heartbeat time of the base station
        Public Property lastHeartbeatTime As Long

        ' Identifier of the base station
        Public Property routerID As Integer

        ' IP address of the base station
        Public Property routerIP As String

        ' Software version of the base station
        Public Property softwareVersion As String

        ' Status of the base station
        Public Property state As Integer

        ' Number of e-ink displays connected to this base station
        Public Property tagQuanty As Integer

    End Class

End Namespace
