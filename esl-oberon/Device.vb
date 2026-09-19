Option Explicit On
Option Strict On
Option Infer Off
Imports System.Xml.Linq

Namespace Base

    ''' <summary>
    ''' Zariadenie - napr. registračná pokladnica, fiškálna tlačiareň, snímač čiarového kódu. Obsahuje údaje o nastavení daného zariadenia v systéme OBERON.
    ''' </summary>   
    Public Class Device
        Inherits Exa.Database.Factory.DataRecord
        Implements IDisposable

#Region " Declaration "

        Public Const CONST_TableName_Devices As String = "Zariadenia"

        Public Const CONST_Printer_Fiscal As String = "*** Fiškálne zariadenie ***"

        Public Const CONST_Printer_Name_Notepad As String = "*** Len zobraziť náhľad ***"
        Public Const CONST_Printer_File_Name As String = "fiscalmodule_print.txt"

        Public Const CONST_Stock_All As String = "*** Všetky sklady ***"
        Public Const CONST_CashRegisterDevice_All As String = "*** Všetky pokladnice ***"

        Public Const CONST_TableName_Bill_Headers As String = "Stock_CashRegister_Bill_Headers_"
        Public Const CONST_TableName_Bill_Items As String = "Stock_CashRegister_Bill_Items_"
        Public Const CONST_TableName_BillPaymentTypes As String = "Stock_CashRegister_Bill_PaymentTypes_"

        Public Const CONST_TableName_Stock_CashRegister_Cash As String = "Stock_CashRegister_Cash_"
        Public Const CONST_TableName_Stock_CashRegister_CashCurrent As String = "Stock_CashRegister_CashCurrent"
        Public Const CONST_TableName_Stock_CashRegister_CashTypes As String = "Stock_CashRegister_CashTypes"


        Public Const CONST_TableName_Bill_Open As String = "Stock_CashRegister_BillOpen"
        Public Const CONST_TableName_Bill_Open_Items As String = "Stock_CashRegister_BillOpen_Items"

        ''' <summary>Prefix názvu počítača pri pripájaní zariadenia z počítača pomocou Windows Remote Desktop (aj s medzerou na konci).</summary>	
        Public Const CONST_RDP_SessionName_Prefix As String = "RDP: "


        Friend Const CONST_XmlInternal_ElementName_DocumentRoot As String = "System"
        Friend Const CONST_XmlInternal_ElementName_FiscalDevice As String = "FiscalDevice"
        Friend Const CONST_XmlInternal_ElementName_KitchenPrinter As String = "KitchenPrinter"
        Friend Const CONST_XmlInternal_ElementName_AttendanceTerminal As String = "AttendanceTerminal"
        Friend Const CONST_XmlInternal_ElementName_BarCodeScanner As String = "BarCodeScanner"
        Friend Const CONST_XmlInternal_ElementName_PaymentTerminal As String = "PaymentTerminal"
        Friend Const CONST_XmlInternal_ElementName_SignaturePad As String = "SignaturePad"
        Friend Const CONST_XmlInternal_ElementName_DeviceParams As String = "DeviceParams"
        Friend Const CONST_DefaultFileName_WithoutExtension As String = "Device"
        Friend Const CONST_DefaultFileName_Extension As String = "xml"

        Private Const C_CRYPTO_KEY As String = "b1$hg7$kU6nV"

        Private lc_ShowError_DeviceType_NotFound As Boolean = False

        ''' <summary>
        ''' Umožňuje ignorovať uloženie default nastavení napr. keď sa nastavenia kopírujú zo schránky clipboard.
        ''' </summary>
        Private lc_SaveBehavior_IgnoreDefaultSettings As Boolean = False

#End Region

#Region " Properties "

        Private prp_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration

        Public ReadOnly Property _AppConfiguration() As Exa.OBERON.ApplicationEnvironment.AppConfiguration
            Get
                Return prp_AppConfiguration
            End Get
        End Property

        Private prp_SaveBehavior As cls_SaveBehavior
        ''' <summary>
        ''' Bližšie určuje akým spôsobom sa uloží záznam pomocou metódy _Save, napr. či sa majú validovať určité hodnoty.
        ''' </summary>
        Public ReadOnly Property _SaveBehavior() As cls_SaveBehavior
            Get
                Return prp_SaveBehavior
            End Get
        End Property


        Private prpIDnum As Long
        ''' <summary>IDNum zariadenia (jednoznačný identifikátor).</summary>
        Public ReadOnly Property IDNum() As Long
            Get
                Return CLng(MyBase.Field("IDNum"))
            End Get
        End Property

        ''' <summary>Názov (pomenovanie) zariadenia definovaný používateľom v zozname zariadení.</summary>
        Public Property Device_Name() As String
            Get
                Return CStr(MyBase.Field("Nazov"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("Nazov") = value
            End Set
        End Property


        ''' <summary>Typ zariadenia, napr. fiškálny modul, registračná pokladnica, zákaznícky displej, dverový zámok a podobne.</summary>
        Public Property Device_Type() As enm_Devices_Type
            Get
                Return CType(MyBase.Field("ZariadenieDruh"), enm_Devices_Type)
            End Get
            Set(ByVal value As enm_Devices_Type)

                On Error Resume Next

                Dim tmpOldValue As enm_Devices_Type

                tmpOldValue = CType(MyBase.Field("ZariadenieDruh"), enm_Devices_Type)

                MyBase.Field("ZariadenieDruh") = value

                If MyBase.RecordState_Application = enm_RecordStateTypes.CreateNew Then
                    '--- Nové zariadenie ---
                    If tmpOldValue <> value Then
                        '--- Zmenil sa typ zariadenia --
                        '--- Opätovne načítať default hodnoty
                        Me.Device_ev_RecordColumns_SetValues(New cls_RecordColumnSetValueEventArgs(Me, cls_RecordColumnSetValueEventArgs.enm_SetTargetTypes.Property, cls_RecordColumnSetValueEventArgs.enm_ValueUseTypes.Default))
                    End If
                End If

            End Set
        End Property


        ''' <summary>
        ''' Vráti názov modelu zariadenia v závislosti na type zariadenia, napr. eKasa Pandora. 
        ''' </summary>
        Public ReadOnly Property Device_Model_Name() As String
            Get
                On Error Resume Next

                If Me.Device_Type = enm_Devices_Type.None Then
                    Return Nothing
                End If

                Return GetDeviceModelName(Me.Device_Type, u_DeviceModelNumber:=Me.Device_Model_Num)
            End Get
        End Property


        ''' <summary>
        ''' Vráti číslo modelu zariadenia. Integer preto, lebo zariadenia sú rôzne a sú uložené v rôznych enum-och. 
        ''' Presný enum je uložený už pri príslušnom zariadení, vlastnosti začínajúcej s prefixom d_.
        ''' </summary>
        Public Property Device_Model_Num() As Integer
            Get
                On Error Resume Next
                Return CInt(MyBase.Field("DeviceModel"))
            End Get
            Set(ByVal value As Integer)

                On Error Resume Next

                MyBase.Field("DeviceModel") = value

                '--- Nastaví presný ENUM k danému zariadeniu 
                z_SetDeviceModelEnumToDevStructure(value)

            End Set
        End Property


        ''' <summary>Vráti info o zariadení v textovom formáte.</summary>
        Public ReadOnly Property Device_Info() As String
            Get

                On Error Resume Next
                Dim tmpSB As New System.Text.StringBuilder

                Select Case Me.Device_Type

                    Case enm_Devices_Type.BarCodeScanner

                        If prp_Communication.Port_Number <> 0 Then
                            '--- Pripája sa cez COM port
                            tmpSB.Append("port COM" & prp_Communication.Port_Number)
                            If prp_Communication.Port_BaudRate <> 0 Then
                                tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "b")
                            End If
                        Else
                            '--- Je zadaná IP 
                            tmpSB.Append("IP adresa" & prp_Communication.TCP_HostName)
                            If prp_Communication.TCP_Port <> 0 Then
                                tmpSB.Append(", Tcp/IP port " & prp_Communication.TCP_Port)
                            End If
                        End If


                    Case enm_Devices_Type.CashRegister
                        If Me.Device_Model_Num <> enm_CashRegister_Model.CashRegister_Universal Then
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)
                        End If
                        If prp_dev_CashRegister.Settings_Stock_Name <> String.Empty Then
                            tmpSB.Append(", sklad '" & prp_dev_CashRegister.Settings_Stock_Name & "'")
                        End If
                        If prp_Communication.CashRegister_PLU_Max <> 0 Then
                            tmpSB.Append(", max. počet PLU " & prp_Communication.CashRegister_PLU_Max)
                        End If
                        If Me.Device_Model_Num <> enm_CashRegister_Model.CashRegister_Universal Then
                            If prp_Communication.Port_Number > 0 OrElse String.IsNullOrEmpty(prp_Communication.TCP_HostName) Then
                                tmpSB.Append(", port COM" & prp_Communication.Port_Number)
                                If prp_Communication.Port_BaudRate <> 0 Then
                                    tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "Bd")
                                End If
                            Else
                                tmpSB.Append(", hostname '" & prp_Communication.TCP_HostName & "'")
                                If prp_Communication.TCP_Port <> 0 Then
                                    tmpSB.Append(", port " & prp_Communication.TCP_Port)
                                End If
                            End If
                        End If

                        If Me.Device_Code <> String.Empty Then
                            tmpSB.Append(", DKP: " & Me.Device_Code)
                        End If

                    Case enm_Devices_Type.DisplayCustomer

                        If prp_Communication.Port_Number <> 0 Then
                            '--- Pripája sa cez COM port
                            tmpSB.Append("port COM" & prp_Communication.Port_Number)
                            If prp_Communication.Port_BaudRate <> 0 Then
                                tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "b")
                            End If
                        Else
                            '--- Je zadaná IP 
                            tmpSB.Append("IP adresa" & prp_Communication.TCP_HostName)
                            If prp_Communication.TCP_Port <> 0 Then
                                tmpSB.Append(", Tcp/IP port " & prp_Communication.TCP_Port)
                            End If
                        End If

                    Case enm_Devices_Type.ElectronicScale
                        tmpSB.Append("port COM" & prp_Communication.Port_Number)
                        If prp_Communication.Port_BaudRate <> 0 Then
                            tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "b")
                        End If

                    Case enm_Devices_Type.DoorKey
                        tmpSB.Append("hostname '" & prp_Communication.TCP_HostName & "'")
                        If prp_Communication.TCP_Port <> 0 Then
                            tmpSB.Append(", port " & prp_Communication.TCP_Port)
                        End If

                    Case enm_Devices_Type.AttendanceTerminal
                        'AttendanceTerminal - info o zariadení
                        'tmpSB.AppendFormat("firma: {0}", prp_dev_AttendanceTerminal.CompanyId) 'Nenačítané z XML
                        tmpSB.AppendFormat("terminál id: {0}", prp_Communication.DeviceCommunicationNumber)
                        tmpSB.AppendFormat(", SN: {0}", Me.Device_ProductNumber)
                        Select Case Me.prp_dev_AttendanceTerminal.AttendanceTerminalModel
                            Case enm_AttendanceTerminalModel.EXALOGIC_AC071
                                tmpSB.AppendFormat(", hostname: {0}:{1}", prp_Communication.TCP_HostName, prp_Communication.TCP_Port)
                                'tmpSB.AppendFormat(", monitor: {0}", prp_dev_AttendanceTerminal.Monitor_IPEndPoint.ToString)
                            Case enm_AttendanceTerminalModel.EXALOGIC_TFT500SK
                                tmpSB.AppendFormat(", server:8081, hostname: {0}:{1}",
                                                   prp_Communication.TCP_HostName, prp_Communication.TCP_Port)
                        End Select

                    Case enm_Devices_Type.PaymentTerminal

                        If String.IsNullOrWhiteSpace(prp_dev_PaymentTerminal.TerminalDesc) = False Then
                            tmpSB.Append($"Terminál '{prp_dev_PaymentTerminal.TerminalDesc}'")
                        Else
                            tmpSB.Append($"Terminál '{prp_dev_PaymentTerminal.TerminalId}'")
                            If String.IsNullOrWhiteSpace(prp_dev_PaymentTerminal.CashId) = False Then
                                tmpSB.Append($", Pokladňa '{prp_dev_PaymentTerminal.CashId}'")
                            End If
                        End If

                        Select Case Me.prp_dev_PaymentTerminal.PaymentTerminalModel

                            Case enm_PaymentTerminalModel.AxaPro,
                                 enm_PaymentTerminalModel.FiskalPro,
                                 enm_PaymentTerminalModel.FiskalProA8,
                                 enm_PaymentTerminalModel.GpEcr2,
                                 enm_PaymentTerminalModel.Printec

                                If prp_Communication.Port_Number > 0 OrElse String.IsNullOrEmpty(prp_Communication.TCP_HostName) Then
                                    tmpSB.Append(", port COM" & prp_Communication.Port_Number)
                                    If prp_Communication.Port_BaudRate <> 0 Then
                                        tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "b")
                                    End If
                                Else
                                    tmpSB.Append(", hostname '" & prp_Communication.TCP_HostName & "'")
                                    If prp_Communication.TCP_Port <> 0 Then
                                        tmpSB.Append(", port " & prp_Communication.TCP_Port)
                                    End If
                                End If

                            Case enm_PaymentTerminalModel.GpTom
                                tmpSB.AppendFormat(", Name '{0}'", dev_PaymentTerminal.MerchantCredential?.UserName)

                            Case enm_PaymentTerminalModel.Teya

                            Case enm_PaymentTerminalModel.SoftPlusTicket
                                tmpSB.AppendFormat(", Name '{0}'", dev_PaymentTerminal.MerchantCredential?.UserName)
                                tmpSB.AppendFormat(", URL '{0}'", dev_PaymentTerminal.CloudUrl?.Host)

                            Case enm_PaymentTerminalModel.Rictom
                                tmpSB.AppendFormat(", <configuration>")

                            Case enm_PaymentTerminalModel.FsInstantQrPay
                                'tmpSB.AppendFormat(", Certificate '{0}'", dev_PaymentTerminal.ClientCertificate)
                                tmpSB.AppendFormat(", IBAN '{0}'", dev_PaymentTerminal.BankIBAN)

                        End Select

                    Case enm_Devices_Type.FiskalModule


                        If Me.prp_dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.UniversalInterface Then
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)
                            If prp_Communication.Port_Number <> 0 Then
                                tmpSB.Append(", port COM" & prp_Communication.Port_Number)
                            End If
                            If prp_Communication.Port_BaudRate <> 0 Then
                                tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate)
                            End If
                            tmpSB.AppendLine(vbCrLf & "Ovládač:  " & prp_Communication.Path)

                        ElseIf prp_dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.Fiscal_UNI_SK Then

                        ElseIf prp_dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.EasyPosEKasa2019 Then
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)
                            tmpSB.Append(", eKasaDll sa nastavuje externe")

                        ElseIf prp_dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.eKasaPandora Then

                            Dim tmp_ECMCommunication$ = Exa.Basic.CodeDom.Enum.EnumFindItem(Of cls_d_FiscalModule.enm_eKasa_ECM_RunMode)(Me.dev_FiscalModule.eKasa_ECM_RunMode)
                            If tmp_ECMCommunication$ = String.Empty Then
                                tmp_ECMCommunication = "nenastavené"
                            End If
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)
                            tmpSB.AppendFormat(", Ovládač ECM: {0}", tmp_ECMCommunication$)

                            If Me.dev_FiscalModule.eKasa_ECM_RunMode = cls_d_FiscalModule.enm_eKasa_ECM_RunMode.ConnectToOtherPC Then
                                If Me.Communication.TCP_HostName <> String.Empty Then
                                    tmpSB.AppendFormat(", IP: {0}", Me.Communication.TCP_HostName)
                                Else
                                    tmpSB.AppendFormat(", IP: {0}", Me.Communication.TCP_IPAddress)
                                End If
                            End If


                        ElseIf Me.prp_dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.VRP_FinancnaSprava Then
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)
                            tmpSB.Append(", prihlas.meno '" & prp_Communication.Login_Name & "'")

                        ElseIf Me.prp_dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.Fiscal_UNI_CZ Then
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)


                        Else
                            tmpSB.Append("číslo " & Me.Communication.DeviceCommunicationNumber)
                            If prp_Communication.Port_Number > 0 OrElse String.IsNullOrEmpty(prp_Communication.TCP_HostName) Then
                                tmpSB.Append(", port COM" & prp_Communication.Port_Number)
                                If prp_Communication.Port_BaudRate <> 0 Then
                                    tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "b")
                                End If
                            Else
                                tmpSB.Append(", hostname '" & prp_Communication.TCP_HostName & "'")
                                If prp_Communication.TCP_Port <> 0 Then
                                    tmpSB.Append(", port " & prp_Communication.TCP_Port)
                                End If
                            End If
                        End If

                        If Me.Device_Code <> String.Empty Then
                            tmpSB.Append(", kód pokladnice: " & Me.Device_Code)
                        End If

                    Case enm_Devices_Type.PDA
                        tmpSB.Append("názov '" & prp_dev_PDA.Name & "'")
                        If prp_Communication.TCP_Port <> 0 Then
                            tmpSB.Append(", TCP IP port " & prp_Communication.TCP_Port)
                        End If


                    Case enm_Devices_Type.PID
                        tmpSB.Append("port COM" & prp_Communication.Port_Number)
                        If prp_Communication.Port_BaudRate <> 0 Then
                            tmpSB.Append(", rýchlosť " & prp_Communication.Port_BaudRate & "b")
                        End If

                    Case enm_Devices_Type.PrinterReceipt

                        tmpSB.Append("model " & CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(Exa.OBERON.Devices.enm_FiskalPrinter_Models), prp_dev_PrinterFiscal.Printer_Model, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription)))
                        tmpSB.Append(", odriadkovanie " & prp_dev_PrinterFiscal.PaperFeedLines)
                        tmpSB.Append(", orezávanie " & CStr(IIf(prp_dev_PrinterFiscal.PaperCut = True, "áno", "nie")))
                        tmpSB.Append(", zásuvka " & CStr(IIf(prp_dev_PrinterFiscal.CashDrawer_CanOpen = True, "áno (" &
                                CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(Exa.OBERON.Devices.FiscalPrinter.Driver_Common.enum_CashDrawer_CanOpen_PIN), prp_dev_PrinterFiscal.CashDrawer_CanOpen_PIN, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription)) & ")", "nie")))

                    Case enm_Devices_Type.PrinterKitchen
                        If prp_dev_PrinterKitchen.Name = Exa.OBERON.Devices.PrinterOrder.CONST_PrinterName_DirectPrint_SerialPort Then
                            tmpSB.Append("Sériový port: " & prp_dev_PrinterKitchen.PrinterSerialPortNumber)
                        ElseIf prp_dev_PrinterKitchen.Name = Exa.OBERON.Devices.PrinterOrder.CONST_PrinterName_DirectPrint_Ethernet Then
                            tmpSB.Append("IP: " & prp_dev_PrinterKitchen.PrinterIPAddress)
                        Else
                            tmpSB.Append("názov '" & prp_dev_PrinterKitchen.Name & "'")
                        End If
                        tmpSB.Append(", číslo " & prp_dev_PrinterKitchen.Number)
                        If prp_dev_PrinterKitchen.LineLenght = 48 Then
                            tmpSB.Append(", znakov: 48")
                        Else
                            tmpSB.Append(", znakov: 40")
                        End If
                        If prp_dev_PrinterKitchen.PaperFeedLines_Before <> 0 Then
                            tmpSB.Append(", odriadkovanie pred " & prp_dev_PrinterKitchen.PaperFeedLines_Before)
                        End If
                        If prp_dev_PrinterKitchen.PaperFeedLines_After <> 0 Then
                            tmpSB.Append(", odriadkovanie po " & prp_dev_PrinterKitchen.PaperFeedLines_After)
                        End If

                    Case enm_Devices_Type.DocumentReader

                        If Me.dev_DocumentReader.DocumentReaderModel = enm_DocumentReaderModel.Access_OCR31x Then
                            tmpSB.AppendLine("ovládač:  " & Exa.OBERON.Devices.DocumentReader.mod_DLL_ACCESS_IS_MSR.DLL_NAME)
                        Else
                            tmpSB.AppendLine("port COM" & prp_Communication.Port_Number)
                        End If

                    Case enm_Devices_Type.SignaturePad

                        tmpSB.AppendLine("Bez ďalších podrobností...")


                    Case enm_Devices_Type.None
                        '--- Nenastavené ---

                    Case Else

#If DEBUG = True Then
                        EXC.Throw("Nepodporovaný druh zariadenia.")
#End If

                End Select

                Dim tmpFinal$ = tmpSB.ToString
                If tmpFinal$ <> String.Empty Then
                    If tmpFinal$.Substring(0, 1) = "," Then
                        '--- String by nemal začínať čiarkou
                        tmpFinal$ = tmpFinal$.Substring(1).Trim
                    End If
                End If

                Return tmpFinal$

            End Get
        End Property

        ''' <summary>Názov prevádzky, ku ktorej patrí zariadenie (nepovinný údaj).</summary>
        Public Property CompanyBranchName() As String
            Get
                Return CStr(MyBase.Field("BranchName"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("BranchName") = value
            End Set
        End Property

        ''' <summary>Názov jedného alebo viacerých počítačov, na ktorých sa je možné k zariadeniu pripojiť. Ak sa používateľ pripája cez RDP, uvádza sa vo formáte napr. RDP: PC_Novak.</summary>
        Public Property Computers() As String()
            Get
                On Error Resume Next

                If CStr(MyBase.Field("Computers")) = String.Empty Then
                    Return New String() {}
                End If

                Return Exa.Basic.Strings.Convert_To_ArrayString(CStr(MyBase.Field("Computers")), Exa.Basic.Strings.enm_StringSeparator_UsingTypes.Fill, CChar("|"), u_ApplyTRIM:=True)

            End Get
            Set(ByVal value As String())
                On Error Resume Next

                MyBase.Field("Computers") = Exa.Basic.Strings.Convert_From_Array(u_Value:=value, u_SeparatorUsingType:=Exa.Basic.Strings.enm_StringSeparator_UsingTypes.Fill, u_Separator:="|", u_Ignore_StringEmpty:=True)

            End Set
        End Property

        ''' <summary>Názov jedného alebo viacerých počítačov, avšak sú uvádzané len také, na ktoré sa je možné pripojiť cez RDP. 
        ''' Zoznam sa odvodzuje zo štandardného zoznamu počítačov, avšak sú tu len také, u ktorých je uvedený prefix "RDP: " (tu sú však uvedené bez tohto prefixu).</summary>
        Public ReadOnly Property ComputersRDP() As String()
            Get

                On Error Resume Next

                If Me.Computers Is Nothing OrElse Me.Computers.Length = 0 Then
                    Return New String() {}
                End If

                Dim tmp_ComputersRDP As String()
                tmp_ComputersRDP = New String() {}

                For i As Integer = 0 To Me.Computers.Length - 1
                    Dim tmp_Str As String = Me.Computers(i)

                    If tmp_Str.IndexOf(CONST_RDP_SessionName_Prefix) >= 0 Then
                        '--- Názov počítača obsahuje daný prefix ---                
                        '--- Pridať do poľa ---
                        Dim tmp_ComputerName$ = tmp_Str.Substring(Device.CONST_RDP_SessionName_Prefix.Length)
                        ReDim Preserve tmp_ComputersRDP(tmp_ComputersRDP.Length)
                        tmp_ComputersRDP(tmp_ComputersRDP.Length - 1) = tmp_ComputerName$
                    End If
                Next

                Return tmp_ComputersRDP

            End Get
        End Property


        ''' <summary>Číslo databázovej tabuľky (formátované, napr. 001), ktoré reprezentuje tabuľku pokladničných dokladov pre dané zariadenie.</summary>
        Public Property TableNumber() As String
            Get
                Return CStr(MyBase.Field("DokladyTabulkaCislo"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("DokladyTabulkaCislo") = value
            End Set
        End Property

        ''' <summary>Kód zariadenia - používateľské číslo pridelené zariadeniu, napr. pri pokladniciach kód pokladnice (pôvodne sa uvádzalo ako DKP).</summary>
        Public Property Device_Code() As String
            Get
                Return CStr(MyBase.Field("DeviceCode"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("DeviceCode") = value
            End Set
        End Property

        ''' <summary>Výrobné číslo zariadenia (typu STRING).</summary>
        Public Property Device_ProductNumber() As String
            Get
                Return CStr(MyBase.Field("DeviceProductNumber"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("DeviceProductNumber") = value
            End Set
        End Property

        ''' <summary>Poznámka.</summary>
        Public Property Notice() As String
            Get
                Return CStr(MyBase.Field("Notice"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("Notice") = value
            End Set
        End Property

        ''' <summary>XML údaje záznamu. Obsahuje XML interné údaje podľa zariadenia daného typu.</summary>
        Friend Property XMLInternalData() As String
            Get
                Return CStr(MyBase.Field("XMLInternalData"))
            End Get
            Set(ByVal value As String)
                MyBase.Field("XMLInternalData") = value
            End Set
        End Property

        ''' <summary>Zariadenie vypnuté /dočasne nepoužívané/.</summary>
        Public Property Disable() As Boolean
            Get
                Return CBool(MyBase.Field("Disable"))
            End Get
            Set(ByVal value As Boolean)
                MyBase.Field("Disable") = value
            End Set
        End Property

        ''' <summary>Parametre/nastavenie určené pre konkrétny typ zariadenia. Ich nastavenie a použitie je závislé od ovládača. Ukladajú sa v XML štruktúre do DB sĺpca 'XMLInternalData'.</summary>
        Public Property Device_Params As New Dictionary(Of String, String)

        Friend prp_Communication As New cls_Communication
        ''' <summary>Nastavenie komunikácie - podľa typu zariadenia.</summary>
        Public ReadOnly Property Communication() As cls_Communication
            Get
                Return prp_Communication
            End Get
        End Property


        Private prp_dev_CashRegister As New cls_d_CashRegister
        ''' <summary>Registračné pokladnice.</summary>
        Public ReadOnly Property dev_CashRegister() As cls_d_CashRegister
            Get
                Return prp_dev_CashRegister
            End Get
        End Property


        Private prp_dev_FiscalModule As cls_d_FiscalModule
        ''' <summary>Fiškálne zariadenie.</summary>    
        Public ReadOnly Property dev_FiscalModule() As cls_d_FiscalModule
            Get
                Return prp_dev_FiscalModule
            End Get
        End Property



        Private prp_dev_PrinterFiscal As FiscalPrinter.Driver_Common
        ''' <summary>Tlačiareň pokladničných dokladov.</summary>
        Public ReadOnly Property dev_PrinterFiscal() As FiscalPrinter.Driver_Common
            Get
                Return prp_dev_PrinterFiscal
            End Get
        End Property


        Private prp_dev_PrinterKitchen As New cls_d_PrinterKitchen
        ''' <summary>Bonovacia tlačiareň.</summary>
        Public ReadOnly Property dev_PrinterKitchen() As cls_d_PrinterKitchen
            Get
                Return prp_dev_PrinterKitchen
            End Get
        End Property



        Private prp_dev_DisplayCustomer As New cls_d_DisplayCustomer
        ''' <summary>Zákaznícky displej.</summary>
        Public ReadOnly Property dev_DisplayCustomer() As cls_d_DisplayCustomer
            Get
                Return prp_dev_DisplayCustomer

            End Get
        End Property


        Private prp_dev_BarCode_Scanner As New cls_d_BarCode_Scanner
        ''' <summary>Snímač čiarového kódu.</summary>
        Public ReadOnly Property dev_BarCode_Scanner() As cls_d_BarCode_Scanner
            Get
                Return prp_dev_BarCode_Scanner
            End Get
        End Property


        Private prp_dev_PID As New cls_d_PID
        ''' <summary>Prístupové systémy, napr. snímač prístupových kľúčov.</summary>
        Public ReadOnly Property dev_PID() As cls_d_PID
            Get
                Return prp_dev_PID
            End Get
        End Property

        Private prp_dev_ElectronicScale As New cls_d_ElectronicScale
        ''' <summary>Elektronická váha.</summary>
        Public ReadOnly Property dev_ElectronicScale() As cls_d_ElectronicScale
            Get
                Return prp_dev_ElectronicScale
            End Get

        End Property

        Private prp_dev_DoorKey As New cls_d_DoorKey
        ''' <summary>Dverový zámok.</summary>
        Public ReadOnly Property dev_DoorKey() As cls_d_DoorKey
            Get
                Return prp_dev_DoorKey
            End Get
        End Property

        Private prp_dev_PriceLabels As New cls_d_PriceLabels
        ''' <summary>Elektronická cenovka.</summary>
        Public ReadOnly Property dev_PriceLabels() As cls_d_PriceLabels
            Get
                Return prp_dev_PriceLabels
            End Get
        End Property

        Private prp_dev_PDA As New cls_d_PDA
        ''' <summary>PDA zariadenia.</summary>
        Public ReadOnly Property dev_PDA() As cls_d_PDA
            Get
                Return prp_dev_PDA
            End Get
        End Property


        Private prp_dev_AttendanceTerminal As New cls_d_AttendanceTerminal
        ''' <summary>
        ''' Dochádzkový systém - terminál.
        ''' </summary>        
        Public ReadOnly Property dev_AttendanceTerminal As cls_d_AttendanceTerminal
            Get
                Return prp_dev_AttendanceTerminal
            End Get
        End Property


        Private prp_dev_PaymentTerminal As New cls_d_PaymentTerminal
        ''' <summary>
        ''' Platobný terminál
        ''' </summary>        
        Public ReadOnly Property dev_PaymentTerminal As cls_d_PaymentTerminal
            Get
                Return prp_dev_PaymentTerminal
            End Get
        End Property

        ''' <summary>
        ''' Čítačka dokladov (MRZ kódu) - čítanie pasov, preukazov totožnosti a podobne.
        ''' </summary>        
        Public ReadOnly Property dev_DocumentReader As New cls_d_DocumentReader


        ''' <summary>
        '''  Digitálna podpisová podložka.
        ''' </summary>        
        Public ReadOnly Property dev_SignaturePad As New cls_d_SignaturePad

#End Region

#Region " Function "

        Public Sub New(ByVal u_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration)

            On Error Resume Next

            prp_AppConfiguration = u_AppConfiguration

            prp_SaveBehavior = New cls_SaveBehavior

            prp_dev_PrinterFiscal = New FiscalPrinter.Driver_Common(prp_AppConfiguration)

            prp_dev_FiscalModule = New cls_d_FiscalModule(Me)

        End Sub


        ''' <summary>Načíta údaje z databázy - jeden záznam.</summary>
        ''' <param name="u_RowKeyValue">IDNum záznamu.</param>
        ''' <param name="u_LockRecord">Určuje či sa má záznam v databáze automaticky zamknúť.</param>
        Public Shadows Function _Load(ByVal u_RowKeyValue As Long, ByVal u_LockRecord As Boolean) As EXC.ExaException

            On Error Resume Next

            Dim myEx As EXC.ExaException

            _Load = EXC.GetDefault()

            myEx = MyBase.Record_Load(u_RowKeyValue, u_LockRecord)

            If myEx.Result = False Then
                _Load = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- načítať interné XML dáta   
            myEx = z_XMLInternalData_Load()
            If myEx.Result = False Then
                _Load = EXC.Get("Chyba pri načítaní interných XML údajov.", myEx)
                _Load.IsWarning = True
            End If

            _Load.Result = True

ExitFunction:

        End Function


        ''' <summary>Načíta údaje o jednom zariadení.</summary>
        ''' <param name="u_DeviceName">Názov zariadenia.</param>
        ''' <param name="u_DeviceType">Typ zariadenia.</param>
        Public Shadows Function _Load(ByVal u_DeviceName As String, ByVal u_DeviceType As enm_Devices_Type) As EXC.ExaException

            On Error Resume Next

            _Load = EXC.GetDefault()
            Dim myEx As EXC.ExaException

            If u_DeviceName = Nothing OrElse u_DeviceName = String.Empty Then
                _Load.Description = "Je potrebné zadať názov zariadenia."
                Exit Function
            End If

            Dim tmpRowFilter$ = String.Empty
            If u_DeviceType <> 0 Then
                '--- Je zadaný typ zariadenia ---
                tmpRowFilter$ = "ZariadenieDruh = " & CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_Devices_Type), u_DeviceType, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))
            End If

            myEx = MyBase.Record_Load(u_DeviceName, False, "Nazov", tmpRowFilter$)
            If myEx.Result = False Then
                _Load = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- načítať interné XML dáta   
            myEx = z_XMLInternalData_Load()
            If myEx.Result = False Then
                _Load = EXC.Get("Chyba pri načítaní interných XML údajov.", myEx)
                _Load.IsWarning = True
            End If

            _Load.Result = True

ExitFunction:


        End Function

        ''' <summary>
        ''' Načíta údaje položky z objektu riadku databázovej tabuľky, na položke nie je možné vykonávať zmeny.
        ''' </summary>        
        Public Shadows Function _Load(ByVal u_DataRow As System.Data.DataRow, Optional ByVal u_LoadIndependentInstance As Boolean = False) As Exa.Basic.Exceptions.ExaException

            On Error Resume Next

            Dim myEx As Exa.Basic.Exceptions.ExaException

            _Load = Exa.Basic.Exceptions.GetDefault()

            myEx = MyBase.Record_Load(u_DataRow, u_LoadIndependentInstance:=u_LoadIndependentInstance)
            If myEx.Result = False Then
                _Load = Exa.Basic.Exceptions.Get(myEx)
                GoTo ExitFunction
            End If

            '--- načítať interné XML dáta   
            myEx = z_XMLInternalData_Load()
            If myEx.Result = False Then
                _Load = EXC.Get("Chyba pri načítaní interných XML údajov.", myEx)
                _Load.IsWarning = True
            End If

            _Load.Result = True

ExitFunction:

        End Function

        ''' <summary>Nový záznam.</summary>
        ''' <param name="u_Device_Type">Typ /druh/ zariadenia - dáva sa z dôvodu default hodnôt</param>
        Public Shadows Function _New(ByVal u_Device_Type As enm_Devices_Type) As EXC.ExaException
            On Error Resume Next

            _New = EXC.GetDefault()

            Dim myEx As EXC.ExaException

            myEx = MyBase.Record_New()
            If myEx.Result = False Then
                _New = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- Načítať interné XML dáta - nastaví default hodnoty
            myEx = z_XMLInternalData_Load()


            Me.Device_Type = u_Device_Type

            '--- Aktualizovať pôvodné /originálne/ hodnoty novými
            MyBase.SetOriginalValues()

            _New.Result = True

ExitFunction:


        End Function


        ''' <summary>
        ''' Zapíše údaje do databázy. 
        ''' </summary>
        Public Shadows Function _Save() As EXC.ExaException
            'On Error Resume Next - Nie je možné používať kvôli lambda výrazom.

            _Save = EXC.GetDefault()

            Dim myEx As EXC.ExaException = Nothing
            Dim m_CommonManagement As Exa.Database.CommonManagement = Nothing

            Try
                Dim tmp_RecordState As Exa.Database.Factory.DataRecord.enm_RecordStateTypes

                Dim m_IsNameChanged As Boolean = Me.FieldInfo(DB.Zariadenia.Nazov).IsChanged
                Dim m_Device_Name_Original As String = CType(Me.FieldInfo(DB.Zariadenia.Nazov).Value_Original, String)

                '--- Zapamätať si stav recordu ---
                tmp_RecordState = MyBase.RecordState_Database

                '--- Špecialita - Názov modelu sa už nepoužíva (už je v DB číslo), ale zapísať názov len aby bol v databáze aktuálny
                MyBase.Row("ZariadenieTyp") = Me.Device_Model_Name


                '--- Uloženie hodnôt do fieldu ako XML data ---
                myEx = z_XMLInternalData_Save()
                If myEx.Result = False Then
                    _Save = EXC.Get(myEx)
                    GoTo ExitFunction
                End If

                '--- Zavolá zdedenú funkciu
                myEx = MyBase.Record_Save(enm_LockRecordTypes.Unlock)

                If myEx.Result = False Then
                    _Save = EXC.Get(myEx)
                    GoTo ExitFunction
                End If


                If tmp_RecordState = enm_RecordStateTypes.CreateNew Then
                    '--- Nový záznam ---

                    If Me.Device_Type = enm_Devices_Type.FiskalModule Then

                        '--- Je potrebné vygenerovať nové tabuľky pre uloženie pokladničných dokladov ---

                        'Otvorenie databázy.
                        m_CommonManagement = New Exa.Database.CommonManagement

                        m_CommonManagement._ConnectionSettings = prp_AppConfiguration._AppObjects._CommonData._ConnectionSettings.Clone

                        myEx = m_CommonManagement._ConnectionOpen()

                        If myEx.Result = False Then
                            _Save = EXC.Get("Chyba pri vytváraní databázových tabuliek.", myEx, myEx.ErrNumber)
                            GoTo ExitFunction
                        End If


                        'Načítanie zoznamu všetkých tabuliek.
                        Dim m_ExistTables_Database() As String = Nothing

                        myEx = m_CommonManagement.Table_GetList(m_ExistTables_Database, u_CharacterCasing:=CharacterCasing.Lower)

                        If myEx.Result = False Then
                            _Save = EXC.Get("Chyba pri vytváraní databázových tabuliek.", myEx, myEx.ErrNumber)
                            GoTo ExitFunction
                        End If


                        'Získanie tabuliek (len pokladničné doklady) s ktorými sa bude pracovať (zrýchli generovanie novej tabulky).
                        Dim m_TableName_Prefix$ = LCase(CONST_TableName_Bill_Headers)
                        Dim m_ExistTables_BillHeaders() As String = Array.FindAll(m_ExistTables_Database, Function(u As String) u.IndexOf(m_TableName_Prefix$) >= 0)


                        'Vygenerovanie čísla tabuľky, ktorá ešte v databáze neexistuje.
                        Dim m_TableNumber$ = Nothing

                        For i As Integer = 1 To 1000
                            m_TableNumber$ = Format(i, "000")

                            Dim m_TableName$ = String.Format("{0}{1}", CONST_TableName_Bill_Headers, m_TableNumber$)

                            If Array.IndexOf(m_ExistTables_BillHeaders, LCase(m_TableName$)) < 0 Then
                                'Aktuálne číslo tabuľky v databáze neexistuje, ukonči generovanie čísla.
                                Exit For
                            End If
                        Next

                        'Vytvor novú tabuľku.
                        myEx = CreateTableStructure_CashRegister(m_CommonManagement, m_TableNumber$)
                        If myEx.Result = False Then
                            _Save = EXC.Get("Chyba pri vytváraní databázových tabuliek.", myEx, myEx.ErrNumber)
                            GoTo ExitFunction
                        End If
                        m_CommonManagement._ConnectionClose()

                        '--- Potrebné generovať default dáta (typy výberov a vkladov) ---			
                        myEx = Exa.OBERON.Devices.Base.Device.WriteFiscalModuleCashTypesDefaultData(Me._AppConfiguration._AppObjects._CommonData, Me.IDNum)
                        If myEx.Result = False Then
                            _Save = EXC.Get("Chyba pri vytváraní databázových tabuliek.", myEx, myEx.ErrNumber)
                            GoTo ExitFunction
                        End If

                        'Nastav a ulož zariadenie. 
                        MyBase.Row("DokladyTabulkaCislo") = m_TableNumber$
                        Me.dev_FiscalModule.DailyBalanceID = 1      '--- Default ---

                        myEx = MyBase.Record_Save(enm_LockRecordTypes.Unlock)

                        If myEx.Result = False Then
                            _Save = myEx
                            GoTo ExitFunction
                        End If


                        '--- DEFAULT NASTAVENIA ---
                        If Me.Device_Type = enm_Devices_Type.FiskalModule AndAlso Me.lc_SaveBehavior_IgnoreDefaultSettings = False Then
                            '--- Fiškálne zariadenie

                            myEx = Me.dev_FiscalModule.CashRegisterOBERONSettings._Load(u_DeviceIDNum:=Me.IDNum)

                            If Me.dev_FiscalModule.FiscalModule_Model = enm_FiskalModule_Model.eKasaPandora Then
                                '--- Pri dennej uzávierke nenulovať hotovosť v Pokladnici OBERON
                                Me.dev_FiscalModule.CashRegisterOBERONSettings.DailyBalance_ResetCashBalance = False
                            End If

                            If Me.Device_Type = enm_Devices_Type.FiskalModule Then
                                '--- Nastavenie predvolenej šablóny fiškálneho modulu.
                                Me.dev_FiscalModule.CashRegisterOBERONSettings.IDNum_MessageTemplate = Me.z_Get_MessageTemplate_IDNum()
                            End If

                            myEx = Me.dev_FiscalModule.CashRegisterOBERONSettings._Save()

                        End If

                    End If

                    '----------------------------------
                    '--- Telemetry
                    '----------------------------------
                    Dim tmp_TelemetryItem As New Exa.OBERON.ApplicationEnvironment.Telemetry.TelemetryItem
                    tmp_TelemetryItem.TelemetryType = Exa.OBERON.ApplicationEnvironment.Telemetry.TelemetryTypes.enm_TelemetryTypes.OBERON_Company_DeviceAdd
                    tmp_TelemetryItem.ValueNum = 1
                    tmp_TelemetryItem.ValueStr = $"[{CInt(Me.Device_Type)}] {Me.Device_Model_Name}"
                    Me._AppConfiguration._AppObjects.Telemetry.AddItem(tmp_TelemetryItem)


                ElseIf tmp_RecordState = enm_RecordStateTypes.Editing Then

                    If m_IsNameChanged = True AndAlso Me.Device_Type = enm_Devices_Type.AttendanceTerminal Then

                        Dim m_NameOld$ = String.Format("|{0}|", m_Device_Name_Original)
                        Dim m_NameNew$ = String.Format("|{0}|", Me.Device_Name)

                        'Zariadenie bolo premenované - nájdi pracovníkov, ktorý ho majú priradený.
                        Dim m_SQLUpdate$ = String.Format("SELECT ID, {1} FROM {0} WHERE {1} IS NOT NULL AND {1} {2}",
                                                            DB.Wages_Employees.TableName,
                                                            "AttendaceTerminals",
                                                            DB_CONV.ToSQLStringLike(m_NameOld, Me.Object_CommonData))

                        Dim m_DataTable As DataTable = Nothing
                        Dim m_DataAdapter As Database.CommonDataObjects.CommonDataAdapter = Nothing

                        myEx = Me.Object_CommonData.ExecuteQuery(u_SQLQuery:=m_SQLUpdate,
                                                            u_CommandType:=CommandType.Text,
                                                            urf_CommonDataAdapter:=m_DataAdapter,
                                                            urf_DataTable:=m_DataTable,
                                                            u_FillLoadOption:=LoadOption.OverwriteChanges,
                                                            u_GenerateInsertCommand:=False, u_GenerateUpdateCommand:=True, u_GenerateDeleteCommand:=False,
                                                            u_CommandBuilderConflictOptions:=ConflictOption.OverwriteChanges)

                        If myEx.Result = False Then
                            _Save.SetWarning("Chyba pri aktualizovaní názvu terminálu v zozname pracovníkov.")
                        Else
                            'Nahraď meno priradeného terminálu všetkým pracovníkom
                            For Each e_Row As DataRow In m_DataTable.Rows
                                e_Row("AttendaceTerminals") = Replace(CStr(e_Row("AttendaceTerminals")), Find:=m_NameOld, Replacement:=m_NameNew)
                            Next
                            Dim m_UpdatedCount As Integer = m_DataAdapter.Update(m_DataTable)
                            If Err.Number <> 0 Then
                                _Save = EXC.Get("Chyba pri aktualizovaní názvu terminálu v zozname pracovníkov. ").ToWarning
                                'Elseif m_UpdatedCount > 0
                            End If
                        End If

                        If m_DataAdapter IsNot Nothing Then m_DataAdapter.Dispose()
                        m_DataAdapter = Nothing

                        If m_DataTable IsNot Nothing Then m_DataTable.Dispose()
                        m_DataTable = Nothing

                    End If

                    If m_IsNameChanged = True AndAlso (Me.Device_Type = enm_Devices_Type.FiskalModule Or Me.Device_Type = enm_Devices_Type.CashRegister) Then
                        'Aktualizovanie názvu pokladnice v knihe tržieb,
                        'pretože zariadenie (pokladnica) bolo premenované.
                        Dim m_SQLUpdate$ = String.Format("UPDATE {0} SET {1} = {2} WHERE {3} = {4}",
                                                     DB.Stock_CashRegister_DailyBalance,
                                                     DB.Stock_CashRegister_DailyBalance.CashRegister_Name,
                                                     DB_CONV.ToSQLString(Me.Device_Name, Me.Object_CommonData),
                                                     DB.Stock_CashRegister_DailyBalance.CashRegister_IDNum,
                                                     Me.IDNum)

                        myEx = Me.Object_CommonData.ExecuteQuery(m_SQLUpdate$)

                        If myEx.Result = False Then
                            _Save.SetWarning("Chyba pri aktualizovaní názvu pokladnice v knihe tržieb.")
                        End If
                    End If

                End If


                '--- Zápis bol OK ---
                _Save.Result = True



            Catch ex As Exception
                _Save = EXC.Get(ex)
            End Try

ExitFunction:

            If m_CommonManagement IsNot Nothing Then m_CommonManagement.Dispose()
            m_CommonManagement = Nothing

        End Function



        ''' <summary>
        ''' Odstráni záznam 
        ''' </summary>
        Public Shadows Function _Delete() As EXC.ExaException

            On Error Resume Next

            _Delete = EXC.GetDefault()

            Dim LANG_Function$ = ""
            Dim tmp_TableNum$ = String.Empty
            Dim tmp_Device_Type As enm_Devices_Type
            Dim tmp_Device_IDNum As Long

            Dim myEx As EXC.ExaException


            '--- Zapamätať si typ zariadenia, po vymazaní bude potrebné ho vedieť ---
            tmp_Device_Type = Me.Device_Type
            tmp_Device_IDNum = Me.IDNum

            If tmp_Device_Type = enm_Devices_Type.FiskalModule Then

                '--- Načítať nastavenia (aby sa mohli vymazať)
                myEx = Me.dev_FiscalModule.CashRegisterOBERONSettings._Load(Me.IDNum)
                If myEx.Result = False Then
                    _Delete = myEx
                    GoTo ExitFunction
                End If

                '--- Zistiť či na predvolaných účtoch tejto registračnej pokladnice nie sú položky ---
                Dim tmpSQL$ = "SELECT COUNT(" & CONST_TableName_Bill_Open_Items & ".ID) FROM " & CONST_TableName_Bill_Open_Items
                tmpSQL$ = tmpSQL$ & " INNER JOIN " & CONST_TableName_Bill_Open & " ON " & CONST_TableName_Bill_Open_Items & ".IDNum_BillOpen = " & CONST_TableName_Bill_Open & ".IDNum"
                tmpSQL$ = tmpSQL$ & " WHERE BillOpen_Default_IDNumDevice = " & Me.IDNum
                Dim tmpCount As Integer = 0
                prp_AppConfiguration._AppObjects._CommonData.ExecuteScalar(Of Integer)(tmpSQL$, tmpCount)
                If tmpCount <> 0 Then
                    '--- Na otvorených účtoch sú položky -
                    Dim LANG_1$ = "V registračnej pokladnici sú v priamom predaji (prípadne na otvorených účtoch) zadané položky, zariadenie nie je možné odobrať."
                    Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)
                    _Delete.Description = mText_1
                    GoTo ExitFunction
                End If


                '--- Vymazať tabuľky pre uloženie pokladničných dokladov - až po odstránení záznamu ---
                tmp_TableNum$ = CStr(MyBase.Field("DokladyTabulkaCislo"))

            End If

            '--- Zavolá zdedenú funkciu
            myEx = MyBase.Record_Delete

            If myEx.Result = False Then
                _Delete = myEx
                GoTo ExitFunction
            End If


            If tmp_Device_Type = enm_Devices_Type.FiskalModule Then

                '--- Odstrániť zostatky hotovosti ---
                'Dim tmpSQL$ = "DELETE FROM " & CONST_TableName_Stock_CashRegister_CashCurrent & " WHERE CashRegister_IDNum = " & tmpDevice_IDNum
                '--- DELETE * Nepoužívať, lebo na Microsoft SQL server to nechodí
                Dim tmpSQL$ = "DELETE FROM " & CONST_TableName_Stock_CashRegister_CashCurrent & " WHERE CashRegister_IDNum = " & tmp_Device_IDNum
                prp_AppConfiguration._AppObjects._CommonData.ExecuteQuery(tmpSQL$)

                '--- Odstrániť predvolené účty  ---
                tmpSQL$ = "DELETE FROM " & CONST_TableName_Bill_Open
                tmpSQL$ = tmpSQL$ & " WHERE BillOpen_Default_IDNumDevice = " & tmp_Device_IDNum
                prp_AppConfiguration._AppObjects._CommonData.ExecuteQuery(tmpSQL$)

                '--- Vymazať tabuľky pre uloženie pokladničných dokladov ---
                Dim tmpObjManagement As New Exa.Database.CommonManagement()

                tmpObjManagement._ConnectionSettings = prp_AppConfiguration._AppObjects._CommonData._ConnectionSettings
                tmpObjManagement._ConnectionOpen()

                tmpObjManagement.Table_Drop(CONST_TableName_Stock_CashRegister_Cash & tmp_TableNum$)
                tmpObjManagement.Table_Drop(CONST_TableName_BillPaymentTypes & tmp_TableNum$)
                tmpObjManagement.Table_Drop(CONST_TableName_Bill_Items & tmp_TableNum$)
                tmpObjManagement.Table_Drop(CONST_TableName_Bill_Headers & tmp_TableNum$)

                tmpObjManagement.Dispose()


                '-- DELETE CASHREGISTER BUTTONS PANLE SETTINGS --
                ': Vymaž nastavenia tlačidiel pravého panela pre toto zariadenia.
                tmpSQL$ = "DELETE FROM Stock_CashRegister_PanelSettings WHERE Device_IDNum = " & tmp_Device_IDNum
                myEx = Me.prp_AppConfiguration._AppObjects._CommonData.ExecuteQuery(tmpSQL$)

                '--- Typy výberov a vkladov hotovosti v pokladnici
                tmpSQL$ = "DELETE FROM Stock_CashRegister_CashTypes WHERE IDNumDevice = " & tmp_Device_IDNum
                myEx = Me.prp_AppConfiguration._AppObjects._CommonData.ExecuteQuery(tmpSQL$)

                '--- Odstrániť nastavenia ---
                Me.dev_FiscalModule.CashRegisterOBERONSettings._Delete()

            End If

            '--- Zápis bol OK ---
            _Delete.Result = True



ExitFunction:


        End Function


        ''' <summary>
        ''' Vytvorí súbor XML s nastaveniami pre CashRegister Universal Interface
        ''' </summary>
        ''' <param name="u_FilePath">Názov súboru XML</param>
        Public Function CashRegisterUniversal_XML_Export(ByVal u_FilePath As String,
                                      ByVal u_InputOutput_FileType As Exa.OBERON.ApplicationEnvironment.InputOutput.enm_XmlCommunication_FileType,
                                      ByVal u_Description As String) As EXC.ExaException

            On Error Resume Next
            CashRegisterUniversal_XML_Export = EXC.GetDefault

            Dim myEx As EXC.ExaException

            Dim tmp_XML_Document As System.Xml.XmlDocument = Nothing
            Dim XMLElamentParser As Exa.Basic.XML.XML_Element_Parser = Nothing

            myEx = Exa.OBERON.ApplicationEnvironment.InputOutput.XML.OBERONXmlDocument_Create(u_InputOutput_FileType,
                                                             "System",
                                                             "",
                                                             u_Description,
                                                             tmp_XML_Document)

            If myEx.Result = False Then
                CashRegisterUniversal_XML_Export = myEx
                GoTo ExitFunction
            End If

            Dim m_XElm As System.Xml.XmlElement = Nothing
            XMLElamentParser = New Exa.Basic.XML.XML_Element_Parser(tmp_XML_Document)

            XMLElamentParser.Settings.NotExistingElement_Create = True
            XMLElamentParser.Settings.Disable_Convert_XML_Text = False

            XMLElamentParser.SetParentElement("/" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_RootNodeName)

            '--- Vytvoriť DATA
            XMLElamentParser.SetNodeValue(Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_SectionName_Data, "", True)

            XMLElamentParser.SetParentElement("/" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_RootNodeName & "/" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_SectionName_Data)

            XMLElamentParser.SetNodeValue("DeviceCommunicationNumber", Me.Communication.DeviceCommunicationNumber, True)
            XMLElamentParser.SetNodeValue("CashRegister_PLU_Max", Me.Communication.CashRegister_PLU_Max, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_WorkingDirectory", Me.Communication.CashRegister_Universal_WorkingDirectory, True)

            Dim tmp_Str$ = String.Empty
            tmp_Str$ = CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(cls_Communication.enm_Text_Encoding), Me.Communication.TextEncoding, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))
            XMLElamentParser.SetNodeValue("CashRegister_Universal_TextEncoding", tmp_Str$, True)

            XMLElamentParser.SetNodeValue("CashRegister_Universal_ExecutableFile_PLURead", Me.Communication.CashRegister_Universal_ExecutableFile_PLURead, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_ExecutableFile_PLUWrite", Me.Communication.CashRegister_Universal_ExecutableFile_PLUWrite, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_ExecutableFile_PLUBalance", Me.Communication.CashRegister_Universal_ExecutableFile_PLUBalance, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_ExecutableFile_DailyBalance", Me.Communication.CashRegister_Universal_ExecutableFile_DailyBalance, True)

            XMLElamentParser.SetNodeValue("CashRegister_Universal_ExecutableFile_Journal", Me.Communication.CashRegister_Universal_ExecutableFile_Journal, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_ExecutableFile_Journal_Move", Me.Communication.CashRegister_Universal_ExecutableFile_Journal_Move, True)


            '--- Source code sú uložené do CDATA ----
            XMLElamentParser.SetNodeValue("CashRegister_Universal_SourceCode_PLURead", Me.Communication.CashRegister_Universal_SourceCode_PLURead, True, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_SourceCode_PLUWrite", Me.Communication.CashRegister_Universal_SourceCode_PLUWrite, True, True)
            XMLElamentParser.SetNodeValue("CashRegister_Universal_SourceCode_Errors", Me.Communication.CashRegister_Universal_SourceCode_Errors, True, True)

            If XMLElamentParser.Log.Error_Count <> 0 Then
                CashRegisterUniversal_XML_Export.Description = "Chyba pri vytváraní XML súboru." & vbCrLf & XMLElamentParser.Log.Errors_ToString
                GoTo ExitFunction
            End If

            Err.Clear()
            tmp_XML_Document.Save(u_FilePath)
            If Err.Number <> 0 Then
                CashRegisterUniversal_XML_Export.Description = Err.Description
                GoTo ExitFunction
            End If

            CashRegisterUniversal_XML_Export.Result = True

ExitFunction:

            If XMLElamentParser IsNot Nothing Then
                XMLElamentParser = Nothing
            End If

        End Function

        ''' <summary>
        ''' Načíta súbor XML s nastaveniami pre CashRegister Universal Interface
        ''' </summary>
        ''' <param name="u_FilePath">Názov súboru XML</param>
        Public Function CashRegisterUniversal_XML_Import(ByVal u_FilePath As String) As EXC.ExaException

            On Error Resume Next
            CashRegisterUniversal_XML_Import = EXC.GetDefault

            Dim myEx As EXC.ExaException

            Dim tmp_XMLDoc As System.Xml.XmlDocument = Nothing
            Dim tmp_XMLNode As System.Xml.XmlElement = Nothing
            Dim tmp_XMLElementParser As Exa.Basic.XML.XML_Element_Parser = Nothing

            Dim tmp_HeaderData As Exa.OBERON.ApplicationEnvironment.InputOutput.XML.stc_XML_OberonHeader = Nothing
            myEx = Exa.OBERON.ApplicationEnvironment.InputOutput.XML.OBERONXmlDocument_Load(u_FilePath,
                                                                                ApplicationEnvironment.InputOutput.enm_XmlCommunication_FileType.Device_CashRegister_UniversalInterface_Settings,
                                                                                tmp_XMLDoc,
                                                                                tmp_HeaderData)
            If myEx.Result = False Then
                CashRegisterUniversal_XML_Import = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- Test na typ dát v súbore
            If CInt(tmp_HeaderData.DocumentType) <> Exa.OBERON.ApplicationEnvironment.InputOutput.enm_XmlCommunication_FileType.Device_CashRegister_UniversalInterface_Settings Then
                CashRegisterUniversal_XML_Import.Description = "Súbor importu nie je súbor nastavenia komunikácie pre '" & Me.Device_Model_Name & "'." & vbCrLf & vbCrLf & "Súbor obsahuje údaje:" & vbCrLf & tmp_HeaderData.DocumentTypeText
                CashRegisterUniversal_XML_Import.ExceptionType = EXC.ExaException.enm_ExceptionTypes.Validation
                GoTo ExitFunction
            End If

            '---------------------
            '--- Načítať na DATA
            '---------------------
            tmp_XMLNode = CType(tmp_XMLDoc.SelectSingleNode("/" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_RootNodeName & "/" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_SectionName_Data), Xml.XmlElement)
            If tmp_XMLNode Is Nothing Then
                '--- Neexistuje element s údajmi
                CashRegisterUniversal_XML_Import.Description = "V súbore importu chýba XML element '" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_SectionName_Data & "'."
                GoTo ExitFunction
            End If

            tmp_XMLElementParser = New Exa.Basic.XML.XML_Element_Parser(tmp_XMLNode)

            '--- Načítať údaje ---
            tmp_XMLElementParser.GetNodeValue(Of String)("DeviceCommunicationNumber", "", Me.Communication.DeviceCommunicationNumber, True)
            tmp_XMLElementParser.GetNodeValue(Of Integer)("CashRegister_PLU_Max", 0, Me.Communication.CashRegister_PLU_Max, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_WorkingDirectory", "", Me.Communication.CashRegister_Universal_WorkingDirectory, True)

            Dim tmp_Str$ = String.Empty : Me.Communication.TextEncoding = cls_Communication.enm_Text_Encoding.Default
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_TextEncoding", "Default", tmp_Str$, True)
            Me.Communication.TextEncoding = CType(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(cls_Communication.enm_Text_Encoding), tmp_Str$, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue), cls_Communication.enm_Text_Encoding)

            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_ExecutableFile_PLURead", "", Me.Communication.CashRegister_Universal_ExecutableFile_PLURead, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_ExecutableFile_PLUWrite", "", Me.Communication.CashRegister_Universal_ExecutableFile_PLUWrite, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_ExecutableFile_PLUBalance", "", Me.Communication.CashRegister_Universal_ExecutableFile_PLUBalance, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_ExecutableFile_DailyBalance", "", Me.Communication.CashRegister_Universal_ExecutableFile_DailyBalance, True)

            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_ExecutableFile_Journal", "", Me.Communication.CashRegister_Universal_ExecutableFile_Journal, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_ExecutableFile_Journal_Move", "", Me.Communication.CashRegister_Universal_ExecutableFile_Journal_Move, True)

            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_SourceCode_PLURead", "", Me.Communication.CashRegister_Universal_SourceCode_PLURead, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_SourceCode_PLUWrite", "", Me.Communication.CashRegister_Universal_SourceCode_PLUWrite, True)
            tmp_XMLElementParser.GetNodeValue(Of String)("CashRegister_Universal_SourceCode_Errors", "", Me.Communication.CashRegister_Universal_SourceCode_Errors, True)

            If tmp_XMLElementParser.Log.Error_Count <> 0 Then
                '--- Dať len varovanie
                CashRegisterUniversal_XML_Import.Description = "Pri importe údajov sa vyskytli chyby (celkom " & tmp_XMLElementParser.Log.Error_Count & "'." & vbCrLf & tmp_XMLElementParser.Log.Errors_ToString
                CashRegisterUniversal_XML_Import.IsWarning = True
            End If


            '------------------------------
            '--- Načítať info o vytvorení
            '------------------------------
            tmp_XMLNode = CType(tmp_XMLDoc.SelectSingleNode("/" & Exa.OBERON.ApplicationEnvironment.InputOutput.XML.CONST_XML_RootNodeName & "/Created"), Xml.XmlElement)
            If tmp_XMLNode Is Nothing Then
                '--- Súbor neobsahuje informáciu o autorovi
                CashRegisterUniversal_XML_Import.ExceptionData = "Model pokladnice:   " & "Neznáme"
                CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & vbCrLf & "Vytvoril:   " & "Neznáme"
                CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & vbCrLf & "Dátum vytvorenia:   " & tmp_HeaderData.DocumentDateTime
            Else
                '--- Existuje element s údajmi - toto je originál súboru

                CashRegisterUniversal_XML_Import.ExceptionData = String.Empty

                tmp_XMLElementParser = New Exa.Basic.XML.XML_Element_Parser(tmp_XMLNode)

                '--- Načítať údaje ---
                Dim tmpStr$ = String.Empty

                '--- Model pokladnice
                CashRegisterUniversal_XML_Import.ExceptionData = "Model pokladnice:   "
                tmp_XMLElementParser.GetNodeValue(Of String)("CashRegisterModel", "", tmpStr$, False)
                If tmpStr$ = String.Empty Then
                    CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & "Neznámy"
                Else
                    CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & tmpStr$
                End If

                '--- Vytvoril
                CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & vbCrLf & "Vytvoril:   "
                tmp_XMLElementParser.GetNodeValue(Of String)("Name", "", tmpStr$, False)
                If tmpStr$ = String.Empty Then
                    CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & "Neznáme"
                Else
                    CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & tmpStr$
                End If


                '--- Dátum vytvorenia
                CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & vbCrLf & "Dátum vytvorenia:   "
                tmp_XMLElementParser.GetNodeValue(Of String)("Date", "", tmpStr$, False)
                If tmpStr$ = String.Empty Then
                    CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & tmp_HeaderData.DocumentDateTime & vbCrLf
                Else
                    CashRegisterUniversal_XML_Import.ExceptionData = CashRegisterUniversal_XML_Import.ExceptionData & tmpStr$ & vbCrLf
                End If

            End If



            CashRegisterUniversal_XML_Import.Result = True

ExitFunction:

            If tmp_XMLElementParser IsNot Nothing Then
                tmp_XMLElementParser = Nothing
            End If

        End Function
        ''' <summary>
        ''' Funkcia exportuje základné info zariadenia v elemente "Device".
        ''' </summary>
        ''' <param name="u_XMLElement"></param>
        ''' <returns></returns>
        ''' <remarks></remarks>
        Public Function Export_ToXML(ByVal u_XMLElement As System.Xml.XmlElement) As Exa.Basic.Exceptions.ExaException

            On Error Resume Next

            Export_ToXML = EXC.GetDefault

            Dim m_EE As Exa.Basic.Exceptions.ExaException = Exa.Basic.Exceptions.GetDefault
            Dim m_XMLParser As New Exa.Basic.XML.XML_Element_Parser(u_XMLElement)

            m_EE = m_XMLParser.SetNodeValue("Device_Model_Name", Me.Device_Model_Name)

            m_EE = m_XMLParser.SetNodeValue("Device_Model_Num", Me.Device_Model_Num)

            m_EE = m_XMLParser.SetNodeValue("Device_Name", Me.Device_Name)

            m_EE = m_XMLParser.SetNodeValue("Device_Type", Me.Device_Type)

            m_EE = m_XMLParser.SetNodeValue("Device_Info", Me.Device_Info)

            m_EE = m_XMLParser.SetNodeValue("TableNumber", Me.TableNumber)

            '--- Záverečný test na chyby -- 
            If m_XMLParser.Log.Error_Count <> 0 Then
                '--- Pri exporte sa vyskytli chyby
                Dim tmp_Str$ = "Pri tvorbe XML dokumentu sa vyskytli chyby (celkom {0})."
                tmp_Str$ = String.Format(tmp_Str$, m_XMLParser.Log.Error_Count)
                Export_ToXML.Description = tmp_Str$ & vbCrLf & vbCrLf & m_XMLParser.Log.Errors_ToString
                GoTo ExitFunction
            End If

            Export_ToXML.Result = True

ExitFunction:

            If m_XMLParser IsNot Nothing Then
                m_XMLParser.Dispose()
                m_XMLParser = Nothing
            End If


        End Function

        ''' <summary>
        ''' Funkcia importuje základné info zariadenia v elemente "Device".
        ''' </summary>
        ''' <param name="u_XmlElement"></param>
        ''' <returns></returns>
        ''' <remarks></remarks>
        Public Function Import_ToXML(ByVal u_XmlElement As Xml.XmlElement, urf_XmlParser As Exa.Basic.XML.XML_Element_Parser) As Exa.Basic.Exceptions.ExaException

            On Error Resume Next

            Import_ToXML = EXC.GetDefault
            Dim m_sValue As String = String.Empty
            Dim m_EE As Exa.Basic.Exceptions.ExaException = Exa.Basic.Exceptions.GetDefault
            Dim tmp_XMLElementParser As Exa.Basic.XML.XML_Element_Parser = Nothing

            '--- Vytvoriť lokálny parser (z dôvodu log-ovania chýb) 
            tmp_XMLElementParser = New Exa.Basic.XML.XML_Element_Parser
            tmp_XMLElementParser.InitializeNew(urf_XmlParser)
            tmp_XMLElementParser.SetParentElement(u_XmlElement)


            m_EE = tmp_XMLElementParser.GetNodeValue(Of String)("Device_Model_Name", "", Me.Device_Model_Name, False)

            m_EE = tmp_XMLElementParser.GetNodeValue(Of Integer)("Device_Model_Num", 0, Me.Device_Model_Num, False)

            m_EE = tmp_XMLElementParser.GetNodeValue(Of String)("Device_Name", "", Me.Device_Name, False)

            m_EE = tmp_XMLElementParser.GetNodeValue(Of String)("Device_Info", "", Me.Device_Info, False)

            m_EE = tmp_XMLElementParser.GetNodeValue(Of String)("TableNumber", "", Me.TableNumber, False)

            '--- Device_Type ---
            m_EE = tmp_XMLElementParser.GetNodeValue(Of Devices.enm_Devices_Type)("Device_Type", 0, Me.Device_Type, False)

            '--- Záverečný test na chyby -- 
            If tmp_XMLElementParser.Log.Error_Count <> 0 Then
                '--- Pri exporte sa vyskytli chyby
                Dim tmp_Str$ = "Pri tvorbe XML dokumentu sa vyskytli chyby (celkom {0})."
                tmp_Str$ = String.Format(tmp_Str$, tmp_XMLElementParser.Log.Error_Count)
                Import_ToXML.Description = tmp_Str$ & vbCrLf & vbCrLf & tmp_XMLElementParser.Log.Errors_ToString
                GoTo ExitFunction
            End If

            Import_ToXML.Result = True

ExitFunction:

        End Function

#End Region

#Region " Private methods "

        Public Enum enumValidation_ArePropertiesValuesValid

            ''' <summary>
            ''' Neznáma /nenastavená/ chyba
            ''' </summary>	
            None = 0

            ''' <summary>
            ''' Nejaká chyba, napr. objekt nie je nastavený, chýba connection a podobne
            ''' </summary>	
            Err = 1

            ''' <summary>
            ''' Nie je zadané IDNum
            ''' </summary>	
            IDNum = 10

            ''' <summary>
            ''' Nie je zadaný názov alebo názov už existuje
            ''' </summary>	
            Name = 11

            ''' <summary>
            ''' Nie je zadaný sklad alebo už existuje
            ''' </summary>	
            Stock = 12

            ''' <summary>
            ''' Nie je zadané predajné miesto.
            ''' </summary>	
            SalePoint = 13

            ''' <summary>
            ''' Nie je zadaná hladina predajnej ceny
            ''' </summary>	
            PriceLevel = 15

            ''' <summary>
            ''' Nie je zadaný typ zariadenia
            ''' </summary>	
            Device_Type = 21

            ''' <summary>
            ''' Nie je zadaný model zariadenia
            ''' </summary>	
            Device_Model = 22

            CashRegister_Universal_WorkingDirectory = 51


        End Enum

        ''' <summary>
        ''' Validácia /kontrola/ zadaných údajov pred uložením ---
        ''' </summary>
        Private Function z_Validation_ArePropertiesValuesValid(ByVal u_Action As enm_Validation_ActionTypes) As EXC.ExaException

            On Error Resume Next

            z_Validation_ArePropertiesValuesValid = EXC.GetDefault()

            Dim tmpSQL$
            Dim myEx As EXC.ExaException


            '--- Test na korektnosť nastavenia class-u
            myEx = Me._CheckStatus()
            If myEx.Result = False Then
                z_Validation_ArePropertiesValuesValid = EXC.Get(myEx)
                Exit Function
            End If

            If Me.IDNum = 0 Then
                '--- Nie je zadaný názov ---
                Dim LANG_1$ = "Je potrebné zadať IDNum."
                Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)
                z_Validation_ArePropertiesValuesValid = EXC.Get(mText_1$, enumValidation_ArePropertiesValuesValid.IDNum)
                Exit Function
            End If

            If u_Action = enm_Validation_ActionTypes.Delete Then
                '--- Pri mazaní už viac netestovať
                GoTo EndFunction
            End If

            If Me.Device_Name = String.Empty Or Len(Me.Device_Name) = 0 Then
                '--- Nie je zadaný názov ---
                Dim LANG_1$ = "Je potrebné zadať názov zariadenia."
                Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)
                z_Validation_ArePropertiesValuesValid = EXC.Get(mText_1$, EXC.ExaException.enm_ExceptionTypes.Validation, enumValidation_ArePropertiesValuesValid.Name)
                Exit Function
            End If

            If Me.Device_Type = 0 Then
                '--- Nie je zadaný typ zariadenia ---
                Dim LANG_1$ = "Je potrebné určiť typ zariadenia."
                Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)
                z_Validation_ArePropertiesValuesValid = EXC.Get(mText_1$, EXC.ExaException.enm_ExceptionTypes.Validation, enumValidation_ArePropertiesValuesValid.Device_Type)
                Exit Function
            End If


            If Me.Device_Model_Num = 0 Then
                '--- Nie je zadaný model zariadenia ---
                Dim LANG_1$ = "Je potrebné určiť model zariadenia."
                Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)
                z_Validation_ArePropertiesValuesValid = EXC.Get(mText_1$, EXC.ExaException.enm_ExceptionTypes.Validation, enumValidation_ArePropertiesValuesValid.Device_Model)
                Exit Function
            End If


            If Me.Device_Type = enm_Devices_Type.FiskalModule Then
                '--- Fiškálne moduly

                '--- Default cesta pre virtuálny fiškál - pozor ! - treba aj v nastaveniach default vo validácii
                If Me.Device_Model_Num = enm_FiskalModule_Model.Fiscal_UNI_SK _
                    OrElse Me.Device_Model_Num = enm_FiskalModule_Model.Fiscal_UNI_CZ Then

                    If prp_Communication.Path = Nothing OrElse prp_Communication.Path = String.Empty OrElse prp_Communication.Path.Length < 3 Then
                        Dim tmp_DirectoryName As String
                        tmp_DirectoryName = Exa.Basic.IO.Directory.GetValidDirectoryName(Me.Device_Model_Name, u_RemoveDiacritical:=True)
                        tmp_DirectoryName = tmp_DirectoryName.Replace(" ", "") '--- Odstrániť medzery
                        prp_Communication.Path = IO.Path.Combine(prp_AppConfiguration.Common.Directory.DATA_System_Fiscal, tmp_DirectoryName) & "\"
                    End If

                End If


            ElseIf Me.Device_Type = enm_Devices_Type.CashRegister Then
                '--- Registračné pokladnice

                If Me.Device_Model_Num = enm_CashRegister_Model.CashRegister_Universal Then
                    '--- Cash Register Universal - nastaviť Default

                    If Me.RecordState_Database = enm_RecordStateTypes.CreateNew Then
                        '--- Importovať nastavenia používateľských skryptov z default XML súboru 
                        Dim tmp_FilePath$ = IO.Path.Combine(Me._AppConfiguration.Common.Directory.OBERON_Temp, "CashRegister_Universal_Interface.xml")
                        If IO.File.Exists(tmp_FilePath$) = True Then
                            Exa.Basic.IO.Files.DeleteFile(tmp_FilePath$)
                        End If

                        Dim FS As IO.FileStream
                        Dim SR As IO.StreamWriter

                        Err.Clear()
                        FS = New IO.FileStream(tmp_FilePath$, IO.FileMode.Create)
                        SR = New IO.StreamWriter(FS, System.Text.Encoding.Default)
                        SR.Write(My.Resources.CashRegister_Universal_Interface)
                        SR.Flush()
                        SR.Close()
                        FS.Close()

                        Me.CashRegisterUniversal_XML_Import(tmp_FilePath$)

                        '--- Pracovný adresár - dať podľa názvu pokladnice
                        prp_Communication.CashRegister_Universal_WorkingDirectory = IO.Path.Combine(prp_AppConfiguration.Common.Directory.DATA_System_CashRegister, Me.Device_Model_Name & "\" & Me.Device_Name) & "\"


                    End If


                End If

            End If


            '----------------------------------------------------------------------------
            '--- Test či v databáze uz neexistuje záznam s týmto názvom
            '----------------------------------------------------------------------------	
            myEx = MyBase.Validation_CheckForExistValue(Me.Device_Name, "Nazov", DB.Zariadenia.ZariadenieDruh & " = " & CInt(Me.Device_Type))
            If myEx.Result = False Then
                '--- Záznam už existuje alebo chyba ---
                '--- V databáze už existuje záznam s týmto názvom ---	 
                Dim LANG_1$ = "V evidencii už existuje zariadenie s názvom '{0}', zadajte iný názov."
                Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)
                mText_1$ = String.Format(mText_1$, Me.Device_Name)
                z_Validation_ArePropertiesValuesValid = EXC.Get(mText_1$, enumValidation_ArePropertiesValuesValid.Name)
                GoTo ExitFunction
            End If

EndFunction:

            z_Validation_ArePropertiesValuesValid.Result = True

ExitFunction:




        End Function

        Private Function z_Get_MessageTemplate_IDNum() As Long
            Dim myEx As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_TopReferenceEvArgs As Exa.OBERON.ApplicationEnvironment.AppObjects.cls_TopReferenceUniversalArgument = Nothing

            Try

                '--- Dictionary, ktorý obsahuje názov a IDNum šablóny.
                Dim m_MessageTemplate_Dictionary As Dictionary(Of String, Long) = Nothing

                '--- Návratová hodnota v ktorej sa vráti Dictionary zo zavolanej udalosti.
                Dim tmp_ReturnedObject As Object = Nothing

                m_TopReferenceEvArgs = New Exa.OBERON.ApplicationEnvironment.AppObjects.cls_TopReferenceUniversalArgument(ApplicationEnvironment.AppObjects.cls_TopReferenceUniversalArgument.enm_TopReferenceCommandArgument.CashRegisterOBERON_GetMessageTemplates)

                '--- Vyvolanie udalosti, v ktorej sa načíta zoznam šablón a vrátia sa ich názvy a IDNum. 
                Me._AppConfiguration._AppObjects.on_ev_TopReference(m_TopReferenceEvArgs, tmp_ReturnedObject, myEx)
                If myEx.Result = False Then
                    '--- Chyba, pri načítavaní zoznamu šablón a vráteniu potrebných údajov, vrátim 0.
                    Return 0
                End If

                '--- Pretypovanie vráteného zoznamu.
                m_MessageTemplate_Dictionary = TryCast(tmp_ReturnedObject, Dictionary(Of String, Long))

                If m_MessageTemplate_Dictionary Is Nothing OrElse m_MessageTemplate_Dictionary.Count <= 0 Then
                    '--- Zoznam šablón je prázdny, vrátim 0.
                    Return 0
                End If

                '--- Vrátenie IDNum prvej šablóny.
                Return m_MessageTemplate_Dictionary.Values(0)

            Catch ex As Exception
                Return 0
            Finally
                m_TopReferenceEvArgs = Nothing
            End Try
        End Function


        Private Sub z_SetDeviceModelEnumToDevStructure(ByVal u_DeviceModelNumber As Integer)

            Try

                Select Case Me.Device_Type

                    Case enm_Devices_Type.BarCodeScanner
                        dev_BarCode_Scanner.prp_BarCodeScannerModel = CType(u_DeviceModelNumber, enm_BarCodeScannerModel)

                    Case enm_Devices_Type.CashRegister
                        dev_CashRegister.prp_CashRegister_Model = CType(u_DeviceModelNumber, enm_CashRegister_Model)

                    Case enm_Devices_Type.FiskalModule
                        dev_FiscalModule.prp_FiscalModule_Model = CType(u_DeviceModelNumber, enm_FiskalModule_Model)

                        '--- Špecialita
                        'If Me.Device_Model_Num = enm_FiskalModule_Model.Fiscal_UNI_SK OrElse
                        '        Me.Device_Model_Num = enm_FiskalModule_Model.Fiscal_UNI_CZ Then
                        '    '--- Default cesta pre virtuálny fiškál - pozor ! - treba aj vo validácii
                        '    If prp_Communication.Path = Nothing OrElse prp_Communication.Path = String.Empty OrElse prp_Communication.Path.Length < 3 Then
                        '        tmp_DirectoryName = tmp_DirectoryName.Replace(" ", "") '--- Odstrániť medzery
                        '        prp_Communication.Path = IO.Path.Combine(prp_AppConfiguration.Common.Directory.DATA_System_Fiscal, Me.Device_Model_Name) & "\"
                        '    End If
                        'End If

                    Case enm_Devices_Type.PrinterReceipt
                        dev_PrinterFiscal.Printer_Model = CType(u_DeviceModelNumber, enm_FiskalPrinter_Models)

                    Case enm_Devices_Type.PrinterKitchen
                        dev_PrinterKitchen.prp_Model = CType(u_DeviceModelNumber, enm_PrinterKitchen_Model)

                    Case enm_Devices_Type.DisplayCustomer
                        dev_DisplayCustomer.prp_DisplayCustomerModel = CType(u_DeviceModelNumber, enm_DisplayCustomerModel)

                    Case enm_Devices_Type.ElectronicScale
                        dev_ElectronicScale.prp_ElectronicScaleModel = CType(u_DeviceModelNumber, enm_ElectronicScaleModel)

                    Case enm_Devices_Type.DoorKey
                        dev_DoorKey.prp_DoorKey_Model = CType(u_DeviceModelNumber, enm_DoorKey_Model)

                    Case enm_Devices_Type.PID
                        dev_PID.prp_PID_Model = CType(u_DeviceModelNumber, enm_PID_Model)

                    Case enm_Devices_Type.PDA
                        dev_PDA.PDA_Model = CType(u_DeviceModelNumber, enm_PDA_Model)

                    Case enm_Devices_Type.AttendanceTerminal
                        dev_AttendanceTerminal.prp_AttendanceTerminalModel = CType(u_DeviceModelNumber, enm_AttendanceTerminalModel)

                    Case enm_Devices_Type.PaymentTerminal
                        dev_PaymentTerminal.prp_PaymentTerminalModel = CType(u_DeviceModelNumber, enm_PaymentTerminalModel)

                    Case enm_Devices_Type.DocumentReader
                        dev_DocumentReader.prp_DocumentReaderModel = CType(u_DeviceModelNumber, enm_DocumentReaderModel)

                    Case enm_Devices_Type.SignaturePad
                        dev_SignaturePad.prp_Model = CType(u_DeviceModelNumber, enm_SignaturePadModel)

                    Case enm_Devices_Type.PriceLabels
                        dev_PriceLabels.prp_PriceLabelsModel = CType(u_DeviceModelNumber, enm_PriceLabelsModel)

                    Case enm_Devices_Type.None
                        '--- Nezadaný typ zariadenia

                    Case Else

                        '--- Nemôže sa tu generovať chyba
#If DEBUG = True Then
                        EXC.Throw("Chyba pri nastavení modelu zariadenia, neznámy typ zariadenia '" & Me.Device_Type & "'.")
#End If

                End Select


            Catch ex As Exception

                EXC.Get($"z_SetDeviceModelEnumToDevStructure error:  {ex.Message}")

            End Try


        End Sub




#End Region

#Region " Zdedené property, metódy a ďalšie objekty "



        Public Overrides ReadOnly Property _RecordSettings() As Database.Factory.DataRecord.stc_RecordSettings
            Get
                Return New Database.Factory.DataRecord.stc_RecordSettings(prp_AppConfiguration._AppObjects._CommonData, CONST_TableName_Devices, prp_AppConfiguration._AppObjects._UserInfo, "IDNum")
            End Get
        End Property

        Public Overrides ReadOnly Property Validation_ArePropertiesValuesValid(ByVal u_Action As enm_Validation_ActionTypes) As EXC.ExaException
            Get
                Return z_Validation_ArePropertiesValuesValid(u_Action)
            End Get
        End Property

        Protected Overrides ReadOnly Property FieldsSettings() As Database.Factory.DataRecord.cls_FieldsSettingsCollection
            Get
                Dim m_FieldsSettings As Database.Factory.DataRecord.cls_FieldsSettingsCollection = MyBase.FieldsSettings

                m_FieldsSettings.Add("IDNum", Database.Viewing.DataViewObjects.Column.enm_AutoIncrementTypes.Manual_Max)

                Return m_FieldsSettings

            End Get
        End Property


        Private Sub Device_ev_RecordColumns_SetValues(ByVal e As Database.Factory.DataRecord.cls_RecordColumnSetValueEventArgs) Handles Me.ev_RecordColumns_SetValues

            On Error Resume Next
            Dim tmp_Default_TCPIP_Port As Long = 0

            Dim myEx As EXC.ExaException = Nothing

            If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties _
                Or e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetDataRows Then
                '--- Default hodnota

                '--- ! Nenastavovať - udalosť je volaná aj pri zmene typu zariadenia - takto by sa nedal zmeniť typ zariadenia
                ' Me.Device_Type = enm_Devices_Type.FiskalModule
            Else

                '--- Nastaviť model zariadenia - nemôže sa nastavovať pri Default_SetProperties, pretože v SET danej property je exception.throw
                e.Set(Me.Device_Model_Num, "DeviceModel", 0)

                e.Set(Me.Communication.DeviceCommunicationNumber, "DeviceCommunicationNumber", "")

            End If

            If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                '--- Načítať vlastnosti z XML 
                myEx = z_XMLInternalData_Load()
            End If

            Select Case Me.Device_Type

                Case enm_Devices_Type.FiskalModule

                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                        '--- Load --
                        '--- Číslo tabuľky v databáze 
                        e.Set(prp_dev_FiscalModule.Journal_DatabaseTable_Number, "DokladyTabulkaCislo", "")
                    End If

                    '--- Jednoznačný identifikátor dennej uzávierky
                    e.Set(prp_dev_FiscalModule.DailyBalanceID, "DailyBalanceID", CLng(1))

                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort")

                    '--- Sériový port ---
                    '--- Korekcia pôvodnej hodnoty, kde mohol byť aj TCP/IP port (upravené do 2 fieldov 05.03.2019)
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                        '--- Load --
                        Dim tmp_PortNumber As Integer
                        e.Set(tmp_PortNumber, "KomunikaciaPort", 1)
                        If tmp_PortNumber > 255 Then
                            '--- Toto bol pôvodne TCP/IP port
                            prp_Communication.Port_Number = 1
                        Else
                            prp_Communication.Port_Number = CByte(tmp_PortNumber)
                        End If
                    ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Save Then
                        '--- Save ---
                        e.Set(prp_Communication.Port_Number, "KomunikaciaPort")
                    End If

                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)
                    e.Set(prp_Communication.Path, "KomunikaciaCesta")
                    e.Set(prp_Communication.Path_Demo, "DatabankaDriverPath") '--- Z dôvodu FM41 - už nie je field v databaze a nechce sa mi len z tohto dovodu ho vyrabat


                    e.Set(prp_Communication.Login_Name, "Communication_LoginName", "")
                    e.Set(prp_Communication.Login_Password, "Communication_LoginPassword", "")

                    e.Set(prp_Communication.CashRegister_PLU_Max, "PokladnicaPocetPLU")

                    e.Set(prp_dev_FiscalModule.Text_Header, "HlavickaRiadok1", "")

                    Select Case Me.Device_Model_Num

                        Case enm_FiskalModule_Model.Fiscal_UNI_CZ
                            e.Set(prp_dev_FiscalModule.Ident_BusinessPremises, "HlavickaRiadok2", "")
                            e.Set(prp_dev_FiscalModule.Ident_Taxpayer, "HlavickaRiadok3", "")
                            e.Set(prp_dev_FiscalModule.Ident_AppointingTaxpayer, "HlavickaRiadok4", "")


                    End Select
                    e.Set(prp_dev_FiscalModule.Text_Header_Additional, "HlavickaRiadok5", "")

                    e.Set(prp_dev_FiscalModule.Text_Footer, "PatickaRiadok1", "")
                    e.Set(prp_dev_FiscalModule.Text_Footer_Additional, "PatickaRiadok2", "")

                    e.Set(prp_dev_FiscalModule.FoodDelivery_OpenHours_CalendarData, "Fiskal_DeliveryCalendarData", "")

                    '--- Displej - používa sa vzhľadom že sú už displeje povinne súčasťou fiškálneho modulu
                    e.Set(prp_dev_DisplayCustomer.Text_StandBy_1, "DisplejKludovaPolohaText1", "Dakujeme za nakup.")
                    e.Set(prp_dev_DisplayCustomer.Text_StandBy_2, "DisplejKludovaPolohaText2", "Dovidenia.")

                    '--- Fiškálna tlačiareň /momentálne nemá veľký význam/ ---
                    e.Set(prp_dev_FiscalModule.FiscalPrinter.PaperFeedLines, "FiskalTlaciarenPosuvRiadky", CByte(8))
                    e.Set(prp_dev_FiscalModule.FiscalPrinter.PaperCut, "FiskalTlaciarenOrezavaniePapiera", True)
                    e.Set(prp_dev_FiscalModule.FiscalPrinter.Standard40Character, "FiskalTlaciaren40Znakova", True)
                    e.Set(prp_dev_FiscalModule.FiscalPrinter.CashDrawer_CanOpen, "FiskalOtvaranieZasuvky", False)
                    e.Set(prp_dev_FiscalModule.FiscalPrinter.CashDrawer_CanOpen_PIN, "FiskalOtvaranieZasuvkyPIN", FiscalPrinter.Driver_Common.enum_CashDrawer_CanOpen_PIN.PIN_2_4)

                    e.Set(prp_dev_FiscalModule.Report_Name, "ReportName", "")

                    'e.Set(prp_dev_FiscalModule.Popis_Sumar, "PopisSumar", "")

                    '--- Špeciálna hodnota - Tlačiareň pre tento fiškál - má význam len pre Fiscal Virtual ---
                    e.Set(prp_dev_PrinterFiscal.Name, "FiskalTlaciarenNazov", "")


                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_FiskalModule_Model.eKasaPandora


                    ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                        '--- Default cesta pre virtuálny fiškál - pozor ! - treba aj vo validácii
                        If Me.Device_Model_Num = enm_FiskalModule_Model.Fiscal_UNI_SK _
                            OrElse Me.Device_Model_Num = enm_FiskalModule_Model.Fiscal_UNI_CZ Then

                            If prp_Communication.Path = Nothing OrElse prp_Communication.Path = String.Empty OrElse prp_Communication.Path.Length < 3 Then
                                Dim tmp_DirectoryName As String
                                tmp_DirectoryName = Exa.Basic.IO.Directory.GetValidDirectoryName(Me.Device_Model_Name, u_RemoveDiacritical:=True)
                                tmp_DirectoryName = tmp_DirectoryName.Replace(" ", "") '--- Odstrániť medzery
                                prp_Communication.Path = IO.Path.Combine(prp_AppConfiguration.Common.Directory.DATA_System_Fiscal, tmp_DirectoryName) & "\"
                            End If
                        End If


                    ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Save Then

                        If Me.Device_Model_Num <> enm_FiskalModule_Model.Fiscal_UNI_SK _
                            And Me.Device_Model_Num <> enm_FiskalModule_Model.Fiscal_UNI_CZ _
                            And Me.Device_Model_Num <> enm_FiskalModule_Model.UniversalInterface Then

                            '--- Cestu má zmysel ukladať len pre tieto fiškály, pre ostatné vymazať propertu
                            prp_Communication.Path = String.Empty   '-- Ak sa nevymaže, program vytvára zbytočne adresár
                            e.Set(prp_Communication.Path, "KomunikaciaCesta")
                        End If

                    End If


                Case enm_Devices_Type.BarCodeScanner

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_BarCodeScannerModel.Universal
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort", CByte(1))
                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)

                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", 2228)


                Case enm_Devices_Type.CashRegister


                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort")

                    '--- Sériový port ---
                    '--- Korekcia pôvodnej hodnoty, kde mohol byť aj TCP/IP port (upravené do 2 fieldov 05.03.2019)
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                        '--- Load --
                        Dim tmp_PortNumber As Integer
                        e.Set(tmp_PortNumber, "KomunikaciaPort", 1)
                        If tmp_PortNumber > 255 Then
                            '--- Toto bol pôvodne TCP/IP port
                            prp_Communication.Port_Number = 1
                        Else
                            prp_Communication.Port_Number = CByte(tmp_PortNumber)
                        End If
                    ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Save Then
                        '--- Save ---
                        e.Set(prp_Communication.Port_Number, "KomunikaciaPort")
                    End If

                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)


                    e.Set(prp_Communication.CashRegister_PLU_Max, "PokladnicaPocetPLU")
                    e.Set(prp_Communication.TextEncoding, "Communication_Encoding")

                    e.Set(prp_Communication.CashRegister_Universal_ExecutableFile_PLUBalance, "CashRegister_Universal_ExecutableFile_PLUBalance")
                    e.Set(prp_Communication.CashRegister_Universal_ExecutableFile_PLURead, "CashRegister_Universal_ExecutableFile_PLURead")
                    e.Set(prp_Communication.CashRegister_Universal_ExecutableFile_PLUWrite, "CashRegister_Universal_ExecutableFile_PLUWrite")
                    e.Set(prp_Communication.CashRegister_Universal_ExecutableFile_DailyBalance, "CashRegister_Universal_ExecutableFile_DailyBalance")

                    e.Set(prp_Communication.CashRegister_Universal_ExecutableFile_Journal, "CashRegister_Universal_ExecutableFile_Journal")
                    e.Set(prp_Communication.CashRegister_Universal_ExecutableFile_Journal_Move, "CashRegister_Universal_ExecutableFile_Journal_Move")

                    e.Set(prp_Communication.CashRegister_Universal_SourceCode_Errors, "CashRegister_Universal_SourceCode_Errors")
                    e.Set(prp_Communication.CashRegister_Universal_SourceCode_PLURead, "CashRegister_Universal_SourceCode_PLURead")
                    e.Set(prp_Communication.CashRegister_Universal_SourceCode_PLUWrite, "CashRegister_Universal_SourceCode_PLUWrite")
                    e.Set(prp_Communication.CashRegister_Universal_WorkingDirectory, "CashRegister_Universal_WorkingDirectory")


                    '--- Sklad z ktorého sa má predávať ---
                    e.Set(prp_dev_CashRegister.Settings_Stock_Name, "PokladnicaPredajSklad")

                    '--- Predajná cena ---
                    e.Set(prp_dev_CashRegister.Settings_PriceLevel, "PokladnicaPredajnaCena", CByte(1))

                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota					
                        Me.Device_Model_Num = enm_CashRegister_Model.Elcom_EURO_150_TE_eKasa
                        Me.Communication.TextEncoding = cls_Communication.enm_Text_Encoding.Default

                    ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                        '--- Load ---

                        '--- Reštauračný režim ---
                        Dim tmpNum As Integer = 0
                        e.Set(tmpNum, "PokladnicaOdpisovanieRestauracnyRezim", 0)
                        If tmpNum = 1 Then
                            prp_dev_CashRegister.Settings_RestaurantMode = True
                        Else
                            prp_dev_CashRegister.Settings_RestaurantMode = False
                        End If


                    ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Save Then
                        '--- Save ---

                        '--- Reštauračný režim ---
                        Dim tmpNum As Integer = 0
                        If prp_dev_CashRegister.Settings_RestaurantMode = True Then
                            tmpNum = 1
                        Else
                            tmpNum = 0
                        End If
                        e.Set(tmpNum, "PokladnicaOdpisovanieRestauracnyRezim")


                    End If

                    '--- Špeciálna hodnota - Tlačiareň pre túto pokladnicu - má význam len pre niektoré pokladnice pre doklady typu vnútorné zúčtovanie ---
                    e.Set(prp_dev_PrinterFiscal.Name, "FiskalTlaciarenNazov", "")



                Case enm_Devices_Type.PrinterReceipt

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_FiskalPrinter_Models.EPSON
                    End If

                    e.Set(prp_dev_PrinterFiscal.PaperFeedLines, "FiskalTlaciarenPosuvRiadky", CByte(8))
                    e.Set(prp_dev_PrinterFiscal.PaperCut, "FiskalTlaciarenOrezavaniePapiera", True)
                    e.Set(prp_dev_PrinterFiscal.Standard40Character, "FiskalTlaciaren40Znakova", True)
                    e.Set(prp_dev_PrinterFiscal.CashDrawer_CanOpen, "FiskalOtvaranieZasuvky", False)
                    e.Set(prp_dev_PrinterFiscal.CashDrawer_CanOpen_PIN, "FiskalOtvaranieZasuvkyPIN", FiscalPrinter.Driver_Common.enum_CashDrawer_CanOpen_PIN.PIN_2_4)

                '--- Toto isté je aj pri fiškálnom module - tlačiareň je ako súčasť fiškálnej tlačiarne ---


                Case enm_Devices_Type.PrinterKitchen

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_PrinterKitchen_Model.Universal
                    End If


                    e.Set(prp_dev_PrinterKitchen.Name, "TlaciarenKuchynaNazov", "")
                    e.Set(prp_dev_PrinterKitchen.Number, "TlaciarenKuchynaCislo", CByte(1))
                    e.Set(prp_dev_PrinterKitchen.PaperFeedLines_Before, "TlaciarenKuchynaPosuvRiadkyZaciatok", CByte(0))
                    e.Set(prp_dev_PrinterKitchen.PaperFeedLines_After, "TlaciarenKuchynaPosuvRiadky", CByte(8))
                    e.Set(prp_dev_PrinterKitchen.LineLenght, DB.Zariadenia.FiskalTlaciaren40Znakova, CByte(40))
                    If prp_dev_PrinterKitchen.LineLenght = 1 Or prp_dev_PrinterKitchen.LineLenght = 0 Then
                        '--- Korekcia - field bol pôvodne použitý ako Boolean
                        prp_dev_PrinterKitchen.LineLenght = 40
                    End If


                    '--- Komunikácia - špecialita (používa sa pri priamej tlači) ---

                    '--- Komunikácia - Ethernet
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(9100))

                    '--- Komunikácia - Serial port ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort", CByte(1))
                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 38400)


                    '--- V Datarecorde je hodnota ukladatá v štandardnej triede Communication
                    '--- Parametre komunikácie sú nastavené aj v triede PrinterKitchen
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                        '--- Nastaviť parametre komunikácie  - z dôvodu použitia priamej tlače a tejto triedy
                        prp_dev_PrinterKitchen.PrinterIPAddress = prp_Communication.TCP_HostName
                        prp_dev_PrinterKitchen.PrinterIPPort = prp_Communication.TCP_Port
                        prp_dev_PrinterKitchen.PrinterSerialPortNumber = prp_Communication.Port_Number
                        prp_dev_PrinterKitchen.PrinterSerialPortBaundRate = prp_Communication.Port_BaudRate
                    End If



                Case enm_Devices_Type.DisplayCustomer

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_DisplayCustomerModel.EPSON_20_Character_x_2_Row
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort")
                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)

                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "localhost")
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", 21001)
                    e.Set(prp_Communication.Login_Name, "Communication_LoginName", "")

                    e.Set(prp_dev_DisplayCustomer.Text_StandBy_1, "DisplejKludovaPolohaText1", "Dakujeme za nakup.")
                    e.Set(prp_dev_DisplayCustomer.Text_StandBy_2, "DisplejKludovaPolohaText2", "Dovidenia.")


                Case enm_Devices_Type.ElectronicScale

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_ElectronicScaleModel.EAN13_Universal
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort", CByte(1))
                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)

                Case enm_Devices_Type.DoorKey

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_DoorKey_Model.SeaGuest
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(5020))
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "localhost")

                    '--- Pracovať v režime Serial port ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort")

                    'Číslo zariadenia
                    e.Set(prp_Communication.DeviceCommunicationNumber, "DeviceCommunicationNumber", CStr(1))

                Case enm_Devices_Type.PDA

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_PDA_Model.Universal
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(10520))

                    e.Set(dev_PDA.Name, "KomunikaciaCesta", "PDA1")


                Case enm_Devices_Type.PriceLabels

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_PriceLabelsModel.OBERON_ESL_2026
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(80))
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "http://192.168.16.251")

                Case enm_Devices_Type.PID

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_PID_Model.ECI_10
                    End If

                    '--- Komunikácia ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort", CByte(1))
                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)

                Case enm_Devices_Type.AttendanceTerminal

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_AttendanceTerminalModel.OBERON
                    End If

                    '--- Každý terminál bude mať prevádzku a názov pracoviska
                    e.Set(prp_dev_AttendanceTerminal.WorkplaceName, "PokladnicaPredajSklad", String.Empty)

                    Select Case CType(Me.Device_Model_Num, enm_AttendanceTerminalModel)

                        Case enm_AttendanceTerminalModel.OBERON

                        Case enm_AttendanceTerminalModel.EXALOGIC_AC071

                            '--- Komunikácia ---
                            e.Set(prp_Communication.DeviceCommunicationNumber, "DeviceCommunicationNumber", CStr(1))
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(5500))
                            e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")
                            e.Set(prp_Communication.Login_Password, "Communication_LoginPassword", "")

                        Case enm_AttendanceTerminalModel.EXALOGIC_TFT500SK
                            e.Set(prp_Communication.DeviceCommunicationNumber, "DeviceCommunicationNumber", CStr(1))
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(8081))
                            e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")

                    End Select

                Case enm_Devices_Type.PaymentTerminal
                    '--- Komunikácia ---
                    e.Set(prp_Communication.TCP_HostName, "Communication_HostName", "")
                    'Select Case CType(Me.Device_Model_Num, enm_PaymentTerminalModel)
                    Select Case Me.prp_dev_PaymentTerminal.PaymentTerminalModel

                        Case enm_PaymentTerminalModel.AxaPro
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(2244))

                        Case enm_PaymentTerminalModel.FiskalPro, enm_PaymentTerminalModel.FiskalProA8
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(6090))

                        Case enm_PaymentTerminalModel.GpEcr2
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(20008))

                        Case enm_PaymentTerminalModel.Printec
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort", CInt(53535))

                        Case enm_PaymentTerminalModel.GpTom

                        Case enm_PaymentTerminalModel.Teya

                        Case enm_PaymentTerminalModel.SoftPlusTicket

                        Case enm_PaymentTerminalModel.Rictom
                            e.Set(prp_Communication.TCP_Port, "Communication_TCPPort")
                            If prp_Communication.TCP_Port = 0 Then prp_Communication.TCP_Port = 555

                    End Select

                    '--- Pracovať v režime Serial port ---
                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort")


                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)


                Case enm_Devices_Type.DocumentReader
                    '--- Čítačka dokumentov (dokladov)

                    e.Set(prp_Communication.Port_Number, "KomunikaciaPort", CByte(1))
                    e.Set(prp_Communication.Port_BaudRate, "KomunikaciaRychlost", 9600)

                Case enm_Devices_Type.SignaturePad
                    '--- Digitálna podpisová podložka 

                    '--- Model ---
                    If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                        '--- Default hodnota
                        Me.Device_Model_Num = enm_SignaturePadModel.ExalogicDSP1
                    End If

            End Select


            If e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Default_SetProperties Then
                '--- Nový záznam - nastavenie default hodnôt ---
                Me.Computers = New String() {My.Computer.Name}

            ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Load Then
                '--- Load --

            ElseIf e.Action = cls_RecordColumnSetValueEventArgs.enm_ActionTypes.Save Then
                '--- Save ---

            End If


        End Sub


#End Region

#Region " Implements function "


#Region " IDisposable Support "


        Private disposedValue As Boolean = False        ' To detect redundant calls

        ' IDisposable
        Protected Overrides Sub Dispose(ByVal disposing As Boolean)
            MyBase.Dispose(disposing)

            If Not Me.disposedValue Then
                If disposing Then
                End If
                On Error Resume Next

                prp_SaveBehavior = Nothing
                prp_Communication = Nothing

                prp_dev_BarCode_Scanner = Nothing
                prp_dev_CashRegister = Nothing
                prp_dev_DisplayCustomer = Nothing
                prp_dev_DoorKey = Nothing
                prp_dev_ElectronicScale = Nothing
                prp_dev_FiscalModule.Dispose() : prp_dev_FiscalModule = Nothing
                prp_dev_PDA = Nothing
                prp_dev_PID = Nothing
                prp_dev_PrinterFiscal.Dispose() : prp_dev_PrinterFiscal = Nothing
                prp_dev_PrinterKitchen = Nothing

                prp_AppConfiguration = Nothing
            End If
            Me.disposedValue = True
        End Sub

#End Region


#End Region

#Region " Ďalšie objekty - Class "

        ''' <summary>Nastavenia komunikácie s daným zariadením, napr. IP adresa, port a podobne (nastavenie komunikačného rozhrania).</summary>
        Public Class cls_Communication

            Public Enum enm_Text_Encoding
                <System.ComponentModel.Description("Default")>
                [Default] = 0

                <System.ComponentModel.Description("ASCII")>
                ASCII = 1

                <System.ComponentModel.Description("BigEndianUnicode")>
                BigEndianUnicode = 2

                <System.ComponentModel.Description("Unicode")>
                Unicode = 3

                <System.ComponentModel.Description("UTF32")>
                UTF32 = 4

                <System.ComponentModel.Description("UTF7")>
                UTF7 = 5

                <System.ComponentModel.Description("UTF8")>
                UTF8 = 6

                <System.ComponentModel.Description("ISO-8859-2")>
                ISO_8859_2 = 7

            End Enum

            ''' <summary>Komunikácia - číslo sériového portu, napr. COM1 = 1.</summary>    
            ''' <remarks>Nie Byte, lebo niekde aj -1</remarks>
            Public Port_Number As Byte

            ''' <summary>Komunikácia - rýchlosť sériového portu, napr. 9600.</summary>    
            Public Port_BaudRate As Integer

            ''' <summary>Číslo zariadenia (typu STRING) - číslo pridelené zariadeniu z hľadiska komunikácie alebo komunikačného protokolu, napr. pri pokladniciach číslo pokladnice.</summary>             
            Public DeviceCommunicationNumber As String

            ''' <summary>Komunikácia - napr. cesta pre fiškálny modul Fiskal Model 40.</summary>    
            Public Path As String

            ''' <summary>Komunikácia - napr. demo cesta pre fiškálny modul Fiskal Model 40.</summary>    
            Public Path_Demo As String

            ''' <summary>Prihlasovacie meno.</summary>    
            Public Login_Name As String

            ''' <summary>Prihlasovacie heslo.</summary>    
            Public Login_Password As String

            ''' <summary>URL na hosťujúci počítač.</summary>    
            Public TCP_HostName As String

            ''' <summary>TCP port. Pri Fiškálnom zariadení eKasa (od roku 2019) je tu port ECM (nie port zariadenia).</summary>    
            Public TCP_Port As Integer

            ''' <summary>IP adresa na hosťujúci počítač. Neukladá sa do databázy, len sa zisťuje z HostName (z názvu počítača).</summary>            
            Public TCP_IPAddress As System.Net.IPAddress

            ''' <summary>Kódovanie súborov, napr. pri CahsRegister Universal Interface.</summary>    
            Public TextEncoding As enm_Text_Encoding

            ''' <summary>
            ''' Registračná pokladnica - maximálny počet PLU v pokladnici
            ''' </summary>    
            Public CashRegister_PLU_Max As Integer

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_WorkingDirectory As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_ExecutableFile_PLURead As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_ExecutableFile_PLUWrite As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_ExecutableFile_PLUBalance As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_ExecutableFile_DailyBalance As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface (kopírovanie žurnálu)
            ''' </summary>    
            Public CashRegister_Universal_ExecutableFile_Journal As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface (presunutie žurnálu)
            ''' </summary>    
            Public CashRegister_Universal_ExecutableFile_Journal_Move As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_SourceCode_PLURead As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_SourceCode_PLUWrite As String

            ''' <summary>
            ''' Registračná pokladnica CashRegister Universal Interface 
            ''' </summary>    
            Public CashRegister_Universal_SourceCode_Errors As String

            Public Function Clone() As cls_Communication

                Dim tmp_Communication As New cls_Communication

                Try

                    tmp_Communication.DeviceCommunicationNumber = Me.DeviceCommunicationNumber
                    tmp_Communication.CashRegister_PLU_Max = Me.CashRegister_PLU_Max

                    tmp_Communication.CashRegister_Universal_WorkingDirectory = Me.CashRegister_Universal_WorkingDirectory
                    tmp_Communication.CashRegister_Universal_ExecutableFile_PLURead = Me.CashRegister_Universal_ExecutableFile_PLURead
                    tmp_Communication.CashRegister_Universal_ExecutableFile_PLUWrite = Me.CashRegister_Universal_ExecutableFile_PLUWrite
                    tmp_Communication.CashRegister_Universal_ExecutableFile_PLUBalance = Me.CashRegister_Universal_ExecutableFile_PLUBalance
                    tmp_Communication.CashRegister_Universal_ExecutableFile_DailyBalance = Me.CashRegister_Universal_ExecutableFile_DailyBalance
                    tmp_Communication.CashRegister_Universal_ExecutableFile_Journal = Me.CashRegister_Universal_ExecutableFile_Journal
                    tmp_Communication.CashRegister_Universal_ExecutableFile_Journal_Move = Me.CashRegister_Universal_ExecutableFile_Journal_Move
                    tmp_Communication.CashRegister_Universal_SourceCode_PLURead = Me.CashRegister_Universal_SourceCode_PLURead
                    tmp_Communication.CashRegister_Universal_SourceCode_PLUWrite = Me.CashRegister_Universal_SourceCode_PLUWrite
                    tmp_Communication.CashRegister_Universal_SourceCode_Errors = Me.CashRegister_Universal_SourceCode_Errors

                    tmp_Communication.Path = Me.Path
                    tmp_Communication.Path_Demo = Me.Path_Demo
                    tmp_Communication.Port_BaudRate = Me.Port_BaudRate
                    tmp_Communication.Port_Number = Me.Port_Number
                    tmp_Communication.TCP_HostName = Me.TCP_HostName
                    tmp_Communication.TCP_Port = Me.TCP_Port
                    tmp_Communication.TCP_IPAddress = Me.TCP_IPAddress

                    tmp_Communication.Login_Name = Me.Login_Name
                    tmp_Communication.Login_Password = Me.Login_Password

                    tmp_Communication.TextEncoding = Me.TextEncoding

                Catch ex As Exception

                End Try

                Return tmp_Communication

            End Function

            ''' <summary>
            ''' Vráti System.Text.Encoding z exa enum-u  enm_Text_Encoding
            ''' </summary>
            Public Function Convert_TextEncoding_To_SystemTextEncoding(ByVal u_Text_Encoding As enm_Text_Encoding) As System.Text.Encoding

                On Error Resume Next

                Select Case u_Text_Encoding

                    Case enm_Text_Encoding.Default
                        Return System.Text.Encoding.Default

                    Case enm_Text_Encoding.ASCII
                        Return System.Text.Encoding.ASCII

                    Case enm_Text_Encoding.BigEndianUnicode
                        Return System.Text.Encoding.BigEndianUnicode

                    Case enm_Text_Encoding.Unicode
                        Return System.Text.Encoding.Unicode

                    Case enm_Text_Encoding.UTF32
                        Return System.Text.Encoding.UTF32

                    Case enm_Text_Encoding.UTF7
                        Return System.Text.Encoding.UTF7

                    Case enm_Text_Encoding.UTF8
                        Return System.Text.Encoding.UTF8

                    Case enm_Text_Encoding.ISO_8859_2
                        Return System.Text.Encoding.GetEncoding("iso-8859-2")

                    Case Else

#If DEBUG Then
                        EXC.Throw("Chybný enm_Text_Encoding.")
#End If

                        Return System.Text.Encoding.Default


                End Select


            End Function


            ''' <summary>
            ''' Vráti info o nastavení komunikácii (o nastavení tohto objektu).
            ''' </summary>	
            Public Shadows Function ToString() As String

                On Error Resume Next

                Dim tmp_SB As New System.Text.StringBuilder

                If Me.Port_Number > 0 Then

                    tmp_SB.AppendLine("COM Port Number:  " & Me.Port_Number)
                    tmp_SB.AppendLine("COM Port BaudRate:  " & Me.Port_BaudRate)
                End If

                If Me.TCP_HostName <> String.Empty Then

                    tmp_SB.AppendLine("TCP Host Name:  " & Me.TCP_HostName)
                    If Me.TCP_IPAddress IsNot Nothing Then
                        tmp_SB.AppendLine("TCP IP Address:  " & Me.TCP_IPAddress.ToString)
                    End If
                    tmp_SB.AppendLine("TCP IP port:  " & Me.TCP_Port)
                End If

                If Me.DeviceCommunicationNumber <> "" Then
                    tmp_SB.AppendLine("Device_Number:  " & Me.DeviceCommunicationNumber)
                End If

                If Me.Login_Name <> String.Empty Then
                    tmp_SB.AppendLine("Login Name:  " & Me.Login_Name)
                End If

                Return tmp_SB.ToString

            End Function


        End Class



        ''' <summary>Údaje pre registračné pokladnice.</summary>
        Public Class cls_d_CashRegister


            Friend Property prp_CashRegister_Model As enm_CashRegister_Model
            ''' <summary>Konkrétny typ /model/ zariadenia, napr. presný model registračnej pokladnice, napr. Euro 200.</summary>
            Public ReadOnly Property CashRegister_Model As enm_CashRegister_Model
                Get
                    Return prp_CashRegister_Model
                End Get
            End Property


            ''' <summary>Cenová hladina, ktorá sa bude používať pri predaji, napr. 1.</summary>    
            Public Settings_PriceLevel As Byte

            ''' <summary>Sklad s ktorým pokladnica pracuje.</summary>    
            Public Settings_Stock_Name As String

            ''' <summary>Reštauračný režim - ovplyvňuje spôsob vytvárania skladových pohybov.</summary>    
            Public Settings_RestaurantMode As Boolean

        End Class


        ''' <summary>Údaje pre fiškálne zariadenia.</summary>
        Public Class cls_d_FiscalModule
            Implements IDisposable

            Private lc_Device As Device

            ''' <summary>Spôsob, akým spôsobom bude OBERON spúšťať program EXALOGIC CashRegister Manager.</summary>
            Public Enum enm_eKasa_ECM_RunMode As Byte
                ''' <summary>Nenastavené.</summary>
                None = 0

                ''' <summary>EXALOGIC CashRegister Manager bude spúšťaný ako bežná Windows aplikácia (nie Windows Service)- bude obsahovať server, ako aj klienta.</summary>
                <System.ComponentModel.Description("Bežná aplikácia")>
                WindowsApp = 1

                ''' <summary>EXALOGIC CashRegister Manager (strana servera) bude nastavená ako Windows service.</summary>
                <System.ComponentModel.Description("Windows služba")>
                WindowsService = 2

                ''' <summary>EXALOGIC CashRegister Manager (strana servera) je spustený na inom počítači.</summary>
                <System.ComponentModel.Description("Pripojenie k inému počítaču")>
                ConnectToOtherPC = 3

            End Enum

            Public Sub New(ByVal u_Device As Device)
                lc_Device = u_Device
                FiscalPrinter = New FiscalPrinter.Driver_Common(u_Device._AppConfiguration)
                prp_CashRegisterOBERONSettings = New Exa.OBERON.Devices.FiscalModule.CashRegisterOBERON_Settings(u_Device._AppConfiguration)
            End Sub

            Friend Property prp_FiscalModule_Model As enm_FiskalModule_Model
            ''' <summary>Konkrétny typ /model/ zariadenia, napr. presný typ fiškálneho zariadenia, napr. eKasa (daného výrobcu), VRP, Fiscal Virtual, Universal Interface a ostatné podporované typy.</summary>
            Public ReadOnly Property FiscalModule_Model As enm_FiskalModule_Model
                Get
                    Return prp_FiscalModule_Model
                End Get
            End Property


            ''' <summary>Číslo databázovej tabuľky pre uloženie pokladničných dokladov, napr. 001.</summary>        
            Public Journal_DatabaseTable_Number As String

            Private prp_CashRegisterOBERONSettings As Exa.OBERON.Devices.FiscalModule.CashRegisterOBERON_Settings = Nothing
            ''' <summary>Nastavenia programu Pokladnica OBERON.</summary>        
            Public ReadOnly Property CashRegisterOBERONSettings As Exa.OBERON.Devices.FiscalModule.CashRegisterOBERON_Settings
                Get
                    Return prp_CashRegisterOBERONSettings
                End Get
            End Property

            ''' <summary>Spôsob, akým bude OBERON spúšťať program EXALOGIC CashRegister Manager.</summary>
            Public eKasa_ECM_RunMode As enm_eKasa_ECM_RunMode

            ''' <summary>TRUE - pokladnica pracuje z hľadiska prepojenia na Finančnú správu Off-line (špeciálny režim), tzv. (max 30 dní) , 
            ''' FALSE - pokladnica pracuje z hľadiska prepojenia a zasielanie dokladov na Finančnú správu štandardne on-line.</summary>    
            Public BillRegisterDelay As Boolean = False

            ''' <summary>Jednoznačný identifikátor dennej uzávierky. Automaticky sa povyšuje po vykonaní dennej uzávierky. 
            ''' Pokladničné doklady priebežne zapisované do databázy patria do danej denej uzávierky. Pri dennej uzávierke sú obraty
            ''' z fiškálneho zariadenia porovnávané s obratmi zapísané v databáze podľa tohto čísla, taktiež sa z týchto záznamov robí zápis do knihy tržieb.</summary>        
            Public DailyBalanceID As Long

            ''' <summary>Hlavička dokladu. [HlavickaRiadok1]</summary>    
            Public Text_Header As String

            ''' <summary>Identifikátor prevádzky. [HlavickaRiadok2]</summary>    
            Public Ident_BusinessPremises As String

            ''' <summary>Identifikačné číslo platcu dane. [HlavickaRiadok3]</summary>    
            Public Ident_Taxpayer As String

            ''' <summary>Identifikačné číslo povereného platcu dane. [HlavickaRiadok4]</summary>    
            Public Ident_AppointingTaxpayer As String

            ''' <summary>Hlavička dokladu - doplňujúca. [HlavickaRiadok5]</summary>    
            Public Text_Header_Additional As String

            ''' <summary>Pätička dokladu.</summary>    
            Public Text_Footer As String

            ''' <summary>Pätička dokladu - doplňujúca.</summary>    
            Public Text_Footer_Additional As String

            ''' <summary>Otváracie hodiny donášky - ročný kalendár. Ak nemá zadanú žiadnu hodnotu, je otvorený každý deň, ak obsahuje hodnoty, obsahuje dni, kedy je otvorené.</summary>
            Public FoodDelivery_OpenHours_CalendarData As String

            ''' <summary>Názov reportu napr. pre virtuálnu reg. pokladňu finančnej správy.</summary>    
            Public Report_Name As String

            ''' <summary>Fiškálna tlačiareň - Tlačiareň pokladničných dokladov.</summary>
            Public FiscalPrinter As FiscalPrinter.Driver_Common


            ''' <summary>
            ''' Aktualizuje (opätovne načíta) jednoznančný identifikátor aktuálnej dennej uzávierky (hodnotu DailyBalanceID), do ktorej paria aktuálne doklady.
            ''' Je to potrebné volať v tedy, ak so zariadením pracujú viacerí používatelia - po dennej uzávierke na jednej pokladnici
            ''' sa musí DailyBalanceID povýšiť aj na inom počítači (ak je pokladnica nepretržite spustená). Refresh hodnotu neukladá, len ju načíta.
            ''' </summary>
            Public Function DailyBalanceIDRefresh() As EXC.ExaException

                Dim myEx As EXC.ExaException
                myEx = EXC.GetDefault

                Try

                    Dim tmp_Value As Long
                    Dim tmp_SQL As String
                    tmp_SQL$ = String.Format("SELECT MAX({1}) FROM {0} WHERE IDNum = {2}", DB.Zariadenia.TableName,
                                                                                           DB.Zariadenia.DailyBalanceID,
                                                                                           lc_Device.IDNum)
                    myEx = lc_Device._AppConfiguration._AppObjects._CommonData.ExecuteScalar(Of Long)(tmp_SQL$, tmp_Value)
                    If myEx.Result = False Then
                        Exit Try
                    End If

                    Me.DailyBalanceID = tmp_Value

                    myEx.Result = True

                Catch ex As Exception

                    myEx = EXC.Get("Chyba DailyBalanceIDRefresh:  " & ex.Message)

                End Try

                Return myEx

            End Function



#Region "IDisposable Support"
            Private disposedValue As Boolean ' To detect redundant calls

            ' IDisposable
            Protected Overridable Sub Dispose(disposing As Boolean)
                If Not Me.disposedValue Then
                    If disposing Then
                    End If
                    On Error Resume Next

                    FiscalPrinter.Dispose()
                    FiscalPrinter = Nothing

                    If prp_CashRegisterOBERONSettings IsNot Nothing Then
                        prp_CashRegisterOBERONSettings.Dispose()
                    End If

                    lc_Device = Nothing

                End If
                Me.disposedValue = True
            End Sub
            ' This code added by Visual Basic to correctly implement the disposable pattern.
            Public Sub Dispose() Implements IDisposable.Dispose
                ' Do not change this code.  Put cleanup code in Dispose(disposing As Boolean) above.
                Dispose(True)
                GC.SuppressFinalize(Me)
            End Sub

#End Region

        End Class





        ''' <summary>
        ''' Tlačiareň pre tlač objednávok (prípadne storna objednávok) z bonovacej knihy.
        ''' </summary>
        Public Class cls_d_PrinterKitchen
            Implements ICloneable

            Friend Property prp_Model As enm_PrinterKitchen_Model
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property Model As enm_PrinterKitchen_Model
                Get
                    Return prp_Model
                End Get
            End Property

            ''' <summary>Tlačiareň do kuchyne - číslo.</summary>    
            Public Property Number As Byte

            ''' <summary>Názov tlačiarne definovanej v systéme Windows. Môže obsahovať aj systémový názov
            ''' <see cref="PrinterOrder.CONST_PrinterName_DirectPrint_SerialPort">*** Priama tlač (serial port) ***</see>, <see cref="PrinterOrder.CONST_PrinterName_DirectPrint_Ethernet">*** Priama tlač (ethernet) ***</see>, 
            ''' alebo  <see cref="CONST_Printer_Fiscal">*** Fiškálny modul ***</see>.</summary>    
            Public Property Name As String

            ''' <summary>
            ''' TRUE - objednávková tlačiareň je pripojená cez sériový alebo ethernet port a tlačí sa na ňu priamo, t.j. nie cez Windows spooler 
            ''' (zisťuje sa aj stav pripravenosti tlačiarne).
            ''' FALSE - pri tlači sa zasiela úloha na Windows tlačiareň (printer spooler).
            ''' </summary>            
            Public ReadOnly Property IsDirectPrint As Boolean
                Get

                    Try
                        If Me.Name = Exa.OBERON.Devices.PrinterOrder.CONST_PrinterName_DirectPrint_SerialPort _
                             OrElse Me.Name = Exa.OBERON.Devices.PrinterOrder.CONST_PrinterName_DirectPrint_Ethernet Then
                            '--- Priama tlač
                            Return True
                        Else
                            '--- Nie priama tlač, ale cez Windows ovládač
                            Return False
                        End If
                    Catch ex As Exception
                        Return False
                    End Try

                End Get
            End Property


            ''' <summary>Ak je typ tlačiarne s priamou ethernet tlačou, zadáva sa tu IP adresa tlačiarne.</summary>    
            Public Property PrinterIPAddress As String

            ''' <summary>Ak je typ tlačiarne s priamou ethernet tlačou, zadáva sa tu IP adresa tlačiarne.</summary>    
            Public Property PrinterIPPort As Integer

            ''' <summary>Ak je typ tlačiarne s priamou sériovou tlačou, zadáva sa tu číslo sériového portu.</summary>    
            Public Property PrinterSerialPortNumber As Byte

            ''' <summary>Ak je typ tlačiarne s priamou sériovou tlačou, zadáva sa tu rýchlosť sériového portu.</summary>    
            Public Property PrinterSerialPortBaundRate As Integer



            ''' <summary>Tlačiareň do kuchyne - posunutie pred začiatkom tlače X riadkov.</summary>    
            Public Property PaperFeedLines_Before As Byte

            ''' <summary>Tlačiareň do kuchyne - posunutie po ukončení tlače X riadkov.</summary>    
            Public Property PaperFeedLines_After As Byte

            ''' <summary>Počet znakov na riadok, najčastejšie 40 alebo 48 znakov.</summary>    
            Public Property LineLenght As Byte

            ''' <summary>Názov tlačového výstupu pre tlač objednávky v grafickom režime.</summary>    
            Public Property ReportNameOrder As String

            ''' <summary>Názov tlačového výstupu pre tlač storna objednávky v grafickom režime.</summary>    
            Public Property ReportNameOrderAnulment As String

            ''' <summary>
            ''' TRUE - Model tlačiarne podporuje ESC sekvencie (OBERON formátovacie znaky) a umožňuje meniť typy písma reportu (priama tlač na tlačiareň EPSON).
            ''' FALSE - Model tlačiarne nepodporuje formátovacie znaky (ESC sekvencie). Vtedy sa text reportu musí vyskladať bez formátovacích znakov.
            ''' </summary>            
            Public ReadOnly Property AllowOBERONFormatChars As Boolean
                Get

                    Try
                        If Me.Model = enm_PrinterKitchen_Model.Epson Then
                            Return True
                        Else
                            Return False
                        End If

                    Catch ex As Exception
                        Return False
                    End Try

                End Get
            End Property



            Public Function Clone() As Object Implements ICloneable.Clone
                On Error Resume Next
                Return CType(Me.MemberwiseClone(), cls_d_PrinterKitchen)
            End Function
        End Class


        ''' <summary>
        ''' Snímač čiarového kódu
        ''' </summary>
        Public Class cls_d_BarCode_Scanner

            Friend Property prp_BarCodeScannerModel As enm_BarCodeScannerModel
            ''' <summary>Konkrétny typ /model/ zariadenia, napr. presný model snímača čiarového kódu.</summary>
            Public ReadOnly Property BarCodeScannerModel As enm_BarCodeScannerModel
                Get
                    Return prp_BarCodeScannerModel
                End Get
            End Property

            ''' <summary>
            ''' Prefix pridaný na začiatok nasnímaného kódu.
            ''' </summary>
            ''' <remarks>Využívané pri vernostných kartách typu RFID.</remarks>
            Public PrefixBarCode As String

            ''' <sumary>Potlačí rozpoznanie váženého čiarového kódu.</sumary>
            Public WeightBarCodeDisable As Boolean

        End Class


        ''' <summary>
        ''' Zákaznícky displey
        ''' </summary>
        Public Class cls_d_DisplayCustomer

            Friend Property prp_DisplayCustomerModel As enm_DisplayCustomerModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property DisplayCustomerModel As enm_DisplayCustomerModel
                Get
                    Return prp_DisplayCustomerModel
                End Get
            End Property

            ''' <summary>
            ''' Zákaznícky display k pokladnici /fiškálnemu modulu/ - text v kľudovej polohe
            ''' </summary>    
            Public Text_StandBy_1 As String

            ''' <summary>
            ''' Zákaznícky display k pokladnici /fiškálnemu modulu/ - text v kľudovej polohe
            ''' </summary>    
            Public Text_StandBy_2 As String


        End Class



        ''' <summary>
        ''' Snímače prístupových klúčov
        ''' </summary>
        Public Class cls_d_PID

            Friend Property prp_PID_Model As enm_PID_Model
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property PID_Model As enm_PID_Model
                Get
                    Return prp_PID_Model
                End Get
            End Property

        End Class


        ''' <summary>
        ''' Elektronické váhy
        ''' </summary>
        Public Class cls_d_ElectronicScale

            Friend Property prp_ElectronicScaleModel As enm_ElectronicScaleModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property ElectronicScaleModel As enm_ElectronicScaleModel
                Get
                    Return prp_ElectronicScaleModel
                End Get
            End Property

        End Class

        ''' <summary>
        ''' Dverový zámok
        ''' </summary>
        Public Class cls_d_DoorKey

            Friend Property prp_DoorKey_Model As enm_DoorKey_Model
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property DoorKey_Model As enm_DoorKey_Model
                Get
                    Return prp_DoorKey_Model
                End Get
            End Property

        End Class


        ''' <summary>
        ''' Elektronické cenovky (Price Labels)
        ''' </summary>
        Public Class cls_d_PriceLabels

            Friend Property prp_PriceLabelsModel As enm_PriceLabelsModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property PriceLabelsModel As enm_PriceLabelsModel
                Get
                    Return prp_PriceLabelsModel
                End Get
            End Property

        End Class


        ''' <summary>
        ''' PDA zariadenia
        ''' </summary>
        Public Class cls_d_PDA

            ''' <summary>
            ''' PDA zariadenia - model
            ''' </summary>    
            Public PDA_Model As enm_PDA_Model

            ''' <summary>
            ''' PDA názov - musí byť zhodné s menom fyzického PDA, môže byť aj TCP/IP adresa
            ''' </summary>
            ''' <remarks></remarks>
            Public Name As String

        End Class

        ''' <summary>
        ''' Dochádzkové terminály - zariadenia
        ''' </summary>
        Public Class cls_d_AttendanceTerminal

            Friend Property prp_AttendanceTerminalModel As enm_AttendanceTerminalModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property AttendanceTerminalModel As enm_AttendanceTerminalModel
                Get
                    Return prp_AttendanceTerminalModel
                End Get
            End Property

            ''' <summary>
            ''' Identifikátor firmy ak je dochádzkový terminál zdielaný medzi firmami. To umožní priradiť pracovníkov k firme.
            ''' </summary>
            Public CompanyId As Integer

            ''' <summary>Názov pracoviska.</summary>
            Public WorkplaceName As String

            ''' <summary>Ďalší port určený pre monitorovanie prechodov.</summary>
            Public Monitor_IPEndPoint As System.Net.IPEndPoint

            ''' <summary>Model zariadenia. Overuje sa na zhodu.</summary>
            Public DeviceModel As String

            ''' <summary>Dátum odkedy sa majú načítať prechody ak je nastavený.</summary>
            Public DateUtcFrom As Date

            ''' <summary>Prepojenie typu prechodu medzi terminálom as dochádzkou.</summary>
            Public Class cls_ShortCutPair
                Public Terminal_ShortCutID As Integer
                Public Terminal_ShortCut As String
                Public Attendance_ShortCut As String
            End Class

            ''' <summary>Vytvorený zoznam definovaných prechodov tak ako sú spárované.</summary>
            Public ShortCut_List As New List(Of cls_ShortCutPair)

            Public Function Clone() As cls_d_AttendanceTerminal
                On Error Resume Next
                Dim m_Object As cls_d_AttendanceTerminal = CType(Me.MemberwiseClone(), cls_d_AttendanceTerminal)
                m_Object.ShortCut_List = Me.ShortCut_List?.ToList()
                m_Object.Monitor_IPEndPoint = New Net.IPEndPoint(Me.Monitor_IPEndPoint.Address, Me.Monitor_IPEndPoint.Port)
                Return m_Object
            End Function

        End Class

        ''' <summary>
        ''' Platobné terminály - zariadenia
        ''' </summary>
        <Serializable>
        Public Class cls_d_PaymentTerminal

            Friend Property prp_PaymentTerminalModel As enm_PaymentTerminalModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property PaymentTerminalModel As enm_PaymentTerminalModel
                Get
                    Return prp_PaymentTerminalModel
                End Get
            End Property

            ''' <summary>
            ''' Platobný terminál - identifikátor - jednoznačne identifikuje zariadenie aj v rozdielnych databázach
            ''' </summary>
            Public TerminalId As String

            ''' <summary>
            ''' Platobný terminál - identifikátor prevádzky/obchodu
            ''' </summary>
            Public StoreId As String

            ''' <summary>
            ''' Pokladňa - identifikátor - jednoznačne identifikuje zariadenie aj v rozdielnych databázach
            ''' </summary>
            Public CashId As String

            ''' <summary>
            ''' URL adresa pre službu/cloud.
            ''' </summary>
            Public CloudUrl As Uri

            '''<summary>GPTom cloud prístup.</summary>
            Public CloudCredential As Net.NetworkCredential

            '''<summary>GPTom účet prístup.</summary>
            Public MerchantCredential As Net.NetworkCredential

            ''' <summary>Api key vygenerované pre platobný terminál.</summary>
            Public ApiKey As String

            ''' <summary>Platobný terminál - popis.</summary>
            Public TerminalDesc As String

            ''' <summary>Povolenie tlače potvrdenky o transakcii na platobnom terminály.</summary>
            Public PrintOnTerminal As Boolean

            ''' <summary>Povolenie tlače potvrdenky o transakcii pre obchodníka.</summary>
            Public PrintReceiptMerchant As Boolean

            ''' <summary>Povolenie zadavánia sumy obslužného pri platbe na platobnom terminály.</summary>
            Public RequestTipEnable As Boolean

            ''' <summary>Sériové číslo certifikátu požadované pre overenie klienta serverom.</summary>
            Public ClientCertificate As String

            ''' <summary>IBAN platobného účtu.</summary>
            Public Property BankIBAN As String

            ''' <summary>Meno platobného účtu pre overenie bankou.</summary>
            Public Property BankAccountName As String

        End Class


        ''' <summary>
        ''' Čítačky na čítanie údajov z cestovných pasov a preukazov totožnosti - zariadenia
        ''' </summary>
        Public Class cls_d_DocumentReader

            Friend Property prp_DocumentReaderModel As enm_DocumentReaderModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property DocumentReaderModel As enm_DocumentReaderModel
                Get
                    Return prp_DocumentReaderModel
                End Get
            End Property

        End Class

        ''' <summary>
        ''' Digitálna podpisová podložka.
        ''' </summary>
        Public Class cls_d_SignaturePad

            Friend Property prp_Model As enm_SignaturePadModel
            ''' <summary>Konkrétny typ /model/ zariadenia.</summary>
            Public ReadOnly Property Model As enm_SignaturePadModel
                Get
                    Return prp_Model
                End Get
            End Property


            ''' <summary>Digitálna podpisová podložka - spôsob používania časového servera pre časovú pečiatku.</summary>
            Public Property TimeStampMode As enm_SignaturePad_TimeStampMode


            ''' <summary>Url vlastného časového servera, ktorý sa má použiť namiesto predvoleného.</summary>
            Public Property TimeStampServerUrl As String


        End Class

#End Region

#Region " System Function "


        ''' <summary>
        ''' Vráti model zariadenia (číslo) podľa známeho názvu - to je možné pretypovať na príslušný ENUM podľa typu zariadenia.
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. fiškálne zariadenie, platobný terminál a podobne.</param>
        ''' <param name="u_DeviceModelName">Názov modelu zariadenia daného typu (príslušný Description ENUM-u modelu zariadenia).</param>        
        Public Shared Function GetDeviceModelNum(ByVal u_DeviceType As enm_Devices_Type,
                                                 ByVal u_DeviceModelName As String) As Integer

            Dim tmp_ReturnValue As Integer = 0
            Static lc_Static_ShowError_GetDeviceModelNum_NotFound As Boolean

            Try

                Select Case u_DeviceType

                    Case enm_Devices_Type.BarCodeScanner
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_BarCodeScannerModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.CashRegister
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_CashRegister_Model), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.FiskalModule
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_FiskalModule_Model), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.PrinterReceipt
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_FiskalPrinter_Models), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.PrinterKitchen
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PrinterKitchen_Model), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.DisplayCustomer
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_DisplayCustomerModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.ElectronicScale
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_ElectronicScaleModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.DoorKey
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_DoorKey_Model), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.PID
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PID_Model), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.PDA
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PDA_Model), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.AttendanceTerminal
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_AttendanceTerminalModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.PaymentTerminal
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PaymentTerminalModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.DocumentReader
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_DocumentReaderModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.SignaturePad
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_SignaturePadModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))

                    Case enm_Devices_Type.PriceLabels
                        tmp_ReturnValue = CInt(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PriceLabelsModel), u_DeviceModelName, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue))


                    Case Else

#If DEBUG Then
                        If lc_Static_ShowError_GetDeviceModelNum_NotFound = False Then
                            EXC.Throw($"Nebol nájdený model zariadenia pre neznámy typ zariadenia '{u_DeviceType}'.")
                        End If
#End If
                        lc_Static_ShowError_GetDeviceModelNum_NotFound = True

                End Select

            Catch ex As Exception

            End Try

            Return tmp_ReturnValue

        End Function

        ''' <summary>
        ''' Vráti model zariadenia (názov) podľa známeho čísla ENUM-u daného typu zariadenia.
        ''' </summary>
        ''' <param name="u_DeviceType">Typ zariadenia, napr. fiškálne zariadenie, platobný terminál a podobne.</param>
        ''' <param name="u_DeviceModelNumber">Číslo modelu zariadenia daného typu (príslušný ENUM modelu zariadenia).</param>        
        Public Shared Function GetDeviceModelName(ByVal u_DeviceType As enm_Devices_Type,
                                                  ByVal u_DeviceModelNumber As Integer) As String


            Static lc_Static_ShowError_GetDeviceModelName_NotFound As Boolean

            Try

                Select Case u_DeviceType

                    Case enm_Devices_Type.BarCodeScanner
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_BarCodeScannerModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.CashRegister
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_CashRegister_Model), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.FiskalModule
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_FiskalModule_Model), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.PrinterReceipt
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_FiskalPrinter_Models), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.PrinterKitchen
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PrinterKitchen_Model), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.DisplayCustomer
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_DisplayCustomerModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.ElectronicScale
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_ElectronicScaleModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.DoorKey
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_DoorKey_Model), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.PID
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PID_Model), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.PDA
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PDA_Model), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.AttendanceTerminal
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_AttendanceTerminalModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.PaymentTerminal
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PaymentTerminalModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.DocumentReader
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_DocumentReaderModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.SignaturePad
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_SignaturePadModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))

                    Case enm_Devices_Type.PriceLabels
                        Return CStr(Exa.Basic.CodeDom.Enum.EnumFindItem(GetType(enm_PriceLabelsModel), u_DeviceModelNumber, Exa.Basic.CodeDom.Enum.EnumItemTypes.EnumValue, Exa.Basic.CodeDom.Enum.EnumItemTypes.AttributeDescription))


                    Case Else

#If DEBUG = True Then
                        If lc_Static_ShowError_GetDeviceModelName_NotFound = False Then
                            EXC.Throw($"Nebol nájdený model zariadenia pre neznámy typ zariadenia '{u_DeviceType}'.")
                        End If
#End If
                        lc_Static_ShowError_GetDeviceModelName_NotFound = True

                End Select

                Return Nothing

            Catch ex As Exception

                Return "Nenájdený (ERR)"

            End Try

        End Function


        ''' <summary>Vytvorí databázové tabuľky pre zariadenie - Fiškálny modul.</summary>
        Public Shared Function CreateTableStructure_CashRegister(ByVal u_CommonManagement As Exa.Database.CommonManagement, ByVal u_TableName_Number As String) As EXC.ExaException

            On Error Resume Next

            Dim myEx As EXC.ExaException
            Dim tmpTableName$

            CreateTableStructure_CashRegister = EXC.GetDefault()

            Dim m_ExaException As EXC.ExaException = Nothing


            '-------------------------------------
            '--- Pokladničné doklady - hlavičky dokladov ---	
            '-------------------------------------
            Dim m_Columns As New Exa.Database.Providers.cls_ColumnCollection

            With m_Columns
                .Add("ID", "PK_ID")
                .Add("sys_lock_protection", Database.enm_DataTypes.Long)
                .Add("IDNum", Database.enm_DataTypes.Long)
                .Add("RecordGUID", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 50))

                .Add("ID_Balance", Database.enm_DataTypes.Long)

                .Add("ComputeMode_Flag", Database.enm_DataTypes.Byte)
                .Add("BillComputeState", Database.enm_DataTypes.Byte)
                .Add("DateTime_Bill", Database.enm_DataTypes.DateTime)
                .Add("Number_Bill", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 20))

                .Add("VatRateSt", Database.enm_DataTypes.Decimal)
                .Add("VatRateR1", Database.enm_DataTypes.Decimal)
                .Add("VatRateR2", Database.enm_DataTypes.Decimal)
                .Add("VatRateR3", Database.enm_DataTypes.Decimal)

                .Add("VatBaseZero", Database.enm_DataTypes.Decimal)
                .Add("VatBaseSt", Database.enm_DataTypes.Decimal)
                .Add("VatBaseR1", Database.enm_DataTypes.Decimal)
                .Add("VatBaseR2", Database.enm_DataTypes.Decimal)
                .Add("VatBaseR3", Database.enm_DataTypes.Decimal)

                .Add("VatValueSt", Database.enm_DataTypes.Decimal)
                .Add("VatValueR1", Database.enm_DataTypes.Decimal)
                .Add("VatValueR2", Database.enm_DataTypes.Decimal)
                .Add("VatValueR3", Database.enm_DataTypes.Decimal)

                .Add("PriceTotal", Database.enm_DataTypes.Decimal)

                .Add("TipsService1", Database.enm_DataTypes.Decimal)
                .Add("TipsService2", Database.enm_DataTypes.Decimal)
                .Add("TipsPreparation1", Database.enm_DataTypes.Decimal)
                .Add("TipsPreparation2", Database.enm_DataTypes.Decimal)

                .Add("PaymentType_Text", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("Notice", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("BusinessPartner_IDNum", Database.enm_DataTypes.Long)
                .Add("BusinessPartner_Name", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))
                .Add("BusinessPartner_City", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 100))

                '--- Fieldy pri transport údajov
                myEx = Exa.OBERON.ApplicationEnvironment.OBERON.CreateTableStructure_Columns_Flags(m_Columns)
                If myEx.Result = False Then
                    CreateTableStructure_CashRegister = EXC.Get(myEx)
                    GoTo ExitFunction
                End If

                .Add("DocumentClassification", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("LS_IsBenefitsCumulate", Database.enm_DataTypes.Byte)
                .Add("LS_IsBenefitsApply", Database.enm_DataTypes.Byte)
                .Add("LS_CardNumber", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 100))
                .Add("LS_TransactionPlace", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("BillLotteryData", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("FSNumber", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 50))

                .Add("FSCustomerId", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 50))
                .Add("FSSellerId", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 50))


                .Add("User_Add", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 10))
                .Add("User_Payment", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 10))

                .Add("Journal_Binary", New Database.stc_DataTypeValues(Database.enm_DataTypes.Binary))
                .Add("XMLData", New Database.stc_DataTypeValues(Database.enm_DataTypes.String))

            End With

            tmpTableName$ = CONST_TableName_Bill_Headers & u_TableName_Number
            myEx = u_CommonManagement.Table_Create(tmpTableName$, m_Columns)
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- Indexy ---
            myEx = u_CommonManagement.Index_Create(tmpTableName$, "IDNum", "IDNum")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            myEx = u_CommonManagement.Index_Create(tmpTableName$, "ID_Balance", "ID_Balance")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If


            myEx = u_CommonManagement.Index_Create(tmpTableName$, "DateTime_Bill", "DateTime_Bill")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '-------------------------------------
            '--- Pokladničné doklady - Položky ---
            '-------------------------------------
            m_Columns = New Exa.Database.Providers.cls_ColumnCollection

            With m_Columns
                .Add("ID", "PK_ID")
                .Add("IDNum", Database.enm_DataTypes.Long)
                .Add("IDNum_Bill", Database.enm_DataTypes.Long)
                .Add("Stock_IDNum", Database.enm_DataTypes.Long)
                .Add("StockCard_IDNum", Database.enm_DataTypes.Long)
                .Add("StockCard_Number", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 30))
                .Add("StockCard_Name", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("Unit", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 20))
                .Add("UnitOther", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 20))
                .Add("SalesPoint", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 100))
                .Add("VAT_Rate", Database.enm_DataTypes.Byte)

                .Add("DateTime_Outgoing", Database.enm_DataTypes.DateTime)
                .Add("Date_Stock_Move", Database.enm_DataTypes.DateTime)
                .Add("Discount", Database.enm_DataTypes.Double)

                .Add("Amount_Unit", Database.enm_DataTypes.Double)
                .Add("Amount_UnitOther", Database.enm_DataTypes.Double)

                .Add("Price_WithoutVAT_Unit", Database.enm_DataTypes.Double)
                .Add("Price_WithoutVAT", Database.enm_DataTypes.Double)

                .Add("Price_WithVAT_Unit", Database.enm_DataTypes.Double)
                .Add("Price_WithVAT", Database.enm_DataTypes.Double)
                .Add("Price_WithVAT_WithoutDiscount", Database.enm_DataTypes.Double)

                .Add("IDNumStockCardVariant", Database.enm_DataTypes.Long)
                .Add("VariantName", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))
                .Add("Notice", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))
                .Add("BarCode", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 50))

                .Add("Item_Compute_Flag", Database.enm_DataTypes.Byte)

                .Add("SerialNumbers_Mode", Database.enm_DataTypes.Byte)
                .Add("Price_ActionIn_IDNum", Database.enm_DataTypes.Long)

                .Add("DocumentSource_Type", Database.enm_DataTypes.Byte)
                .Add("DocumentSource_IDNum", Database.enm_DataTypes.Long)
                .Add("DocumentSource_Number", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 30))
                .Add("DocumentSource_Data", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))

                .Add("User_Add", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 10))
            End With


            tmpTableName$ = CONST_TableName_Bill_Items & u_TableName_Number
            myEx = u_CommonManagement.Table_Create(tmpTableName$, m_Columns)
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- Indexy ---
            myEx = u_CommonManagement.Index_Create(tmpTableName$, "IDNum", "IDNum")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            myEx = u_CommonManagement.Index_Create(tmpTableName$, "IDNum_Bill", "IDNum_Bill")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            myEx = u_CommonManagement.Index_Create(tmpTableName$, "Date_Stock_Move", "Date_Stock_Move")            '--- Potrebné pre vytvorenie skladových pohybov (výrazne skracuje dĺžku načítania)
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If


            '-------------------------------------
            '--- Pokladničné doklady - Typy platieb ---
            '-------------------------------------
            m_Columns = New Exa.Database.Providers.cls_ColumnCollection

            With m_Columns
                .Add("ID", "PK_ID")
                .Add("IDNum_Bill", Database.enm_DataTypes.Long)
                .Add("Compute_Mode", Database.enm_DataTypes.Long)
                .Add("PaymentType_Name", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 100))
                .Add("Price", Database.enm_DataTypes.Double)
                .Add("FC_Currency_Code", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 20))
                .Add("FC_ExchangeRate", Database.enm_DataTypes.Double)
                .Add("FC_Price", Database.enm_DataTypes.Double)
                .Add("PaymentTransactionData", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))
            End With

            tmpTableName$ = CONST_TableName_BillPaymentTypes & u_TableName_Number
            myEx = u_CommonManagement.Table_Create(tmpTableName$, m_Columns)
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- Indexy ---
            myEx = u_CommonManagement.Index_Create(tmpTableName$, "IDNum_Bill", "IDNum_Bill")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '-----------------------------------------------------------
            '--- Pokladničné doklady - hotovosť a aj výbery a vklady ---
            '-----------------------------------------------------------
            m_Columns = New Exa.Database.Providers.cls_ColumnCollection

            With m_Columns
                .Add("ID", "PK_ID")
                .Add("ID_Balance", Database.enm_DataTypes.Long)
                .Add("Bill_Header_IDNum", Database.enm_DataTypes.Long)
                .Add("Cash_Flag", Database.enm_DataTypes.Byte)
                .Add("Bill_Number", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 20))
                .Add("Cash_Date_Time", Database.enm_DataTypes.DateTime)
                .Add("Price", Database.enm_DataTypes.Double)
                .Add("Cash_In_Price", Database.enm_DataTypes.Double)
                .Add("Cash_In_CurrencyCode", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 10))
                .Add("Cash_In_ExchangeRate", Database.enm_DataTypes.Double)
                .Add("Cash_Out_Price", Database.enm_DataTypes.Double)
                .Add("Cash_Out_CurrencyCode", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 20))
                .Add("Cash_Out_ExchangeRate", Database.enm_DataTypes.Double)
                .Add("User_Add", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 10))
                .Add("Description", Database.enm_DataTypes.String) 'MEMO
                .Add("Notice", New Database.stc_DataTypeValues(Database.enm_DataTypes.Char, 255))
            End With


            tmpTableName$ = CONST_TableName_Stock_CashRegister_Cash & u_TableName_Number
            myEx = u_CommonManagement.Table_Create(tmpTableName$, m_Columns)
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If

            '--- Indexy ---
            myEx = u_CommonManagement.Index_Create(tmpTableName$, "Bill_Header_IDNum", "Bill_Header_IDNum")
            If myEx.Result = False Then
                CreateTableStructure_CashRegister = EXC.Get(myEx)
                GoTo ExitFunction
            End If


            CreateTableStructure_CashRegister.Result = True

ExitFunction:


        End Function


        ''' <summary>Pri vytvorení (zadefinovaní) zariadenia do systému OBERON typu Fiškálny modul metóda zapíše predvolené hodnoty do číselníka výberov a vkladov hotovosti v pokladnici,
        ''' napr. Počiatočný vklad, Odvod tržby a podobne.</summary>
        Public Shared Function WriteFiscalModuleCashTypesDefaultData(ByVal u_CommonData As Exa.Database.CommonData, ByVal u_IDNumDevice As Long) As EXC.ExaException

            On Error Resume Next

            WriteFiscalModuleCashTypesDefaultData = EXC.GetDefault

            Dim myEx As EXC.ExaException
            Dim tmp_SQLValuesList As List(Of String)
            Dim tmp_SQLBase As String = String.Format("INSERT INTO {0} ({1}, {2}, {3}, {4}, {5})", CONST_TableName_Stock_CashRegister_CashTypes,
                                                                                           DB.C_FIELD_NAME_SORT_ORDER,
                                                                                           "IDNumDevice",
                                                                                           "Name",
                                                                                           "CashType",
                                                                                           "AccountCoding")
            Dim tmp_SQLBaseValues As String = " VALUES ({0}, {1}, {2}, {3}, {4})"
            Dim tmp_SQLValues As String

            If u_CommonData Is Nothing Then
                WriteFiscalModuleCashTypesDefaultData = EXC.Get("Chybný parameter 'u_CommonData.'")
                GoTo ExitFunction
            End If

            If u_IDNumDevice = 0 Then
                WriteFiscalModuleCashTypesDefaultData = EXC.Get("Je potrebné zadať jednoznačný identifikátor zariadenia.")
                GoTo ExitFunction
            End If

            '--- Zoznam SQL - potom sa bude hromadne spúšťať ---
            tmp_SQLValuesList = New List(Of String)

            '--- Vygenerovať dáta ---
            tmp_SQLValues = String.Format(tmp_SQLBaseValues, 10, u_IDNumDevice, Exa.Database.ConvertFunctions.ToSQLString(Exa.Application.TranslateText("Počiatočný vklad"), u_CommonData), 11, "NULL")
            tmp_SQLValuesList.Add(tmp_SQLBase & tmp_SQLValues)

            tmp_SQLValues = String.Format(tmp_SQLBaseValues, 20, u_IDNumDevice, Exa.Database.ConvertFunctions.ToSQLString(Exa.Application.TranslateText("Vklad do pokladnice"), u_CommonData), 12, "NULL")
            tmp_SQLValuesList.Add(tmp_SQLBase & tmp_SQLValues)

            tmp_SQLValues = String.Format(tmp_SQLBaseValues, 50, u_IDNumDevice, Exa.Database.ConvertFunctions.ToSQLString(Exa.Application.TranslateText("Odvod tržby"), u_CommonData), 21, "NULL")
            tmp_SQLValuesList.Add(tmp_SQLBase & tmp_SQLValues)

            tmp_SQLValues = String.Format(tmp_SQLBaseValues, 60, u_IDNumDevice, Exa.Database.ConvertFunctions.ToSQLString(Exa.Application.TranslateText("Výber z pokladnice"), u_CommonData), 22, "NULL")
            tmp_SQLValuesList.Add(tmp_SQLBase & tmp_SQLValues)

            '--- Zapísať údaje ---
            For i As Integer = 0 To tmp_SQLValuesList.Count - 1
                myEx = u_CommonData.ExecuteQuery(tmp_SQLValuesList(i))
                If myEx.Result = False Then
                    '--- ERR ---
                    WriteFiscalModuleCashTypesDefaultData = EXC.Get(myEx)
                    GoTo ExitFunction
                End If
            Next


            WriteFiscalModuleCashTypesDefaultData.Result = True

ExitFunction:


        End Function


#End Region

#Region " METHODS PRIVATE - XML"


        ''' <summary>Metóda slúži na načítanie hodnôt niektorých vlastností z XML údajov.</summary>
        Private Function z_XMLInternalData_Load() As Exa.Basic.Exceptions.mod_Exceptions.ExaException
            On Error Resume Next

            z_XMLInternalData_Load = Exa.Basic.Exceptions.GetDefault

            Dim myEx As Exa.Basic.Exceptions.ExaException
            Dim tmp_XML_Element_Parser As Exa.Basic.XML.XML_Element_Parser = Nothing
            Dim tmp_XMLDocument As System.Xml.XmlDocument = Nothing
            Dim tmp_XML_Element_Root As System.Xml.XmlElement = Nothing
            Dim tmp_XMLNode_Items_List As Xml.XmlNodeList = Nothing
            Dim tmp_ValueString As String = String.Empty
            Dim tmp_ValueInteger As Integer

            '--- Default hodnoty 
            Me.dev_FiscalModule.BillRegisterDelay = False
            Me.dev_FiscalModule.eKasa_ECM_RunMode = cls_d_FiscalModule.enm_eKasa_ECM_RunMode.None

            ' pred načítaním vymaž
            Me.Device_Params.Clear()

            If Me.XMLInternalData = String.Empty Then
                '--- Ešte nebolo nič uložené ---
                GoTo EndFunction  '--- OK
            End If

            myEx = Exa.Basic.XML.LoadXmlData(Me.XMLInternalData, CONST_XmlInternal_ElementName_DocumentRoot, tmp_XMLDocument)
            If myEx.Result = False Then
                z_XMLInternalData_Load = Exa.Basic.Exceptions.Get("Chyba pri načítaní XML dokumentu.", myEx)
                GoTo ExitFunction
            End If

            '--- XML element parser --
            tmp_XML_Element_Parser = New Exa.Basic.XML.XML_Element_Parser(tmp_XMLDocument)
            With tmp_XML_Element_Parser
                .Settings.NotExistingElement_Create = True
                .Settings.Disable_Convert_XML_Text = False
            End With
            myEx = tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_DocumentRoot)
            If myEx.Result = False Then
                z_XMLInternalData_Load = Exa.Basic.Exceptions.Get("Chybná štruktúra XML dokumentu.", myEx)
                GoTo ExitFunction
            End If

            tmp_XML_Element_Root = tmp_XML_Element_Parser.GetRootElement

            '---------------------
            '--- Kitchen Printer ---
            '---------------------

            Select Case Me.Device_Type

                Case enm_Devices_Type.FiskalModule
                    '---------------------------
                    '--- Fiškálne zariadenia ---
                    '---------------------------
                    tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_FiscalDevice)

                    tmp_XML_Element_Parser.GetNodeValue(Of Boolean)("BillRegisterDelay", False, Me.dev_FiscalModule.BillRegisterDelay, u_Required:=False)

                    tmp_XML_Element_Parser.GetNodeValue(Of Integer)("eKasa_ECM_Mode", 0, tmp_ValueInteger, False)
                    Me.dev_FiscalModule.eKasa_ECM_RunMode = CType(tmp_ValueInteger, cls_d_FiscalModule.enm_eKasa_ECM_RunMode)

                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.PrinterKitchen
                    '---------------------------
                    '--- Bonovacie tlačiarne ---
                    '---------------------------

                    tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_KitchenPrinter)

                    tmp_XML_Element_Parser.GetNodeValue(Of String)("ReportNameOrder", "Objednávka", tmp_ValueString, u_Required:=False)
                    Me.dev_PrinterKitchen.ReportNameOrder = tmp_ValueString

                    tmp_XML_Element_Parser.GetNodeValue(Of String)("ReportNameOrderAnulment", "Storno objednávky", tmp_ValueString, u_Required:=False)
                    Me.dev_PrinterKitchen.ReportNameOrderAnulment = tmp_ValueString

                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.AttendanceTerminal
                    '---------------------------
                    '--- Dochádzkové terminály -
                    '---------------------------

                    'Default hodnoty
                    If Me.dev_AttendanceTerminal.Monitor_IPEndPoint Is Nothing Then
                        Me.dev_AttendanceTerminal.Monitor_IPEndPoint = New System.Net.IPEndPoint(Net.IPAddress.Any, 0)
                    End If

                    'myEx = tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_AttendanceTerminal)
                    'If myEx.Result = True Then

                    Dim m_AtendanceElement As Xml.XmlElement = tmp_XML_Element_Root.GetElementsByTagName(CONST_XmlInternal_ElementName_AttendanceTerminal).OfType(Of Xml.XmlElement).FirstOrDefault
                    If m_AtendanceElement IsNot Nothing Then
                        tmp_XML_Element_Parser.SetParentElement(m_AtendanceElement)

                        tmp_XML_Element_Parser.GetNodeValue(Of Integer)("Monitor_IPPort", Me.dev_AttendanceTerminal.Monitor_IPEndPoint.Port, Me.dev_AttendanceTerminal.Monitor_IPEndPoint.Port, u_Required:=False)
                        tmp_XML_Element_Parser.GetNodeValue(Of String)("Monitor_IPAddr", "", tmp_ValueString, u_Required:=False)
                        If tmp_ValueString <> String.Empty Then System.Net.IPAddress.TryParse(tmp_ValueString, Me.dev_AttendanceTerminal.Monitor_IPEndPoint.Address)

                        tmp_XML_Element_Parser.GetNodeValue(Of String)("DeviceModel", Me.dev_AttendanceTerminal.DeviceModel, Me.dev_AttendanceTerminal.DeviceModel, u_Required:=False)

                        tmp_XML_Element_Parser.GetNodeValue(Of Integer)("CompanyId", Me.dev_AttendanceTerminal.CompanyId, Me.dev_AttendanceTerminal.CompanyId, u_Required:=False)

                        'Načítaj zoznam spárovaných typov prechodov
                        With Me.dev_AttendanceTerminal.ShortCut_List
                            .Clear()

                            myEx = tmp_XML_Element_Parser.GetNodeList(u_NodePath:="TimeSheet_Types/Item", urf_NodeList:=tmp_XMLNode_Items_List)
                            If myEx.Result = True AndAlso tmp_XMLNode_Items_List IsNot Nothing Then
                                For Each e_XmlItem As Xml.XmlElement In tmp_XMLNode_Items_List.OfType(Of Xml.XmlElement)()
                                    Dim m_ShortCutPair As New cls_d_AttendanceTerminal.cls_ShortCutPair With {
                                       .Terminal_ShortCut = e_XmlItem.GetAttribute("Terminal"),
                                        .Attendance_ShortCut = e_XmlItem.GetAttribute("Attendance")
                                    }

                                    If m_ShortCutPair.Terminal_ShortCut <> String.Empty AndAlso m_ShortCutPair.Attendance_ShortCut <> String.Empty Then
                                        If Integer.TryParse(e_XmlItem.GetAttribute("Id"), m_ShortCutPair.Terminal_ShortCutID) = False Then
                                            m_ShortCutPair.Terminal_ShortCutID = -1
                                        End If
                                        .Add(m_ShortCutPair)
                                    End If
                                Next
                            End If
                        End With

                        tmp_XML_Element_Parser.GetNodeValue(Of Date)("DateUtcFrom", Nothing, Me.dev_AttendanceTerminal.DateUtcFrom, u_Required:=False)
                        DateTime.SpecifyKind(Me.dev_AttendanceTerminal.DateUtcFrom, DateTimeKind.Utc)

                    End If


                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.BarCodeScanner
                    '---------------------------
                    '--- Snímač čiarového kódu -
                    '---------------------------
                    'Default hodnoty
                    Me.dev_BarCode_Scanner.WeightBarCodeDisable = False

                    myEx = tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_BarCodeScanner)
                    If myEx.Result = True Then
                        tmp_XML_Element_Parser.GetNodeValue(Of String)("PrefixBarCode", "", Me.dev_BarCode_Scanner.PrefixBarCode, u_Required:=True)
                        tmp_XML_Element_Parser.GetNodeValue(Of Boolean)("WeightBarCode_Disable", Me.dev_BarCode_Scanner.WeightBarCodeDisable, Me.dev_BarCode_Scanner.WeightBarCodeDisable, u_Required:=True)
                    End If

                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)


                Case enm_Devices_Type.PaymentTerminal
                    '---------------------------
                    '--- Platobné terminály -
                    '---------------------------
                    myEx = tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_PaymentTerminal)

                    tmp_XML_Element_Parser.GetNodeValue(Of String)("TerminalId", "POS001", tmp_ValueString, u_Required:=False)
                    Me.dev_PaymentTerminal.TerminalId = tmp_ValueString

                    tmp_XML_Element_Parser.GetNodeValue(Of String)("CashId", "CASH001", tmp_ValueString, u_Required:=False)
                    Me.dev_PaymentTerminal.CashId = tmp_ValueString

                    tmp_XML_Element_Parser.GetNodeValue(Of String)("TerminalDesc", Nothing, tmp_ValueString, u_Required:=False)
                    Me.dev_PaymentTerminal.TerminalDesc = tmp_ValueString

                    Select Case Me.dev_PaymentTerminal.PaymentTerminalModel

                        Case enm_PaymentTerminalModel.GpTom
                            Dim m_Name As String = Nothing
                            Dim m_Pwd As String = Nothing

                            tmp_XML_Element_Parser.GetNodeValue(Of String)("CloudAccountName", Nothing, m_Name, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("CloudAccountPassword", Nothing, m_Pwd, u_Required:=False)
                            m_Pwd = Exa.Basic.Security.Crypto.DecryptTextUTF8(m_Pwd, C_CRYPTO_KEY)
                            Me.dev_PaymentTerminal.CloudCredential = New Net.NetworkCredential(m_Name, m_Pwd)

                            tmp_XML_Element_Parser.GetNodeValue(Of String)("MerchantAccountName", Nothing, m_Name, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("MerchantAccountPassword", Nothing, m_Pwd, u_Required:=False)
                            m_Pwd = Exa.Basic.Security.Crypto.DecryptTextUTF8(m_Pwd, C_CRYPTO_KEY)
                            Me.dev_PaymentTerminal.MerchantCredential = New Net.NetworkCredential(m_Name, m_Pwd)

                            tmp_XML_Element_Parser.GetNodeValue(Of String)("ApiKey", Nothing, Me.dev_PaymentTerminal.ApiKey, u_Required:=False)

                        Case enm_PaymentTerminalModel.Teya
                            Dim m_ClientId As String = Nothing
                            Dim m_ClientSecret As String = Nothing
                            'Nastavenia načítané z XMLInternalData
                            'ClientId a ClientSecret sú nastavené napevno pre alikáciu OBERON v účte pre developerov
                            'tmp_XML_Element_Parser.GetNodeValue(Of String)("ClientId", Nothing, m_ClientId, u_Required:=False)
                            'tmp_XML_Element_Parser.GetNodeValue(Of String)("ClientSecret", Nothing, m_ClientSecret, u_Required:=False)
                            'm_ClientSecret = Exa.Basic.Security.Crypto.DecryptTextUTF8(m_ClientSecret, C_CRYPTO_KEY)
                            'Me.dev_PaymentTerminal.CloudCredential = New Net.NetworkCredential(m_ClientId, m_ClientSecret)

                            tmp_XML_Element_Parser.GetNodeValue(Of String)("StoreId", Nothing, Me.dev_PaymentTerminal.StoreId, u_Required:=False)

                        Case enm_PaymentTerminalModel.SoftPlusTicket
                            Dim m_Name As String = Nothing
                            Dim m_Pwd As String = Nothing
                            Dim m_Url As String = Nothing

                            tmp_XML_Element_Parser.GetNodeValue(Of String)("LoginName", Nothing, m_Name, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("LoginPassword", Nothing, m_Pwd, u_Required:=False)
                            m_Pwd = Exa.Basic.Security.Crypto.DecryptTextUTF8(m_Pwd, C_CRYPTO_KEY)
                            Me.dev_PaymentTerminal.MerchantCredential = New Net.NetworkCredential(m_Name, m_Pwd)

                            tmp_XML_Element_Parser.GetNodeValue(Of String)("CloudUrl", Nothing, m_Url, u_Required:=False)
                            Uri.TryCreate(m_Url, UriKind.Absolute, Me.dev_PaymentTerminal.CloudUrl)

                        Case enm_PaymentTerminalModel.Printec
                            tmp_XML_Element_Parser.GetNodeValue(Of Boolean)("PrintOnTerminal", False, Me.dev_PaymentTerminal.PrintOnTerminal, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of Boolean)("PrintReceiptMerchant", False, Me.dev_PaymentTerminal.PrintReceiptMerchant, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of Boolean)("RequestTip", False, Me.dev_PaymentTerminal.RequestTipEnable, u_Required:=False)

                        Case enm_PaymentTerminalModel.FsInstantQrPay
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("ClientCert", Nothing, Me.dev_PaymentTerminal.ClientCertificate, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("IBAN", Nothing, Me.dev_PaymentTerminal.BankIBAN, u_Required:=False)
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("BankAccountName", Nothing, Me.dev_PaymentTerminal.BankAccountName, u_Required:=False)


                    End Select

                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)


                Case enm_Devices_Type.SignaturePad
                    '---------------------------
                    '--- Podpisová podložka -
                    '---------------------------

                    Me.dev_SignaturePad.TimeStampMode = enm_SignaturePad_TimeStampMode.Default

                    If tmp_XML_Element_Parser.ElementExists(CONST_XmlInternal_ElementName_SignaturePad).Result = False Then
                        '--- Staršia verzia údajov zariadenie neobsahuje element tak to tu do nekonečna padá

                    Else
                        '--- Element existuje tak robme niečo
                        myEx = tmp_XML_Element_Parser.SetParentElement(CONST_XmlInternal_ElementName_SignaturePad)
                        If myEx.Result = True Then
                            tmp_XML_Element_Parser.GetNodeValue(Of Integer)("TimeStampMode", 0, tmp_ValueInteger, u_Required:=False)
                            Me.dev_SignaturePad.TimeStampMode = CType(tmp_ValueInteger, enm_SignaturePad_TimeStampMode)
                            tmp_XML_Element_Parser.GetNodeValue(Of String)("TimeStampServerUrl", "", Me.dev_SignaturePad.TimeStampServerUrl, u_Required:=False)
                        End If

                        '--- Návrat na root --
                        tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)
                    End If

                Case enm_Devices_Type.DisplayCustomer
                    '----------------------------------------
                    '--- Zákaznícky display na pokladnici. -
                    '----------------------------------------


            End Select

            '--- Návrat na root --
            tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

            'Nepoužije sa metóda Parser-u, lebo pri chýbajúcom elemente vypisuje chybu o nenájdení elementu
            Dim m_XmlElement As Xml.XmlElement = TryCast(tmp_XML_Element_Parser.ParentElement.SelectSingleNode(CONST_XmlInternal_ElementName_DeviceParams), Xml.XmlElement)
            If m_XmlElement IsNot Nothing AndAlso m_XmlElement.ChildNodes.Count > 0 Then
                'Načítaj uložené hodnoty do zoznamu pre použitie v zariadení
                For Each e_XmlItem As Xml.XmlElement In m_XmlElement.ChildNodes.OfType(Of Xml.XmlElement)()
                    If e_XmlItem.Name <> String.Empty Then
                        Me.Device_Params(e_XmlItem.Name) = e_XmlItem.InnerText
                    End If
                Next
            End If

            '---------------------------------------------
            '--- Záverečný test na chyby -- 
            '---------------------------------------------
            If tmp_XML_Element_Parser.Log.Error_Count <> 0 Then
                '--- Pri exporte sa vyskytli chyby
                Dim tmp_Str$ = "Pri načítaní XML dokumentu sa vyskytli chyby (celkom {0})."
                tmp_Str$ = String.Format(tmp_Str$, tmp_XML_Element_Parser.Log.Error_Count)
                z_XMLInternalData_Load.Description = tmp_Str$ & vbCrLf & vbCrLf & tmp_XML_Element_Parser.Log.Errors_ToString
                GoTo ExitFunction
            End If

            If tmp_XML_Element_Parser.Log.Warning_Count <> 0 Then
                '--- Pri načítaní sa vyskytli varovania
                Dim tmp_Str$ = "Pri načítaní XML dokumentu sa vyskytli problémy (celkom {0})."
                tmp_Str$ = String.Format(tmp_Str$, tmp_XML_Element_Parser.Log.Error_Count)
                z_XMLInternalData_Load.Description = tmp_Str$ & vbCrLf & vbCrLf & tmp_XML_Element_Parser.Log.Warnings_ToString
                z_XMLInternalData_Load.IsWarning = True
            End If

EndFunction:

            z_XMLInternalData_Load.Result = True

ExitFunction:

            If tmp_XMLNode_Items_List IsNot Nothing Then
                tmp_XMLNode_Items_List = Nothing
            End If

            If tmp_XML_Element_Parser IsNot Nothing Then
                tmp_XML_Element_Parser.Dispose()
                tmp_XML_Element_Parser = Nothing
            End If

            If tmp_XMLDocument IsNot Nothing Then
                tmp_XMLDocument = Nothing
            End If


        End Function


        ''' <summary>Metóda slúži na dodatočné uloženie XML údajov.</summary>
        Private Function z_XMLInternalData_Save() As Exa.Basic.Exceptions.mod_Exceptions.ExaException
            On Error Resume Next

            z_XMLInternalData_Save = Exa.Basic.Exceptions.GetDefault

            Dim myEx As Exa.Basic.Exceptions.ExaException
            Dim tmp_XML_Element_Parser As Exa.Basic.XML.XML_Element_Parser = Nothing
            Dim tmp_XMLDocument As System.Xml.XmlDocument = Nothing
            Dim tmp_XML_Element_Root As System.Xml.XmlElement = Nothing
            Dim tmp_XMLNode_Items_List As Xml.XmlNodeList = Nothing

            myEx = Exa.Basic.XML.CreateXmlData(CONST_XmlInternal_ElementName_DocumentRoot, tmp_XMLDocument)
            If myEx.Result = False Then
                z_XMLInternalData_Save = Exa.Basic.Exceptions.Get("Chyba pri vytváraní XML dokumentu.", myEx)
                GoTo ExitFunction
            End If

            '--- inicializácia parsera
            tmp_XML_Element_Parser = New Exa.Basic.XML.XML_Element_Parser(tmp_XMLDocument, CONST_XmlInternal_ElementName_DocumentRoot)

            tmp_XML_Element_Root = tmp_XML_Element_Parser.ParentElement


            Select Case Me.Device_Type

                Case enm_Devices_Type.FiskalModule
                    '---------------------------
                    '--- Fiškálne zariadenia ---
                    '---------------------------

                    tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_FiscalDevice, u_SetParentElement:=True)

                    tmp_XML_Element_Parser.SetNodeValue(Of Boolean)("BillRegisterDelay", Me.dev_FiscalModule.BillRegisterDelay, False)
                    tmp_XML_Element_Parser.SetNodeValue(Of Integer)("eKasa_ECM_Mode", Me.dev_FiscalModule.eKasa_ECM_RunMode, False)

                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)


                Case enm_Devices_Type.PrinterKitchen
                    '---------------------------
                    '--- Bonovacie tlačiarne ---
                    '---------------------------

                    tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_KitchenPrinter, u_SetParentElement:=True)

                    tmp_XML_Element_Parser.SetNodeValue("ReportNameOrder", Me.dev_PrinterKitchen.ReportNameOrder, True)
                    tmp_XML_Element_Parser.SetNodeValue("ReportNameOrderAnulment", Me.dev_PrinterKitchen.ReportNameOrderAnulment, True)

                    '--- Návrat na root --
                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.AttendanceTerminal
                    '---------------------------
                    '--- Dochádzkové terminály -
                    '---------------------------

                    tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_AttendanceTerminal, u_SetParentElement:=True)

                    If Me.dev_AttendanceTerminal.Monitor_IPEndPoint Is Nothing Then
                        Me.dev_AttendanceTerminal.Monitor_IPEndPoint = New Net.IPEndPoint(Net.IPAddress.Loopback, 0)
                    End If
                    tmp_XML_Element_Parser.SetNodeValue(Of Integer)("Monitor_IPPort", Me.dev_AttendanceTerminal.Monitor_IPEndPoint.Port, False)
                    tmp_XML_Element_Parser.SetNodeValue(Of String)("Monitor_IPAddr", Me.dev_AttendanceTerminal.Monitor_IPEndPoint.Address.ToString, False)
                    tmp_XML_Element_Parser.SetNodeValue(Of String)("DeviceModel", Me.dev_AttendanceTerminal.DeviceModel, u_Required:=False)
                    tmp_XML_Element_Parser.SetNodeValue(Of Integer)("CompanyId", Me.dev_AttendanceTerminal.CompanyId, u_Required:=False)

                    'Zmazanie hodnoty, iba vytvorenie elementu
                    tmp_XML_Element_Parser.SetNodeValue(Of Date)("DateUtcFrom", Me.dev_AttendanceTerminal.DateUtcFrom, u_Required:=False)

                    tmp_XML_Element_Parser.CreateElement("TimeSheet_Types", u_SetParentElement:=True)

                    'Vytvor záznam párovania prechodov medzi terminálom a typmi prechodov v OBERON-e
                    Dim tmp_XML_Element As Xml.XmlElement = tmp_XML_Element_Parser.ParentElement
                    For Each e_Item As cls_d_AttendanceTerminal.cls_ShortCutPair In Me.dev_AttendanceTerminal.ShortCut_List

                        tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element)
                        tmp_XML_Element_Parser.CreateElement("Item", True)

                        tmp_XML_Element_Parser.SetAttributeValue(u_NodeName:="", u_AttributeName:="Id", u_Value:=e_Item.Terminal_ShortCutID)
                        tmp_XML_Element_Parser.SetAttributeValue(u_NodeName:="", u_AttributeName:="Terminal", u_Value:=e_Item.Terminal_ShortCut)
                        tmp_XML_Element_Parser.SetAttributeValue(u_NodeName:="", u_AttributeName:="Attendance", u_Value:=e_Item.Attendance_ShortCut)
                    Next


                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.BarCodeScanner
                    '---------------------------
                    '--- Snímač čiarového kódu -
                    '---------------------------

                    tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_BarCodeScanner, u_SetParentElement:=True)
                    tmp_XML_Element_Parser.SetNodeValue(Of String)("PrefixBarCode", Me.dev_BarCode_Scanner.PrefixBarCode, u_Required:=False)
                    tmp_XML_Element_Parser.SetNodeValue(Of Boolean)("WeightBarCode_Disable", Me.dev_BarCode_Scanner.WeightBarCodeDisable, u_Required:=False)

                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.PaymentTerminal
                    '---------------------------
                    '--- Platobné terminály -
                    '---------------------------

                    tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_PaymentTerminal, u_SetParentElement:=True)

                    tmp_XML_Element_Parser.SetNodeValue(Of String)("TerminalId", Me.dev_PaymentTerminal.TerminalId, u_Required:=False)
                    tmp_XML_Element_Parser.SetNodeValue(Of String)("CashId", Me.dev_PaymentTerminal.CashId, u_Required:=False)
                    tmp_XML_Element_Parser.SetNodeValue(Of String)("TerminalDesc", Me.dev_PaymentTerminal.TerminalDesc, u_Required:=False)

                    Select Case Me.dev_PaymentTerminal.PaymentTerminalModel

                        Case enm_PaymentTerminalModel.GpTom

                            Dim m_Pwd As String

                            Me.dev_PaymentTerminal.CloudCredential = If(Me.dev_PaymentTerminal.CloudCredential, New Net.NetworkCredential())
                            m_Pwd = Exa.Basic.Security.Crypto.EncryptTextUTF8(Me.dev_PaymentTerminal.CloudCredential.Password, C_CRYPTO_KEY)

                            tmp_XML_Element_Parser.SetNodeValue(Of String)("CloudAccountName", Me.dev_PaymentTerminal.CloudCredential.UserName, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("CloudAccountPassword", m_Pwd, u_Required:=False)

                            Me.dev_PaymentTerminal.MerchantCredential = If(Me.dev_PaymentTerminal.MerchantCredential, New Net.NetworkCredential())
                            m_Pwd = Exa.Basic.Security.Crypto.EncryptTextUTF8(Me.dev_PaymentTerminal.MerchantCredential.Password, C_CRYPTO_KEY)

                            tmp_XML_Element_Parser.SetNodeValue(Of String)("MerchantAccountName", Me.dev_PaymentTerminal.MerchantCredential.UserName, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("MerchantAccountPassword", m_Pwd, u_Required:=False)

                            tmp_XML_Element_Parser.SetNodeValue(Of String)("ApiKey", Me.dev_PaymentTerminal.ApiKey, u_Required:=False)

                        Case enm_PaymentTerminalModel.Teya
                            'Nastavenia ukladané v XMLInternalData - nastavené pre aplikáciu podľa údajov na portáli https://developer.teya.com/
                            'Dim m_ClientSecret As String
                            'Me.dev_PaymentTerminal.CloudCredential = If(Me.dev_PaymentTerminal.CloudCredential, New Net.NetworkCredential())
                            'm_ClientSecret = Exa.Basic.Security.Crypto.EncryptTextUTF8(Me.dev_PaymentTerminal.CloudCredential.Password, C_CRYPTO_KEY)
                            'tmp_XML_Element_Parser.SetNodeValue(Of String)("ClientId", Me.dev_PaymentTerminal.CloudCredential.UserName, u_Required:=False)
                            'tmp_XML_Element_Parser.SetNodeValue(Of String)("ClientSecret", m_ClientSecret, u_Required:=False)

                            tmp_XML_Element_Parser.SetNodeValue(Of String)("StoreId", Me.dev_PaymentTerminal.StoreId, u_Required:=False)

                        Case enm_PaymentTerminalModel.SoftPlusTicket
                            Dim m_Pwd As String

                            Me.dev_PaymentTerminal.MerchantCredential = If(Me.dev_PaymentTerminal.MerchantCredential, New Net.NetworkCredential())
                            m_Pwd = Exa.Basic.Security.Crypto.EncryptTextUTF8(Me.dev_PaymentTerminal.MerchantCredential.Password, C_CRYPTO_KEY)

                            tmp_XML_Element_Parser.SetNodeValue(Of String)("LoginName", Me.dev_PaymentTerminal.MerchantCredential.UserName, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("LoginPassword", m_Pwd, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("CloudUrl", Me.dev_PaymentTerminal.CloudUrl?.OriginalString, u_Required:=False)

                        Case enm_PaymentTerminalModel.Printec
                            tmp_XML_Element_Parser.SetNodeValue(Of Boolean)("PrintOnTerminal", Me.dev_PaymentTerminal.PrintOnTerminal, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of Boolean)("PrintReceiptMerchant", Me.dev_PaymentTerminal.PrintReceiptMerchant, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of Boolean)("RequestTip", Me.dev_PaymentTerminal.RequestTipEnable, u_Required:=False)

                        Case enm_PaymentTerminalModel.FsInstantQrPay
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("ClientCert", Me.dev_PaymentTerminal.ClientCertificate, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("IBAN", Me.dev_PaymentTerminal.BankIBAN, u_Required:=False)
                            tmp_XML_Element_Parser.SetNodeValue(Of String)("BankAccountName", Me.dev_PaymentTerminal.BankAccountName, u_Required:=False)


                    End Select

                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)


                Case enm_Devices_Type.SignaturePad
                    '---------------------------
                    '--- Podpisová podložka -
                    '---------------------------

                    tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_SignaturePad, u_SetParentElement:=True)
                    tmp_XML_Element_Parser.SetNodeValue(Of Integer)("TimeStampMode", CInt(Me.dev_SignaturePad.TimeStampMode), u_Required:=False)
                    tmp_XML_Element_Parser.SetNodeValue(Of String)("TimeStampServerUrl", Me.dev_SignaturePad.TimeStampServerUrl, u_Required:=False)

                    tmp_XML_Element_Parser.SetParentElement(tmp_XML_Element_Root)

                Case enm_Devices_Type.DisplayCustomer
                    '----------------------------------------
                    '--- Zákaznícky display na pokladnici. -
                    '----------------------------------------

            End Select

            'Pridaj rozširujúce parametre do XML
            If Me.Device_Params IsNot Nothing AndAlso Me.Device_Params.Count > 0 Then
                'Vytvor element pre uloženie hodnôt parametrov
                tmp_XML_Element_Parser.CreateElement(CONST_XmlInternal_ElementName_DeviceParams, u_SetParentElement:=True)
                For Each e_Item As KeyValuePair(Of String, String) In Me.Device_Params
                    If e_Item.Key <> String.Empty AndAlso e_Item.Value <> String.Empty Then
                        tmp_XML_Element_Parser.SetNodeValue(Of String)(e_Item.Key, e_Item.Value, u_Required:=False, u_CreateCData:=Not Security.SecurityElement.IsValidText(e_Item.Value))
                    End If
                Next
            End If


            '---------------------------------------------
            '--- Záverečný test na chyby -- 
            '---------------------------------------------
            If tmp_XML_Element_Parser.Log.Error_Count <> 0 Then
                '--- Pri exporte sa vyskytli chyby
                Dim tmp_Str$ = "Pri načítaní XML dokumentu sa vyskytli chyby (celkom {0})."
                tmp_Str$ = String.Format(tmp_Str$, tmp_XML_Element_Parser.Log.Error_Count)
                z_XMLInternalData_Save.Description = tmp_Str$ & vbCrLf & vbCrLf & tmp_XML_Element_Parser.Log.Errors_ToString
                GoTo ExitFunction
            End If

            If tmp_XML_Element_Parser.Log.Warning_Count <> 0 Then
                '--- Pri načítaní sa vyskytli varovania
                Dim tmp_Str$ = "Pri načítaní XML dokumentu sa vyskytli problémy (celkom {0})."
                tmp_Str$ = String.Format(tmp_Str$, tmp_XML_Element_Parser.Log.Error_Count)
                z_XMLInternalData_Save.Description = tmp_Str$ & vbCrLf & vbCrLf & tmp_XML_Element_Parser.Log.Warnings_ToString
                z_XMLInternalData_Save.IsWarning = True
            End If


            '------------------------------------------------------
            '--- Nastaviť vlastnosť s XML data ---
            '------------------------------------------------------

            Me.XMLInternalData = tmp_XML_Element_Parser.ToString(True, u_RemoveXmlDeclaration:=True)
            If String.IsNullOrWhiteSpace(Me.XMLInternalData) Then
                z_XMLInternalData_Save = Exa.Basic.Exceptions.Get("Chyba pri prevode XML dokumentu do textu. " & Err.Description)
                GoTo ExitFunction
            End If

            '--- Uloženie do súboru xml	(pre testovacie účely)
#If DEBUG Then
            Dim tmp_FileName$ = CONST_DefaultFileName_WithoutExtension & "_XmlInternal." & CONST_DefaultFileName_Extension
            Dim tmp_FilePath As String = IO.Path.Combine(Me._AppConfiguration.Common.Directory.OBERON_Temp, tmp_FileName$)
            myEx = tmp_XML_Element_Parser._Save(tmp_FilePath, True, True)
            If myEx.Result = False Then
                z_XMLInternalData_Save = Exa.Basic.Exceptions.Get("Chyba pri uložení XML súboru.", myEx)
                GoTo ExitFunction
            End If
#End If


            z_XMLInternalData_Save.Result = True

ExitFunction:

            If tmp_XMLNode_Items_List IsNot Nothing Then
                tmp_XMLNode_Items_List = Nothing
            End If

            If tmp_XML_Element_Parser IsNot Nothing Then
                tmp_XML_Element_Parser.Dispose()
                tmp_XML_Element_Parser = Nothing
            End If

            If tmp_XMLDocument IsNot Nothing Then
                tmp_XMLDocument = Nothing
            End If


        End Function
#End Region

#Region "Clipboard"

        ''' <summary>Obsahuje údaje schránky pre kopírovanie záznamu.</summary>
        <Serializable()>
        Public Class cls_DeviceClipboardData
            Inherits Exa.Database.Factory.cls_DataRecordClipboardData

            Public IDNum As Long = 0

            Friend Shadows ReadOnly Property Object_HashTable As Hashtable
                Get
                    Return MyBase.Object_HashTable
                End Get
            End Property

        End Class

        Private Sub Device_ev_Clipboard(sender As Object, e As Database.Factory.DataRecord.cls_ClipboardEventArgs) Handles Me.ev_Clipboard

            Try
                Dim m_ExaException As EXC.ExaException = Nothing

                Select Case e.ActionType
                    Case Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Copy
                        'Vloženie údajov zariadenia do schránky 'Clipboard'.
                        Dim m_ClipboardData As New cls_DeviceClipboardData With
                            {.ConnectionSettings = e.ClipboardData.ConnectionSettings,
                             .TableName = e.ClipboardData.TableName,
                             .RowID = e.ClipboardData.RowID}

                        'Nastav údaje (hodnoty) hlavného záznamu.
                        With m_ClipboardData
                            .ImportValues(Me.ToClipboardData())
                            .IDNum = Me.IDNum
                        End With

                        'Načítanie a vloženie práv od schránky clipboard.
                        m_ExaException = Me.z_Clipboard_DeviceSettings_Copy(urf_ClipboardData:=m_ClipboardData)
                        If (m_ExaException.Result = False) Then
                            e.ExaException = m_ExaException
                            Exit Try
                        End If

                        e.ClipboardData = m_ClipboardData

                    Case Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Paste
                        'Vytvor nový objekt zariadenia pre vytvorenie nového záznamu.
                        Dim m_ClipboardData As cls_DeviceClipboardData = TryCast(e.ClipboardData, cls_DeviceClipboardData)

                        If m_ClipboardData Is Nothing Then Exit Try

                        Dim m_DeviceType As enm_Devices_Type = CType(m_ClipboardData.Field("ZariadenieDruh"), enm_Devices_Type)
                        e.ExaException = Me._New(m_DeviceType)

                        If e.ExaException.Result = False Then Exit Try

                        'Nastavenie hodnôt zo schránky 'Clipboard'.
                        Me.FromClipboardData(m_ClipboardData, "Nazov", u_FieldsToIgnore:=New String() {DB.Zariadenia.DailyBalanceID})

                        Me.lc_SaveBehavior_IgnoreDefaultSettings = True 'Neukladať default nastavenia.

                        e.ExaException = Me._Save()
                        If e.ExaException.Result = False Then Exit Try

                        'Zápis nastavení fiškála do DB.
                        If (m_DeviceType = enm_Devices_Type.FiskalModule) Then
                            Dim m_DataView As New Exa.Database.Viewing.DataView
                            m_DataView._CommonData = Me.Object_CommonData
                            Dim m_Table As New Exa.Database.Viewing.DataViewObjects.Table(m_DataView, "sys_settings_data")
                            Dim m_Section As String = $"FiscalDevice({Me.IDNum})"

                            Dim m_LoadBehavior As New Exa.Database.Viewing.DataViewObjects.Table.cls_Behavior_DataLoading
                            m_LoadBehavior.Limit_Use = False
                            m_LoadBehavior.RowFilter = $"ItemSection = {DB_CONV.ToSQLString(m_Section, Me.Object_CommonData)}"

                            m_Table._Columns.Add(m_Table.DatabaseTable_Schema)

                            e.ExaException = m_Table._LoadData(m_LoadBehavior) 'Nemalo by načítať žiadne údaje, ale len inicializovať table pre zápis nových údajov.
                            If e.ExaException.Result = False Then Exit Try

                            For Each e_Entry As DictionaryEntry In m_ClipboardData.Object_HashTable
                                Try
                                    Dim m_HashKey As String = CStr(e_Entry.Key)
                                    If (m_HashKey.StartsWith("<SET>") = False) Then Continue For 'Len hodnoty typu právo.
                                    Dim m_ArrValues() As String = m_HashKey.Split("█"c)
                                    Dim m_SubSection As String = m_ArrValues(1)
                                    Dim m_Key As String = m_ArrValues(2)
                                    Dim m_NewRow As DataRow = m_Table.DatabaseTable_Data.NewRow

                                    With m_NewRow
                                        .Item("ItemSection") = m_Section
                                        .Item("ItemSubSection") = m_SubSection
                                        .Item("ItemKey") = m_Key
                                        .Item("ItemValue") = CStr(e_Entry.Value)
                                    End With

                                    m_Table.DatabaseTable_Data.Rows.Add(m_NewRow)
                                Catch ex As Exception
                                    EXC.Catch(ex, Me)
                                End Try
                            Next

                            e.ExaException = m_Table._UpdateDatabase()
                            If e.ExaException.Result = False Then Exit Try
                        End If

                        e.ExaException.Result = True
                        e.Handled = True

                End Select

            Catch ex As Exception
                EXC.Catch(ex, Me)
            Finally
                Me.lc_SaveBehavior_IgnoreDefaultSettings = False
            End Try

        End Sub

        Private Function z_Clipboard_DeviceSettings_Copy(ByRef urf_ClipboardData As cls_DeviceClipboardData) As EXC.ExaException

            If (urf_ClipboardData Is Nothing) Then Throw New ArgumentNullException("urf_ClipboardData")

            z_Clipboard_DeviceSettings_Copy = EXC.GetDefault

            Dim m_ExaException As EXC.ExaException = Nothing
            Dim m_DataReader As Exa.Database.CommonDataObjects.CommonDataReader = Nothing

            Try
                If (Me.RecordState_Database <> enm_RecordStateTypes.Editing) Then Throw New InvalidOperationException("Nastavenia zariadenia nie je možné načítať, pretože nie je načítané zariadenie.")

                'Nastavenia pokladnice, len keď je zariadenie fiškálny modul.
                If (Me.Device_Type = enm_Devices_Type.FiskalModule) Then
                    Dim m_Section As String = DB_CONV.ToSQLString($"FiscalDevice({Me.IDNum})", Me.Object_CommonData)
                    Dim m_SQL As String = $"SELECT ItemSubSection, ItemKey, ItemValue FROM sys_settings_data WHERE ItemSection = {m_Section}"

                    m_ExaException = Me.Object_CommonData.ExecuteQuery(m_SQL, CommandType.Text, m_DataReader)

                    If (m_ExaException.Result = False) Then
                        z_Clipboard_DeviceSettings_Copy = EXC.Get("Chyba pri načítaní nastavení pokladnice.", m_ExaException)
                        Exit Try
                    End If

                    Do While (m_DataReader.Read)
                        Try
                            Dim m_SubSection As String = CStr(DB_CONV.ReplaceDBNull(m_DataReader.Item(0)))
                            Dim m_Value As String = CStr(DB_CONV.ReplaceDBNull(m_DataReader.Item(2)))
                            Dim m_Key As String = $"<SET>█{m_SubSection}█{CStr(DB_CONV.ReplaceDBNull(m_DataReader.Item(1)))}"
                            urf_ClipboardData.Object_HashTable.Add(m_Key, m_Value)
                        Catch ex As Exception
                            EXC.Catch(ex, Me)
                        End Try
                    Loop
                End If

                z_Clipboard_DeviceSettings_Copy.Result = True
            Catch ex As Exception
                z_Clipboard_DeviceSettings_Copy = EXC.Get(ex)
            Finally
                m_DataReader?.Dispose()
            End Try

        End Function

#End Region

#Region " CLASS - SaveBehavior"

        ''' <summary>
        ''' Bližšie určuje akým spôsobom sa uloží záznam pomocou metódy _Save, napr. či sa má kontrolovať určitá hodnota.
        ''' </summary>
        Public Class cls_SaveBehavior

            ''' <summary>
            ''' Príznak či pri metóde _Save kontrolovať na zadanie predajného miesta.
            ''' </summary>
            <Obsolete>
            Public Property ValidateSalesPointName As Boolean = False

        End Class


#End Region


#Region " DEVICE INFO "

        ''' <summary>
        ''' Obsahuje údaje o zariadení. Ide o samostatnú štruktúru, ktorú je vhodnejšie použiť v porovnaní s Datarecord-om.
        ''' </summary>
        Public Class DeviceInfo

            ''' <summary>Jednoznačný identifikátor zariadenia v systéme OBERON (v zozname zariadení).</summary>
            Public Property DeviceIDNum As Long

            ''' <summary>Názov (pomenovanie) zariadenia definovaný používateľom v zozname zariadení.</summary>
            Public Property DeviceName As String

            ''' <summary>Typ zariadenia, napr. fiškálny modul, registračná pokladnica, zákaznícky displej, dverový zámok a podobne.</summary>
            Public Property DeviceType As enm_Devices_Type


            ''' <summary>Typ zariadenia, napr. fiškálny modul, registračná pokladnica, zákaznícky displej, dverový zámok a podobne.</summary>
            Public Property Communication As cls_Communication


            ''' <summary>
            ''' Vráti názov modelu zariadenia v závislosti na type zariadenia, napr. eKasa Pandora. 
            ''' </summary>
            Public ReadOnly Property DeviceModelName As String
                Get
                    On Error Resume Next

                    If Me.DeviceType = enm_Devices_Type.None Then
                        Return Nothing
                    End If

                    Return GetDeviceModelName(Me.DeviceType, u_DeviceModelNumber:=Me.DeviceModelNum)
                End Get
            End Property

            ''' <summary>
            ''' Vráti číslo modelu zariadenia. Integer preto, lebo zariadenia sú rôzne a sú uložené v rôznych enum-och. 
            ''' Presný enum je uložený už pri príslušnom zariadení, vlastnosti začínajúcej s prefixom d_.
            ''' </summary>
            Public Property DeviceModelNum As Integer


            ''' <summary>Vráti info o zariadení v textovom formáte.</summary>
            Public Property DeviceInfo As String

            ''' <summary>Názov prevádzky, ku ktorej patrí zariadenie (nepovinný údaj).</summary>
            Public Property CompanyBranchName As String


            ''' <summary>Názov jedného alebo viacerých počítačov, na ktorých sa je možné k zariadeniu pripojiť. Ak sa používateľ pripája cez RDP, uvádza sa vo formáte napr. RDP: PC_Novak.</summary>
            Public Property Computers As String()


            ''' <summary>Názov jedného alebo viacerých počítačov, avšak sú uvádzané len také, na ktoré sa je možné pripojiť cez RDP. 
            ''' Zoznam sa odvodzuje zo štandardného zoznamu počítačov, avšak sú tu len také, u ktorých je uvedený prefix "RDP: " (tu sú však uvedené bez tohto prefixu).</summary>
            Public Property ComputersRDP As String()

            ''' <summary>Kód zariadenia - používateľské číslo pridelené zariadeniu, napr. pri pokladniciach kód pokladnice (pôvodne sa uvádzalo ako DKP).</summary>
            Public Property DeviceCode As String

            ''' <summary>Výrobné číslo zariadenia (typu STRING).</summary>
            Public Property DeviceProductNumber As String


            Public Sub From(u_Device As Device)

                Try

                    Me.DeviceIDNum = u_Device.IDNum
                    Me.Communication = u_Device.Communication.Clone
                    Me.DeviceName = u_Device.Device_Name
                    Me.DeviceType = u_Device.Device_Type
                    Me.DeviceModelNum = u_Device.Device_Model_Num
                    Me.DeviceInfo = u_Device.Device_Info
                    Me.CompanyBranchName = u_Device.CompanyBranchName
                    Me.Computers = u_Device.Computers
                    Me.ComputersRDP = u_Device.ComputersRDP
                    Me.DeviceCode = u_Device.Device_Code
                    Me.DeviceProductNumber = u_Device.Device_ProductNumber

                Catch ex As Exception
                End Try


            End Sub

        End Class

#End Region

    End Class

End Namespace
