Imports System.Threading
Imports System.Threading.Tasks

Namespace PriceLabels.OBERON_ESL_2026

    ''' <summary>
    ''' Trieda pre sledovanie statusu elektronickej cenovky po update.
    ''' Cyklicky vola GetTagsMsg a zistuje status cenovky.
    ''' Statusy: 1 = ready, 2 = updating, 3 = failed, 4 = success, -1 = error
    ''' </summary>
    Public Class PriceTagStatusMonitor
    Implements IDisposable

    ' Udalosť pri zmene statusu cenovky
    Public Event StatusChanged(sender As Object, e As StatusChangedEventArgs)

    ' Udalosť po dokončení monitorovania
    Public Event MonitoringCompleted(sender As Object, e As MonitoringCompletedEventArgs)

    ' CancellationTokenSource pre zrušenie monitorovania
    Private lc_CancellationTokenSource As CancellationTokenSource

    ' Úloha pre sledovanie
    Private lc_MonitoringTask As Task

    ' Zoznam MAC adries sledovaných cenoviek
    Private lc_Macs As List(Of String)

    ' Referencia na OBERON_ESL_2026Client
    Private lc_Client As OBERON_ESL_2026Client

    ' Časový interval medzi volaniami v milisekundách (predvolene 1000ms = 1s)
    Public Property CheckIntervalMs As Integer = 1000

    ' True ak je monitorovanie aktívne
    Public ReadOnly Property IsMonitoring As Boolean
        Get
            Return lc_MonitoringTask IsNot Nothing AndAlso Not lc_MonitoringTask.IsCompleted
        End Get
    End Property

    ''' <summary>
    ''' Konštruktor s referenciou na klienta.
    ''' </summary>
    ''' <param name="u_Client">HTTP klient pre komunikáciu s API cenoviek</param>
    Public Sub New(ByVal u_Client As OBERON_ESL_2026Client)
        If u_Client Is Nothing Then
            Throw New ArgumentNullException(NameOf(u_Client))
        End If

        lc_Client = u_Client
        lc_Macs = New List(Of String)
    End Sub

    ''' <summary>
    ''' Spusti monitorovanie statusu cenoviek.
    ''' </summary>
    ''' <param name="u_Macs">Zoznam MAC adries cenoviek</param>
    Public Sub StartMonitoring(ByVal u_Macs As List(Of String))
        If u_Macs Is Nothing OrElse u_Macs.Count = 0 Then
            Throw New ArgumentException("Zoznam MAC adries nesmie byť prázdny.", NameOf(u_Macs))
        End If

        ' Ak je monitorovanie už aktívne, najprv sa zastaví
        If IsMonitoring Then
            StopMonitoring()
        End If

        lc_Macs = u_Macs
        lc_CancellationTokenSource = New CancellationTokenSource()

        ' Spustenie monitorovacieho cyklu na samostatnej úlohe (vlákne)
        #Disable Warning BC42358
        lc_MonitoringTask = Task.Run(Sub() MonitorLoop(lc_CancellationTokenSource.Token))
        #Enable Warning BC42358
    End Sub

    ''' <summary>
    ''' Spusti monitorovanie statusu cenovky (kompatibilná verzia s jednou MAC).
    ''' </summary>
    ''' <param name="u_Mac">MAC adresa cenovky</param>
    Public Sub StartMonitoring(ByVal u_Mac As String)
        StartMonitoring(New List(Of String) From {u_Mac})
    End Sub

    ''' <summary>
    ''' Zastavi monitorovanie statusu cenovky.
    ''' Bezpečne ukončí bežiace vlákno pomocou CancellationToken.
    ''' </summary>
    Public Sub StopMonitoring()
        If lc_CancellationTokenSource IsNot Nothing Then
            lc_CancellationTokenSource.Cancel()
        End If

        ' Čakať kým sa úloha ukončí (max 1 sekunda)
        Dim startTime As DateTime = DateTime.Now
        While IsMonitoring AndAlso (DateTime.Now - startTime).TotalMilliseconds < 1000
            Thread.Sleep(100)
        End While

        lc_MonitoringTask = Nothing
    End Sub

    ''' <summary>
    ''' Hlavný monitorovací cyklus.
    ''' Prechádza všetky MAC adresy a získava ich status.
    ''' </summary>
    Private Async Function MonitorLoop(ByVal cancellationToken As CancellationToken) As Task
        Try
            While Not cancellationToken.IsCancellationRequested
                ' Získať status všetkých cenoviek
                For Each mac As String In lc_Macs
                    Dim status As Integer? = lc_Client.GetTagStatusByMac(mac)

                    ' Vykonať Update na UI thread
                    RaiseEvent StatusChanged(Me, New StatusChangedEventArgs(status))
                Next

                ' Čakať pred ďalším volaním
                Await Task.Delay(CheckIntervalMs, cancellationToken).ConfigureAwait(False)
            End While
        Catch ex As OperationCanceledException
            ' Monitorovanie bolo zrušené - to je OK
        Catch ex As Exception
            ' Vyvolaj StatusChanged s chybovým statusom
            RaiseEvent StatusChanged(Me, New StatusChangedEventArgs(-1))
        End Try

        ' Oznámiť dokončenie
        RaiseEvent MonitoringCompleted(Me, New MonitoringCompletedEventArgs(If(lc_CancellationTokenSource?.IsCancellationRequested, False, Nothing)))
    End Function

    ''' <summary>
    ''' Uvolni zdroje.
    ''' </summary>
    Public Sub Dispose() Implements IDisposable.Dispose
        StopMonitoring()

        If lc_CancellationTokenSource IsNot Nothing Then
            lc_CancellationTokenSource.Dispose()
        End If

        GC.SuppressFinalize(Me)
    End Sub

End Class

''' <summary>
''' Event arguments pre StatusChanged event.
''' Status: 1 = ready, 2 = updating, 3 = failed, 4 = success, -1 = error
''' </summary>
Public Class StatusChangedEventArgs
    Inherits EventArgs

    ' Aktuálny status cenovky (1, 2, 3, 4 alebo -1 pre chybu)
    Public Property Status As Integer?

    ' True ak je status 4 (úspešný)
    Public ReadOnly Property IsSuccess As Boolean
        Get
            Return Status = 4
        End Get
    End Property

    ' True ak je status 3 (zlyhal)
    Public ReadOnly Property IsFailed As Boolean
        Get
            Return Status = 3
        End Get
    End Property

    ''' <summary>
    ''' Konštruktor.
    ''' </summary>
    ''' <param name="u_Status">Počiatočný status cenovky</param>
    Public Sub New(ByVal u_Status As Integer?)
        Me.Status = u_Status
    End Sub
End Class

''' <summary>
''' Event arguments pre MonitoringCompleted event.
''' </summary>
Public Class MonitoringCompletedEventArgs
    Inherits EventArgs

    ' Finálny status cenovky
    Public Property FinalStatus As Integer?

    ''' <summary>
    ''' Konštruktor.
    ''' </summary>
    ''' <param name="u_FinalStatus">Finálny status cenovky</param>
    Public Sub New(ByVal u_FinalStatus As Integer?)
        Me.FinalStatus = u_FinalStatus
    End Sub
End Class

End Namespace
