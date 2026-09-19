Imports Newtonsoft.Json

Namespace PriceLabels.OBERON_ESL_2026.Models

    ''' <summary>
    ''' Pagination information for API responses.
    ''' </summary>
    Public Class PageInfo

        ' Current page number
        Public Property currentPage As Integer

        ' Whether there is a next page
        Public Property hasNext As Boolean

        ' Whether there is a previous page
        Public Property hasPrevious As Boolean

        ' Number of items per page
        Public Property pageSize As Integer

        ' Starting row number
        Public Property startRow As Integer

        ' Total number of pages
        Public Property totalPages As Integer

        ' Total number of rows
        Public Property totalRows As Integer

    End Class

End Namespace
