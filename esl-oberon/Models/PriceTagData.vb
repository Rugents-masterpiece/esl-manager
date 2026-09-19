Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Dátová štruktúra pre zaslanie údajov na jednu elektronickú cenovku.
    ''' Používa sa pre POST request na /esls_new/associate/updateScreen.
    ''' </summary>
    Public Class PriceTagData

        ' MAC adresa elektronickej cenovky (formát: "92.81.05.82")
        Public Property Mac As String

        ' Typ mapovania (mappingtype) - urcuje ako ma byt obsah cenovky zobrazeny
        Public Property MappingType As Integer

        ' ID šablóny (styleid) - urcuje vzhled cenovky podla šablóny
        Public Property StyleId As Integer

        ' A/D strana zobrazenia: 161 (A), 162 (B), 163 (oboje)
        Public Property ADisplayFlag As Integer = 163

        ' Dynamické polia pre šablónu (NameUnitMJ, PriceRetail, Name, atď.)
        Public Property Fields As New Dictionary(Of String, Object)

    End Class

End Namespace