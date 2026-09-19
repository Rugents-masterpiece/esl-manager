Option Strict On
Imports Exa.OBERON.Devices.Base
Imports Exa.OBERON.Devices
Imports System.Threading.Tasks

Namespace Base

    ''' <summary>Aktívne zariadenia v systéme. Obsahuje vytvorené inštancie zariadení pripojené k tomuto počítaču, 
    ''' napr. snímač čiarových kódov, zákaznícky displej a podobne.</summary>
    Public Class DeviceEngine
        Implements IDisposable


#Region " Declaration "

        Private lc_DeviceList As Device_List = Nothing
        Private lc_Engine_IsInitialize As Boolean


        ''' <summary>
        ''' Druh zmeny stavu aktívnych zariadení v systéme.
        ''' </summary>
        Public Enum enm_DeviceEngineStateType As Byte

            ''' <summary>Neznámy stav aktualizávcie.</summary>
            None = 0


            ''' <summary>Stav zoznamu zariadení po spustení (aktivácii) v systéme. Tu je možné mapovať udalosti vyvolávané zariadeniami.</summary>
            [Started] = 1


            ''' <summary>Stav pred začatím aktualizácie zoznamu.</summary>
            [Refreshing] = 5


            ''' <summary>Stav pred ukončením (deaktivovaním) zariadení v systéme. Tu je požadované odmapovanie udalostí k zariadeniam.</summary>
            [Stopping] = 9

        End Enum

        ''' <summary>
        ''' Udalosť pri zmene stavu zoznamu aktívnych zariadení v systéme.
        ''' </summary>
        ''' <param name="engineState">Bližšie určenie stavu do ktorého prechádza zoznam aktívnych zariadení systému.</param>
        Public Event ev_DeviceEngineStateChange(engineState As enm_DeviceEngineStateType)


#End Region


#Region " DECLARATION - EVENTS "

        Public Event ev_BarCodeScanner_StateChange(u_IsReady As TriState)


        ''' <summary>Zosnímanie čiarového kódu a snímači čiarového kódu číslo 1 alebo 2 (OBERON podporuje 2 snímače).</summary>    
        Public Event ev_BarCodeScanner_Readed(ByVal u_EventArgs As BarcodeScanner.Driver_Common.BarCodeScanner_Readed_EventArgs)

        Public Sub on_ev_BarCodeScanner_Readed(ByVal u_BarCode As String)

            On Error Resume Next

            If Me.BarCodeScanner1 IsNot Nothing Then
                '--- Vyvolať udalosť na snímači č. 1 ---
                Me.BarCodeScanner1.on_ev_BarCodeScanner_Readed(u_BarCode)
            Else
                '--- Ak sa nedá na 1, pokúsiť sa na 2.
                If Me.BarCodeScanner2 IsNot Nothing Then
                    '--- Vyvolať udalosť ---
                    Me.BarCodeScanner2.on_ev_BarCodeScanner_Readed(u_BarCode)
                End If
            End If

        End Sub

        Public Event ev_ElectronicScale_Weight_Readed(u_EventArgs As ElectronicScale.Driver_Common.cls_ElectronicScale_Weight_Readed_EventArgs)

        Public Sub on_ev_ElectronicScale_Weight_Readed(u_EventArgs As ElectronicScale.Driver_Common.cls_ElectronicScale_Weight_Readed_EventArgs)
            On Error Resume Next
            RaiseEvent ev_ElectronicScale_Weight_Readed(u_EventArgs)
        End Sub

#End Region


#Region " Properties "


        Private prp_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration

        ''' <summary>
        ''' App objekt - základný objekt združujúci ďalšie objekty.
        ''' </summary>
        Public ReadOnly Property _AppConfiguration() As Exa.OBERON.ApplicationEnvironment.AppConfiguration
            <DebuggerStepThrough>
            Get
                Return prp_AppConfiguration
            End Get
        End Property


        ''' <summary>Zoznam všetkých zariadení definovaných v systéme.</summary>
        Public ReadOnly Property DeviceList() As Device_List
            <DebuggerStepThrough>
            Get
                Return lc_DeviceList
            End Get
        End Property


        Private prp_IsRunning As Boolean
        ''' <summary>Príznak či je Engine so zariadeniami spustený.</summary>
        Public ReadOnly Property IsRunning() As Boolean
            <DebuggerStepThrough>
            Get
                Return prp_IsRunning
            End Get
        End Property

        Private prp_BarCodeScanner1 As BarcodeScanner.Driver_Common
        ''' <summary>
        ''' Snímač čiarového kódu číslo 1. OBERON podporuje súčasne dva snímače čiarových kódov.
        ''' </summary> 
        Friend ReadOnly Property BarCodeScanner1() As BarcodeScanner.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_BarCodeScanner1
            End Get
        End Property


        Private prp_BarCodeScanner2 As BarcodeScanner.Driver_Common
        ''' <summary>
        ''' Snímač čiarového kódu číslo 2. OBERON podporuje súčasne dva snímače čiarových kódov.
        ''' </summary>    
        Friend ReadOnly Property BarCodeScanner2() As BarcodeScanner.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_BarCodeScanner2
            End Get
        End Property


        ''' <summary>
        ''' Vracia, či na aktuálnom počítači v tejto chvíli je aktívny aspoň jeden snímač čiarového kódu. Trieda DeviceEngine musí byť v režime Run.
        ''' </summary>    
        Public ReadOnly Property BarCodeScannerHasActive() As Boolean
            Get
                On Error Resume Next
                If Me.BarCodeScanner1 Is Nothing And Me.BarCodeScanner2 Is Nothing Then
                    Return False
                End If

                Return True
            End Get
        End Property

        Private prp_BarCodeScanner_IDEvent As Integer
        ''' <summary>
        ''' Je možné nastaviť ID udalosti - potom pri zosnímaní čiarového kódu je v udalosti dané ID a je možné rozlíšiť pre aký objekt patrí zosnímaný kód, 
        ''' napr. či predať položku, alebo prihlásiť používateľa.
        ''' </summary>  
        Public Property BarCodeScanner_IDEvent() As Integer
            Get
                Return prp_BarCodeScanner_IDEvent
            End Get
            Set(value As Integer)

                On Error Resume Next
                prp_BarCodeScanner_IDEvent = value

                If Me.BarCodeScanner1 IsNot Nothing Then
                    Me.BarCodeScanner1.BarCodeScanner_IDEvent = prp_BarCodeScanner_IDEvent
                End If

                If Me.BarCodeScanner2 IsNot Nothing Then
                    Me.BarCodeScanner2.BarCodeScanner_IDEvent = prp_BarCodeScanner_IDEvent
                End If

            End Set
        End Property

        ''' <summary>
        ''' Príznak či je zariadenie funkčné /práve pripojené a pracuje správne/ alebo nie. Ak sa používajú 2 snímače, stačí ak funguje korektne aspoň jeden.
        ''' </summary>
        Public ReadOnly Property BarCodeScanner_IsReady() As TriState
            Get
                On Error Resume Next
                If Me.BarCodeScanner1 IsNot Nothing AndAlso Me.BarCodeScanner1.IsReady = TriState.True Then
                    Return TriState.True
                End If

                If Me.BarCodeScanner2 IsNot Nothing AndAlso Me.BarCodeScanner2.IsReady = TriState.True Then
                    Return TriState.True
                End If

                Return TriState.False

            End Get
        End Property



        Private prp_DisplayCustomer As DisplayCustomer.Driver_Common
        ''' <summary>
        ''' Externý zákaznícky displej.
        ''' </summary>
        Public ReadOnly Property DisplayCustomer() As DisplayCustomer.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_DisplayCustomer
            End Get
        End Property


        Private prp_PriceLabels As PriceLabels.Driver_Common
        ''' <summary>
        ''' Systém na elektronické cenovky (Price Labels).
        ''' </summary>
        Public ReadOnly Property PriceLabels() As PriceLabels.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_PriceLabels
            End Get
        End Property


        Private prp_ElectronicScales As New List(Of ElectronicScale.Driver_Common)
        ''' <summary>
        ''' Elektronické váhy.
        ''' </summary>
        Public ReadOnly Property ElectronicScales() As IEnumerable(Of ElectronicScale.Driver_Common)
            <DebuggerStepThrough>
            Get
                Return prp_ElectronicScales
            End Get
        End Property

        Public ReadOnly Property ElectronicScale(u_Name As String) As ElectronicScale.Driver_Common
            <DebuggerStepThrough>
            Get
                If String.IsNullOrWhiteSpace(u_Name) Then
                    Return prp_ElectronicScales?.FirstOrDefault
                Else
                    Return prp_ElectronicScales?.FirstOrDefault(Function(m) String.Equals(m.DeviceName, u_Name, StringComparison.InvariantCultureIgnoreCase))
                End If
            End Get
        End Property


        Private prp_PID As PID.Driver_Common
        ''' <summary>
        ''' PID - prístupový systém.
        ''' </summary>
        Public ReadOnly Property PID() As PID.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_PID
            End Get
        End Property


        Private prp_DoorKey As DoorKey.Driver_Common
        ''' <summary>
        ''' Dverové zámky. 
        ''' </summary>
        Public ReadOnly Property DoorKey() As DoorKey.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_DoorKey
            End Get
        End Property

        Private prp_DocumentReader As DocumentReader.Driver_Common
        ''' <summary>
        ''' Čítačka dokladov.
        ''' </summary>
        Public ReadOnly Property DocumentReader() As DocumentReader.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_DocumentReader
            End Get
        End Property

        Private prp_SignaturePad As SignaturePad.Driver_Common
        ''' <summary>
        ''' Digitálna podpisová podložka.
        ''' </summary>
        Public ReadOnly Property SignaturePad() As SignaturePad.Driver_Common
            <DebuggerStepThrough>
            Get
                Return prp_SignaturePad
            End Get
        End Property



        Private prp_FiscalModuleCount As Byte
        ''' <summary>
        ''' Počet fiškálnych modulov inštalovaných v systéme /len aktívne zariadenia/.
        ''' </summary>
        Public ReadOnly Property FiscalModuleCount() As Byte
            <DebuggerStepThrough>
            Get
                Return prp_FiscalModuleCount
            End Get
        End Property


        Private prp_CashRegisterCount As Byte
        ''' <summary>
        ''' Počet registračných pokladníc (napr. EURO) inštalovaných v systéme /len aktívne zariadenia/.
        ''' </summary>
        Public ReadOnly Property CashRegisterCount() As Byte
            <DebuggerStepThrough>
            Get
                Return prp_CashRegisterCount
            End Get
        End Property

#End Region


#Region " METHODS "


        Public Sub New(ByVal u_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration)

            On Error Resume Next
            prp_AppConfiguration = u_AppConfiguration

            prp_IsRunning = False

            lc_Engine_IsInitialize = False

        End Sub


        ''' <summary>
        ''' Inicializácia engin-u so zariadeniami (načíta zoznam zariadení).
        ''' </summary>
        Public Function EngineInitialize(ByVal u_App_Starting As Boolean) As EXC.ExaException

            On Error Resume Next

            Dim myEx As EXC.ExaException

            EngineInitialize = EXC.GetDefault

            lc_Engine_IsInitialize = False

            If Me.IsRunning = True Then
                Me.EngineStop()
            End If

            '--- Aktualizovať zoznam zariadení
            myEx = Me.Refresh(u_App_Starting)
            If myEx.Result = False Then
                EngineInitialize = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            lc_Engine_IsInitialize = True

            EngineInitialize.Result = True

ExitFunction:


        End Function


        ''' <summary>
        ''' Štart engin-u so zariadeniami, ak je v zozname zariadení napr. snímač čiarového kódu, tak sa otvorí komunikačný port a "načúva sa" ...
        ''' </summary>
        Public Function EngineRun() As EXC.ExaException


            On Error Resume Next

            Dim myEx As EXC.ExaException

            EngineRun = EXC.GetDefault

            '--- Príznak že je engine vypnutý
            prp_IsRunning = False

            '--- Aktualizovať zoznam zariadení
            If lc_Engine_IsInitialize = False Then
                EngineRun.Description = "Engine zariadení nie je inicializovaný."
                GoTo ExitFunction
            End If

            '--- Spustiť Engine 
            myEx = z_Engine_Run()
            If myEx.Result = False Then
                EngineRun = EXC.Get(myEx)
                GoTo ExitFunction
            End If


            '--- Príznak že je engine spustený
            prp_IsRunning = True

            EngineRun.Result = True

ExitFunction:


        End Function


        Public Function EngineStop() As EXC.ExaException

            On Error Resume Next

            EngineStop = EXC.GetDefault


            '--- Príznak že je engine vypnutý
            prp_IsRunning = False

            z_Engine_Stop()

            EngineStop.Result = True

ExitFunction:


        End Function


        ''' <summary>
        ''' Načíta, prípadne aktualizuje zoznam zariadení, napr. mohol zmeniť iný používateľ v sieti
        ''' </summary>
        ''' <returns>Funkcia je vykonaná vždy aj pri volaní metódy Engine_Run</returns>
        ''' <remarks></remarks>
        Public Function Refresh(ByVal u_App_Starting As Boolean) As EXC.ExaException

            On Error Resume Next

            Refresh = EXC.GetDefault

            Dim myEx As EXC.ExaException


            If lc_DeviceList IsNot Nothing Then
                lc_DeviceList.Dispose()
                lc_DeviceList = Nothing
            End If

            lc_DeviceList = New Device_List(prp_AppConfiguration)
            lc_DeviceList._Privileges_Set_Full(u_App_Starting)

            '--- Zapamätať si stav Enginu ---
            Dim tmpFlag_IsRunning As Boolean
            tmpFlag_IsRunning = Me.IsRunning

            If tmpFlag_IsRunning = True Then
                '--- Engine je spustený - potrebné zastaviť
                z_Engine_Stop()
            End If


            '--- Načítať zoznam zariadení ---
            myEx = lc_DeviceList._LoadData(u_LoadOnly_Enabled_Devices:=True)
            If myEx.Result = False Then
                Refresh = EXC.Get(myEx)
                GoTo ExitFunction
            End If


            '--- Načítať počty zariadení
            Dim tmpObjDevice As Device = Nothing
            prp_FiscalModuleCount = 0
            prp_CashRegisterCount = 0
            For Each e As DataRow In lc_DeviceList.Object_Table.DatabaseTable_Data.Rows


                tmpObjDevice = lc_DeviceList.DataRecord(e, True)

                If tmpObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    Continue For
                End If

                If tmpObjDevice.Device_Type = enm_Devices_Type.FiskalModule Then
                    '--- Fiškálny modul
                    prp_FiscalModuleCount = CByte(prp_FiscalModuleCount + 1)
                End If

                If tmpObjDevice.Device_Type = enm_Devices_Type.CashRegister Then
                    '--- Registračná pokladnica
                    prp_CashRegisterCount = CByte(prp_CashRegisterCount + 1)

                End If
            Next

            If Not tmpObjDevice Is Nothing Then
                tmpObjDevice.Dispose()
                tmpObjDevice = Nothing
            End If


            If tmpFlag_IsRunning = True Then
                '--- Engine bol spustený - je potrebné opätovne spustiť
                myEx = z_Engine_Run()
                If myEx.Result = False Then
                    Refresh = EXC.Get(myEx)
                    GoTo ExitFunction
                End If
            End If


            Refresh.Result = True

ExitFunction:


        End Function


        ''' <summary>
        ''' Vráti či dané zariadenie existuje v systéme, či už na tomto počítači alebo aj na inom.
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálne moduly</param>
        Public Function Device_Exists(ByVal u_DeviceType As enm_Devices_Type, ByRef urf_Device As Device) As Boolean

            On Error Resume Next

            Device_Exists = False

            Dim myEx As EXC.ExaException

            Dim tmp_ObjDevice As New Device(prp_AppConfiguration)

            For Each e As DataRowView In lc_DeviceList.Object_Table.DatabaseTable_View     '--- Treba mať zotriedené, lebo niekedy treba vrátiť vždy prvé podľa názvu

                myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=False)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    GoTo NextRecord
                End If


                If tmp_ObjDevice.Device_Type = u_DeviceType Then
                    '--- Typ zariadenia súhlasí 
                    Device_Exists = True

                    '--- Vytvoriť nezávislý DataRecord s nezávislým DataRow-om
                    myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=True)
                    If myEx.Result = False Then
                        GoTo NextRecord
                    End If

                    urf_Device = tmp_ObjDevice
                    Exit For
                End If

NextRecord:

            Next

ExitFunction:


        End Function


        ''' <summary>
        ''' Vráti či dané zariadenie existuje v systéme, či už na tomto počítači alebo aj na inom.
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálny modul</param>
        ''' <param name="u_Device_Model">Model zariadenia, napr. FM 3000</param>
        Public Function Device_Exists(ByVal u_DeviceType As enm_Devices_Type, ByVal u_Device_Model As Integer, ByRef urf_Device As Device) As Boolean

            On Error Resume Next

            Device_Exists = False

            Dim myEx As EXC.ExaException


            For Each e As DataRowView In lc_DeviceList.Object_Table.DatabaseTable_View     '--- Treba mať zotriedené, lebo niekedy treba vrátiť vždy prvé podľa názvu

                Dim tmp_ObjDevice As New Device(prp_AppConfiguration)

                myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=False)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Device_Type = u_DeviceType Then
                    '--- Typ zariadenia súhlasí 
                    If tmp_ObjDevice.Device_Model_Num = u_Device_Model Then
                        '--- Model zariadenia súhlasí 
                        '--- Zariadenie bolo nájdené
                        Device_Exists = True

                        '--- Vytvoriť nezávislý DataRecord s nezávislým DataRow-om
                        myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=True)
                        If myEx.Result = False Then
                            GoTo NextRecord
                        End If

                        urf_Device = tmp_ObjDevice
                        Exit For
                    End If
                End If

NextRecord:

            Next

ExitFunction:

        End Function


        ''' <summary>
        ''' Vráti či dané zariadenie existuje v systéme, či už na tomto počítači alebo aj na inom.
        ''' </summary>
        ''' <param name="u_DeviceName">Názov zariadenia.</param>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálne moduly</param>   
        Public Function Device_Exists(ByVal u_DeviceName As String, ByVal u_DeviceType As enm_Devices_Type, ByRef urf_Device As Device) As Boolean

            On Error Resume Next

            Device_Exists = False

            Dim myEx As EXC.ExaException

            Dim tmp_ObjDevice As New Device(prp_AppConfiguration)

            For Each e As DataRowView In lc_DeviceList.Object_Table.DatabaseTable_View     '--- Treba mať zotriedené, lebo niekedy treba vrátiť vždy prvé podľa názvu

                myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=False)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Device_Type <> u_DeviceType Then
                    '--- Zariadenie je iného typu ---
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Device_Name = u_DeviceName Then
                    '--- Typ zariadenia súhlasí 
                    Device_Exists = True

                    '--- Vytvoriť nezávislý DataRecord s nezávislým DataRow-om
                    myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=True)
                    If myEx.Result = False Then
                        GoTo NextRecord
                    End If

                    urf_Device = tmp_ObjDevice
                    Exit For
                End If

NextRecord:

            Next

ExitFunction:


        End Function


        ''' <summary>
        ''' Vráti či dané zariadenie existuje /má sa používať/ na tomto počítači. 
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálne moduly</param>   
        ''' <param name="u_DeviceNumber">Poradové číslo zariadenia. Ak nula (alebo 1), bude vrátené vždy prvé zariadenie, ak 2 (alebo vyššie), 
        ''' bude vrátené zariadenie daného typu druhé v poradí, napr. podpora dvoch snímačov čiarových kódov.</param>   
        ''' <param name="u_DeviceModel">Model zariadenia, napr. presný typ dochádzkového terminálu.</param>
        ''' <param name="u_DeviceIdentification">Je možné zadať ďalší identifikátor zariadenia, ktoré má byť vrátené, napr. číslo bonovacej tlačiarne.</param>
        Public Function Device_Exists_ThisComputer(ByVal u_DeviceType As enm_Devices_Type,
                                                   ByRef urf_Device As Device,
                                                   Optional ByVal u_DeviceNumber As Byte = 0,
                                                   Optional ByVal u_DeviceModel As Integer = -1,
                                                   Optional ByVal u_DeviceIdentification As String = Nothing) As Boolean

            Dim tmp_Result As Boolean = False

            Try

                Dim myEx As EXC.ExaException = Nothing

                tmp_Result = z_Device_Exists_ThisComputer(u_DeviceType:=u_DeviceType,
                                                          urf_Device,
                                                          u_DeviceNumber:=u_DeviceNumber,
                                                          u_DeviceModel:=u_DeviceModel,
                                                          u_DeviceIdentification:=u_DeviceIdentification)

                If tmp_Result = True Then

                    '--- Špecialita - načítať nastavenia pokladnice
                    If urf_Device.Device_Type = enm_Devices_Type.FiskalModule Then
                        '--- Načítať nastavenia zariadenia
                        myEx = urf_Device.dev_FiscalModule.CashRegisterOBERONSettings._Load(urf_Device.IDNum)
                        If myEx.Result = False Then
                            Exa.Basic.Debug.Console._Write("Chyba pri načítaní nastavení zariadenia.", "DeviceEngine", myEx.GetFullDescription, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)
                        End If
                    End If

                End If


            Catch ex As Exception

            End Try

            Return tmp_Result

        End Function


        ''' <summary>Vráti či dané zariadenie existuje /má sa používať/ na tomto počítači.</summary>
        ''' <param name="u_DeviceNumber">Poradové číslo zariadenia. Ak nula (alebo 1), bude vrátené vždy prvé zariadenie, ak 2 (alebo vyššie), 
        ''' bude vrátené zariadenie daného typu druhé v poradí, napr. podpora dvoch snímačov čiarových kódov.</param>   
        ''' <param name="u_DeviceModel">Model zariadenia, napr. presný typ dochádzkového terminálu.</param>
        ''' <param name="u_DeviceIdentification">Je možné zadať ďalší identifikátor zariadenia, ktoré má byť vrátené, napr. číslo bonovacej tlačiarne.</param>     
        Public Function Device_Exists_ThisComputer(ByVal u_DeviceType As enm_Devices_Type,
                                                   Optional ByVal u_DeviceNumber As Byte = 0,
                                                   Optional ByVal u_DeviceModel As Integer = -1,
                                                   Optional ByVal u_DeviceIdentification As String = Nothing) As Boolean


            Dim tmp_Result As Boolean = False

            Try

                Dim myEx As EXC.ExaException = Nothing

                tmp_Result = z_Device_Exists_ThisComputer(u_DeviceType:=u_DeviceType,
                                                          urf_Device:=Nothing,
                                                          u_DeviceNumber:=u_DeviceNumber,
                                                          u_DeviceModel:=u_DeviceModel,
                                                          u_DeviceIdentification:=u_DeviceIdentification)

            Catch ex As Exception

            End Try

            Return tmp_Result

        End Function



        ''' <summary>
        ''' Vráti či dané zariadenie existuje /má sa používať/ na tomto počítači. 
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálne moduly</param>   
        ''' <param name="u_DeviceNumber">Poradové číslo zariadenia. Ak nula (alebo 1), bude vrátené vždy prvé zariadenie, ak 2 (alebo vyššie), 
        ''' bude vrátené zariadenie daného typu druhé v poradí, napr. podpora dvoch snímačov čiarových kódov.</param>   
        ''' <param name="u_DeviceModel">Model zariadenia, napr. presný typ dochádzkového terminálu.</param>
        ''' <param name="u_DeviceIdentification">Je možné zadať ďalší identifikátor zariadenia, ktoré má byť vrátené, napr. číslo bonovacej tlačiarne.</param>
        Private Function z_Device_Exists_ThisComputer(ByVal u_DeviceType As enm_Devices_Type,
                                                       ByRef urf_Device As Device,
                                                       Optional ByVal u_DeviceNumber As Byte = 0,
                                                       Optional ByVal u_DeviceModel As Integer = -1,
                                                       Optional ByVal u_DeviceIdentification As String = Nothing) As Boolean

            On Error Resume Next

            z_Device_Exists_ThisComputer = False

            Dim myEx As EXC.ExaException

            '--- Zistiť názov session - názov počítača ak je program spustený cez Windows Remote Desktop
            Dim tmp_RDP_SessionName$ = Exa.Basic.Net.GetRDPClientName()

            Dim tmp_Count_FoundDevice As Integer = 0
            For Each e As DataRowView In lc_DeviceList.Object_Table.DatabaseTable_View      '--- Treba mať zotriedené, lebo niekedy treba vrátiť vždy prvé podľa názvu

                Dim tmp_ObjDevice As New Device(prp_AppConfiguration)

                myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=False)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Device_Type <> u_DeviceType Then
                    '--- Iný typ zariadenia ---
                    GoTo NextRecord
                End If

                If u_DeviceModel <> -1 Then
                    '--- Má sa vyhľadať konkrétny model ---
                    If tmp_ObjDevice.Device_Model_Num <> u_DeviceModel Then
                        '--- Model zariadenia nesúhlasí 
                        GoTo NextRecord
                    End If
                End If


                '----------------------------------------------------------------------------
                '--- Počítač ---
                '----------------------------------------------------------------------------

                If tmp_ObjDevice.Computers Is Nothing _
                    OrElse tmp_ObjDevice.Computers.Length = 0 Then
                    '--- Nie je zadaný názov počítača --
                    GoTo NextRecord
                End If


                If tmp_RDP_SessionName <> String.Empty Then
                    '--- RDP - bol zistený názov RDP počítača (session)                    

                    '--- Pravdepodobne je tento počítač pripojený cez RDP ---
                    If tmp_ObjDevice.ComputersRDP.Length = 0 Then
                        GoTo NextRecord
                    End If

                    If tmp_ObjDevice.ComputersRDP.Contains(tmp_RDP_SessionName$.ToUpper) = False Then
                        '--- Názov počítača nesúhlasí 
                        GoTo NextRecord

                    End If

                Else
                    '--- Štandardný názov počítača /nie RDP/
                    If tmp_ObjDevice.Computers.Contains(My.Computer.Name.ToUpper) = False Then
                        '--- Názov počítača nesúhlasí 
                        GoTo NextRecord
                    End If
                End If


                '----------------------------------------------------------------------------
                '--- Špeciality ---
                '----------------------------------------------------------------------------

                '--- Špecialita na bonovacie tlačiarne
                If u_DeviceType = enm_Devices_Type.PrinterKitchen _
                    AndAlso String.IsNullOrWhiteSpace(u_DeviceIdentification) = False Then
                    '--- Tlačiareň do kuchyne - vyhľadáva sa podľa čísla tlačiarne 
                    If tmp_ObjDevice.dev_PrinterKitchen.Number <> CByte(u_DeviceIdentification) Then
                        '--- Neprávne číslo tlačiarne
                        GoTo NextRecord
                    End If
                End If


                '----------------------------------------------------------------------------
                '--- Špeciality - poradové číslo ---
                '----------------------------------------------------------------------------
                If u_DeviceNumber = 0 Or u_DeviceNumber = 1 Then
                    '--- Vrátiť prvé zariadenie daného typu ---
                    '--- OK - pokračovať a načítať zariadenie

                Else
                    '--- Vrátiť ďalšie v poradí ---
                    tmp_Count_FoundDevice = tmp_Count_FoundDevice + 1  '--- počítadlo zariadení
                    If u_DeviceNumber = tmp_Count_FoundDevice Then
                        '--- Číslo zariadenia OK ---
                        '--- OK - pokračovať a načítať zariadenie
                    Else
                        '--- Nesprávne číslo zariadenia ---
                        GoTo NextRecord
                    End If
                End If


                '---------------------------------------------------------------------------
                '--- Toto zariadenie povaťovať za správne
                '---------------------------------------------------------------------------
                myEx = tmp_ObjDevice._Load(e.Row, u_LoadIndependentInstance:=True)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                urf_Device = tmp_ObjDevice

                z_Device_Exists_ThisComputer = True

                '--- Ďalej už nehľadať
                Exit For

NextRecord:

            Next


        End Function






        ''' <summary>
        ''' Vráti zoznam zariadení daného typu na tomto počítači.
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálne moduly</param>   
        Public Function Devices_Exists_ThisComputer(ByVal u_DeviceType As enm_Devices_Type, ByRef urf_Device_List As Device_List) As EXC.ExaException

            On Error Resume Next

            Devices_Exists_ThisComputer = EXC.GetDefault

            Dim myEx As EXC.ExaException
            Dim tmp_RowFilter$ = "ID = 0"

            '--- Zistiť názov session - názov počítača ak je program spustený cez Windows Remote Desktop
            Dim tmp_RDP_SessionName$ = Exa.Basic.Net.GetRDPClientName()

            For Each e As DataRow In lc_DeviceList.Object_Table.DatabaseTable_Data.Rows

                Dim tmp_ObjDevice As New Device(prp_AppConfiguration)

                myEx = tmp_ObjDevice._Load(e, u_LoadIndependentInstance:=False)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    GoTo NextRecord
                End If


                If tmp_RDP_SessionName <> String.Empty Then
                    '--- Bol zistený názov RDP počítača (session)
                    '--- Pravdepodobne je tento počítač pripojený cez RDP ---            
                    If tmp_ObjDevice.ComputersRDP.Contains(tmp_RDP_SessionName$.ToUpper) = False Then
                        '--- Nesprávny názov počítača
                        GoTo NextRecord
                    End If
                Else
                    '--- Štandardný názov počítača /nie RDP/
                    If tmp_ObjDevice.Computers.Contains(My.Computer.Name.ToUpper) = False Then
                        '--- Nesprávny názov počítača
                        GoTo NextRecord
                    End If
                End If


                If tmp_ObjDevice.Device_Type = u_DeviceType Then
                    '--- Typ zariadenia súhlasí 
                    tmp_RowFilter$ = Exa.Database.ConvertFunctions.RowFilter_AppendFilter(tmp_RowFilter$, "ID = " & tmp_ObjDevice.ID, Database.Viewing.DataViewObjects.Filters.Filter.enm_ConditionMergeTypes.OR)
                End If

NextRecord:

            Next

            '--- Načítať zoznam vybraných zariadení ---
            Dim tmp_Selected_DeviceList As Device_List
            tmp_Selected_DeviceList = New Device_List(Me._AppConfiguration)
            tmp_Selected_DeviceList._Privileges_Set_Full(True)   '--- Nastaviť plné práva !!! Inak nebude možné spustiť pokladnicu
            myEx = tmp_Selected_DeviceList._LoadData(tmp_RowFilter$)
            If myEx.Result = False Then
                Devices_Exists_ThisComputer = myEx
                GoTo ExitFunction
            End If

            '--- Vrátiť hdnotu ---
            urf_Device_List = tmp_Selected_DeviceList

            Devices_Exists_ThisComputer.Result = True

ExitFunction:


        End Function


        ''' <summary>
        ''' Vráti zoznam zariadení daného typu definovaných v systéme, avšak bez zariadenia definované v tomto počítači
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. Fiškálne moduly</param>   
        ''' <param name="u_DeviceIDNum_Include">IDNum zariadenia, ktoré sa má v zozname objaviť bez ohľadu na jeho vlastnosti (ak 0, nevyberie sa žiadne špeciálne zariadenie).</param>   
        Public Function Devices_Exists_Network(ByVal u_DeviceType As enm_Devices_Type, ByVal u_DeviceIDNum_Include As Long, ByRef urf_Device_List As Device_List) As EXC.ExaException

            On Error Resume Next

            Devices_Exists_Network = EXC.GetDefault

            Dim myEx As EXC.ExaException
            Dim tmp_RowFilter$

            If u_DeviceIDNum_Include = 0 Then
                tmp_RowFilter$ = "IDNum = 0"
            Else
                tmp_RowFilter$ = "IDNum = " & u_DeviceIDNum_Include
            End If

            For Each e As DataRow In lc_DeviceList.Object_Table.DatabaseTable_Data.Rows

                Dim tmp_ObjDevice As New Device(prp_AppConfiguration)

                myEx = tmp_ObjDevice._Load(e, u_LoadIndependentInstance:=False)
                If myEx.Result = False Then
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Disable = True Then
                    '--- Zariadenie je vypnuté ---
                    GoTo NextRecord
                End If

                If tmp_ObjDevice.Device_Type = u_DeviceType Then
                    '--- Správny typ zariadenia ---
                    If tmp_ObjDevice.Computers.Contains(My.Computer.Name.ToUpper) = False Then
                        '--- Toto zariadenie sa nepripája k tomuto počítaču - vybrať len zariadenia na iných počítačoch 
                        tmp_RowFilter$ = Exa.Database.ConvertFunctions.RowFilter_AppendFilter(tmp_RowFilter$, "ID = " & tmp_ObjDevice.ID, Database.Viewing.DataViewObjects.Filters.Filter.enm_ConditionMergeTypes.OR)
                    End If
                End If

NextRecord:

            Next

            '--- Načítať zoznam vybraných zariadení ---
            Dim tmp_Selected_DeviceList As Device_List
            tmp_Selected_DeviceList = New Device_List(Me._AppConfiguration)
            tmp_Selected_DeviceList._Privileges_Set_Full(True)   '--- Nastaviť plné práva !!! Inak nebude možné spustiť pokladnicu
            myEx = tmp_Selected_DeviceList._LoadData(tmp_RowFilter$)
            If myEx.Result = False Then
                Devices_Exists_Network = myEx
                GoTo ExitFunction
            End If

            '--- Vrátiť hdnotu ---
            urf_Device_List = tmp_Selected_DeviceList

            Devices_Exists_Network.Result = True

ExitFunction:


        End Function


        ''' <summary>
        ''' Vráti zoznam zariadení určitého typu (základný zoznam konkrétnych typov).
        ''' </summary>
        ''' <param name="u_DeviceType">Filtrovanie typu zariadenia, napr. registračné pokladnice.</param>
        ''' <param name="u_OnlyThisComputer">Len zariadenia počítača na ktorom sa pracuje.</param>
        ''' <param name="u_WithoutDisabled">TRUE - len aktívne (povolené) zariadenia, FALSE - všetky zariadenia.</param>
        ''' <param name="u_AttendanceOnlyOnLine">Parameter platí len pre dochádzkové terminály. 
        ''' TRUE - budú vrátené len zariadenia, ktoré komunikujú s OBERON-om on-line,
        ''' FALSE - vráti všetky dochádzkové terminály.</param>
        Public Function Device_Models_GetEnumList(Of T As Structure)(ByVal u_DeviceType As enm_Devices_Type,
                                                        ByVal u_OnlyThisComputer As Boolean,
                                                        ByVal u_WithoutDisabled As Boolean,
                                                        Optional u_AttendanceOnlyOnLine As Boolean = False) As Collections.Generic.List(Of T)
            On Error Resume Next

            '--- Zistiť názov session - názov počítača ak je program spustený cez Windows Remote Desktop
            Dim tmp_RDP_SessionName$ = Exa.Basic.Net.GetRDPClientName()


            Device_Models_GetEnumList = New Collections.Generic.List(Of T)

            Dim m_Device As Exa.OBERON.Devices.Base.Device = Nothing

            For Each eRow As Data.DataRow In Me.lc_DeviceList.Object_Table.DatabaseTable_Data.Rows

                m_Device = Me.lc_DeviceList.DataRecord(eRow, u_IsIndependentInstance:=True)

                If u_WithoutDisabled = True And m_Device.Disable = True Then
                    '--- ak sa robia len aktívne tak preskočiť
                    Continue For
                End If


                If u_OnlyThisComputer = True Then
                    '--- Vrátiť zoznam zariadení pripájaných len k tomuto počítaču

                    If tmp_RDP_SessionName <> String.Empty Then
                        '--- Počítač pripojený cez RDP
                        If m_Device.ComputersRDP.Contains(tmp_RDP_SessionName$.ToUpper) = False Then
                            '--- Nesprávny názov počítača
                            Continue For
                        End If
                    Else
                        '--- Nebol zistený názov RDP počítača (session)
                        '--- Pravdepodobne nie je tento počítač pripojený cez RDP ---

                        '--- Štandardný názov počítača /nie RDP/
                        If m_Device.Computers.Contains(My.Computer.Name.ToUpper) = False Then
                            '--- Nesprávny názov počítača
                            Continue For
                        End If
                    End If

                End If


                If m_Device.Device_Type <> u_DeviceType Then
                    '--- Iný typ zariadenia ---
                    Continue For
                End If

                '--- Je to rovnaký typ zariadenia
                Dim m_Type As T = CType(CObj(m_Device.Device_Model_Num), T)

                If u_DeviceType = enm_Devices_Type.AttendanceTerminal Then
                    '--- Dochádzkový terminál ---
                    Dim tmp_AttendanceTerminal_Model As enm_AttendanceTerminalModel
                    tmp_AttendanceTerminal_Model = CType(m_Device.Device_Model_Num, enm_AttendanceTerminalModel)

                    Select Case tmp_AttendanceTerminal_Model

                        Case enm_AttendanceTerminalModel.OBERON,
                             enm_AttendanceTerminalModel.EXALOGIC_AC071,
                             enm_AttendanceTerminalModel.EXALOGIC_TFT500SK

                            '--- Tu sú uvedené on-line terminály ---
                            '--- Tieto pridať do zoznamu ---

                        Case enm_AttendanceTerminalModel.None
                            '--- Tu treba pridať ďalšie off-line terminály ---

                            If u_AttendanceOnlyOnLine = True Then
                                '--- Má sa vrátiť len on-line terminály - tieto off-line vynechať---
                                Continue For
                            End If

                    End Select

                End If

                '--- Pridať do zoznamu ---
                If Device_Models_GetEnumList.Contains(m_Type) = False Then
                    '--- Tak ho tam pridá
                    Device_Models_GetEnumList.Add(m_Type)
                End If

            Next

            '--- kill local independent instance object
            If m_Device IsNot Nothing Then
                m_Device.Dispose()
            End If
            m_Device = Nothing

        End Function


        ''' <summary>
        ''' Vráti zoznam zariadení určitého typu (názvy konkrétnych typov zadaných v zozname zariadení).
        ''' </summary>
        ''' <param name="u_DeviceType">Filtrovanie typu zariadenia, napr. registračné pokladnice.</param>
        ''' <param name="u_OnlyThisComputer">Len zariadenia počítača na ktorom sa pracuje.</param>
        ''' <param name="u_WithoutDisabled">TRUE - len aktívne (povolené) zariadenia, FALSE - všetky zariadenia.</param>
        ''' <param name="u_AttendanceOnlyOnLine">Parameter platí len pre dochádzkové terminály. 
        ''' TRUE - budú vrátené len zariadenia, ktoré komunikujú s OBERON-om on-line,
        ''' FALSE - vráti všetky dochádzkové terminály.</param>
        ''' <param name="u_Communication_IPAddress">IP adresa zariadenia - ak je hodnota zadaná, bude sa hľadať zariadenie, 
        ''' ktoré má nastavené pre komunikáciu túto IP adresu.</param>
        Public Function Device_Types_GetList(ByVal u_DeviceType As enm_Devices_Type,
                                                        ByVal u_OnlyThisComputer As Boolean,
                                                        ByVal u_WithoutDisabled As Boolean,
                                                        Optional u_AttendanceOnlyOnLine As Boolean = False,
                                                        Optional u_Communication_IPAddress As String = Nothing) As List(Of String)
            On Error Resume Next

            '--- Zistiť názov session - názov počítača ak je program spustený cez Windows Remote Desktop
            Dim tmp_RDP_SessionName$ = Exa.Basic.Net.GetRDPClientName()


            Device_Types_GetList = New List(Of String)

            Dim m_Device As Exa.OBERON.Devices.Base.Device = Nothing

            For Each eRow As Data.DataRow In Me.lc_DeviceList.Object_Table.DatabaseTable_Data.Rows

                m_Device = Me.lc_DeviceList.DataRecord(eRow, True)

                If u_WithoutDisabled = True And m_Device.Disable = True Then
                    '--- ak sa robia len aktívne tak preskočiť
                    Continue For
                End If


                If u_OnlyThisComputer = True Then
                    '--- Vrátiť zoznam zariadení pripájaných len k tomuto počítaču

                    If tmp_RDP_SessionName <> String.Empty Then
                        '--- Počítač pripojený cez RDP
                        If m_Device.ComputersRDP.Contains(tmp_RDP_SessionName$.ToUpper) = False Then
                            '--- Nesprávny názov počítača
                            Continue For
                        End If
                    Else
                        '--- Nebol zistený názov RDP počítača (session)
                        '--- Pravdepodobne nie je tento počítač pripojený cez RDP ---

                        '--- Štandardný názov počítača /nie RDP/
                        If m_Device.Computers.Contains(My.Computer.Name.ToUpper) = False Then
                            '--- Nesprávny názov počítača
                            Continue For
                        End If
                    End If

                End If

                If m_Device.Device_Type <> u_DeviceType Then
                    '--- Iný typ zariadenia ---
                    Continue For
                End If

                '--- Je to rovnaký typ zariadenia

                If u_DeviceType = enm_Devices_Type.AttendanceTerminal Then
                    '--- Dochádzkový terminál ---
                    Dim tmp_AttendanceTerminal_Model As enm_AttendanceTerminalModel
                    tmp_AttendanceTerminal_Model = CType(m_Device.Device_Model_Num, enm_AttendanceTerminalModel)

                    Select Case tmp_AttendanceTerminal_Model

                        Case enm_AttendanceTerminalModel.OBERON,
                             enm_AttendanceTerminalModel.EXALOGIC_AC071,
                             enm_AttendanceTerminalModel.EXALOGIC_TFT500SK
                            '--- Tu sú uvedené on-line terminály ---
                            '--- Tieto pridať do zoznamu ---

                        Case enm_AttendanceTerminalModel.None
                            '--- Tu treba pridať ďalšie off-line terminály ---

                            If u_AttendanceOnlyOnLine = True Then
                                '--- Má sa vrátiť len on-line terminály - tieto off-line vynechať---
                                Continue For
                            End If

                    End Select

                End If

                '--- IP adresa
                If String.IsNullOrWhiteSpace(u_Communication_IPAddress) = False Then
                    '--- Hľadať zariadenie na konkrétnej IP
                    If m_Device.Communication.TCP_HostName <> u_Communication_IPAddress Then
                        '--- Nezhoda IP adries
                        Continue For
                    End If
                End If


                '--- Pridať do zoznamu ---
                If Device_Types_GetList.Contains(m_Device.Device_Name) = False Then
                    '--- Tak ho tam pridá
                    Device_Types_GetList.Add(m_Device.Device_Name)
                End If

            Next

            '--- kill local independent instance object
            If m_Device IsNot Nothing Then
                m_Device.Dispose()
            End If
            m_Device = Nothing

        End Function


        ''' <summary>
        ''' 
        ''' </summary>
        ''' <param name="u_CashRegisterTableName">Názov table pre pokladnicu OBERON - obsahuje číselný index.</param>
        ''' <param name="urf_Device">Objekt zariadenia</param>
        ''' <returns></returns>
        ''' <remarks></remarks>
        Public Function GetDevice(ByVal u_CashRegisterTableName As String,
                                  ByRef urf_Device As Exa.OBERON.Devices.Base.Device) As Exa.Basic.Exceptions.ExaException
            On Error Resume Next

            GetDevice = EXC.GetDefault()

            Dim m_EE As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_Device_List As Exa.OBERON.Devices.Base.Device_List = Nothing

            '--- Získať len čísla z názvu tabulky.
            Dim TableNumber As String = String.Empty
            Dim myChars() As Char = u_CashRegisterTableName.ToCharArray()
            For Each ch As Char In myChars
                If Char.IsDigit(ch) Then
                    TableNumber = TableNumber + ch
                End If
            Next

            If TableNumber = String.Empty Then
                GoTo ExitFunction
            End If

            m_Device_List = New Exa.OBERON.Devices.Base.Device_List(Me._AppConfiguration)
            '--- Načíta device list do lokálnej property.
            Dim tmp_str As String = String.Format("{0} = '{1}'", "DokladyTabulkaCislo", TableNumber)

            m_EE = m_Device_List._LoadData(tmp_str)
            If m_EE.Result = False Then
                '--- Chyba
                GoTo ExitFunction
            End If

            If m_Device_List.Count = 0 Then
                GoTo ExitFunction
            End If

            '--- Načíta objekt zariadenia podľa databázového čisla tabulky.
            urf_Device = New Exa.OBERON.Devices.Base.Device(Me._AppConfiguration)
            m_EE = urf_Device._Load(m_Device_List.Object_Table.DatabaseTable_Data.Rows(0), u_LoadIndependentInstance:=True)
            If m_EE.Result = False Then
                '--- Chyba
                GetDevice = m_EE
                GoTo ExitFunction
            End If


            GetDevice.Result = True


ExitFunction:

        End Function



        ''' <summary>
        ''' Vráti predajné miesta pokladníc v parametri. Názvy predajných miest sú uložené v inej tabuľke (nastavenie pokladnice).
        ''' </summary>
        ''' <param name="u_FiscalDeviceNames">Zoznam pokladníc.</param>
        ''' <param name="urf_SalesPoints">Návratová hodnota - zoznam pokladníc.</param>                
        Public Function GetFiscalDeviceSalesPoints(ByVal u_FiscalDeviceNames As List(Of String),
                                                   ByRef urf_SalesPoints As List(Of String)) As Exa.Basic.Exceptions.ExaException

            Dim myEx As EXC.ExaException = Nothing
            Dim tmp_CashRegisterOBERON_Settings As Exa.OBERON.Devices.FiscalModule.CashRegisterOBERON_Settings = Nothing
            Dim tmp_Device As Exa.OBERON.Devices.Base.Device = Nothing

            Try

                '--- Návratová hodnota
                urf_SalesPoints = New List(Of String)

                If u_FiscalDeviceNames Is Nothing _
                    OrElse u_FiscalDeviceNames.Count = 0 Then
                    '--- Nezadané
                    myEx = EXC.GetOK()
                    Exit Try
                End If

                tmp_CashRegisterOBERON_Settings = New Exa.OBERON.Devices.FiscalModule.CashRegisterOBERON_Settings(Me._AppConfiguration)

                For i As Integer = 0 To u_FiscalDeviceNames.Count - 1

                    myEx = Me.DeviceList.GetDevice(u_DeviceName:=u_FiscalDeviceNames(index:=i), tmp_Device)
                    If myEx.Result = False Then
                        Exit Try
                    End If

                    myEx = tmp_CashRegisterOBERON_Settings._Load(tmp_Device.IDNum)
                    If myEx.Result = False Then
                        Exit Try
                    End If

                    '--- Pridať do výsledku
                    urf_SalesPoints.Add(tmp_CashRegisterOBERON_Settings.SalesPoint)

                Next


                myEx.Result = True

            Catch ex As Exception

                myEx = EXC.Get($"GetFiscalDeviceSalesPoints error.", ex)

            Finally

                Try

                    If tmp_CashRegisterOBERON_Settings IsNot Nothing Then
                        tmp_CashRegisterOBERON_Settings.Dispose()
                        tmp_CashRegisterOBERON_Settings = Nothing
                    End If

                    If tmp_Device IsNot Nothing Then
                        tmp_Device.Dispose()
                        tmp_Device = Nothing
                    End If
                Catch ex As Exception
                End Try

            End Try

            Return myEx

        End Function



        ''' <summary>
        ''' Vyvolanie udalosti zmeny stavu aktívnych zariadení v systéme.
        ''' </summary>
        Friend Sub OnDeviceEngineStateChange(engineState As enm_DeviceEngineStateType)

            RaiseEvent ev_DeviceEngineStateChange(engineState)

        End Sub


#End Region


#Region " EVENTS HANDLERS "

        Private Sub eh_ev_BarCodeScanner_StateChange()

            Try
                Dim m_IsReady As TriState = TriState.UseDefault

                Select Case True
                    Case prp_BarCodeScanner1 IsNot Nothing AndAlso prp_BarCodeScanner1?.IsReady = TriState.False
                        m_IsReady = TriState.False
                    Case prp_BarCodeScanner2 IsNot Nothing AndAlso prp_BarCodeScanner2?.IsReady = TriState.False
                        m_IsReady = TriState.False
                    Case prp_BarCodeScanner1 IsNot Nothing AndAlso prp_BarCodeScanner1?.IsReady = TriState.True
                        m_IsReady = TriState.True
                    Case prp_BarCodeScanner2 IsNot Nothing AndAlso prp_BarCodeScanner2?.IsReady = TriState.True
                        m_IsReady = TriState.True
                End Select


                If Me._AppConfiguration._AppObjects.form_Main.InvokeRequired Then
                    Me._AppConfiguration._AppObjects.form_Main.BeginInvoke(Sub() RaiseEvent ev_BarCodeScanner_StateChange(m_IsReady))
                    Exit Sub
                End If
                RaiseEvent ev_BarCodeScanner_StateChange(m_IsReady)

            Catch ex As Exception
            End Try

        End Sub

        Private Sub eh_ev_BarCodeScanner_Readed(ByVal u_EventArgs As BarcodeScanner.Driver_Common.BarCodeScanner_Readed_EventArgs)

            On Error Resume Next


            If Me._AppConfiguration._AppObjects.form_Main.InvokeRequired Then
                Me._AppConfiguration._AppObjects.form_Main.BeginInvoke(Sub() RaiseEvent ev_BarCodeScanner_Readed(u_EventArgs))
                Exit Sub
            End If
            RaiseEvent ev_BarCodeScanner_Readed(u_EventArgs)

        End Sub


#End Region


#Region " Function private "


        ''' <summary>
        ''' Štart engin-u so zariadeniami, ak je v zozname zariadení napr. snímač čiarového kódu, tak sa otvorí komunikáčný port a "načúva sa" ...
        ''' </summary>
        Private Function z_Engine_Run() As EXC.ExaException

            On Error Resume Next

            Dim myEx As EXC.ExaException

            z_Engine_Run = EXC.GetDefault


            '---------------------------------------------------
            '--- Zatvoriť zariadenia ktoré môžu byť otvorené ---
            '---------------------------------------------------
            z_Engine_Stop()


            '--- Aktualizovanie stavu
            Me.OnDeviceEngineStateChange(enm_DeviceEngineStateType.Refreshing)


            Dim tmp_ObjDevice As Device = Nothing

            '-----------------------------------------------------------------------------------------------
            '--- Snímač čiarového kódu č. 1 ---
            '-----------------------------------------------------------------------------------------------

            If Me.Device_Exists_ThisComputer(enm_Devices_Type.BarCodeScanner, tmp_ObjDevice, 1) Then
                '--- Na tomto počítači má byť inštalovaný a prevádzkovaný snímač čiarového kódu ---


                If prp_BarCodeScanner1 Is Nothing Then
                    Err.Clear()
                    prp_BarCodeScanner1 = New BarcodeScanner.Driver_Common(tmp_ObjDevice.Communication, tmp_ObjDevice.dev_BarCode_Scanner)
                    If Err.Number <> 0 Then
                        '--- Chyba pri inicializácii

                        Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                        '--- LOG --
                        prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Snímač čiarových kódov - chyba pri inicializácii")

                        Exa.Basic.Debug.Console._Write("Chyba pri inicializácii ovládača zariadenia snímača čiarových kódov č.1.", "", m_Description1,
                                                       "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)
                        GoTo After_BarcodeScanner1
                    End If

                    AddHandler prp_BarCodeScanner1.ev_BarCodeScanner_StateChange, AddressOf eh_ev_BarCodeScanner_StateChange
                    AddHandler prp_BarCodeScanner1.ev_BarCodeScanner_Readed, AddressOf eh_ev_BarCodeScanner_Readed

                End If


                myEx = prp_BarCodeScanner1._PortOpen()
                If myEx.Result = False Then
                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Snímač čiarových kódov - chyba pri inicializácii")

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení komunikácie so snímačom čiarových kódov č.1.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_BarcodeScanner1
                End If

                Dim m_Description As String = "Port_Number:  " & tmp_ObjDevice.Communication.Port_Number & vbCrLf & "Port BaudRate:  " & tmp_ObjDevice.Communication.Port_BaudRate
                Exa.Basic.Debug.Console._Write("Snímač čiarových kódov č.1 bol inicializovaný.", "", m_Description,
                                               "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If

After_BarcodeScanner1:

            '-----------------------------------------------------------------------------------------------
            '--- Snímač čiarového kódu č. 2 ---
            '-----------------------------------------------------------------------------------------------

            If Me.Device_Exists_ThisComputer(enm_Devices_Type.BarCodeScanner, tmp_ObjDevice, 2) Then
                '--- Na tomto počítači má byť inštalovaný a prevádzkovaný snímač čiarového kódu ---


                If prp_BarCodeScanner2 Is Nothing Then
                    Err.Clear()
                    prp_BarCodeScanner2 = New BarcodeScanner.Driver_Common(tmp_ObjDevice.Communication, tmp_ObjDevice.dev_BarCode_Scanner)
                    If Err.Number <> 0 Then
                        '--- Chyba pri inicializácii

                        Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                        '--- LOG --
                        prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Snímač čiarových kódov - chyba pri inicializácii")

                        Exa.Basic.Debug.Console._Write("Chyba pri inicializácii ovládača zariadenia snímača čiarových kódov č.2.", "", m_Description1,
                                                       "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)
                        GoTo After_BarcodeScanner2
                    End If

                    AddHandler prp_BarCodeScanner2.ev_BarCodeScanner_StateChange, AddressOf eh_ev_BarCodeScanner_StateChange
                    AddHandler prp_BarCodeScanner2.ev_BarCodeScanner_Readed, AddressOf eh_ev_BarCodeScanner_Readed

                End If


                myEx = prp_BarCodeScanner2._PortOpen()
                If myEx.Result = False Then
                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Snímač čiarových kódov - chyba pri inicializácii")

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení komunikácie so snímačom čiarových kódov č.2.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_BarcodeScanner2
                End If

                Dim m_Description As String = "Port_Number:  " & tmp_ObjDevice.Communication.Port_Number & vbCrLf & "Port BaudRate:  " & tmp_ObjDevice.Communication.Port_BaudRate
                Exa.Basic.Debug.Console._Write("Snímač čiarových kódov č.2 bol inicializovaný.", "", m_Description,
                                               "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If


After_BarcodeScanner2:


            '-----------------------------------------------------------------------------------------------
            '--- DocumentReader - Čítačka dokladov ---
            '-----------------------------------------------------------------------------------------------

            If Me.Device_Exists_ThisComputer(enm_Devices_Type.DocumentReader, tmp_ObjDevice) Then

                Err.Clear()
                prp_DocumentReader = New DocumentReader.Driver_Common(tmp_ObjDevice)
                If prp_DocumentReader Is Nothing _
                    Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "DocumentReader zariadenie - chyba pri inicializácii")


                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii zariadenia typu 'Čítačka dokladov'.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_DocumentReader
                End If

                '--- Otvoriť komunikáciu
                myEx = prp_DocumentReader.Open()
                If myEx.Result = False Then
                    '--- LOG --
                    If prp_AppConfiguration._AppObjects._Log_Firm.IsLogSettingsLoaded Then
                        prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "DocumentReader - chyba pri inicializácii")
                    End If

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení spojenia so zariadením typu 'Čítačka dokladov'.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_DocumentReader
                End If


                If prp_DocumentReader.Support.PernamentOpen = True Then
                    '--- Komunikácia so zariadením stále otvorená, napr. ak čítačka dokladov sníma aj čiarový kód
                    '--- Zatvoriť komunikáciu s čítačkou
                    Exa.Basic.Debug.Console._Write("Zariadenie 'Čítačka dokladov' bolo inicializované.", "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    AddHandler prp_DocumentReader.ev_BarCodeScanner_Readed, AddressOf eh_ev_BarCodeScanner_Readed

                Else
                    '--- Zatvoriť komunikáciu s čítačkou
                    Exa.Basic.Debug.Console._Write("Zariadenie 'Čítačka dokladov' bolo otestované.", "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    'Zatvor spojenie so zariadením. Nemusí sa držať stále
                    prp_DocumentReader.Close()

                End If
            End If


After_DocumentReader:



            '-----------------------------------------------------------------------------------------------
            '--- Zákaznícky Displej---
            '-----------------------------------------------------------------------------------------------
            If Me.Device_Exists_ThisComputer(enm_Devices_Type.DisplayCustomer, tmp_ObjDevice) Then
                '--- Na tomto počítači má byť inštalovaný a prevádzkovaný displej ---

                Err.Clear()
                prp_DisplayCustomer = New DisplayCustomer.Driver_Common(tmp_ObjDevice)
                If prp_DisplayCustomer Is Nothing Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Zákaznícky displej - chyba pri inicializácii")

                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii displeja.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_Display
                End If

                '--- Nastaviť zariadenie --
                prp_DisplayCustomer.Communication = tmp_ObjDevice.Communication.Clone

                '--- Špecialita - OBERON Smart displej - doplniť heslo k webovej službe
                If prp_DisplayCustomer.DisplayCustomerModel = enm_DisplayCustomerModel.OBERON_Smart Then
                    prp_DisplayCustomer.Communication.Login_Password = Me._AppConfiguration._AppObjects._UserInfo.GetUserPassword(prp_DisplayCustomer.Communication.Login_Name, u_Refresh_UserList:=False)
                End If

                prp_DisplayCustomer.Settings.TextStandBy1 = tmp_ObjDevice.dev_DisplayCustomer.Text_StandBy_1
                prp_DisplayCustomer.Settings.TextStandBy2 = tmp_ObjDevice.dev_DisplayCustomer.Text_StandBy_2

                myEx = prp_DisplayCustomer.ShowDateTime()

                If myEx.Result = False Then

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení komunikácie s displejom.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_Display
                End If

                Dim m_Description As String = "Port_Number:  " & tmp_ObjDevice.Communication.Port_Number & vbCrLf & "Port BaudRate:  " & tmp_ObjDevice.Communication.Port_BaudRate
                Exa.Basic.Debug.Console._Write("Displej bol inicializovaný.", "", m_Description,
                                               "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If

After_Display:


            '-----------------------------------------------------------------------------------------------
            '--- Elektronické cenovky (Price Labels) ---
            '-----------------------------------------------------------------------------------------------
            If Me.Device_Exists_ThisComputer(enm_Devices_Type.PriceLabels, tmp_ObjDevice) Then
                '--- Na tomto počítači má byť inštalované a prevádzkované cenovkové zariadenie ---

                Err.Clear()
                prp_PriceLabels = New PriceLabels.Driver_Common(tmp_ObjDevice)
                If prp_PriceLabels Is Nothing Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Elektronické cenovky - chyba pri inicializácii")

                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii ovladača elektronickej cenovky.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_PriceLabels
                End If

                '--- Nastaviť zariadenie --
                prp_PriceLabels.Communication = tmp_ObjDevice.Communication.Clone

                '--- Test komunikácie (async funkcia musí byť volaná bez On Error Resume Next)
                Dim tmp_CommTestEx As EXC.ExaException = CallAsyncCommunicationTest(prp_PriceLabels)
                myEx = tmp_CommTestEx

                If myEx.Result = False Then

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri testovaní komunikácie s cenovkami.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_PriceLabels
                End If

                Dim m_Description As String = "IP adresa:  " & tmp_ObjDevice.Communication.TCP_HostName
                Exa.Basic.Debug.Console._Write("Cenovky boli inicializované.", "", m_Description,
                                               "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If

After_PriceLabels:


            '-----------------------------------------------------------------------------------------------
            '--- Elektronické váhy ---
            '-----------------------------------------------------------------------------------------------
            Dim tmp_ObjDevices As Device_List = Nothing
            myEx = Me.Devices_Exists_ThisComputer(enm_Devices_Type.ElectronicScale, tmp_ObjDevices)
            If myEx.Result = False Then
                '--- Chyba pri inicializácii

                Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription

                '--- LOG --
                prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Elektronické váhý - chyba pri načítaní")


                Exa.Basic.Debug.Console._Write("Chyba pri načítaní nastavení elektronických váh.", "", m_Description1,
                                                       "Zariadenie: Elektronické váhy", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)
                GoTo After_ElectronicScale
            End If

            For Each e_Device As Device In tmp_ObjDevices.AsEnumerable().OfType(Of Device)

                Err.Clear()
                Dim m_ElectronicScale As New ElectronicScale.Driver_Common(e_Device.dev_ElectronicScale.ElectronicScaleModel, e_Device.Device_Name)
                If m_ElectronicScale Is Nothing Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Elektronická váha - chyba pri inicializácii")

                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii ovladača elektronickej váhy.", "", m_Description1,
                                                       "Zariadenie: " & e_Device.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)
                    Continue For
                End If

                m_ElectronicScale.Communication.Port_Number = e_Device.Communication.Port_Number
                m_ElectronicScale.Communication.Port_BaudRate = e_Device.Communication.Port_BaudRate

                myEx = m_ElectronicScale.CommunicationOpen()
                If myEx.Result = False Then
                    '--- LOG --
                    If prp_AppConfiguration._AppObjects._Log_Firm.IsLogSettingsLoaded = True Then
                        '--- LOG-ovať len ak je už objekt s logom inicializovaný
                        prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Elektronická váha - chyba pri inicializácii")
                    End If

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení komunikácie s elektronickou váhou.", "", m_Description1,
                                                   "Zariadenie: " & e_Device.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    Continue For
                End If

                AddHandler m_ElectronicScale.ev_ElectronicScale_Weight_Readed, AddressOf on_ev_ElectronicScale_Weight_Readed

                'Pridej do zoznamu
                prp_ElectronicScales.Add(m_ElectronicScale)

                Dim m_Description As String = "Port_Number:  " & e_Device.Communication.Port_Number & vbCrLf & "Port BaudRate:  " & e_Device.Communication.Port_BaudRate
                Exa.Basic.Debug.Console._Write("Elektronická váha bola inicializovaná.", "", m_Description,
                                               "Zariadenie: " & e_Device.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            Next



After_ElectronicScale:


            '-----------------------------------------------------------------------------------------------
            '--- PID - prístupový systém ---
            '-----------------------------------------------------------------------------------------------
            If Me.Device_Exists_ThisComputer(enm_Devices_Type.PID, tmp_ObjDevice) Then
                '--- Na tomto počítači má byť inštalované a prevádzkované PID zariadenie, napr. snímač prístupového klúča ---

                Err.Clear()
                prp_PID = New PID.Driver_Common(tmp_ObjDevice.dev_PID.PID_Model)
                If prp_PID Is Nothing Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "PID zariadenie - chyba pri inicializácii")

                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii PID zariadenia.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_PID
                End If

                prp_PID.Port_Number = tmp_ObjDevice.Communication.Port_Number
                prp_PID.Port_BaudRate = CShort(tmp_ObjDevice.Communication.Port_BaudRate)

                '--- Otvoriť komunikáciu
                myEx = prp_PID._CommunicationOpen()
                If myEx.Result = False Then
                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "Snímač čiarových kódov - chyba pri inicializácii")

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení komunikácie s PID zariadením.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_PID
                End If

                Dim m_Description As String = "Port_Number:  " & tmp_ObjDevice.Communication.Port_Number & vbCrLf & "Port BaudRate:  " & tmp_ObjDevice.Communication.Port_BaudRate
                Exa.Basic.Debug.Console._Write("PID zariadenie bolo inicializované.", "", m_Description,
                                               "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If

After_PID:


            '-----------------------------------------------------------------------------------------------
            '--- DoorKey - Dverové zámky ---
            '-----------------------------------------------------------------------------------------------
            If Me.Device_Exists_ThisComputer(enm_Devices_Type.DoorKey, tmp_ObjDevice) Then
                '--- Na tomto počítači má byť inštalované a prevádzkované DoorKey zariadenie ---

                Err.Clear()
                prp_DoorKey = New DoorKey.Driver_Common(tmp_ObjDevice.dev_DoorKey.DoorKey_Model)
                If prp_DoorKey Is Nothing Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description
                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "DoorKey zariadenie - chyba pri inicializácii")

                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii DoorKey zariadenia.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_DoorKey
                End If

                '--- Nastavenia komunikácia ---
                prp_DoorKey.Communication = tmp_ObjDevice.Communication.Clone

                '--- Otvoriť komunikáciu
                myEx = prp_DoorKey.DoorKey_CommunicationOpen()
                If myEx.Result = False Then
                    '--- LOG --
                    If prp_AppConfiguration._AppObjects._Log_Firm.IsLogSettingsLoaded Then
                        prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "DoorKey - chyba pri inicializácii")
                    End If

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení komunikácie s DoorKey zariadením.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_DoorKey
                End If

                Dim m_Description As String = "Communication Settings:" & vbCrLf & tmp_ObjDevice.Communication.ToString
                Exa.Basic.Debug.Console._Write("DoorKey zariadenie bolo inicializované.", "", m_Description,
                                               "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If

After_DoorKey:




            '-----------------------------------------------------------------------------------------------
            '--- SignaturePad ---
            '-----------------------------------------------------------------------------------------------

            If Me.Device_Exists_ThisComputer(enm_Devices_Type.SignaturePad, tmp_ObjDevice) Then

                Err.Clear()
                prp_SignaturePad = New SignaturePad.Driver_Common(tmp_ObjDevice)
                If prp_SignaturePad Is Nothing _
                    Or Err.Number <> 0 Then
                    '--- Chyba pri inicializácii

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & Err.Description

                    '--- LOG --
                    prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "SignaturePad zariadenie - chyba pri inicializácii")

                    Exa.Basic.Debug.Console._Write("Chyba pri inicializácii zariadenia typu 'Podpisová podložka'.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_SignaturePad
                End If

                '--- Otvoriť komunikáciu
                myEx = prp_SignaturePad.CommunicationOpen()
                If myEx.Result = False Then
                    '--- LOG --
                    If prp_AppConfiguration._AppObjects._Log_Firm.IsLogSettingsLoaded Then
                        prp_AppConfiguration._AppObjects._Log_Firm._Write(ApplicationEnvironment.Logs.Data.Log.enm_EventIDTypes.Error_Device, ApplicationEnvironment.Logs.Data.Log.enm_LogTypes.Error, Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.OBERON, "SignaturePad - chyba pri inicializácii")
                    End If

                    Dim m_Description1 As String = "Chyba:" & vbCrLf & myEx.GetFullDescription
                    Exa.Basic.Debug.Console._Write("Chyba pri vytvorení spojenia so zariadením typu 'Podpisová podložka'.", "", m_Description1,
                                                   "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Error, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

                    GoTo After_SignaturePad
                End If

                myEx = prp_SignaturePad.CommunicationClose()

                '--- Zatvoriť komunikáciu 
                Exa.Basic.Debug.Console._Write("Zariadenie 'Podpisová podložka' bolo otestované.", "Zariadenie: " & tmp_ObjDevice.Device_Name, Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Device)

            End If


After_SignaturePad:


            '--- Príznak že je engine spustený
            prp_IsRunning = True

            '--- Aktualizovanie stavu
            Me.OnDeviceEngineStateChange(enm_DeviceEngineStateType.Started)


            z_Engine_Run.Result = True

ExitFunction:

        End Function



        ''' <summary>
        ''' Zastavenie Engin-u
        ''' </summary>
        Private Function z_Engine_Stop() As EXC.ExaException

            On Error Resume Next

            z_Engine_Stop = EXC.GetDefault

            '--- Aktualizovanie stavu
            Me.OnDeviceEngineStateChange(enm_DeviceEngineStateType.Stopping)


            If prp_BarCodeScanner1 IsNot Nothing Then
                RemoveHandler prp_BarCodeScanner1.ev_BarCodeScanner_StateChange, AddressOf eh_ev_BarCodeScanner_StateChange
                RemoveHandler prp_BarCodeScanner1.ev_BarCodeScanner_Readed, AddressOf eh_ev_BarCodeScanner_Readed
                prp_BarCodeScanner1.Dispose()
                prp_BarCodeScanner1 = Nothing
            End If

            If prp_BarCodeScanner2 IsNot Nothing Then
                RemoveHandler prp_BarCodeScanner2.ev_BarCodeScanner_StateChange, AddressOf eh_ev_BarCodeScanner_StateChange
                RemoveHandler prp_BarCodeScanner2.ev_BarCodeScanner_Readed, AddressOf eh_ev_BarCodeScanner_Readed
                prp_BarCodeScanner2.Dispose()
                prp_BarCodeScanner2 = Nothing
            End If

            If prp_DocumentReader IsNot Nothing Then
                RemoveHandler prp_DocumentReader.ev_BarCodeScanner_Readed, AddressOf eh_ev_BarCodeScanner_Readed
                prp_DocumentReader.Dispose()
                prp_DocumentReader = Nothing
            End If


            If prp_DisplayCustomer IsNot Nothing Then
                prp_DisplayCustomer.Dispose()
                prp_DisplayCustomer = Nothing
            End If

            If prp_ElectronicScales IsNot Nothing Then
                For Each e_Item As ElectronicScale.Driver_Common In prp_ElectronicScales
                    RemoveHandler e_Item.ev_ElectronicScale_Weight_Readed, AddressOf on_ev_ElectronicScale_Weight_Readed
                    e_Item.Dispose()
                Next
                prp_ElectronicScales.Clear()
            End If

            If prp_PID IsNot Nothing Then
                prp_PID.Dispose()
                prp_PID = Nothing
            End If

            If prp_DoorKey IsNot Nothing Then
                prp_DoorKey.Dispose()
                prp_DoorKey = Nothing
            End If


            '--- Príznak že je engine vypnutý
            prp_IsRunning = False


            z_Engine_Stop.Result = True

ExitFunction:


        End Function


        Private Sub z_Dispose()

            On Error Resume Next
            z_Engine_Stop()

            If lc_DeviceList IsNot Nothing Then
                lc_DeviceList.Dispose()
                lc_DeviceList = Nothing
            End If

            prp_AppConfiguration = Nothing


        End Sub


#End Region


#Region " Private Async Helper "

        ''' <summary>
        ''' Pomocná funkcia pre volanie async CommunicationTest bez On Error Resume Next.
        ''' </summary>
        Private Function CallAsyncCommunicationTest(ByVal u_PriceLabels As PriceLabels.Driver_Common) As EXC.ExaException
            Dim tmp_Ex As EXC.ExaException = EXC.GetDefault
            Try
                '--- Volanie async funkcie a čakanie na výsledok (na background thread)
                tmp_Ex = Task.Run(Function() u_PriceLabels.CommunicationTest().Result).Result
            Catch ex As Exception
                '--- Získať skutočnú chybu (v prípade Task.Run() je to TargetInvocationException)
                Dim tmp_ErrorMsg As String = "Zariadenie neodpovedalo"
                Try
                    Dim tmp_ActualEx As Exception = ex
                    If TypeOf ex Is System.Reflection.TargetInvocationException AndAlso ex.InnerException IsNot Nothing Then
                        tmp_ActualEx = ex.InnerException
                    End If
                    If tmp_ActualEx IsNot Nothing Then
                        tmp_ErrorMsg = tmp_ActualEx.Message
                    End If
                Catch
                    '--- Ak sa zlyhá získanie chybového hlásenia, použi výchozí text
                    tmp_ErrorMsg = "Zariadenie neodpovedalo"
                End Try
                '--- Overiť, či ex nie je Nothing
                If ex IsNot Nothing Then
                    tmp_Ex = EXC.Get(tmp_ErrorMsg, ex)
                Else
                    tmp_Ex = EXC.Get(tmp_ErrorMsg)
                End If
            End Try
            Return tmp_Ex
        End Function

#End Region


#Region " IDisposable Support "


        Private disposedValue As Boolean = False        ' To detect redundant calls

        ' IDisposable
        Protected Overridable Sub Dispose(ByVal disposing As Boolean)
            If Not Me.disposedValue Then
                If disposing Then
                End If

                z_Dispose()

            End If
            Me.disposedValue = True
        End Sub


        ' This code added by Visual Basic to correctly implement the disposable pattern.
        Public Sub Dispose() Implements IDisposable.Dispose
            ' Do not change this code.  Put cleanup code in Dispose(ByVal disposing As Boolean) above.
            Dispose(True)
            GC.SuppressFinalize(Me)
        End Sub

#End Region


    End Class

End Namespace
