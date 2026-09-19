Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Konštantné hodnoty pre elektronické cenovky.
    ''' </summary>
    Public Module PriceTagConstants

        ' Predvolená MAC adresa cenovky
        Public Const CONST_DefaultMac As String = "92.81.05.82"

        ' ============================================================================
        ' Šablóny pre elektronické cenovky - nové typy displejov (2025)
        ' ============================================================================

        ' 2.1" B/W/R (Black/White/Red) - 250 x 132 px
        ' MAC adresa: 92.93.73.60
        ' API id: 147, mappingtype: 502
        Public Const CONST_StyleId_SF21BasePriceTag_V1 As Integer = 147
        Public Const CONST_MappingType_SF21BasePriceTag_V1 As Integer = 502

        ' 2.1" B/W (Black/White) - 250 x 122 px
        ' MAC adresa: 92.97.83.93
        ' API id: 145, mappingtype: 291
        Public Const CONST_StyleId_S21BasePriceTag_V1 As Integer = 145
        Public Const CONST_MappingType_S21BasePriceTag_V1 As Integer = 291

        ' 2.9" B/W/R (Black/White/Red) - 296 x 128 px
        ' MAC adresa: 92.81.18.41
        ' API id: 146, mappingtype: 413
        Public Const CONST_StyleId_S29BasePriceTag_V1 As Integer = 146
        Public Const CONST_MappingType_S29BasePriceTag_V1 As Integer = 413

    End Module
End Namespace