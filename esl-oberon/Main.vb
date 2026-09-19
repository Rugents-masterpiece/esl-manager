<HideModuleName()>
Public Module Main


#Region " DECLARATION "

    ''' <summary>
    ''' Zariadenia, napr. registračná pokladnica, tlačiareň bločkov, snímač prístupových kľúčov.
    ''' </summary>
    Enum enm_Devices_Type

        ''' <summary>Nezadané, nenastavené ...</summary>        
        None = 0

        ''' <summary>Registračné pokladnice, napr. EURO.</summary>
        <System.ComponentModel.Description("Registračná pokladnica")>
        CashRegister = 1


        ''' <summary>Fiškálne zariadenia.</summary>    
        <System.ComponentModel.Description("Fiškálne zariadenie")>
        FiskalModule = 2


        ''' <summary>Tlačiarne pokladničných dokladov.</summary>
        <System.ComponentModel.Description("Tlačiareň pokladničných dokladov")>
        PrinterReceipt = 3


        ''' <summary>Platobný terminál.</summary>    
        <System.ComponentModel.Description("Platobný terminál")>
        PaymentTerminal = 15


        ''' <summary>Snímač čiarového kódu.</summary>    
        <System.ComponentModel.Description("Snímač čiarového kódu")>
        BarCodeScanner = 5


        ''' <summary>Zákaznícky display na pokladnici.</summary>    
        <System.ComponentModel.Description("Zákaznícky displej")>
        DisplayCustomer = 7


        ''' <summary>Bonovacia tlačiareň.</summary> 
        <System.ComponentModel.Description("Bonovacia tlačiareň")>
        PrinterKitchen = 6

        '''' <summary>
        '''' Databanky
        '''' </summary>    
        '<System.ComponentModel.Description("Databanka")> _
        'Databank = 8


        ''' <summary>Elektronická váha.</summary>    
        <System.ComponentModel.Description("Elektronická váha")>
        ElectronicScale = 13

        ''' <summary>Snímač prístupu /personal identification device/.</summary>    
        <System.ComponentModel.Description("Snímač prístupu")>
        PID = 9

        ''' <summary>Čítačka cestovných pasov a preukazov totožnosti.</summary>    
        <System.ComponentModel.Description("Čítačka dokladov")>
        DocumentReader = 25

        ''' <summary>Dochádzkový terminál.</summary>    
        <System.ComponentModel.Description("Dochádzkový terminál")>
        AttendanceTerminal = 21

        ''' <summary>Digitálna podpisová podložka.</summary>    
        <System.ComponentModel.Description("Digitálna podpisová podložka")>
        SignaturePad = 28

        ''' <summary>Dverové zámky.</summary>    
        <System.ComponentModel.Description("Dverový zámok")>
        DoorKey = 10

        ''' <summary>PDA.</summary>
        <System.ComponentModel.Description("PDA zariadenie")>
        PDA = 12


        ''' <summary>Elektronické cenovky (Price Labels).</summary>
        <System.ComponentModel.Description("Elektronické cenovky")>
        PriceLabels = 30


    End Enum


    ''' <summary>
    ''' Registračné pokladnice, podporované typy, napr.EURO, Frigo atď
    ''' </summary>
    Public Enum enm_CashRegister_Model

        None = 0

        'E50TE - Euro-50 Mini, E50CASHTE - Euro-50 Cash
        <System.ComponentModel.Description("Euro 50 (eKasa)")>
        Elcom_EURO_50_TE_eKasa = 310

        'E150TE - Euro-150 Flexy, E155TE - Euro-150 Flexy Plus
        <System.ComponentModel.Description("Euro 150 (eKasa)")>
        Elcom_EURO_150_TE_eKasa = 312


        <System.ComponentModel.Description("CashRegister Universal Interface")>
        CashRegister_Universal = 999


    End Enum



    ''' <summary>
    ''' Registračné pokladnice - spôsob režimu práce
    ''' </summary>
    Public Enum enm_CashRegister_Model_Mode

        OFF_LINE = 0
        ON_LINE = 1

    End Enum


    ''' <summary>Druhy fiškálnych zariadení, napr. eKasa, VRP, Fiscal Virtual, Universal Interface a ostatné podporované typy do roku 2019, napr. FM4000, EFOX, Axis atď.</summary>
    Public Enum enm_FiskalModule_Model

        None = 0


        <System.ComponentModel.Description("eKasa PANDORA")>
        eKasaPandora = 201

#If DEBUG = True Then
        <System.ComponentModel.Description("eKasa PENELOPA")>
        PenelopaEKasa = 205
#Else
        PenelopaEKasa = 205
#End If


        <System.ComponentModel.Description("FiskalPRO (eKasa)")>
        FiskalProEKasa = 211

        <System.ComponentModel.Description("FiskalPRO Android (eKasa)")>
        FiskalProA8EKasa = 212

        <System.ComponentModel.Description("Bowa Pegas eKasa")>
        PegasFM06eKasa = 215


        <System.ComponentModel.Description("Easy-Pos.eKasa 2019")>
        EasyPosEKasa2019 = 231

        <System.ComponentModel.Description("Elcom-EFox (eKasa)")>
        Elcom_EFox_eKasa = 251

        <System.ComponentModel.Description("Elcom Euro-50 On-line (eKasa)")>
        Elcom_50_eKasa_OnLine = 301

        <System.ComponentModel.Description("Elcom Euro-150 On-line (eKasa)")>
        Elcom_150_eKasa_OnLine = 302


        <System.ComponentModel.Description("Fiscal Universal Interface")>
        UniversalInterface = 80


        <System.ComponentModel.Description("Fiscal UNI (CZ)")>
        Fiscal_UNI_CZ = 81

        <System.ComponentModel.Description("Fiscal UNI (SK)")>
        Fiscal_UNI_SK = 99

        <System.ComponentModel.Description("VRP - Finančná správa")>
        VRP_FinancnaSprava = 97


    End Enum


    ''' <summary>Modely pokladničných tlačiarní. </summary>
    Public Enum enm_FiskalPrinter_Models

        <System.ComponentModel.Description("<Obecný>")>
        Universal = 99

        <System.ComponentModel.Description("EPSON")>
        EPSON = 1

        <System.ComponentModel.Description("STAR")>
        STAR = 2

        <System.ComponentModel.Description("BIXOLON")>
        BIXOLON = 3

    End Enum


    ''' <summary>Bonovacia tlačiareň - podporované typy.</summary>
    Public Enum enm_PrinterKitchen_Model

        None = 0

        ''' <summary>Obecný textový režim - na tlač sa používa textový režim (spravidla na ovládač tlačiarne Generic text only).</summary>
        <System.ComponentModel.Description("<Obecný>")>
        Universal = 99

        ''' <summary>ESC/POS tlačiareň - EPSON.</summary>
        <System.ComponentModel.Description("EPSON TM - x")>
        Epson = 100

        ''' <summary>Obecný grafický režim - na tlač sa používa štandardný tlačový stroj.</summary>
        <System.ComponentModel.Description("<Grafický režim>")>
        GraphicMode = 1

    End Enum

    ''' <summary>Snímač čiarového kódu.</summary>
    Public Enum enm_BarCodeScannerModel

        None = 0

        <System.ComponentModel.Description("<Obecný>")>
        Universal = 99

        <System.ComponentModel.Description("ECI - 125 (RFID kódy)")>
        ECI_125 = 5

        <System.ComponentModel.Description("ECI - 20 (RFID kódy)")>
        ECI_20 = 6

        <System.ComponentModel.Description("QeeR skener")>
        OBERON_BarCode_Scanner = 7

        'BarCodeScanner - podporuje reconnect pri odpojení (napr. BT scanner)
        <System.ComponentModel.Description("<COM port scanner>")>
        UniSerialPort = 98

    End Enum


    ''' <summary>Zákaznícky displej pri registračnej pokladnici s fiškálnym modulom.</summary>
    Public Enum enm_DisplayCustomerModel


        ''' <summary>
        ''' OBERON Smart Display - dáta zasiela do webservice a odtiaľ si ich ťahá externá aplikácia a zobazuje na displeji.
        ''' </summary>
        <System.ComponentModel.Description("OBERON Smart Display")>
        OBERON_Smart = 21

        ''' <summary>
        ''' Mini QR Display - zobrazuje údaje k platbe (QR) a napr. sumu počas pridávania položiek.
        ''' </summary>
        <System.ComponentModel.Description("Mini QR Display")>
        MiniQrDisplay = 6

        ''' <summary>
        ''' EXALOGIC OBERON - dvojriadkový displej (20 znakov x 2 riadky).
        ''' </summary>
        <System.ComponentModel.Description("EXALOGIC OBERON")>
        EXALOGIC_OBERON = 5

        <System.ComponentModel.Description("EPSON 20 znakov x 2 riadky")>
        EPSON_20_Character_x_2_Row = 2

        <System.ComponentModel.Description("ELCOM ED-2500R")>
        ELCOM_ED_2500R = 3

        <System.ComponentModel.Description("Zonerich ZQ-TC2002A-V12")>
        ZQ_TC2002A_V12 = 4

        <System.ComponentModel.Description("VAROS Disp20C")>
        VAROS_Disp20C = 1


    End Enum



    ''' <summary>
    ''' Snímač prístupových kľúčov, PID /personal identifikation device/
    ''' </summary>
    Public Enum enm_PID_Model

        <System.ComponentModel.Description("ECI - 125")>
        ECI_125 = 1

        <System.ComponentModel.Description("ECI - 10")>
        ECI_10 = 5

        <System.ComponentModel.Description("ECI - 20")>
        ECI_20 = 6

    End Enum

    ''' <summary>
    ''' KOmunikácia zaraidení cez UDP protokol.
    ''' </summary>
    Public Enum enm_UDP_Model

        <System.ComponentModel.Description("OBERON Barcode Scanner")>
        OBERON_Barcode_Scanner = 1


    End Enum


    ''' <summary>
    ''' Dverové zámky /pre hotelový systém/  
    ''' </summary>
    Public Enum enm_DoorKey_Model


        <System.ComponentModel.Description("SALTO")>
        Salto = 3

        <System.ComponentModel.Description("ASSA ABLOY")>
        AssaAbloy = 4

        <System.ComponentModel.Description("SeaGuest")>
        SeaGuest = 1

        'TODO: Vlado - DEBUG SWITCH - Onity HT22, HT28 - do vydania verzie nezobrazovať zariadenie
#If DEBUG = False Then
        Onity = 2
#Else
        <System.ComponentModel.Description("Onity HT22, HT28")>
        Onity = 2
#End If

    End Enum


    ''' <summary>
    ''' Elektronické cenovky (Price Labels)
    ''' </summary>
    Public Enum enm_PriceLabelsModel

        None = 0

        ''' <summary>OBERON ESL 2026 - Systém na elektronické cenovky.</summary>
        <System.ComponentModel.Description("OBERON ESL 2026")>
        OBERON_ESL_2026 = 1

    End Enum


    ''' <summary>
    ''' PDA zariadenia /vreckové počítače/
    ''' </summary>
    Public Enum enm_PDA_Model

        None = 0

        <System.ComponentModel.Description("<Obecný>")>
        Universal = 99

    End Enum

    ''' <summary>
    ''' Váhy
    ''' </summary>
    Public Enum enm_ElectronicScaleModel

        None = 0

        ''' <summary>Obecný vážený EAN13.</summary>
        <System.ComponentModel.Description("<Obecný vážený EAN13>")>
        EAN13_Universal = 1

        ''' <summary>EAN13 s kontrolným súčtom.</summary>
        <System.ComponentModel.Description("<EAN13 s kontrolným súčtom>")>
        EAN13_WithCheckSum = 2

        '''' <summary>Výrobca CAS - pre viaceré typy pokladníc.</summary>
        <System.ComponentModel.Description("CAS Standard Protocol")>
        CAS_StandardProtocol = 11

        '''' <summary>Výrobca DIBAL - pre viaceré typy pokladníc.</summary>
        <System.ComponentModel.Description("DIBAL Apollo/Posnet Protocol")>
        DIBAL_ApolloPostnetProtocol = 12

        '''' <summary>Výrobca DIBAL - pre viaceré typy pokladníc.</summary>
        <System.ComponentModel.Description("DIBAL Uniprox Protocol")>
        DIBAL_UniproxProtocol = 13

        '''' <summary>Výrobca DIBAL - pre viaceré typy pokladníc.</summary>
        <System.ComponentModel.Description("DIBAL Delta Protocol")>
        DIBAL_DeltaProtocol = 14

        '''' <summary>Výrobca Datalogic - váhy MAGELLAN s protokolom SASI</summary>
        <System.ComponentModel.Description("Datalogic SASI protokol")>
        Datalogic_SASI_Protocol = 31

        '''' <summary>Priemyselné váhy - indikátor BWS.</summary>
        <System.ComponentModel.Description("Priemyselné váhy - indikátor BWS")>
        Indicator_BWS = 21

        '''' <summary>Výrobca DINI ARGEO - váhy DFW/DFWL.</summary>
        <System.ComponentModel.Description("DINI ARGEO DFW/DFWL")>
        DiniArgeo_DFW_485 = 32



        '''' <summary>Protokol AP1.</summary>
        ''<System.ComponentModel.Description("<Protokol AP-1>")> _
        'Protokol_AP_1 = 51

        '''' <summary>Protokol DB-2.</summary>
        '<System.ComponentModel.Description("<Protokol DB-2>")> _
        'Protokol_DB_2 = 52

    End Enum


    ''' <summary>Platobné terminály.</summary>
    Public Enum enm_PaymentTerminalModel

        None = 0

        ''' <summary>NOP eKasa (okamžité platby).</summary>
        <System.ComponentModel.Description("NOP eKasa (okamžité platby)")>
        FsInstantQrPay = 10


        ''' <summary>GP tom.</summary>
        <System.ComponentModel.Description("GP tom")>
        GpTom = 4

        ''' <summary>GP ECR2.</summary>
        <System.ComponentModel.Description("GP ECR2")>
        GpEcr2 = 7

        ''' <summary>Teya.</summary>
        <System.ComponentModel.Description("Teya")>
        Teya = 8

        ''' <summary>FiskalPRO.</summary>
        <System.ComponentModel.Description("FiskalPRO")>
        FiskalPro = 2

        ''' <summary>FiskalPRO.</summary>
        <System.ComponentModel.Description("FiskalPRO Android")>
        FiskalProA8 = 3

        ''' <summary>AxaPro.</summary>
        <System.ComponentModel.Description("AxaPro")>
        AxaPro = 1

#If DEBUG Then
        ''' <summary>Rictom.</summary>
        <System.ComponentModel.Description("Rictom")>
        Rictom = 5

#Else
        Rictom = 5
#End If
        ''' <summary>Softplus Ticket.</summary>
        <System.ComponentModel.Description("Softplus Ticket")>
        SoftPlusTicket = 6

        ''' <summary>Printec ČSOB.</summary>
        <System.ComponentModel.Description("Printec ENGAGE (PRSK05)")>
        Printec = 9

    End Enum


    ''' <summary>
    ''' Digitálna podpisová podložka.
    ''' </summary>
    Public Enum enm_SignaturePadModel

        <System.ComponentModel.Description("EXALOGIC-DSP1")>
        ExalogicDSP1 = 11

    End Enum

    ''' <summary>Digitálna podpisová podložka - spôsob používania časového servera pre časovú pečiatku.</summary>
    Public Enum enm_SignaturePad_TimeStampMode As Integer

        ''' <summary>
        ''' Používať predvolený.
        ''' </summary>
        <System.ComponentModel.Description("Používať predvolený")>
        [Default] = 0

        ''' <summary>Nepoužívať (napr. pri dočasnom výpadku).</summary>
        <System.ComponentModel.Description("Nepoužívať")>
        Disable = 1

        ''' <summary>Používať zadaný (vlastný) časový server - používateľ zadá url ľubovolného časového servera.</summary>
        <System.ComponentModel.Description("Používať zadaný (vlastný)")>
        OtherTimeStampServer = 2

    End Enum


    ''' <summary>Typ položky pokladničného dokladu - určuje spôsob zaevidovania do fiškálneho zariadenia.</summary>	   
    Public Enum enm_BillItemRegisterFlag As Integer

        ''' <summary>Nedefinované.</summary>
        None = 0

        ''' <summary>Štandardná položka - kladná položka, napr. bežný predaj.</summary>
        <System.ComponentModel.Description("Štandardná položka")>
        Standard = 1

        ''' <summary>Záporná položka (vratný obal) - najčastejšie sa používa pre vratné obaly.</summary>		
        <System.ComponentModel.Description("Vratný obal (záporná položka)")>
        Negative = 2

        ''' <summary>Vrátenie tovaru (storno) - vrátenie položky, ktorá bola predaná v niektorom z predchádzajúcich ukončených nákupov v minulosti.</summary>		
        <System.ComponentModel.Description("Vrátenie tovaru (záporná položka)")>
        Refund = 3

        ''' <summary>Zľava - mínusová položka, ktorá je považovaná len za zľavu (nie je to bežná zľava zadaná pri položke).</summary>		
        <System.ComponentModel.Description("Zľava")>
        Discount = 4

        ''' <summary>Oprava - Kladná alebo záporná položka - negácia položky už zaevidovaného dokladu v prípade jej opravy. 
        ''' Je možné použiť pri zámene tovaru na účtenke, napr. menu dňa s ryžov - ryžu mínusom a nahradiť ryžu hranolkami.</summary>
        <System.ComponentModel.Description("Oprava (kladná alebo záporná položka)")>
        Repair = 5

        '--- Podľa zákona na platného v roku 2010,2011 /nový zákon/ sa musí mínusová položka členiť:
        '--- - záporná položka - vratné obaly
        '--- - vrátený tovar - /pôvodne podľa zákona to bolo storno/
        '--- - zľavy - záporná položka s poskytnutou zľavou
        '--- - storno položky - storno položky v rámci toho istého dokladu. Používa sa pri režime, keď po pridaní položky sa ihneď zaúčtuje /v OBERON-e nepodporované/
        '--- - oprava - oprava položky ešte pred zaúčtovaním /v OBERON-e nepodporované/

        '--- Zákon platný od roku 2019 pozná ďalšie typy zápornej položky

        ''' <summary>Odpočítaná záloha - položka so zápornou hodnotou vo výške sumy prijatého preddavku uvedená na doklade vystavenom v čase úhrady 
        ''' doplatku ceny za predaný tovar alebo poskytnutú službu.</summary>		
        <System.ComponentModel.Description("Odpočítaná záloha (záporná položka)")>
        RefundAdvance = 7

        ''' <summary>Výmena poukazu – položka so zápornou hodnotou pri výmene jednoúčelového poukazu za tovar alebo poskytnuté služby.</summary>		
        <System.ComponentModel.Description("Výmena poukazu (záporná položka)")>
        RefundVoucher = 9



    End Enum

    ''' <summary>Dochádzkové terminály.</summary>
    Public Enum enm_AttendanceTerminalModel

        None = 0

        ''' <summary>Dochádzkový terminál EXALOGIC A-C071S.</summary>
        <System.ComponentModel.Description("EXALOGIC A-C071S")>
        EXALOGIC_AC071 = 2

        ''' <summary>Dochádzkový terminál ZKTeco TFT500.</summary>
        <System.ComponentModel.Description("EXALOGIC TFT500SK")>
        EXALOGIC_TFT500SK = 5

        ''' <summary>OBERON softvérový terminál - v režime na samostatnom počítači.</summary>
        <System.ComponentModel.Description("OBERON terminál")>
        OBERON = 51

        ''' <summary>OBERON - Agenda firmy - umožňuje sa prihlásiť priamo z programu na ktoromkoľvek počítači.</summary>
        <System.ComponentModel.Description("OBERON - Agenda firmy terminál")>
        OBERON_Agenda = 52

#If DEBUG = True Then
        ''' <summary>OBERON Web terminál.</summary>
        <System.ComponentModel.Description("OBERON Web terminál")>
        OBERON_Web = 55
#Else
        OBERON_Web = 55
#End If


    End Enum

    ''' <summary>Čítačky dokumentov napr. pasov, občianskych preukazov, víz, ...</summary>
    Public Enum enm_DocumentReaderModel

        None = 0

        ''' <summary>Čítačka cestovných pasov a preukazov totožnosti Access OCR31x.</summary>
        <System.ComponentModel.Description("Access OCR31x")>
        Access_OCR31x = 1


        ''' <summary>Ručná čítačka cestovných pasov a preukazov totožnosti Xtiot XTZ6201.</summary>
        <System.ComponentModel.Description("Xtiot XTZ62E")>
        Xtiot_XTZ62E = 2


    End Enum

#End Region


#Region " METHODS "



#End Region


End Module
