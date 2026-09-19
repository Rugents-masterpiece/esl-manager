Imports System.Text.Json.Serialization

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Information about an electronic price tag.
    ''' Returned by GET /esls_new/associate/getTagsMsg
    ''' </summary>
    Public Class TagInfo

        ' Height of the tag in pixels
        Public Property height As Integer

        ' Identifier of the tag (internal ID in device)
        Public Property ido As Integer

        ' MAC address of the electronic price tag (format: "92.81.05.82")
        Public Property mac As String

        ' Power level of the tag (battery/power status)
        Public Property power As Integer

        ' Status of the router the tag is connected to
        Public Property routerStatus As Integer

        ' ID of the router the tag is connected to
        Public Property routerid As String

        ' RSSI (Received Signal Strength Indicator) - signal strength
        Public Property rssi As Double

        ' Optional field for display style
        Public Property showStyle As String

        ' Status of the electronic price tag:
        ' 1 = Ready (waiting for update)
        ' 2 = Updating (data being applied)
        ' 3 = Update failed
        ' 4 = Update successful
        Public Property status As Integer

        ' ID of the style/template used on this tag
        Public Property styleId As Integer

        ' Substitute (special flag for substitute tags)
        <Newtonsoft.Json.JsonProperty("sub")>
        Public Property substitute As Integer

        ' Width of the tag in pixels
        Public Property width As Integer
    End Class

End Namespace
