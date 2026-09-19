Option Strict On

Imports Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026
Imports Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models
Imports Exa.OBERON.[Shared].Common.Document.Document_Item.enm_Price_UserInput_VATMode
Imports Exa.OBERON.Stock.StockCards
Imports Exa.Database.Viewing.TemplateValues
Imports System.Threading.Tasks
Imports System.Linq
Imports Exa.Application.Forms.Options
Imports Exa.Application.Controls
Imports Exa.Application.Controls.Simple.S_DataGrid
Imports Exa.Application.Forms.Data.Factory
Imports Exa.Application.Controls.Simple
Imports System.Windows.Forms.VisualStyles.VisualStyleElement
Imports Exa.Application.Language
Imports Newtonsoft.Json.Linq

Namespace Forms.StockCards

    ''' <summary>Formulár skladovej karty.</summary>
    Public Class frm_StockCard_NewEdit
        Implements Exa.Application.Forms.Data.Factory.IDataList(Of StockCard_List)
        Implements Exa.Application.Forms.Options.frm_Options.IFormOptions

#Region "Declaration"

        'Privates
        Private lc_AppConfiguration As Exa.OBERON.ApplicationEnvironment.AppConfiguration = Nothing
        Private lc_Selected_Stock As Exa.OBERON.Shared.Stock.Stocks.Stock.cls_StockInfo = Nothing
        Private lc_PriceLevel As Byte = 1
        Private lc_DeviceEngine As Exa.OBERON.Devices.Base.DeviceEngine = Nothing
        Private lc_ObjectsOBERON_Stock As Exa.OBERON.Stock.Features.ObjectsOBERON_Stock = Nothing
        '
        'Zoznam (list) enumov registračných pokladníc inštalovaných v zozname zariadení (firmy)
        Private lc_DeviceModelsList As List(Of Exa.OBERON.Devices.enm_CashRegister_Model)

        ''' <summary>Obsahuje údaj o zozname jedálnych lístkov, do ktorých patrí táto skladová karta.</summary>
        Private lc_FoodMenu_SelectedList As New List(Of String)

        'Režim práce na tomto forme napr. pri pridaní nového záznamu zmena default hodnôt.
        Private lc_WorkMode As enm_WorkModeTypes = enm_WorkModeTypes.Default
        '
        'Používateľská hodnota, používa sa pre automatické nastavenie pôvodnej hodnoty (napr. povolenie po zakázaní controlu).
        Private lc_UserValue_PricesCalculationType As StockCard.enm_Prices_SellCalculationMode = StockCard.enm_Prices_SellCalculationMode.Ask_Before

        Private lc_Variant_DataRecord_DataGridCellFormatting As StockCard_Variant = Nothing
        Private lc_Parameter_DataRecord_DataGridCellFormatting As StockCard_Parameter = Nothing

        ''' <summary>Status monitor pre sledovanie statusu cenovky.</summary>
        Private lc_StatusMonitor As Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.PriceTagStatusMonitor

        Private lc_StockCard_Cache As StockCard_Cache = Nothing
        Private lc_HashTable_VariantDefinition As Hashtable = Nothing

        Private lc_Permission_IsAllControlsLocked As Boolean = False

#End Region


#Region " INHERITANCE SETTINGS - FORM DATA RECORD & TEMPLATES "


        Public Shadows ReadOnly Property _DataList As StockCard_List Implements Application.Forms.Data.Factory.mod_Factory.IDataList(Of StockCard_List)._DataList
            Get
                Return DirectCast(MyBase._DataList, StockCard_List)
            End Get
        End Property

        Public Shadows ReadOnly Property _DataRecord As StockCard
            Get
                Return DirectCast(MyBase._DataRecord, StockCard)
            End Get
        End Property

        Private Sub Form_ev_DataRecordAction(ByVal sender As Object, ByVal e As Application.Forms.Data.Factory.Form_DataRecord_Win32.cls_DataRecordActionEventArgs) Handles Me.ev_DataRecordAction

            On Error Resume Next
            Dim myex As EXC.ExaException

            e.ExaException = Exa.Basic.Exceptions.GetDefault


            Select Case e.Action
                Case cls_DataRecordActionEventArgs.enm_ActionTypes.Record_Load
                    With Me._DataRecord._Load_Behavior
                        .Items_Variant = True
                        .Items_Parameter = True
                        .Items_Supplier = True
                        .Items_Product = True '--- Musia sa načítať, pretože sa podľa tohto nastavuje combo Typ Karty
                        .ExtendedProperties = False  '--- Netreba vždy načítavať 
                    End With

                    e.ExaException = Me._DataRecord._Load(CLng(e.RowKey_Value), Me.lc_Selected_Stock, e.LockRecord_Load)

                    If e.ExaException.Result = False Then
                        '--- ERR pri načítaní

                        '--- Vynulovať text okna (ak bol predtým nastavený) ---
                        Me.Text_Notice = String.Empty

                    Else
                        '--- Záznam bol načítaný - nastavenie práv
                        Dim myEx_Permission As Exa.Basic.Exceptions.ExaException

                        myEx_Permission = Me._DataRecord._Permission.GetPermissionActual(ApplicationEnvironment.enm_Permission_RecordAction.Load)

                        If myEx_Permission.Result = False Then
                            '--- Zamknúť controly
                            Exa.Application.Forms.LockAllControls(Me)
                            lc_Permission_IsAllControlsLocked = True

                            Me.Text_Notice = " - [" & myEx_Permission.ExceptionData & "]"

                        Else
                            '--- Je potrebné odomknúť všetky controly, ak došlu ku zamknutiu controlov pri načítaní záznamu.
                            If lc_Permission_IsAllControlsLocked = True Then
                                Exa.Application.Forms.UnlockAllControls(Me)

                                lc_Permission_IsAllControlsLocked = False
                            End If

                            Me.Text_Notice = Nothing

                        End If

                        '--- Právo na cenotvorbu - nastavuje sa v udalosti formulára --- 


                        '--- Do textu okna doplniť názov skladovej karty
                        Me.Text_Notice = Me.Text_Notice & "  -  " & Me._DataRecord.Name

                        z_SetVariantDataGrid_SearchPanel()
                    End If

                    Exit Sub

                Case cls_DataRecordActionEventArgs.enm_ActionTypes.Record_Save
                    With Me._DataRecord._Save_Behavior
                        .Number_AutoGenerate = False  '--- Negenerovať číslo
                        .Items_Variant = True
                        .Items_Parameter = True
                        .Items_Supplier = True
                        .Items_Product = False 'Položky sa budú načítavať len pri zobrazení receptúry (z dôvodu optimalizácie)
                        .Items_FileRepository = False 'Položky sa budú načítavať len pri zobrazení obrázkov (z dôvodu optimalizácie)
                        If Me._DataRecord.ExtendedValues.IsLoaded = True Then
                            '--- Externé vlastnosti boli načítané - potrebné aj uložiť --
                            .ExtendedProperties = True
                        Else
                            .ExtendedProperties = False
                        End If

                        .Save_Partial = False
                        .Number_Test_Exists_Other_Stock = TriState.UseDefault
                        .Validate_CashRegister_Code = True
                    End With

                    '--- Vždy zapnúť MsgBox-y
                    Me._DataRecord.Validation_ShowMsgBox = True
RetrySave:
                    e.ExaException = Me._DataRecord._Save(e.LockRecord_Save)

                    If e.ExaException.Result = False Then
                        '--- Err ---
                        Select Case e.ExaException.ErrNumber

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.NumberExists
                                '--- Číslo karty už existuje ---
                                Dim tmp_DialogResult As DialogResult
                                Dim tmpStr$
                                tmpStr$ = Exa.Application.TranslateTextEx("Skladová karta s číslom '{0}' už existuje, vygenerovať nové číslo?", Me._DataRecord.Number)
                                Dim m_Description$ = Nothing
                                If e.ExaException.ExceptionData <> String.Empty Then
                                    m_Description$ = Exa.Application.TranslateText("Poznámka") & ":" & vbCrLf & e.ExaException.ExceptionData
                                End If
                                tmp_DialogResult = Exa.Application.MsgBox(tmpStr$, MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2, m_Description$)
                                If tmp_DialogResult = Windows.Forms.DialogResult.Yes Then

                                    Dim tmp_NewNumber As String = Nothing
                                    myex = Me._DataRecord.NumberGetNew(Me.lc_Selected_Stock, u_StockGroup:=Me._DataRecord.Stock_Group, u_GenerateFromDatabase:=True, tmp_NewNumber)
                                    If myex.Result = True Then
                                        '--- OK
                                        Me._DataRecord.Number = tmp_NewNumber
                                        Me._DataRecord.CashRegister_Code = tmp_NewNumber

                                        Me.fro_txt_CisloKarty._Text = Me._DataRecord.Number
                                        Me.fro_txt_RPoklSFiskalom_KodPolozky._Text = Me._DataRecord.Number
                                    End If


                                    Exa.Application.Cursor_Wait()
                                    GoTo RetrySave
                                Else
                                    Me.fro_txt_CisloKarty.BlinkAndFocus()
                                End If

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.CashRegister_Flags_PLU_Name
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_RegistracnePokladnice._Page_VisibleIndex
                                Me.fro_txt_RPokladnica_NazovPolozky.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.CashRegister_Flags_PLU_Number
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_RegistracnePokladnice._Page_VisibleIndex
                                Me.fro_cbo_RPOffline_CisloPLU.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.CustomsEvidence_Alcohol_Name
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_DoplnujuceUdaje._Page_VisibleIndex
                                Me.fro_txt_SBL_ObchodnyNazov.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.CustomsEvidence_Alcohol_Percentage
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_DoplnujuceUdaje._Page_VisibleIndex
                                Me.fro_txt_SBL_PercentoObjemu.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.Name
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Zakladne._Page_VisibleIndex
                                Me.fro_txt_Nazov.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.Number, Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.NumberExists
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Zakladne._Page_VisibleIndex
                                Me.fro_txt_CisloKarty.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.VAT_Rate
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Cena._Page_VisibleIndex
                                Me.fro_cbo_SadzbaDPH.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.VAT_Rate_OnSpuply
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Cena._Page_VisibleIndex
                                Me.fro_cbo_SadzbaDPH_PreNakup.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.BarCode
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_RegistracnePokladnice._Page_VisibleIndex
                                Me.fro_txt_RPokladnice_CiarovyKod.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.CashRegisterCode
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_RegistracnePokladnice._Page_VisibleIndex
                                Me.fro_txt_RPoklSFiskalom_KodPolozky.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.Price_WithVAT_Recommended
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Cena._Page_VisibleIndex
                                Me.fro_txt_PredajnaCena_Doporucena.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.Unit
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Zakladne._Page_VisibleIndex
                                Me.fro_cbo_MJ.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.SameNumberLinkedItem
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_Zakladne._Page_VisibleIndex
                                Me.fro_txt_NumberLinkedItem.BlinkAndFocus()

                            Case Exa.OBERON.Stock.StockCards.StockCard.enm_Validation_ArePropertiesValuesValid.SerialNumber_NotAllowd
                                Exa.Application.MsgBox(e.ExaException.Description, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_DoplnujuceUdaje._Page_VisibleIndex
                                Me.fro_cbo_DoplnUdaje_SerialNumbersMode.BlinkAndFocus()

                            Case Else
                                Dim LANG_1$ = "Chyba pri uložení záznamu do databázy."
                                Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)

                                Exa.Application.MsgBox(mText_1$, e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)

                        End Select

                    Else
                        '--- Ok
                        If e.ExaException.IsWarning = True Then
                            '--- Varovanie
                            Exa.Application.MsgBox("Pri uložení skladovej karty sa vyskytol problém. ", e.ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                        End If
                    End If


                    Exit Sub

                Case cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Load_Edit,
                        cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Load_Default

                    Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing


                    'POZOR: Form zostáva v pamäti preto je dôležité odstrániť staré údaje,
                    '       napr. 'SetValues_Load_Default' musí nastaviť každý control na forme do pôvodného stavu alebo s default hodnotou

                    With Me._DataRecord
                        '-- TAB 1 - Základné --

                        '--- Množstvo a cena

                        If ._Stock IsNot Nothing AndAlso ._Stock.ExternalStock = True Then
                            '--- Externý sklad - umožniť meniť zostatkové množstvo
                            fro_txt_Mnozstvo_Aktualne.ReadOnly = False
                            fro_txt_Cena_Obstaravacia.ReadOnly = False
                        Else
                            '--- Bežný sklad
                            fro_txt_Mnozstvo_Aktualne.ReadOnly = True
                            fro_txt_Cena_Obstaravacia.ReadOnly = True
                        End If

                        Me.fro_txt_Mnozstvo_Aktualne._Text = CStr(.Amount)
                        Me.fro_txt_Cena_Obstaravacia._Text = CStr(.Price_Supply_Unit)


                        Me.fro_txt_Cena_PoslednaNakupna._Text = CStr(.Price_LastPurchase)

                        Me.fro_txt_CisloKarty._Text = .Number
                        Me.fro_txt_KP._Text = .Classification_Production

                        '--- Názov - (Nastaví max dĺžku podľa hodnoty stĺpca v databáze
                        If Me._DataList Is Nothing Then
                            '--- V režime bez datalistu - chcelo by to dorobiť, aby to bolo korektné
                            fro_txt_Nazov.MaxLength = 50
                        Else
                            fro_txt_Nazov.MaxLength = Me._DataList.Object_Table.DatabaseTable_Data.Columns(DB.SkladoveKarty00001.Nazov).MaxLength
                            If fro_txt_Nazov.MaxLength = 0 Then
                                fro_txt_Nazov.MaxLength = 50
                            End If
                        End If

                        Me.fro_txt_Nazov.TextSlovak = .Name
                        Me.fro_txt_Nazov.TextTranslations = .NameTranslations

                        '--- Doplňujúci text - (Nastaví max dĺžku podľa hodnoty stĺpca v databáze
                        If Me._DataList Is Nothing Then
                            '--- V režime bez datalistu - chcelo by to dorobiť, aby to bolo korektné
                            fro_txt_DoplnujuciText.MaxLength = 50
                        Else
                            fro_txt_DoplnujuciText.MaxLength = Me._DataList.Object_Table.DatabaseTable_Data.Columns(DB.SkladoveKarty00001.DoplnText).MaxLength
                            If fro_txt_DoplnujuciText.MaxLength = 0 Then
                                fro_txt_DoplnujuciText.MaxLength = 50
                            End If
                        End If

                        Me.fro_txt_DoplnujuciText.TextSlovak = .TextAdditional
                        Me.fro_txt_DoplnujuciText.TextTranslations = .TextAdditionalTranslations

                        Me.fro_cbo_Umiestnenie._Text = .Location
                        Me.fro_TreeCategory._TreeCategories = .TreeCategories
                        'Nastaví max dĺžku podľa hodnoty stĺpca v databáze
                        If Me._DataList Is Nothing Then
                            '--- V režime bez datalistu - chcelo by to dorobiť, aby to bolo korektné
                            Me.fro_TreeCategory._CheckedCategories_MaxLength = 1024
                        Else
                            Me.fro_TreeCategory._CheckedCategories_MaxLength = Me._DataList.Object_Table.DatabaseTable_Data.Columns(DB.SkladoveKarty00001.TreeCategory).MaxLength
                        End If

                        Me.fro_cbo_SadzbaDPH._SelectItem(.VATRate)
                        Me.fro_cbo_SadzbaDPH_PreNakup._SelectItem(.VATRateIncome)
                        Me.fro_cbo_SkladovaSkupina.TextSlovak = .Stock_Group
                        Me.fro_cbo_SkladovaSkupina.TextTranslations = .Stock_GroupTranslations

                        '--- Typ karty - musí sa vždy zoznam nanovo naplniť, pretože sa z neho odstraňujú položky z dôvodu dostupných možností pri zmene typu
                        Me.fro_cbo_TypKarty._Items.Clear()
                        Me.fro_cbo_TypKarty._Items.AddRange(GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType))
                        Me.fro_cbo_TypKarty._SelectItem(.CardType, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                        Me.fro_cbo_MJ.TextSlovak = .Unit
                        Me.fro_cbo_MJ.TextTranslations = .UnitTranslations

                        Me.fro_txt_NumberLinkedItem._Text = .NumberLinkedItem

                        Me.fro_chk_NeaktivnaKarta._Checked = .Disabled

                        Me.z_SetControls_UnitsForPriceInput_ComboBox()
                        Me.z_SetControls_UnitsForPriceInput_Labels()


                        '-- TAB 2 - Ceny --
                        If .Price_Type = StockCard.enm_Prices_Type.Markup_Percentage Then
                            Me.fro_rdb_TvorbaCeny_NavysenieVPercentach._Checked = True
                        ElseIf .Price_Type = StockCard.enm_Prices_Type.RecomendedPrice Then
                            Me.fro_rdb_TvorbaCeny_ZlavaZDoporucenejCeny._Checked = True
                        ElseIf .Price_Type = StockCard.enm_Prices_Type.Markup_Value Then
                            Me.fro_rdb_TvorbaCeny_NavysenieVSume._Checked = True
                        Else
                            Me.fro_rdb_TvorbaCeny_PevnaPredajnaCena._Checked = True
                        End If
                        z_PriceChangeType(u_PriceCalculation:=False)

                        If .Prices_SellCalculationMode = StockCard.enm_Prices_SellCalculationMode.Always Then
                            Me.fro_rdb_PrepocetCeny_Vzdy._Checked = True
                        ElseIf .Prices_SellCalculationMode = StockCard.enm_Prices_SellCalculationMode.Ask_Before Then
                            Me.fro_rdb_PrepocetCeny_PytatSa._Checked = True
                        Else
                            Me.fro_rdb_PrepocetCeny_Nikdy._Checked = True
                        End If
                        Me.lc_UserValue_PricesCalculationType = .Prices_SellCalculationMode

                        '--- Zaokrúhlenie predajnej ceny
                        Me.fro_cbo_PredajnaCena_Zaokruhlenie._SelectItem(.Price_Rounding, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                        Dim m_PriceInputType As enm_PriceInputTypes = CType(Me.fro_cbo_PredajnaCena_Zadavanie._Selected_Item.Value, enm_PriceInputTypes)
                        Me.z_SetPrices(enm_PriceSetTargetTypes.Controls, m_PriceInputType)

                        If .Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Allow Then
                            Me.fro_rdb_ZlavyPredaj_Umoznit._Checked = True
                        ElseIf .Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Ask Then
                            Me.fro_rdb_ZlavyPredaj_Pytatsa._Checked = True
                        Else
                            Me.fro_rdb_ZlavyPredaj_Neumoznit._Checked = True
                        End If

                        Me.fro_txt_ZlavyPredaj_MaximalnaZlava._Text = CStr(.Price_Discount_MaxPercento)
                        Me.fro_chk_IgnoreExtendedSalePricing._Checked = .Prices_IgnoreExtendedSalePricing


                        'Umožni meniť ceny, pretože okno zostáva v pamäti.
                        'Me.fro_txt_PredajnaCena1_BezDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena1_Navysenie.Enabled = True
                        'Me.fro_txt_PredajnaCena1_SDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena2_BezDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena2_Navysenie.Enabled = True
                        'Me.fro_txt_PredajnaCena2_SDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena3_BezDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena3_Navysenie.Enabled = True
                        'Me.fro_txt_PredajnaCena3_SDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena4_BezDPH.Enabled = True
                        'Me.fro_txt_PredajnaCena4_Navysenie.Enabled = True
                        'Me.fro_txt_PredajnaCena4_SDPH.Enabled = True

                        'Me.fro_cbo_SadzbaDPH.Enabled = True
                        '            Me.fro_cbo_SadzbaDPH_PreNakup.Enabled = True
                        '            Me.fro_rdb_TvorbaCeny_NavysenieVPercentach.Enabled = True
                        '            Me.fro_rdb_TvorbaCeny_NavysenieVSume.Enabled = True
                        '            Me.fro_rdb_TvorbaCeny_PevnaPredajnaCena.Enabled = True
                        '            Me.fro_rdb_TvorbaCeny_ZlavaZDoporucenejCeny.Enabled = True
                        '            Me.fro_txt_PredajnaCena_Doporucena.Enabled = True
                        '            Me.fro_cbo_PredajnaCena_Zaokruhlenie.Enabled = True



                        '--- Rozšírená cenotvorba ----
                        z_SetControls_Price_ButtonExtendedPrices()

                        '-- TAB 3 - Doplň. údaje --
                        Me.fro_txt_NastaveniaMJ_VahaMJ._Text = CStr(.Unit_Weight)
                        Me.fro_cbo_NastaveniaMJ_VahaMJ._SelectItem(.Unit_Weight_Unit)
                        Me.fro_cbo_NastaveniaMJ_MJPrePorovnanieCeny._SelectItem(.Unit_Calculation_PriceCompare)
                        Me.fro_txt_NastaveniaMJ_MJPrePorovnanieCeny_Koeficient._Text = CStr(.Unit_Calculation_PriceCompare_Coefficient)
                        Me.fro_txt_DoplnUdaje_DatumZaevidovaniaKarty._Text = CStr(.DateTime_Created.ToLocalTime)

                        Me.fro_txt_DoplnUdaje_ZarucnaDoba._Text = CStr(.Guarantee_Period_Value)
                        Me.fro_cbo_DoplnUdaje_ZarucnaDoba._SelectItem(.Guarantee_Period_Unit, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                        Me.fro_cbo_DoplnUdaje_ZarucnaDobaExpirationMode._SelectItem(.Guarantee_ExpirationMode, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                        Me.fro_cbo_DoplnUdaje_SerialNumbersMode._SelectItem(.SerialNumber_Mode, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                        Me.fro_chk_PrijateNaKomisionalnyPredaj._Checked = .Sale_Commision
                        Me.fro_chk_DoplnUdaje_UvadzatVCenniku._Checked = .PriceList_Show
                        Me.fro_txt_PopisPriPredaji._Text = .Sale_Description

                        Me.fro_txt_Uctovanie_Predkontacia_Cislo._Text = CStr(.Accounting_AccountCoding)
                        z_SetControls_UctovaniePredkontaciaText()

                        Me.fro_txt_CustomsTariffCode._Text = CStr(.CustomsTariffCode)
                        z_SetControls_CustomsTariffCodeText()

                        Me.fro_ColorSelector_FarbaPolozky._Color = .ItemColor


                        '--- Spotrebiteľské balenie liehu
                        Me.fro_chk_SBL_UvadzatVOznameniOPrijmeAleboPredaji._Checked = .CustomsEvidence_Alcohol_Register
                        Me.fro_txt_SBL_ObchodnyNazov._Text = .CustomsEvidence_Alcohol_Name
                        Me.fro_txt_SBL_ObjemVLitroch._Text = CStr(.CustomsEvidence_Alcohol_Volume)
                        Me.fro_txt_SBL_PercentoObjemu._Text = CStr(.CustomsEvidence_Alcohol_Percentage)


                        Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMinimalne._Text = CStr(.Amount_Minimal)
                        Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMaximalne._Text = CStr(.Amount_Maximal)
                        Me.fro_txt_MinimalOrderAmount._Text = CStr(.MinimalOrderAmount)
                        Me.fro_chk_LS_PointsCalculate._Checked = .LS_IsPointsCalculate
                        Me.fro_txt_LS_PointsBenefitsCumulate._Text = CStr(.LS_PointsBenefitsCumulate)
                        Me.fro_txt_LS_PointsBenefitsApply._Text = CStr(.LS_PointsBenefitsApply)

                        If e.Action = cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Load_Edit Then
                            Me.fro_dgv_Variants._DataSource = Me._DataRecord.Items_Variant
                            Me.fro_dgv_Parameters._DataSource = Me._DataRecord.Items_Parameter
                            Me.fro_dgv_Suppliers._DataSource = Me._DataRecord.Items_Supplier

                            'Zobraz počet variánt a parametrov.
                            Me.fro_lbl_Variants_Count._Text = Exa.Application.TranslateTextEx("Počet variant:  {0}", CStr(Me._DataRecord.Items_Variant.Count))
                            Me.fro_lbl_Parameters_Count._Text = Exa.Application.TranslateTextEx("Počet:  {0}", CStr(Me._DataRecord.Items_Parameter.Count))

                            '--- Varianty ---
                            z_SetControls_VariantsCheckAmountInfo()

                        Else
                            'OPRAVA: Opravuje chybu ktorá vzniká tým, že form zostáva v pamäti, zostáva nastavený už nekorektný zdroj údajov,
                            '        zdroj údajov nového záznamu sa nastaví pri uložení záznamu pred pridaním odberateľa
                            Me.fro_dgv_Variants._DataSource = Nothing
                            Me.fro_dgv_Parameters._DataSource = Nothing
                            Me.fro_dgv_Suppliers._DataSource = Nothing

                            Me.fro_lbl_Variants_Count._Text = Exa.Application.TranslateTextEx("Počet variant:  {0}", "0")
                            Me.fro_lbl_Parameters_Count._Text = Exa.Application.TranslateTextEx("Počet:  {0}", "0")
                        End If


                        '-- TAB 5 - Internetový obchod --
                        ': Len ak je stránka zobrazená, zobrazenie stránky sa nastavuje v konštruktore podľa nastavení programu
                        If Me.fro_tab_InternetovyObchod.VisibleTab = True Then
                            '--- WWW - (Nastaví max dĺžku podľa hodnoty stĺpca v databáze)
                            If Me._DataList Is Nothing Then
                                '--- V režime bez datalistu - chcelo by to dorobiť, aby to bolo korektné
                                fro_cbo_IObchod_Web.Text_MaxLength = 50
                            Else

                                fro_cbo_IObchod_Web.Text_MaxLength = Me._DataList.Object_Table.DatabaseTable_Schema.Columns.Item(DB.SkladoveKarty00001.InShopWWW).MaxLength
                                If fro_cbo_IObchod_Web.Text_MaxLength = 0 Then
                                    fro_cbo_IObchod_Web.Text_MaxLength = 50
                                End If
                            End If

                            Me.fro_chk_IObchod_ZaraditDoIObchodu._Checked = .eShop._Show
                            'Me.fro_txt_IObchod_Nazov._Text = .eShop.Name
                            Me.fro_txt_IObchod_Nazov.TextSlovak = .eShop.Name
                            Me.fro_txt_IObchod_Nazov.TextTranslations = .EShop_NameTranslations

                            'Me.fro_txt_IObchod_Popis._Text = .eShop.Description
                            Me.fro_txt_IObchod_Popis.TextSlovak = .eShop.Description
                            Me.fro_txt_IObchod_Popis.TextTranslations = .EShop_ShortDescriptionTranslations


                            Me.fro_cbo_IObchod_Vyrobca._Text = .eShop.Producer
                            Me.fro_cbo_IObchod_Web._Text = .eShop.WWW
                            Me.fro_txt_IObchod_Zlava._Text = CStr(.eShop.Discount)
                            Me.fro_txt_IObchod_Zlava_Platnost._Text = CStr(.eShop.Discount_Availability)

                            'Me.fro_cbo_IObchod_DobaDodania._Text = .eShop.DeliveryTerm
                            Me.fro_cbo_IObchod_DobaDodania_Skladom.TextSlovak = .eShop.DeliveryTerm
                            Me.fro_cbo_IObchod_DobaDodania_Skladom.TextTranslations = .EShop_DeliveryTermTranslations

                            Me.fro_cbo_IObchod_DobaDodania_Nulove.TextSlovak = .eShop.DeliveryTermOnZeroAmount
                            Me.fro_cbo_IObchod_DobaDodania_Nulove.TextTranslations = .EShop_DeliveryTermOnZeroAmountTranslations


                            Me.fro_chk_IObchod_Novinka._Checked = .eShop.IsNewItem
                            Me.fro_chk_IObchod_Vypredaj._Checked = .eShop.SaleOut

                            Me.fro_cbo_IObchod_Availability._SelectItem(.Availability, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                        End If


                        '-- TAB 6 - Reg. pokladnice --
                        Me.fro_txt_RPokladnice_CiarovyKod._Text = Exa.Basic.Strings.Convert_From_Array(.BarCodes, Exa.Basic.Strings.enm_StringSeparator_UsingTypes.Behind, ", ", True)

                        Me.fro_cbo_RegPokladnica_ItemFlags._SelectItem(.CashRegister_ItemFlag, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)


                        Me.fro_txt_RPoklSFiskalom_KodPolozky._Text = .CashRegister_Code 'POZOR: Nastaviť pred nastavením controlu 'fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici' 

                        If e.Action = cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Load_Default AndAlso Me.lc_WorkMode = enm_WorkModeTypes.CashRegister Then
                            Me.fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici._Checked = True
                            'POZOR: V tomto okamihu dôjde tiež k spracovaniu udalosti 'fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici_ev_CheckedChanged',
                            '       ktorá nastaví 'Kód položky' podľa aktuálneho 'Čísla karty'
                        Else
                            Me.fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici._Checked = .CashRegister_Sale
                        End If

                        Me.fro_cbo_RPoklSFiskalom_TovarovaSkupina._Text = .CashRegister_CommodityGroup
                        Me.fro_cbo_AutomatickaTlacEtikety._Text = .CashRegister_ReportTagName


                        If e.Action = cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Load_Default Then
                            ' toto sa musí resetnúť pri každom default načítaní, pretože ak sa uloží predošlá karta tak z comba nie je
                            ' odstránená položka, tak isto aj pri zmene skladu zostanú načítané staré údaje.
                            Me.fro_cbo_RPOffline_CisloPLU.ResetNeedLoadItems()
                            Me.fro_cbo_AutomatickaTlacEtikety.ResetNeedLoadItems()
                        End If

                        If .CashRegister_Flags.PLU_Number > 0 Then
                            Me.fro_cbo_RPOffline_CisloPLU._Text = CStr(.CashRegister_Flags.PLU_Number)
                        Else
                            Me.fro_cbo_RPOffline_CisloPLU._Text = String.Empty
                        End If

                        Me.fro_txt_RPokladnica_NazovPolozky.TextSlovak = .CashRegister_Flags.PLU_Name
                        Me.fro_txt_RPokladnica_NazovPolozky.TextTranslations = .CashRegister_PLUName_Translations

                        Me.fro_cbo_RegPokladnica_CashRegisterGroup.TextSlovak = .CookRecipe_CashRegisterCategory
                        Me.fro_cbo_RegPokladnica_CashRegisterGroup.TextTranslations = .CookRecipe_CashRegisterCategoryTranslations



                        '-- TAB 7 - Receptúra --
                        ': Len ak je stránka zobrazená, zobrazenie stránky sa nastavuje v konštruktore podľa nastavení programu
                        If Me.fro_tab_Receptura.VisibleTab = True Then

                            '--- Bonovacie tlačiarne ---
                            If e.Action = cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Load_Default Then
                                '--- Naplniť zoznam tlačiarní ---
                                Me.fro_cbo_RegPokladnica_PrinterOrder1._Items.Update_Begin()
                                Me.fro_cbo_RegPokladnica_PrinterOrder2._Items.Update_Begin()
                                Me.fro_cbo_RegPokladnica_PrinterOrder1._Items.Clear()
                                Me.fro_cbo_RegPokladnica_PrinterOrder2._Items.Clear()
                                For i = 0 To Exa.OBERON.Devices.PrinterOrder.CONST_PrinterOrderMax
                                    Me.fro_cbo_RegPokladnica_PrinterOrder1._Items.Add(CStr(i))
                                    Me.fro_cbo_RegPokladnica_PrinterOrder2._Items.Add(CStr(i))
                                Next
                                Me.fro_cbo_RegPokladnica_PrinterOrder1._Items.Update_End()
                                Me.fro_cbo_RegPokladnica_PrinterOrder2._Items.Update_End()
                            End If

                            Me.fro_cbo_RegPokladnica_PrinterOrder1._Text = CStr(.CashRegister_PrinterOrder)
                            Me.fro_cbo_RegPokladnica_PrinterOrder2._Text = CStr(.CashRegister_PrinterOrderCopy)


                            Me.fro_txt_CookRecipe_Menu_SideDishCodes._Text = Exa.Basic.Strings.Convert_From_Array(.CookRecipe_Menu_SideDishCodes,
                                                                                                                  u_SeparatorUsingType:=Exa.Basic.Strings.mod_String.enm_StringSeparator_UsingTypes.Behind,
                                                                                                                  u_Separator:=", ",
                                                                                                                  u_Ignore_StringEmpty:=True)

                            Me.fro_txt_CookRecipe_Menu_Specification._Text = Exa.Basic.Strings.Convert_From_Array(.CookRecipe_Menu_Specifications,
                                                                                                                  u_SeparatorUsingType:=Exa.Basic.Strings.mod_String.enm_StringSeparator_UsingTypes.Behind,
                                                                                                                  u_Separator:=", ",
                                                                                                                  u_Ignore_StringEmpty:=True)

                            Me.fro_chkt_CookRecipe_Menu_SpecificationRequired._Checked = .CookRecipe_Menu_SpecificationIsRequired

                            Me.fro_chk_RegPokladnica_Inventura_TlacitVInventarnomSupise._Checked = .CashRegister_InventoryPrint

                            'Zoznam skupín v jedálnom lístku, hodnota bude do 'DataGridu' načítaná v udalosti Form_Load
                            Me.lc_FoodMenu_SelectedList = .CookRecipe_Menu_Names.ToList
                        End If

                        .BarCodeSettings._UpdateControl(fro_isl_BarcodeSettings)


                    End With


                Case cls_DataRecordActionEventArgs.enm_ActionTypes.SetValues_Save
                    With Me._DataRecord
                        '-- TAB 1 - Základné --


                        '--- Množstvo a cena
                        If ._Stock.ExternalStock = True Then
                            '--- Externý sklad - zostatkové množstvo sa môže uložiť
                            .Amount = CDec(Me.fro_txt_Mnozstvo_Aktualne._Value)
                        End If

                        If Me.fro_txt_Cena_Obstaravacia.ReadOnly = True Or Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = True Then
                            '--- Neukladať obstar. cenu (užívateľ môže mať zakázané právo na zobrazovanie) ----
                        Else
                            .Price_Supply_Unit = CDec(Me.fro_txt_Cena_Obstaravacia._Value)
                        End If

                        If Me.fro_txt_Cena_PoslednaNakupna.ReadOnly = True Or Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = True Then
                            '--- Neukladať poslednú nákupnú cenu (užívateľ môže mať zakázané právo na zobrazovanie) ----
                        Else
                            .Price_LastPurchase = CDec(Me.fro_txt_Cena_PoslednaNakupna._Value)
                        End If

                        .Number = Me.fro_txt_CisloKarty._Text
                        .Classification_Production = Me.fro_txt_KP._Text

                        .Name = Me.fro_txt_Nazov.TextSlovak
                        .TextAdditional = Me.fro_txt_DoplnujuciText.TextSlovak


                        .Location = Me.fro_cbo_Umiestnenie._Text
                        .TreeCategories = Me.fro_TreeCategory._TreeCategories

                        .VATRate = CByte(Me.fro_cbo_SadzbaDPH._Text)
                        If Me.lc_AppConfiguration.Stock.Using_Firm_TwoVATRate = True Then
                            '--- Používať aj sadzbu DPH pre nákup ---
                            .VATRateIncome = CByte(Me.fro_cbo_SadzbaDPH_PreNakup._Text)
                        Else
                            '--- Do sadzby DPH pre nákup nastaviť štandardnú sadzbu DPH
                            .VATRateIncome = CByte(Me.fro_cbo_SadzbaDPH._Text)
                        End If

                        .Stock_Group = Me.fro_cbo_SkladovaSkupina.TextSlovak
                        .CardType = CType(Me.fro_cbo_TypKarty._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType)
                        .Unit = Me.fro_cbo_MJ.TextSlovak

                        .NumberLinkedItem = Me.fro_txt_NumberLinkedItem._Text

                        .Disabled = Me.fro_chk_NeaktivnaKarta._Checked


                        '-- TAB 2 - Ceny --
                        If Me.fro_rdb_TvorbaCeny_NavysenieVPercentach._Checked = True Then
                            .Price_Type = StockCard.enm_Prices_Type.Markup_Percentage
                        ElseIf Me.fro_rdb_TvorbaCeny_ZlavaZDoporucenejCeny._Checked = True Then
                            .Price_Type = StockCard.enm_Prices_Type.RecomendedPrice
                        ElseIf Me.fro_rdb_TvorbaCeny_NavysenieVSume._Checked = True Then
                            .Price_Type = StockCard.enm_Prices_Type.Markup_Value
                        Else
                            .Price_Type = StockCard.enm_Prices_Type.Fixed_Price
                        End If

                        If Me.fro_rdb_PrepocetCeny_Vzdy._Checked = True Then
                            .Prices_SellCalculationMode = StockCard.enm_Prices_SellCalculationMode.Always
                        ElseIf Me.fro_rdb_PrepocetCeny_PytatSa._Checked = True Then
                            .Prices_SellCalculationMode = StockCard.enm_Prices_SellCalculationMode.Ask_Before
                        Else
                            .Prices_SellCalculationMode = StockCard.enm_Prices_SellCalculationMode.Never
                        End If

                        Dim m_PriceInputType As enm_PriceInputTypes = CType(Me.fro_cbo_PredajnaCena_Zadavanie._Selected_Item.Value, enm_PriceInputTypes)
                        Me.z_SetPrices(enm_PriceSetTargetTypes.DataRecord, m_PriceInputType)

                        If Me.fro_rdb_ZlavyPredaj_Umoznit._Checked = True Then
                            .Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Allow
                        ElseIf Me.fro_rdb_ZlavyPredaj_Pytatsa._Checked = True Then
                            .Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Ask
                        Else
                            .Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Disallow
                        End If

                        .Price_Discount_MaxPercento = CDec(Me.fro_txt_ZlavyPredaj_MaximalnaZlava._Value)

                        If Me.lc_AppConfiguration.Stock.Using_Firm_ExtendedSalePrice = True Then
                            .Prices_IgnoreExtendedSalePricing = Me.fro_chk_IgnoreExtendedSalePricing._Checked
                        End If

                        '-- TAB 3 - Doplň. údaje --
                        .Unit_Weight = CDec(Me.fro_txt_NastaveniaMJ_VahaMJ._Value)
                        .Unit_Weight_Unit = Me.fro_cbo_NastaveniaMJ_VahaMJ._Text
                        .Unit_Calculation_PriceCompare = fro_cbo_NastaveniaMJ_MJPrePorovnanieCeny._Text
                        .Unit_Calculation_PriceCompare_Coefficient = CDec(fro_txt_NastaveniaMJ_MJPrePorovnanieCeny_Koeficient._Value)

                        If CDate(Me.fro_txt_DoplnUdaje_DatumZaevidovaniaKarty._Value) = Nothing Then
                            .DateTime_Created = Now.Date.ToUniversalTime
                        Else
                            .DateTime_Created = CDate(Me.fro_txt_DoplnUdaje_DatumZaevidovaniaKarty._Value).ToUniversalTime
                        End If

                        .Guarantee_Period_Value = CDbl(Me.fro_txt_DoplnUdaje_ZarucnaDoba._Value)
                        .Guarantee_Period_Unit = CType(Me.fro_cbo_DoplnUdaje_ZarucnaDoba._Selected_Item.Value, StockCard.enm_GuaranteePeriodUnit)
                        .Guarantee_ExpirationMode = CType(fro_cbo_DoplnUdaje_ZarucnaDobaExpirationMode._Selected_Item.Value, StockCard.enm_GuaranteePeriodExpirationMode)

                        .SerialNumber_Mode = CType(fro_cbo_DoplnUdaje_SerialNumbersMode._Selected_Item.Value, Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode)

                        .Sale_Commision = Me.fro_chk_PrijateNaKomisionalnyPredaj._Checked
                        .PriceList_Show = Me.fro_chk_DoplnUdaje_UvadzatVCenniku._Checked
                        .Accounting_AccountCoding = CInt(Me.fro_txt_Uctovanie_Predkontacia_Cislo._Value)
                        .CustomsTariffCode = CStr(Me.fro_txt_CustomsTariffCode._Value)
                        .Sale_Description = Me.fro_txt_PopisPriPredaji._Text

                        .CustomsEvidence_Alcohol_Register = Me.fro_chk_SBL_UvadzatVOznameniOPrijmeAleboPredaji._Checked
                        .CustomsEvidence_Alcohol_Name = Me.fro_txt_SBL_ObchodnyNazov._Text
                        .CustomsEvidence_Alcohol_Volume = CDec(Me.fro_txt_SBL_ObjemVLitroch._Value)
                        .CustomsEvidence_Alcohol_Percentage = CDec(Me.fro_txt_SBL_PercentoObjemu._Value)

                        .ItemColor = Me.fro_ColorSelector_FarbaPolozky._Color

                        '-- TAB 4 - Obch. partneri --

                        .Amount_Minimal = CDec(Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMinimalne._Value)
                        .Amount_Maximal = CDec(Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMaximalne._Value)
                        .MinimalOrderAmount = CDec(Me.fro_txt_MinimalOrderAmount._Value)
                        .LS_IsPointsCalculate = Me.fro_chk_LS_PointsCalculate._Checked
                        .LS_PointsBenefitsCumulate = CDec(Me.fro_txt_LS_PointsBenefitsCumulate._Value)
                        .LS_PointsBenefitsApply = CDec(Me.fro_txt_LS_PointsBenefitsApply._Value)

                        '-- TAB 5 - Internetový obchod --
                        ': Len ak je stránka zobrazená, zobrazenie stránky sa nastavuje v konštruktore podľa nastavení programu
                        If Me.fro_tab_InternetovyObchod.VisibleTab = True Then
                            .eShop._Show = Me.fro_chk_IObchod_ZaraditDoIObchodu._Checked

                            .eShop.Name = Me.fro_txt_IObchod_Nazov.TextSlovak
                            .eShop.Description = Me.fro_txt_IObchod_Popis.TextSlovak

                            .eShop.Producer = Me.fro_cbo_IObchod_Vyrobca._Text
                            .eShop.WWW = Me.fro_cbo_IObchod_Web._Text
                            .eShop.Discount = CDec(Me.fro_txt_IObchod_Zlava._Value)
                            .eShop.Discount_Availability = CType(Me.fro_txt_IObchod_Zlava_Platnost._Value, Date)

                            .eShop.DeliveryTerm = Me.fro_cbo_IObchod_DobaDodania_Skladom.TextSlovak
                            .eShop.DeliveryTermOnZeroAmount = Me.fro_cbo_IObchod_DobaDodania_Nulove.TextSlovak

                            .eShop.IsNewItem = Me.fro_chk_IObchod_Novinka._Checked
                            .eShop.SaleOut = Me.fro_chk_IObchod_Vypredaj._Checked

                            .Availability = CType(Me.fro_cbo_IObchod_Availability._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_Availability)

                        End If


                        '-- TAB 6 - Reg. pokladnice --
                        If Me.fro_txt_RPokladnice_CiarovyKod._Text = String.Empty Then
                            .BarCodes = Nothing
                        Else
                            .BarCodes = Exa.Basic.Strings.Convert_To_ArrayString(Me.fro_txt_RPokladnice_CiarovyKod._Text, Exa.Basic.Strings.enm_StringSeparator_UsingTypes.Behind, CChar(", "), True)
                        End If

                        .CashRegister_ItemFlag = CType(Me.fro_cbo_RegPokladnica_ItemFlags._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_CashRegister_ItemFlag)

                        .CashRegister_Sale = Me.fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici._Checked

                        .CashRegister_Flags.PLU_Name = Me.fro_txt_RPokladnica_NazovPolozky.TextSlovak

                        .CashRegister_Code = Me.fro_txt_RPoklSFiskalom_KodPolozky._Text
                        .CashRegister_CommodityGroup = Me.fro_cbo_RPoklSFiskalom_TovarovaSkupina._Text
                        .CashRegister_ReportTagName = Me.fro_cbo_AutomatickaTlacEtikety._Text

                        If Me.fro_cbo_RPOffline_CisloPLU._Text <> String.Empty AndAlso Trim(Me.fro_cbo_RPOffline_CisloPLU._Text).Length > 0 Then
                            .CashRegister_Flags.PLU_Number = CInt(Me.fro_cbo_RPOffline_CisloPLU._Value)
                        Else
                            .CashRegister_Flags.PLU_Number = 0
                        End If

                        .CookRecipe_CashRegisterCategory = Me.fro_cbo_RegPokladnica_CashRegisterGroup.TextSlovak


                        '-- TAB 7 - Receptúra --
                        ': Len ak je stránka zobrazená, zobrazenie stránky sa nastavuje v konštruktore podľa nastavení programu
                        If Me.fro_tab_Receptura.VisibleTab = True Then
                            .CashRegister_PrinterOrder = CByte(Me.fro_cbo_RegPokladnica_PrinterOrder1._Value)
                            .CashRegister_PrinterOrderCopy = CByte(Me.fro_cbo_RegPokladnica_PrinterOrder2._Value)

                            .CookRecipe_Menu_Names = Me.lc_FoodMenu_SelectedList.ToArray

                            .CookRecipe_Menu_SideDishCodes = Exa.Basic.Strings.Convert_To_ArrayString(Me.fro_txt_CookRecipe_Menu_SideDishCodes._Text,
                                                                                                                  u_SeparatorUsingType:=Exa.Basic.Strings.mod_String.enm_StringSeparator_UsingTypes.Behind,
                                                                                                                  u_Separator:=","c,
                                                                                                                  u_ApplyTRIM:=True)

                            .CookRecipe_Menu_Specifications = Exa.Basic.Strings.Convert_To_ArrayString(Me.fro_txt_CookRecipe_Menu_Specification._Text,
                                                                                                                  u_SeparatorUsingType:=Exa.Basic.Strings.mod_String.enm_StringSeparator_UsingTypes.Behind,
                                                                                                                  u_Separator:=","c,
                                                                                                                  u_ApplyTRIM:=True)

                            .CookRecipe_Menu_SpecificationIsRequired = Me.fro_chkt_CookRecipe_Menu_SpecificationRequired._Checked

                            .CashRegister_InventoryPrint = Me.fro_chk_RegPokladnica_Inventura_TlacitVInventarnomSupise._Checked

                        End If


                        .BarCodeSettings._Update(fro_isl_BarcodeSettings._Items)

                    End With

            End Select

            e.ExaException.Result = True

        End Sub

        Private Sub Form_ev_TemplateValuesAction(sender As Object, e As Application.Controls.Composition.C_TemplateValues.mod_TemplateValues.cls_TemplateActionEventArgs) Handles Me.ev_TemplateValuesAction

            On Error Resume Next

            Select Case e.Action
                Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.enm_ActionTypes.Set_Settings
                    e.Settings = New Exa.Application.Controls.Composition.C_TemplateValues.stc_TemplatesSettings(Exa.OBERON.Stock.StockCards.StockCard.C_TEMPLATE_VALUES_IDENTIFIER, Me.lc_AppConfiguration._AppObjects._UserInfo.UserMainValues.IDNum, Me.fro_btn_Sablony)

                Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.enm_ActionTypes.Add_Fields
                    With e.Fields
                        .Add(Me.GetTemplateControls)
                        '
                        .Add("Typ karty", "TypKarty", GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType))
                        '
                        .Add("Tvorba predajnej ceny", "RabatSkOrPercento", GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_Prices_Type))
                        .Add("Prepočet predajnej ceny", "PrepocetCP", GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_Prices_SellCalculationMode))
                        .Add("Zľavy pri predaji", "Discount_Flag", GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_Prices_SellCalculationMode))
                        .Add("Zaokrúhlenie ceny s DPH", "ZaokruhlenieCP", enm_TemplateInputTypes.DropDownList, enm_TemplateValueFormatTypes.Custom,
                                u_Custom_Texts:=New String() {"12,7777 => 13,000", "12,7777 => 12,800", "12,7777 => 12,780", "12,7777 => 12,778"},
                                u_Custom_Values:=New Object() {Exa.Basic.Numerics.enm_Decimal_Places.Decimal_0, Exa.Basic.Numerics.enm_Decimal_Places.Decimal_1, Exa.Basic.Numerics.enm_Decimal_Places.Decimal_2, Exa.Basic.Numerics.enm_Decimal_Places.Decimal_3})
                        '
                        .Add("Výrobné a sériové čísla", "VyrobneCislaEvidovat", GetType(Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode))
                        .Add("Kategória", DB.SkladoveKarty00001.TreeCategory, enm_TemplateInputTypes.Text, u_ShowButtonList:=True, u_ReadOnly:=True)
                        '


                    End With

                Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.enm_ActionTypes.Ev_ApplyValuesBegin
                    AddHandler Me._DataRecord.ev_DataRecordPropertyChange, AddressOf Me.eh_DataRecordPropertyChange

                Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.enm_ActionTypes.Ev_ApplyValuesEnd
                    RemoveHandler Me._DataRecord.ev_DataRecordPropertyChange, AddressOf Me.eh_DataRecordPropertyChange

                    Me.z_SetControls_CustomsTariffCodeText()

                Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.enm_ActionTypes.On_SetDataRecordRowValues

                    Select Case e.SetDataRecordRowValuesEventArgs.Action
        'Case Database.Factory.DataRecord.cls_SetRowValuesFromTemplateEventArgs.enm_ActionTypes.Starting
        '* Zatiaľ sa nepoužíva ...

                        Case Database.Factory.DataRecord.cls_SetRowValuesFromTemplateEventArgs.enm_ActionTypes.UpdatingRowValue
                            Dim m_DatabaseField$ = e.SetDataRecordRowValuesEventArgs.DatabaseField

                            'Zruš nastavenie hodnoty zo šablóny, ak je control pre ktorý platí hodnota šablóny zakázaný.
                            If StrComp(m_DatabaseField$, "CenaObstar", CompareMethod.Text) = 0 Then
                                e.SetDataRecordRowValuesEventArgs.Cancel = Not Me.fro_txt_Cena_Obstaravacia.Enabled Or Me.fro_txt_Cena_Obstaravacia.ReadOnly

                            ElseIf StrComp(m_DatabaseField$, "CenaLastNakupna", CompareMethod.Text) = 0 Then
                                e.SetDataRecordRowValuesEventArgs.Cancel = Not Me.fro_txt_Cena_PoslednaNakupna.Enabled Or Me.fro_txt_Cena_PoslednaNakupna.ReadOnly

                            End If

                        Case Database.Factory.DataRecord.cls_SetRowValuesFromTemplateEventArgs.enm_ActionTypes.Completed
                            Dim m_ChangedDatabaseFields() As String = e.SetDataRecordRowValuesEventArgs.ChangedDatabaseFields

                            'Prepočítaj navýšenie (zľavu) alebo predajné ceny s DPH.
                            'Uprednostnené sú predajné ceny pred navýšením (zľavou), ak sú zadané všetky hodnoty súčasne.
                            '
                            'POZOR: Všetky názvy databázových stĺpcov sú zadané s malými písmenami.
                            If Array.IndexOf(m_ChangedDatabaseFields, LCase("CenaPredajSDPH1")) >= 0 Then
                                Me._DataRecord.Price_Calculation(1, StockCard.enm_Price_Calculation.Change_Price_With_VAT, 0, True)
                            ElseIf Array.IndexOf(m_ChangedDatabaseFields, LCase("Rabat1")) >= 0 Then
                                Me._DataRecord.Price_Calculation(1, StockCard.enm_Price_Calculation.Change_Markup, 0, True)
                            End If

                            If Array.IndexOf(m_ChangedDatabaseFields, LCase("CenaPredajSDPH2")) >= 0 Then
                                Me._DataRecord.Price_Calculation(2, StockCard.enm_Price_Calculation.Change_Price_With_VAT, 0, True)
                            ElseIf Array.IndexOf(m_ChangedDatabaseFields, LCase("Rabat2")) >= 0 Then
                                Me._DataRecord.Price_Calculation(2, StockCard.enm_Price_Calculation.Change_Markup, 0, True)
                            End If

                            If Array.IndexOf(m_ChangedDatabaseFields, LCase("CenaPredajSDPH3")) >= 0 Then
                                Me._DataRecord.Price_Calculation(3, StockCard.enm_Price_Calculation.Change_Price_With_VAT, 0, True)
                            ElseIf Array.IndexOf(m_ChangedDatabaseFields, LCase("Rabat3")) >= 0 Then
                                Me._DataRecord.Price_Calculation(3, StockCard.enm_Price_Calculation.Change_Markup, 0, True)
                            End If

                            If Array.IndexOf(m_ChangedDatabaseFields, LCase("CenaPredajSDPH4")) >= 0 Then
                                Me._DataRecord.Price_Calculation(4, StockCard.enm_Price_Calculation.Change_Price_With_VAT, 0, True)
                            ElseIf Array.IndexOf(m_ChangedDatabaseFields, LCase("Rabat4")) >= 0 Then
                                Me._DataRecord.Price_Calculation(4, StockCard.enm_Price_Calculation.Change_Markup, 0, True)
                            End If

                    End Select

                Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.enm_ActionTypes.On_FormTemplateEditor

                    Select Case e.FormTemplateEditorAction.Action
        'Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.stc_OnFormTemplateEditorAction.enm_ActionTypes.SetTemplateValueRow
        '* Zatiaľ sa nepoužíva ...

                        Case Application.Controls.Composition.C_TemplateValues.cls_TemplateActionEventArgs.stc_OnFormTemplateEditorAction.enm_ActionTypes.EditorCellControlAction

                            Select Case e.FormTemplateEditorAction.EditorCellControlActionEventArgs.ActionType
                                Case Application.Controls.Composition.C_TemplateValues.BaseControls.C_Template_Values_Win32.cls_EditorCellControlActionEventArgs.enm_ActionTypes.FillDropDown
                                    Dim m_DatabaseField$ = e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DatabaseField

                                    If StrComp(m_DatabaseField$, "SadzbaDPH", CompareMethod.Text) = 0 Or StrComp(m_DatabaseField$, "SadzbaDPHNakup", CompareMethod.Text) = 0 Then
                                        'Sadzby DPH.
                                        Dim m_VATRates As List(Of Decimal) = Me.lc_AppConfiguration.Common.VAT.RatesInfo.GetRateList()

                                        With e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DropDownItems
                                            .Update_Begin()
                                            .Clear()
                                            For Each e_VATRate As Byte In m_VATRates
                                                .Add(CStr(e_VATRate))
                                            Next
                                            .Update_End()
                                        End With

                                    ElseIf StrComp(m_DatabaseField$, "RecepturaPoplatokSkupina", CompareMethod.Text) = 0 Then
                                        'Tovarová skupina.
                                        Dim m_StockCard_ComodityGroup_List As New Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_ComodityGroup_List(Me.lc_AppConfiguration)

                                        With e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DropDownItems
                                            .Clear()
                                            .AddRange(m_StockCard_ComodityGroup_List, True)
                                        End With

                                        If m_StockCard_ComodityGroup_List IsNot Nothing Then m_StockCard_ComodityGroup_List.Dispose()
                                        m_StockCard_ComodityGroup_List = Nothing

                                    ElseIf StrComp(m_DatabaseField$, "MJVahaMJ", CompareMethod.Text) = 0 Then
                                        'Váha MJ.
                                        With e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DropDownItems
                                            .Update_Begin()
                                            .Clear()
                                            .Add("g")
                                            .Add("kg")
                                            .Add("t")
                                            .Update_End()
                                        End With

                                    ElseIf StrComp(m_DatabaseField$, "ZarucnaDoba", CompareMethod.Text) = 0 Then
                                        'Záručná doba.
                                        With e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DropDownItems
                                            .Clear()
                                            .AddRange(GetType(StockCard.enm_GuaranteePeriodUnit))
                                        End With

                                    ElseIf StrComp(m_DatabaseField$, DB.SkladoveKarty00001.CashRegisterReportTagName, CompareMethod.Text) = 0 Then
                                        'Automatická tlač etikety.
                                        Dim m_ExaException As EXC.ExaException = Nothing
                                        Dim m_StockCard_Reports_CashRegisterTags As New Exa.OBERON.Stock.StockCards.Reports.StockCard_Reports_CashRegisterTags(Me.lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)
                                        Dim m_ModuleBooksAndReports As New Exa.Application.Reports.Report_List.cls_ModuleBookWithReportsIDCollection

                                        With m_ModuleBooksAndReports
                                            .Add(Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_Report_Module_Stock.StockCard_CashRegister_Tags,
                                                    Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_ReportID_StockCards_CashRegister_Tags.Etikety_1ksNaList,
                                                    Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_ReportID_StockCards_CashRegister_Tags.Etikety_Landscape_1ksNaList)
                                        End With

                                        Dim m_ReportList As Exa.Application.Reports.Report_List = Nothing

                                        m_ExaException = m_StockCard_Reports_CashRegisterTags.LoadReportList(Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.Stock,
                                                                                                                m_ModuleBooksAndReports,
                                                                                                                m_ReportList)

                                        If m_ExaException.Result = True AndAlso m_ReportList IsNot Nothing AndAlso m_ReportList.Object_Table IsNot Nothing Then
                                            With e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DropDownItems
                                                .Update_Begin()
                                                .Clear()
                                                .Add(String.Empty) '* Položka pre výber keď tlačový výstup nie je zadaný ...

                                                For Each e_Row As DataRow In m_ReportList.Object_Table.DatabaseTable_Data.Rows
                                                    Dim m_Report As Exa.Application.Reports.Report = m_ReportList.DataRecord(e_Row, True)
                                                    Dim m_Image As Drawing.Image = Exa.Application.Reports.GetReportItemImage(CType(m_Report.Image_Number, Exa.Application.Reports.enm_ReportItemImageTypes))
                                                    Dim m_IsLocked As Boolean = False

                                                    'If m_Report.UserPrivileges = String.Empty OrElse m_Report.UserPrivileges.Contains("\" & u_User_IDNum & "\") = False Then
                                                    '    m_IsLocked = True
                                                    'End If
                                                    '* Zrušené, nepoužíva sa zatiaľ ...

                                                    .Add(m_Report.Name, m_Report.IDNum, m_Image)
                                                Next

                                                .Update_End()
                                            End With
                                        End If

                                        If m_ReportList IsNot Nothing Then m_ReportList.Dispose()
                                        m_ReportList = Nothing

                                        If m_StockCard_Reports_CashRegisterTags IsNot Nothing Then m_StockCard_Reports_CashRegisterTags.Dispose()
                                        m_StockCard_Reports_CashRegisterTags = Nothing

                                        'ElseIf StrComp(e.DatabaseField, "VyrobneCislaEvidovat", CompareMethod.Text) = 0 Then
                                        'Výrobné a sériové čísla.
                                        'e.DropDownItems.AddRange(GetType(Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode))
                                        '* Zatiaľ sa nepoužíva ...

                                    End If

                                Case Application.Controls.Composition.C_TemplateValues.BaseControls.C_Template_Values_Win32.cls_EditorCellControlActionEventArgs.enm_ActionTypes.ListSelect
                                    Dim m_DatabaseField$ = e.FormTemplateEditorAction.EditorCellControlActionEventArgs.DatabaseField

                                    If StrComp(m_DatabaseField$, DB.SkladoveKarty00001.TreeCategory, CompareMethod.Text) = 0 Then
                                        'Zobraz okno pre výber kategórií skladových kariet.
                                        Dim m_ArrCheckedCategories As String() = Nothing
                                        Dim m_Value$ = CStr(e.FormTemplateEditorAction.EditorCellControlActionEventArgs.Values(CStr(DB.SkladoveKarty00001.TreeCategory)))

                                        If m_Value$ <> String.Empty Then
                                            m_ArrCheckedCategories = Exa.OBERON.Shared.Controls.Stock.StockCardCategory._ConvertTreeCategory_FromString(m_Value$)
                                        End If

                                        Dim m_SelItemPath$ = Nothing

                                        If m_ArrCheckedCategories IsNot Nothing AndAlso m_ArrCheckedCategories.Length > 0 Then
                                            m_SelItemPath$ = m_ArrCheckedCategories(0)
                                        End If

                                        Dim f_StockCard_TreeCategories_List As New Exa.OBERON.Shared.Forms.Stock.StockCategories.frm_StockCard_TreeCategories_List(
                                                                                        Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select,
                                                                                        Me.lc_ObjectsOBERON_Stock._ObjectsOBERON,
                                                                                        True,
                                                                                        m_SelItemPath$,
                                                                                        m_ArrCheckedCategories,
                                                                                        u_RootPath:={Me._Selected_Stock.TreeCategory_RootPath}.ToList)

                                        f_StockCard_TreeCategories_List._SelectionBehavior = [Shared].Forms.Stock.StockCategories.frm_StockCard_TreeCategories_List.enm_SelectionBehaviorTypes.Items

                                        Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                                        m_DialogResult = Exa.Application.ShowWindow(f_StockCard_TreeCategories_List, True, Me.ParentForm)

                                        If m_DialogResult = Windows.Forms.DialogResult.OK Then
                                            m_ArrCheckedCategories = f_StockCard_TreeCategories_List._GetCheckedCategories()

                                            e.FormTemplateEditorAction.EditorCellControlActionEventArgs.SelectedListValue = Exa.OBERON.Shared.Controls.Stock.StockCardCategory._ConvertTreeCategory_ToString(m_ArrCheckedCategories)
                                        End If

                                        If f_StockCard_TreeCategories_List IsNot Nothing Then f_StockCard_TreeCategories_List.Dispose()
                                        f_StockCard_TreeCategories_List = Nothing


                                    ElseIf StrComp(m_DatabaseField$, DB.SkladoveKarty00001.CustomsTariffCode, CompareMethod.Text) = 0 Then
                                        'Zobrazenie okna pre výber colného sadzobníku.
                                        Dim m_Value$ = CStr(e.FormTemplateEditorAction.EditorCellControlActionEventArgs.Values(CStr(DB.SkladoveKarty00001.CustomsTariffCode)))
                                        Dim frm_CustomsTariff_List As New Exa.OBERON.Shared.Forms.Stock.CustomsTariffs.frmW_CustomsTariff_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select, Me.lc_ObjectsOBERON_Stock._ObjectsOBERON, m_Value$)

                                        If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                                            Exit Select
                                        End If

                                        Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                                        m_DialogResult = Exa.Application.ShowWindow(frm_CustomsTariff_List, True, Me)

                                        If m_DialogResult = Windows.Forms.DialogResult.OK Then
                                            e.FormTemplateEditorAction.EditorCellControlActionEventArgs.SelectedListValue = CStr(frm_CustomsTariff_List._SelectedRow_CustomsTariffCode)
                                        End If

                                        If frm_CustomsTariff_List IsNot Nothing Then frm_CustomsTariff_List.Dispose()
                                        frm_CustomsTariff_List = Nothing


                                    End If

                            End Select

                    End Select

            End Select

        End Sub


#End Region


#Region " CLASSES "

        ''' <summary>Trieda pre vykresľovanie farby v gride.</summary>
        Private Class cls_VarinatsDetailsCell
            Inherits Exa.Application.Controls.Simple.S_DataGrid.ExtensionControls.Cells.CustomCell

            Protected Overrides Sub Paint(ByVal graphics As System.Drawing.Graphics, ByVal clipBounds As System.Drawing.Rectangle, ByVal cellBounds As System.Drawing.Rectangle, ByVal rowIndex As Integer, ByVal cellState As System.Windows.Forms.DataGridViewElementStates, ByVal value As Object, ByVal formattedValue As Object, ByVal errorText As String, ByVal cellStyle As System.Windows.Forms.DataGridViewCellStyle, ByVal advancedBorderStyle As System.Windows.Forms.DataGridViewAdvancedBorderStyle, ByVal paintParts As System.Windows.Forms.DataGridViewPaintParts)
                On Error Resume Next

                '-- VALIDATION --
                If cellStyle.ForeColor = Nothing Then
                    MyBase.Paint(graphics, clipBounds, cellBounds, rowIndex, cellState, value, formattedValue, errorText, cellStyle, advancedBorderStyle, paintParts)
                    Exit Sub
                End If

                'Vykreslenie údajov vlastným spôsobom.
                If (cellState And DataGridViewElementStates.Selected) = DataGridViewElementStates.Selected Then
                    If Me.DataGridView.ContainsFocus = False Then
                        graphics.FillRectangle(New Drawing.SolidBrush(Exa.Application.Theme.Colors.Alternate.Selection_Inactive), cellBounds)
                    Else
                        graphics.FillRectangle(New Drawing.SolidBrush(cellStyle.SelectionBackColor), cellBounds)
                    End If
                Else
                    graphics.FillRectangle(New Drawing.SolidBrush(cellStyle.BackColor), cellBounds)
                End If

                Dim m_Rect As New Drawing.Rectangle(cellBounds.X + 1, cellBounds.Y + 1, cellBounds.Width - 2, cellBounds.Height - 2)
                Dim m_Form_StockCard_NewEdit As frm_StockCard_NewEdit = DirectCast(Me.OwningColumn.Tag, frm_StockCard_NewEdit)
                Dim m_StockCard_Variant_List As StockCard_Variant_List = m_Form_StockCard_NewEdit._DataRecord.Items_Variant
                Dim m_SelRow As DataRow = m_StockCard_Variant_List.Object_Table.DatabaseTable_View(rowIndex).Row

                If m_SelRow IsNot Nothing Then
                    Dim m_StockCard_Variant As StockCard_Variant = m_StockCard_Variant_List.DataRecord(m_SelRow, True)

                    If m_StockCard_Variant.Attributes IsNot Nothing AndAlso m_StockCard_Variant.Attributes.Length > 0 Then
                        Dim m_PadX% = 3

                        'Vykresli najskôr farby.
                        For i As Integer = 0 To m_StockCard_Variant.Attributes.Length - 1
                            Dim e_VariantDefinition_IDNum As Long = m_StockCard_Variant.Attributes(i)

                            If m_Form_StockCard_NewEdit.lc_HashTable_VariantDefinition.ContainsKey(e_VariantDefinition_IDNum) = True Then
                                Dim m_Row_VariantDefinition As DataRow = DirectCast(m_Form_StockCard_NewEdit.lc_HashTable_VariantDefinition.Item(e_VariantDefinition_IDNum), DataRow)
                                Dim m_StockCard_VariantDefinition As StockCard_VariantDefinition = m_Form_StockCard_NewEdit.lc_StockCard_Cache.StockCard_VariantDefinition_List.DataRecord(m_Row_VariantDefinition, True)

                                If m_StockCard_VariantDefinition.ValueType = StockCard_VariantDefinition.enm_ValueType.Color Then
                                    Dim m_Rect_Color As New Drawing.Rectangle(m_Rect.X + m_PadX%, m_Rect.Y, 26, m_Rect.Height - 2)
                                    Dim m_Path As Drawing.Drawing2D.GraphicsPath = Exa.Basic.Drawing.GetRoundedRectangle(m_Rect_Color, 3)

                                    With graphics
                                        Dim m_Color As Drawing.Color = m_StockCard_VariantDefinition.GetValue(Of Drawing.Color)()

                                        .FillPath(New Drawing.SolidBrush(m_Color), m_Path)
                                        .DrawPath(Drawing.Pens.DimGray, m_Path)
                                    End With

                                    m_PadX% += 30
                                End If
                            End If
                        Next

                        'Vykresli ostatné hodnoty.
                        For i As Integer = 0 To m_StockCard_Variant.Attributes.Length - 1
                            Dim e_VariantDefinition_IDNum As Long = m_StockCard_Variant.Attributes(i)

                            If m_Form_StockCard_NewEdit.lc_HashTable_VariantDefinition.ContainsKey(e_VariantDefinition_IDNum) = True Then
                                Dim m_Row_VariantDefinition As DataRow = DirectCast(m_Form_StockCard_NewEdit.lc_HashTable_VariantDefinition.Item(e_VariantDefinition_IDNum), DataRow)
                                Dim m_StockCard_VariantDefinition As StockCard_VariantDefinition = m_Form_StockCard_NewEdit.lc_StockCard_Cache.StockCard_VariantDefinition_List.DataRecord(m_Row_VariantDefinition, True)

                                If m_StockCard_VariantDefinition.ValueType <> StockCard_VariantDefinition.enm_ValueType.Color Then
                                    Dim m_Text$ = String.Format("{0}  ", m_StockCard_VariantDefinition.GetValue())

                                    If i < m_StockCard_Variant.Attributes.Length - 1 Then
                                        m_Text$ = String.Format("{0};   ", m_StockCard_VariantDefinition.GetValue())
                                    End If

                                    Dim m_Text_Width% = CInt(graphics.MeasureString(m_Text$, cellStyle.Font).Width)
                                    Dim m_Rect_Text As New Drawing.Rectangle(m_Rect.X + m_PadX% + 3, m_Rect.Y + 1, m_Text_Width% + 3, m_Rect.Height - 2)

                                    With graphics
                                        Dim m_StringFormat As New Drawing.StringFormat(Drawing.StringFormatFlags.NoWrap)

                                        With m_StringFormat
                                            .LineAlignment = Drawing.StringAlignment.Center
                                            .Alignment = Drawing.StringAlignment.Center
                                        End With

                                        .DrawString(m_Text$, cellStyle.Font, Drawing.Brushes.Black, m_Rect_Text, m_StringFormat)
                                    End With

                                    m_PadX% += m_Text_Width% + 4
                                End If
                            End If
                        Next
                    End If
                End If

                MyBase.PaintBorder(graphics, clipBounds, cellBounds, cellStyle, advancedBorderStyle)

            End Sub

        End Class

#End Region


#Region " ENUMS "

        Public Enum enm_WorkModeTypes As Integer
            ''' <summary>Bez špeciálnych úprav.</summary>
            [Default] = 0
            ''' <summary>Niektoré možnosti budú prispôsobené práci na pokladnici napr. pri novej karte bude automaticky zapnutá možnosť 'Umožniť predávať na pokladnici OBERON'.</summary>
            CashRegister = 1
        End Enum

        Private Enum enm_PriceInputTypes As Byte
            ''' <summary>Zadávanie ceny za základnú mernú jednotku.</summary>
            BaseUnit = 1
            ''' <summary>Zadávanie ceny za prepočítanú mernú jednotku (výdaj, len ak je povolený prepočet merných jednotiek).</summary>
            OutgoingUnit = 2
        End Enum

        Private Enum enm_PriceSetTargetTypes As Byte
            ''' <summary>Nastaví objekt 'DataRecord' podľa hodnôt z controlov.</summary>
            DataRecord = 1
            ''' <summary>Nastaví controly podľa údajov z objektu 'DataRecord'.</summary>
            Controls = 2
        End Enum

#End Region


#Region " PROPERTIES "

        Public Property _Selected_Stock As Exa.OBERON.Shared.Stock.Stocks.Stock.cls_StockInfo
            Get
                Return Me.lc_Selected_Stock
            End Get
            Set(ByVal value As Exa.OBERON.Shared.Stock.Stocks.Stock.cls_StockInfo)

                On Error Resume Next

                If Me.IsHandleCreated = True Then
                    Exa.Basic.Exceptions.Throw("Sklad je možné nastaviť len pred vytvorením handle okna.")
                    Exit Property
                End If

                Me.lc_Selected_Stock = value

            End Set
        End Property

#End Region

        '<Obsolete>
        Sub New(ByVal u_StockCard_List As StockCard_List,
                ByVal u_Selected_Stock As Exa.OBERON.Shared.Stock.Stocks.Stock.cls_StockInfo,
                ByVal u_PriceLevel As Byte,
                ByVal u_DeviceEngine As Exa.OBERON.Devices.Base.DeviceEngine,
                Optional ByVal u_WorkMode As enm_WorkModeTypes = enm_WorkModeTypes.Default,
                Optional ByVal u_RememberSettings_NewDataRecordFields As Boolean = False)

            On Error Resume Next

            InitializeComponent()

            'Dedenie
            Me.lc_AppConfiguration = u_StockCard_List._AppConfiguration
            Me.lc_Selected_Stock = u_Selected_Stock
            Me.lc_PriceLevel = u_PriceLevel
            Me.lc_DeviceEngine = u_DeviceEngine
            Me.lc_ObjectsOBERON_Stock = u_StockCard_List._ObjectsOBERON_Stock
            Me.lc_WorkMode = u_WorkMode


            '-- HODNOTY Z KTORÝCH JE MOŽNÉ VYBERAŤ --
            ': Pridaj (načítaj) hodnoty z ktorých je možné vyberať.
            Me.z_New_AddSelectableValues()


            'Inicializácia tohto formu.
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Me.RememberSettings_NewDataRecordFields = u_RememberSettings_NewDataRecordFields
            m_ExaException = MyBase.InitializeData(u_StockCard_List)

            If m_ExaException.Result = False Then
                Exa.Basic.Exceptions.Throw(m_ExaException.Description, Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError)
                Exit Sub
            End If

            'Mapovanie udalostí 'DataRecord-u'.
            'AddHandler Me._DataRecord.ev_StockCard_ValueChange, AddressOf Me.eh_DataRecord_ev_StockCard_ValueChange
            'ZMENA: Presunuté do udalosti 'Form_Load', pretože okno zostáva v pamäti a táto udalosť sa ruší v udalosti 'Form_Closing'


            '-- SET CONTROLS --
            ': Nastavenie controlov.
            Me.z_New_SetControls()

        End Sub

        '<Obsolete>
        Sub New(ByVal u_StockCard As StockCard,
                ByVal u_PriceLevel As Byte,
                ByVal u_DeviceEngine As Exa.OBERON.Devices.Base.DeviceEngine,
                Optional ByVal u_WorkMode As enm_WorkModeTypes = enm_WorkModeTypes.Default,
                Optional ByVal u_CloseDataRecordOnFormClosing As Boolean = True,
                Optional ByVal u_RememberSettings_NewDataRecordFields As Boolean = True)
            On Error Resume Next

            InitializeComponent()


            'Dedenie
            Me.lc_AppConfiguration = u_StockCard._AppConfiguration
            Me.lc_Selected_Stock = u_StockCard._Stock
            Me.lc_PriceLevel = u_PriceLevel
            Me.lc_DeviceEngine = u_DeviceEngine
            Me.lc_ObjectsOBERON_Stock = u_StockCard._ObjectsOBERON_Stock
            Me.lc_WorkMode = u_WorkMode
            '
            Me.RememberSettings_NewDataRecordFields = u_RememberSettings_NewDataRecordFields


            '-- HODNOTY Z KTORÝCH JE MOŽNÉ VYBERAŤ --
            ': Pridaj (načítaj) hodnoty z ktorých je možné vyberať.
            Me.z_New_AddSelectableValues()


            'Inicializácia tohto formu.
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = MyBase.InitializeData(u_StockCard, u_CloseDataRecordOnFormClosing)

            If m_ExaException.Result = False Then
                Exa.Basic.Exceptions.Throw(m_ExaException.Description, Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError)
                Exit Sub
            End If

            'Mapovanie udalostí 'DataRecord-u'.
            'AddHandler Me._DataRecord.ev_StockCard_ValueChange, AddressOf Me.eh_DataRecord_ev_StockCard_ValueChange
            'ZMENA: Presunuté do udalosti 'Form_Load', pretože okno zostáva v pamäti a táto udalosť sa ruší v udalosti 'Form_Closing'


            '-- SET CONTROLS --
            ': Nastavenie controlov.
            Me.z_New_SetControls()

        End Sub

        Private Sub z_New_AddSelectableValues()
            On Error Resume Next

            'Sadzby DPH.
            Dim m_VatRates As List(Of Decimal) = Me.lc_AppConfiguration.Common.VAT.RatesInfo.GetRateList

            Me.fro_cbo_SadzbaDPH._Items.AddRange(m_VatRates.ToArray)
            Me.fro_cbo_SadzbaDPH_PreNakup._Items.AddRange(m_VatRates.ToArray)

            'Záručná doba.
            Me.fro_cbo_DoplnUdaje_ZarucnaDoba._Items.AddRange(GetType(StockCard.enm_GuaranteePeriodUnit))
            Me.fro_cbo_DoplnUdaje_ZarucnaDobaExpirationMode._Items.AddRange(GetType(StockCard.enm_GuaranteePeriodExpirationMode))

            'Typ položky v pokladnici.
            Me.fro_cbo_RegPokladnica_ItemFlags._Items.Clear()
            Me.fro_cbo_RegPokladnica_ItemFlags._Items.AddRange(GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_CashRegister_ItemFlag))

            'Výrobné čísla.
            Me.fro_cbo_DoplnUdaje_SerialNumbersMode._Items.AddRange(GetType(Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode))

            'Váha MJ.
            With Me.fro_cbo_NastaveniaMJ_VahaMJ._Items
                .Update_Begin()
                .Add("kg")
                .Add("g")
                .Add("t")
                .Update_End()
            End With

            'Zaokrúhlenie ceny.
            Me.fro_cbo_PredajnaCena_Zaokruhlenie._Items.AddRange(GetType(StockCard.enm_Prices_Rounding))


            Me.fro_cbo_IObchod_Availability._Items.AddRange(GetType(Exa.OBERON.Stock.StockCards.StockCard.enm_Availability))

        End Sub

        Private Sub z_New_SetControls()
            On Error Resume Next

            'Schovanie niektorých stránok TabControlu podľa nastavení skladu
            Me.fro_tab_Objednavky.VisibleTab = Me.lc_AppConfiguration.Stock.Using_Firm_Orders
            Me.fro_tab_Variants.VisibleTab = Me.lc_AppConfiguration.Stock.Using_Firm_StockCard_Variants
            Me.fro_tab_Parameters.VisibleTab = Me.lc_AppConfiguration.Stock.Using_Firm_StockCard_Parameters
            Me.fro_tab_InternetovyObchod.VisibleTab = Me.lc_AppConfiguration.Stock.Using_Firm_EShop
            Me.fro_tab_Receptura.VisibleTab = Me.lc_AppConfiguration.Stock.Using_Firm_Recipe

            'Schovanie stĺpcov controlu 'DataGrid' na variantách podľa nastavenia objednávok.
            If Me.lc_AppConfiguration.Stock.Using_Firm_Orders = False Then
                Me.cln_Variants_CatalogNumber.Visible = False
                Me.cln_Variants_AmountMinimal.Visible = False
                Me.cln_Variants_AmountMaximal.Visible = False
            End If

            '--- Units - obrázky na tlačítkach
            fro_btn_Unit_New.Image = Exa.Resources.Images.Common_AddNew
            fro_btn_Unit_Edit.Image = Exa.Resources.Images.Common_Edit
            fro_btn_Unit_Del.Image = Exa.Resources.Images.Common_Delete

            '--- Skryť niektoré objekty
            If Me.lc_AppConfiguration.Stock.Using_Firm_TwoVATRate = False Then
                fro_cbo_SadzbaDPH_PreNakup.Visible = False
                fro_lbl_SadzbaDPH_PreNakup.Visible = False
                fro_lbl_SadzbaDPH_PreNakup_Percento.Visible = False
            End If

            '--- Rozšírená cenotvorba ---
            If Me.lc_AppConfiguration.Stock.Using_Firm_ExtendedSalePrice = True Then
                fro_btn_ExtendedPrices.Visible = True
                fro_chk_IgnoreExtendedSalePricing.Visible = True
            Else
                fro_btn_ExtendedPrices.Visible = False
                fro_chk_IgnoreExtendedSalePricing.Visible = False
            End If

            'Nastavenie tlačítka nastaviť, podľa počtu registračných pokladníc definovaných v zariadeniach
            If Me.lc_DeviceEngine IsNot Nothing Then
                Me.lc_DeviceModelsList = Me.lc_DeviceEngine.Device_Models_GetEnumList(Of Exa.OBERON.Devices.enm_CashRegister_Model)(Devices.enm_Devices_Type.CashRegister, False, True)
            End If

            If Me.lc_DeviceModelsList IsNot Nothing AndAlso Me.lc_DeviceModelsList.Count > 0 Then
                'Ak je v zariadeniach definované len 'CashRegisterUniversal' tlačítko nastaviť bude zakázané.
                Dim m_ArrCashRegisterUniversal() As Devices.enm_CashRegister_Model = Array.FindAll(Me.lc_DeviceModelsList.ToArray, Function(u As Devices.enm_CashRegister_Model) (u = Devices.enm_CashRegister_Model.CashRegister_Universal))

                If m_ArrCashRegisterUniversal.Length = Me.lc_DeviceModelsList.Count Then
                    'V zozname zariadení sú definované len univerzálne registračné pokladnice, tlačítko bude zakázané.
                    Me.fro_btn_RPOffline_Nastavit.Enabled = False
                Else
                    'Umožni nastaviť príznaky štandardnej registračnej pokladnice.
                    Me.fro_btn_RPOffline_Nastavit.Enabled = True
                End If
            Else
                Me.fro_btn_RPOffline_Nastavit.Enabled = False
            End If


            'Nastavenie objektu ktorý umožňuje vybrať/nastaviť kategóriu skladovej karty.
            With Me.fro_TreeCategory
                ._ObjectsOBERON = Me.lc_ObjectsOBERON_Stock._ObjectsOBERON
                ._AllowCheckBoxes = True

                'ZMENA od 23.4.2015: Umožni vybranie aj hlavnej kategórie.
                ._CheckBehavior = [Shared].Forms.Stock.StockCategories.frm_StockCard_TreeCategories_List.enm_CheckBehaviorTypes.AnyNode
            End With


            If Me.lc_AppConfiguration.Stock.Using_Firm_SBL = False Then
                Me.fro_grp_SBL.Visible = False
            Else
                Me.fro_grp_SBL.Visible = True
            End If


            'Tlač etikiet na registračnej pokladnici nastav podľa nastavení programu.
            'Me.fro_cbo_AutomatickaTlacEtikety.Visible = CBool(Me._DataRecord._AppConfiguration.CashRegisterOBERON.Print_Tags_Mode <> ApplicationEnvironment.AppConfigurationObjects.AppConfiguration_CashRegisterOBERON.enm_PrintTagsMode.None)


            '-- VARIANTS --
            ': Načítanie cache pre vykresľovanie variánt.
            If Me.lc_AppConfiguration.Stock.Using_Firm_StockCard_Variants = True Then
                Me.z_LoadDrawingCache_Variants()
            End If


            '--- Varianty skladových kariet - info --
            fro_lbl_VariantCheckAmountInfo.Visible = False

            '-- DEVICE ENGINE --
            ': Mapovanie udalostí
            'If Me.lc_DeviceEngine.BarCodeScanner IsNot Nothing Then
            '    RemoveHandler Me.lc_DeviceEngine.BarCodeScanner.BarCodeScanner_Readed, AddressOf eh_DeviceEngine_BarCodeScanner_Readed_Value
            '    AddHandler Me.lc_DeviceEngine.BarCodeScanner.BarCodeScanner_Readed, AddressOf eh_DeviceEngine_BarCodeScanner_Readed_Value
            'End If
            '* Form zostáva v pamäti, preto je potrebné udalosti mapovať vo 'Form_Load'


            'Nastavenie zobrazenia tlačidiel.
            'Me.fro_btn_FileRepository.Visible = Me.lc_ObjectsOBERON._AppConfiguration.Common.FileRepository


            Me.OptionsFormInfo = New Exa.Application.Forms.Options.frm_Options.stc_FormInfoValues With
                                              {.Object_Form = Me,
                                               .Object_DataGrid = Me.fro_dgv_Variants,
                                               .Parameters = New Object() {Me.lc_ObjectsOBERON_Stock}}
            'Pridanie kontextovej ponuky
            Me.fro_dgv_Variants.FormOptions = Me

            '--- Nastaviť zoznam premenných pre nastavenie generovania čiarových kódov
            Exa.OBERON.Shared.Features.BarCodeSettings.GetAvailableVariablesSelectorItemCollection([Shared].Features.BarCodeGenerator.enm_BarCodeGeneratorEvidence.StockCards, fro_isl_BarcodeSettings)


        End Sub


        Private Sub Form_Load(ByVal sender As Object, ByVal e As System.EventArgs) Handles Me.Load
            On Error Resume Next
            Dim myex As EXC.ExaException


            'Nastaviť tlačítku tučné písmo, ak záznam obsahuje nejaké pripojené dokumenty.
            z_SetControlsFileRepository()


            '-- MAP EVENTS --
            ': Mapovanie udalostí 'DataRecord-u'
            RemoveHandler Me._DataRecord.ev_DataRecordPropertyChange, AddressOf Me.eh_DataRecordPropertyChange
            AddHandler Me._DataRecord.ev_DataRecordPropertyChange, AddressOf Me.eh_DataRecordPropertyChange

            ': Podpora snímača čiarových kód
            If Me.lc_DeviceEngine IsNot Nothing Then
                RemoveHandler Me.lc_DeviceEngine.ev_BarCodeScanner_Readed, AddressOf eh_DeviceEngine_BarCodeScanner_Readed_Value
                AddHandler Me.lc_DeviceEngine.ev_BarCodeScanner_Readed, AddressOf eh_DeviceEngine_BarCodeScanner_Readed_Value
            End If


            '-- SET CONTROLS --
            ': Nastav controly podľa načítaných údajov z databázy 'DataRecord-u'
            Me.z_SetControls_SerialNumbers()

            ': V 'DataGrid-e' zobraz príznaky Off-Line registračných pokladníc
            Me.z_SetDataGrid_RPOffLine()


            ': Do 'DataGridu' zobraz zoznam položiek skupín v jedálnom lístku
            If Me.lc_FoodMenu_SelectedList IsNot Nothing Then
                With Me.fro_dgv_ZaradenieNaJedalnomListku.Items
                    .Update_Begin()
                    .Clear()

                    For Each mItem As String In Me.lc_FoodMenu_SelectedList
                        .Add(mItem)
                    Next

                    .Update_End()
                End With
            End If

            ': Ostatné nastavenia
            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                'Nová skladová karta
                Me.fro_btn_Rezervacie_Prijate.Enabled = False

                'Typ karty 'Receptúra' je možné použiť len ak je v nastaveniach programu povolené pracovať s receptúrami
                If Me.lc_AppConfiguration.Stock.Using_Firm_Recipe = False Then
                    Me.fro_cbo_TypKarty._Items.Remove(CStr(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Recipe), Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                End If

                'Typ karty 'Výrobok' je možné použiť len ak je v nastaveniach programu povolené pracovať s výrobkami
                If Me.lc_AppConfiguration.Stock.Using_Firm_Product = False Then
                    Me.fro_cbo_TypKarty._Items.Remove(CStr(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Product), Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                End If

            Else
                'Edit

                Me.fro_btn_Rezervacie_Prijate.Enabled = True

            End If


            '--- Typ karty - nastaviť či je možné meniť
            z_SetControls_StockCardType()

            '--- Alternatívne MJ
            z_SetControls_UnitOthers()

            ': Resetuj controly so zoznamom merných jednotiek, pretože form zostáva v pamäti a merné jednotky mohli byť zmenené (napr. na forme zoznam merných jednotiek).
            Me.fro_cbo_MJ.ResetNeedLoadItems()

            Me.fro_cbo_IObchod_Vyrobca.ResetNeedLoadItems()
            Me.fro_cbo_IObchod_Web.ResetNeedLoadItems()


            '--- Objednávky
            If fro_TabControl._Selected_PageIndex = fro_tab_Objednavky._Page_VisibleIndex Then
                '--- Vypočítať objednané množstvá ---
                z_Order_Calculate()
            End If

            '--- Zmluvné ceny pre odberateľov - nastaviť počet desatinných miest
            fro_cln_Odberatelia_Cena_BezDPH.ValueFormat_Number_Precision = Me._DataRecord._AppConfiguration.Common.SystemSettings.Document_DecimalPlace_Price_WithVAT_Unit

            'Nastaviť tlačítku tučné písmo, ak záznam obsahuje nejaké pripojené dokumenty.
            z_SetControlsFileRepository()


        End Sub

        Private Sub frm_StockCard_NewEdit_ev_LockAllControls(sender As Object, e As Application.Forms.Data.Factory.Form_DataRecord_Win32.cls_LockAllControlsEventArgs) Handles Me.ev_LockAllControls

            On Error Resume Next

            '--- Právo na cenotvorbu --- 
            z_SetControls_Price_Privileges()

            '--- Potvrdiť odchytenie udalosti ---
            e.Handled = True

        End Sub

        Private Sub Form_FormClosing(ByVal sender As Object, ByVal e As System.Windows.Forms.FormClosingEventArgs) Handles Me.FormClosing

            On Error Resume Next

            'Udalosť 'Dispose' nie je možné použiť pretože objekt '_DataList' už neexistuje
            RemoveHandler Me._DataRecord.ev_DataRecordPropertyChange, AddressOf Me.eh_DataRecordPropertyChange

            'ZMENA: Pôvodne sa tento kód nachádzal vo 'Form_Dispose', ale keďže form zostáva v pamäti,
            '       odstráň túto udlaosť po zatvorení formu
            If Me.lc_DeviceEngine IsNot Nothing Then
                RemoveHandler Me.lc_DeviceEngine.ev_BarCodeScanner_Readed, AddressOf eh_DeviceEngine_BarCodeScanner_Readed_Value
            End If

        End Sub

        Private Sub frm_StockCard_NewEdit_ev_LanguageDataTranslationChanged(sender As Object, e As cls_LanguageDataTranslationChangedEventArgs) Handles Me.ev_LanguageDataTranslationChanged
            On Error Resume Next

            Me.fro_dgv_Variants.Refresh()
            Me.fro_dgv_Parameters.Refresh()

        End Sub

        Private Sub Form_Disposed(ByVal sender As Object, ByVal e As System.EventArgs) Handles Me.Disposed
            On Error Resume Next

            If lc_Variant_DataRecord_DataGridCellFormatting IsNot Nothing Then
                lc_Variant_DataRecord_DataGridCellFormatting = Nothing
            End If

            If lc_Parameter_DataRecord_DataGridCellFormatting IsNot Nothing Then
                lc_Parameter_DataRecord_DataGridCellFormatting = Nothing
            End If

            If Me.lc_HashTable_VariantDefinition IsNot Nothing Then Me.lc_HashTable_VariantDefinition.Clear()
            Me.lc_HashTable_VariantDefinition = Nothing

            If Me.lc_StockCard_Cache IsNot Nothing Then Me.lc_StockCard_Cache.Dispose()
            Me.lc_StockCard_Cache = Nothing

            'Objektu musia zostať nažive, nie je možné ich zatvoriť 'Dispose' pretože sa ešte používajú
            Me.lc_Selected_Stock = Nothing
            Me.lc_AppConfiguration = Nothing
            Me.lc_DeviceEngine = Nothing
            Me.lc_ObjectsOBERON_Stock = Nothing
            Me.lc_DeviceModelsList = Nothing

        End Sub


#Region " BUTTONS "

        Private Sub fro_btn_OK_ev_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_btn_OK.ev_Click

            On Error Resume Next

            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            '--- uloženie
            m_ExaException = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Unlock)

            If m_ExaException.Result = False Then Exit Sub

            '--- ak je na položke zadané PLU tak treba zoznam PLU vymazať aby ho bolo nutné znova načítať
            If Me._DataRecord.CashRegister_Flags.PLU_Number <> 0 Then
                fro_cbo_RPOffline_CisloPLU._Items.Clear()
                fro_cbo_RPOffline_CisloPLU.ResetNeedLoadItems()
            End If

            'Zatvor okno
            Me.DialogResult = Windows.Forms.DialogResult.OK
            Me.Close()

        End Sub


        Private Sub fro_btn_PodrobnyPopis_ev_Click(sender As Object, e As EventArgs) Handles fro_btn_PodrobnyPopis.ev_Click
            On Error Resume Next

            Dim myEx As Exa.Basic.Exceptions.ExaException = Nothing

            'Keď sa používajú cudzie jazyky záznam musí byť uložený, pretože preklad potrebuje ID záznamu.
            If Exa.Application.Language.AllowDataTranslation = True Then
                If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                    '--- Nový záznam ---
                    myEx = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)
                    If myEx.Result = False Then
                        Exit Sub
                    End If
                End If
            End If

            Dim f_StockCard_DetailDescription As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_DetailDescription(Me, frm_StockCard_DetailDescription.enm_EditFieldName.Description)

            If Me.lc_Permission_IsAllControlsLocked = True Then
                Exa.Application.Forms.LockAllControls(f_StockCard_DetailDescription)
            End If

            Exa.Application.ShowWindow(f_StockCard_DetailDescription, True, Me)

            If f_StockCard_DetailDescription IsNot Nothing Then f_StockCard_DetailDescription.Dispose()
            f_StockCard_DetailDescription = Nothing

        End Sub

        Private Sub fro_btn_Ceny_Prepocitat_ev_Click(sender As System.Object, e As System.EventArgs) Handles fro_btn_Ceny_Prepocitat.ev_Click

            On Error Resume Next

            Dim tmp_DialogResult As DialogResult
            Dim LANG_1$ = "Prepočítať predajné ceny na tejto skladovej karte podľa aktuálnych hodnôt navýšenia?"
            Dim mText_1$ = Exa.Application.TranslateText(LANG_1$)

            tmp_DialogResult = Exa.Application.MsgBox(mText_1, MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2)
            If tmp_DialogResult <> Windows.Forms.DialogResult.Yes Then
                Exit Sub
            End If

            Exa.Application.Cursor_Wait()

            '--- Nastaví navýšenie podľa textových polí
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                            StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            '--- Prepočet
            Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Markup, 0, True)

            '--- Načítanie zmenených hodnôt
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Exa.Application.Cursor_Default()

        End Sub

        Private Sub fro_btn_VyrobneCisla_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_VyrobneCisla.ev_Click

            On Error Resume Next

            'Vytvor objekt ktorý obsahuje info potrebné pre prácu s výrobnými číslami
            Dim tmp_SerialNumber_DocumentItem As New Exa.OBERON.Stock.SerialNumbers.SerialNumber_DocumentItem(Me.lc_ObjectsOBERON_Stock)

            With tmp_SerialNumber_DocumentItem
                .IDNum_Stock_Card = Me._DataRecord.IDNum
                .IDNum_Stock = Me._DataRecord.IDNum_Stock
                .SerialNumbersMode = Me._DataRecord.SerialNumber_Mode
            End With

            'Zobraz okno
            Dim frm_SerialNumber_List As New Exa.OBERON.Stock.Forms.SerialNumbers.frm_SerialNumber_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select,
                                                                                                        Me.lc_ObjectsOBERON_Stock,
                                                                                                        Me.lc_DeviceEngine,
                                                                                                        tmp_SerialNumber_DocumentItem)

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then GoTo g_ExitSub

            'ŠPECIALITA: Zakáž vyberanie položiek, okno slúži len na prezeranie,
            '            štandardne sa nastavuje typ okna napr. Select, List, View atď. hodnota sa zvyčajne nastavuje v konštruktore
            frm_SerialNumber_List.fro_btn_OK.Visible = False

            Exa.Application.ShowWindow(frm_SerialNumber_List, True, Me)

g_ExitSub:

            If frm_SerialNumber_List IsNot Nothing Then frm_SerialNumber_List.Dispose()
            frm_SerialNumber_List = Nothing

        End Sub

        Private Sub fro_btn_Zlozenie_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Zlozenie.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me._DataRecord.Items_Product Is Nothing Then
                Exa.Basic.Exceptions.Throw("Objekt skladovej karty (StockCard DataRecord) nemá inicializované položky (vlastnosť Items_Product DataList).")
                Exit Sub
            End If


            'Ak karta ešte nie je uložená je potrebné ju uložiť
            Dim myEx As Exa.Basic.Exceptions.ExaException = Nothing

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                myEx = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)

                If myEx.Result = False Then
                    Exit Sub
                End If
            End If

            'Je potrebné načítať zoznam položiek objektu 'Items_Product',
            'len ak údaje ešte neboli načítané (vlastnosť 'Object_Table' = Nothing)
            If Me._DataRecord.Items_Product.Object_Table Is Nothing Then
                myEx = Me._DataRecord.Items_Product._LoadData(Me.lc_Selected_Stock)

                If myEx.Result = False Then
                    Exa.Application.MsgBox("Chyba pri načítaní položiek výrobku (receptúry).", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                    Exit Sub
                End If
            End If


            'Zobraz okno ktoré umožňuje eidotavanie zloženia výrobku alebo receptúry
            If CType(Me.fro_cbo_TypKarty._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType) = StockCard.enm_StockCardType.Product Then
                '-----------------
                '--- Výrobok
                '-----------------
                Dim f_StockCard_Product As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_Product(Me._DataRecord, Me.lc_Selected_Stock, Me.lc_PriceLevel, Me.lc_DeviceEngine)

                If Me.lc_Permission_IsAllControlsLocked = True Then
                    Exa.Application.Forms.LockAllControls(f_StockCard_Product)
                End If

                Exa.Application.ShowWindow(f_StockCard_Product, True, Me)

                If f_StockCard_Product IsNot Nothing Then f_StockCard_Product.Dispose()
                f_StockCard_Product = Nothing

            ElseIf CType(Me.fro_cbo_TypKarty._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType) = StockCard.enm_StockCardType.Collection Then
                '-----------------
                '--- Sada
                '-----------------
                Dim frm_StockCard_Collection As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_Collection(Me._DataRecord, Me.lc_Selected_Stock, Me.lc_PriceLevel, Me.lc_DeviceEngine)

                If Me.lc_Permission_IsAllControlsLocked = True Then
                    Exa.Application.Forms.LockAllControls(frm_StockCard_Collection)
                End If

                Exa.Application.ShowWindow(frm_StockCard_Collection, True, Me)

                If frm_StockCard_Collection IsNot Nothing Then frm_StockCard_Collection.Dispose()
                frm_StockCard_Collection = Nothing


            Else
                '-----------------
                '--- Receptúra
                '-----------------
                If Me._DataRecord.ExtendedValues.IsLoaded = False Then
                    '--- Externé vlastnosti ešte neboli načítané - načítať ---
                    myEx = Me._DataRecord.ExtendedValues._Load()
                    If myEx.Result = False Then
                        If myEx.ErrNumber <> Exa.Database.Factory.enm_ErrNumbers.DatabaseRow_NotFound Then
                            Exa.Application.MsgBox("Chyba pri načítaní rozšírených vlastností skladovej karty.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                        End If
                        '--- Pokračovať ďalej ---
                    End If
                End If

                Dim f_StockCard_CookRecipe As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_CookRecipe(Me._DataRecord, Me.lc_Selected_Stock, Me.lc_PriceLevel, Me.lc_DeviceEngine)

                If Me.lc_Permission_IsAllControlsLocked = True Then
                    Exa.Application.Forms.LockAllControls(f_StockCard_CookRecipe)
                End If

                Exa.Application.ShowWindow(f_StockCard_CookRecipe, True, Me)

                If f_StockCard_CookRecipe IsNot Nothing Then f_StockCard_CookRecipe.Dispose()
                f_StockCard_CookRecipe = Nothing

            End If


            Exa.Application.Cursor_Wait()


            '--- Volať uloženie - mohla sa zmeniť obstar. cena, zloženie receptúry, váha, obstarávacie náklady ---
            If Me._DataRecord.RecordInfo_LockProtection = Database.Factory.DataRecord.enm_RecordInfo_LockProtectionTypes.Locked_FreeForMe Then
                '--- Záznam môže používateľ aktualizovať ---

                '--- Uložiť ----
                myEx = Me._DataRecord._SaveProductData(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)
                If myEx.Result = False Then
                    Exa.Application.MsgBox("Chyba pri uložení obstarávacej ceny.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                End If
            End If

            '--- Zobraziť novú obstarávaciu cenu a poslednú nákupnú cenu ---
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceSupply)

            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceLastPurchase)

            '--- Zobraziť predajné ceny ---
            If Me._DataRecord.CardType = StockCard.enm_StockCardType.Collection Then
                '--- Len pri sade
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)
            End If

            '--- Typ karty - nastaviť či je možné meniť
            z_SetControls_StockCardType()

            Exa.Application.Cursor_Default()

        End Sub



        Private Sub fro_btn_Unit_New_ev_Click(sender As Object, e As EventArgs) Handles fro_btn_Unit_New.ev_Click

            Dim tmp_frm_StockCard_Unit As frm_StockCard_Unit = Nothing

            Try

                tmp_frm_StockCard_Unit = New frm_StockCard_Unit(Me._DataRecord, u_ItemIndex:=-1)

                Exa.Application.ShowWindow(tmp_frm_StockCard_Unit, u_IsDialog:=True)

                If tmp_frm_StockCard_Unit.DialogResult = DialogResult.OK Then
                    '--- OK
                    z_SetControls_UnitOthers()
                    fro_dgv_UnitOthers._Selected_RowIndex = Me._DataRecord.UnitOthers.Count - 1

                    Me.z_SetControls_UnitsForPriceInput_ComboBox()
                    Me.z_SetControls_UnitsForPriceInput_Labels()

                End If

            Catch ex As Exception

            Finally

                If tmp_frm_StockCard_Unit IsNot Nothing Then
                    tmp_frm_StockCard_Unit.Dispose()
                    tmp_frm_StockCard_Unit = Nothing
                End If

            End Try

        End Sub

        Private Sub fro_btn_Unit_Edit_ev_Click(sender As Object, e As EventArgs) Handles fro_btn_Unit_Edit.ev_Click

            Dim tmp_frm_StockCard_Unit As frm_StockCard_Unit = Nothing

            Try

                tmp_frm_StockCard_Unit = New frm_StockCard_Unit(Me._DataRecord, u_ItemIndex:=fro_dgv_UnitOthers._Selected_RowIndex)

                Exa.Application.ShowWindow(tmp_frm_StockCard_Unit, u_IsDialog:=True)

                If tmp_frm_StockCard_Unit.DialogResult = DialogResult.OK Then
                    '--- OK
                    z_SetControls_UnitOthers()

                    Me.z_SetControls_UnitsForPriceInput_ComboBox()
                    Me.z_SetControls_UnitsForPriceInput_Labels()

                End If

            Catch ex As Exception

            Finally

                If tmp_frm_StockCard_Unit IsNot Nothing Then
                    tmp_frm_StockCard_Unit.Dispose()
                    tmp_frm_StockCard_Unit = Nothing
                End If

            End Try

        End Sub

        Private Sub fro_btn_Unit_Del_ev_Click(sender As Object, e As EventArgs) Handles fro_btn_Unit_Del.ev_Click

            Try

                Me._DataRecord.UnitOthers.RemoveAt(fro_dgv_UnitOthers._Selected_RowIndex)

                z_SetControls_UnitOthers()

                Me.z_SetControls_UnitsForPriceInput_ComboBox()
                Me.z_SetControls_UnitsForPriceInput_Labels()


            Catch ex As Exception

            End Try

        End Sub


        Private Sub fro_btn_Variants_New_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Variants_New.ev_Click

            On Error Resume Next

            'Ak karta ešte nie je uložená je potrebné ju uložiť
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                m_ExaException = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)

                If m_ExaException.Result = False Then
                    GoTo g_ExitSub
                Else
                    Me.fro_dgv_Variants._DataSource = Me._DataRecord.Items_Variant
                End If
            End If


            '-- NEW DATA RECORD --
            ': 'DataRecord' priprav na pridanie nového záznamu
            m_ExaException = Me._DataRecord.Items_Variant.DataRecord._New

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox(m_ExaException.Description, m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If


            'Zobraz okno
            Dim frm_StockCard_Variant_NewEdit As New frm_StockCard_Variant_NewEdit(Me._DataRecord.Items_Variant, lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)

            Exa.Application.ShowWindow(frm_StockCard_Variant_NewEdit, True, Me)

            If frm_StockCard_Variant_NewEdit IsNot Nothing Then
                frm_StockCard_Variant_NewEdit.Dispose()
                frm_StockCard_Variant_NewEdit = Nothing
            End If

            'Zobraz počet variánt.
            Me.fro_lbl_Variants_Count._Text = Exa.Application.TranslateTextEx("Počet variant:  {0}", CStr(Me._DataRecord.Items_Variant.Count))

            '--- Varianty ---
            z_SetControls_VariantsCheckAmountInfo()


            '-- VARIANTS --
            ': Načítanie cache pre vykresľovanie variánt.
            If Me.lc_AppConfiguration.Stock.Using_Firm_StockCard_Variants = True Then
                Me.z_LoadDrawingCache_Variants()
                z_SetVariantDataGrid_SearchPanel()
            End If



g_ExitSub:

            Me.fro_dgv_Variants.Focus()

        End Sub

        Private Sub fro_btn_Variants_Edit_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Variants_Edit.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me.fro_dgv_Variants._RowsCount = 0 Then
                Exit Sub
            End If

            Dim myEx As EXC.ExaException
            Dim frm_StockCard_Variant_NewEdit As New frm_StockCard_Variant_NewEdit(Me._DataRecord.Items_Variant, lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)

            myEx = frm_StockCard_Variant_NewEdit._LoadValues(Me.fro_dgv_Variants, True)
            If myEx.Result = False Then
                Exa.Application.MsgBox(myEx.Description, myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitSub
            End If

            Exa.Application.ShowWindow(frm_StockCard_Variant_NewEdit, True, Me)


            '-- VARIANTS --
            ': Načítanie cache pre vykresľovanie variánt.
            If Me.lc_AppConfiguration.Stock.Using_Firm_StockCard_Variants = True Then
                Me.z_LoadDrawingCache_Variants()
            End If

            '--- Varianty ---
            z_SetControls_VariantsCheckAmountInfo()

ExitSub:
            If frm_StockCard_Variant_NewEdit IsNot Nothing Then
                frm_StockCard_Variant_NewEdit.Dispose()
                frm_StockCard_Variant_NewEdit = Nothing
            End If

            Me.fro_dgv_Variants.Focus()

        End Sub

        Private Sub fro_btn_Variants_Delete_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Variants_Delete.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me.fro_dgv_Variants._RowsCount = 0 Then Exit Sub

            ': Naozaj vymazať
            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None
            Dim m_SelRow As DataRow = Me._DataRecord.Items_Variant.Object_Table.DatabaseTable_View(Me.fro_dgv_Variants._Selected_RowIndex).Row
            Dim tmp_StockCard_Variant As StockCard_Variant = Me._DataRecord.Items_Variant.DataRecord(m_SelRow, True)
            Dim m_CurID As Long = tmp_StockCard_Variant.IDNum

            m_DialogResult = Exa.Application.MsgBox(Exa.Application.TranslateTextEx("Vymazať variantu '{0}'?", tmp_StockCard_Variant.Name), MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2)

            If m_DialogResult <> Windows.Forms.DialogResult.Yes Then
                tmp_StockCard_Variant = Nothing
                Exit Sub
            End If


            '-- DELETE RECORD --
            ': Vymazanie z databázy
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me._DataRecord.Items_Variant.DataRecord._Delete(m_CurID)

            If m_ExaException.Result = False Then
                If m_ExaException.ErrNumber = Exa.Basic.Exceptions.enm_ErrNumbers.ActionCanceledByUser Then
                    '* Prerušenie vymazania - hlásenie sa zobrazilo nižšie
                Else
                    'Iná chyba, hlášku nezobrazuje DataRecord
                    Exa.Application.MsgBox("Chyba pri vymazaní záznamu, nie je možné pokračovať.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                End If
            Else
                '-- DELETE LANGUAGE DATA --
                ': Vymazanie prekladu tohoto variantu.
                If Me.lc_AppConfiguration.Data.IsLanguageData = True Then
                    m_ExaException = Me._DataList.LanguageDataList.DeleteAllEvidenceValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_CardVariant, m_CurID)

                    If m_ExaException.Result = False Then
                        Exa.Application.MsgBox("Pri vymazaní záznamu v cudzom jazyku sa vyskytol problém.", m_ExaException, MsgBoxStyle.Exclamation Or MsgBoxStyle.OkOnly, , Me.Text)
                    End If
                End If
            End If

            tmp_StockCard_Variant = Nothing

            'Zobraz počet variánt.
            Me.fro_lbl_Variants_Count._Text = Exa.Application.TranslateTextEx("Počet variant:  {0}", CStr(Me._DataRecord.Items_Variant.Count))

            '--- Varianty ---
            z_SetControls_VariantsCheckAmountInfo()
            z_SetVariantDataGrid_SearchPanel()

        End Sub


        Private Sub fro_btn_Parameters_New_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Parameters_New.ev_Click

            On Error Resume Next

            'Ak karta ešte nie je uložená je potrebné ju uložiť
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                m_ExaException = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)

                If m_ExaException.Result = False Then
                    GoTo g_ExitSub
                Else
                    Me.fro_dgv_Parameters._DataSource = Me._DataRecord.Items_Parameter
                End If
            End If


            '-- NEW DATA RECORD --
            ': 'DataRecord' priprav na pridanie nového záznamu
            m_ExaException = Me._DataRecord.Items_Parameter.DataRecord._New

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox(m_ExaException.Description, m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If


            'Zobraz okno
            Dim frm_StockCard_Parameter_NewEdit As New frm_StockCard_Parameter_NewEdit(Me._DataRecord.Items_Parameter, lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)

            Exa.Application.ShowWindow(frm_StockCard_Parameter_NewEdit, True, Me)

            If frm_StockCard_Parameter_NewEdit IsNot Nothing Then
                frm_StockCard_Parameter_NewEdit.Dispose()
                frm_StockCard_Parameter_NewEdit = Nothing
            End If

            'Zobraz počet parametrov.
            Me.fro_lbl_Parameters_Count._Text = Exa.Application.TranslateTextEx("Počet:  {0}", CStr(Me._DataRecord.Items_Parameter.Count))



g_ExitSub:

            Me.fro_dgv_Parameters.Focus()

        End Sub

        Private Sub fro_btn_Parameters_Edit_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Parameters_Edit.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me.fro_dgv_Parameters._RowsCount = 0 Then
                Exit Sub
            End If

            Dim myEx As EXC.ExaException
            Dim frm_StockCard_Parameter_NewEdit As New frm_StockCard_Parameter_NewEdit(Me._DataRecord.Items_Parameter, lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)

            myEx = frm_StockCard_Parameter_NewEdit._LoadValues(Me.fro_dgv_Parameters, True)
            If myEx.Result = False Then
                Exa.Application.MsgBox(myEx.Description, myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitSub
            End If

            Exa.Application.ShowWindow(frm_StockCard_Parameter_NewEdit, True, Me)

ExitSub:
            If frm_StockCard_Parameter_NewEdit IsNot Nothing Then
                frm_StockCard_Parameter_NewEdit.Dispose()
                frm_StockCard_Parameter_NewEdit = Nothing
            End If

            Me.fro_dgv_Parameters.Focus()

        End Sub

        Private Sub fro_btn_Parameters_Delete_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Parameters_Delete.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me.fro_dgv_Parameters._RowsCount = 0 Then Exit Sub

            ': Naozaj vymazať
            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None
            Dim m_SelRow As DataRow = Me._DataRecord.Items_Parameter.Object_Table.DatabaseTable_View(Me.fro_dgv_Parameters._Selected_RowIndex).Row
            Dim tmp_StockCard_Parameter As StockCard_Parameter = Me._DataRecord.Items_Parameter.DataRecord(m_SelRow, True)


            m_DialogResult = Exa.Application.MsgBox(Exa.Application.TranslateTextEx("Vymazať parameter '{0}'?", tmp_StockCard_Parameter.Name), MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2)

            If m_DialogResult <> Windows.Forms.DialogResult.Yes Then
                tmp_StockCard_Parameter = Nothing
                Exit Sub
            End If


            '-- DELETE RECORD --
            ': Vymazanie z databázy
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_CurID As Long = tmp_StockCard_Parameter.IDNum

            m_ExaException = Me._DataRecord.Items_Parameter.DataRecord._Delete(tmp_StockCard_Parameter.IDNum)

            If m_ExaException.Result = False Then
                If m_ExaException.ErrNumber = Exa.Basic.Exceptions.enm_ErrNumbers.ActionCanceledByUser Then
                    '* Prerušenie vymazania - hlásenie sa zobrazilo nižšie
                Else
                    'Iná chyba, hlášku nezobrazuje DataRecord
                    Exa.Application.MsgBox("Chyba pri vymazaní záznamu, nie je možné pokračovať.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                End If
            Else
                '-- DELETE LANGUAGE DATA --
                ': Vymazanie prekladu tohoto parametra.
                If Me.lc_AppConfiguration.Data.IsLanguageData = True Then
                    m_ExaException = Me._DataList.LanguageDataList.DeleteAllEvidenceValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_CardParameters, m_CurID)

                    If m_ExaException.Result = False Then
                        Exa.Application.MsgBox("Pri vymazaní záznamu v cudzom jazyku sa vyskytol problém.", m_ExaException, MsgBoxStyle.Exclamation Or MsgBoxStyle.OkOnly, , Me.Text)
                    End If
                End If
            End If

            tmp_StockCard_Parameter = Nothing

            'Zobraz počet parametrov.
            Me.fro_lbl_Parameters_Count._Text = Exa.Application.TranslateTextEx("Počet:  {0}", CStr(Me._DataRecord.Items_Parameter.Count))

        End Sub




        Private Sub fro_btn_Suppliers_New_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Suppliers_New.ev_Click

            On Error Resume Next

            'Ak karta ešte nie je uložená je potrebné ju uložiť
            Dim myEx As Exa.Basic.Exceptions.ExaException = Nothing

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                myEx = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)

                If myEx.Result = False Then
                    GoTo g_ExitSub
                Else
                    Me.fro_dgv_Suppliers._DataSource = Me._DataRecord.Items_Supplier
                End If
            End If


            '-- NEW DATA RECORD --
            ': 'DataRecord' priprav na pridanie nového záznamu
            myEx = Me._DataRecord.Items_Supplier.DataRecord._New

            If myEx.Result = False Then
                Exa.Application.MsgBox(myEx.Description, myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If


            'Zobraz okno
            Dim frm_StockCard_Supplier_NewEdit As New frm_StockCard_Supplier_NewEdit(Me._DataRecord.Items_Supplier, lc_ObjectsOBERON_Stock)

            Exa.Application.ShowWindow(frm_StockCard_Supplier_NewEdit, True, Me)

            If frm_StockCard_Supplier_NewEdit IsNot Nothing Then
                frm_StockCard_Supplier_NewEdit.Dispose()
                frm_StockCard_Supplier_NewEdit = Nothing
            End If

g_ExitSub:

            Me.fro_dgv_Suppliers.Focus()

        End Sub

        Private Sub fro_btn_Suppliers_Edit_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Suppliers_Edit.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me.fro_dgv_Suppliers._RowsCount = 0 Then
                Exit Sub
            End If

            Dim myEx As EXC.ExaException
            Dim frm_StockCard_Supplier_NewEdit As New frm_StockCard_Supplier_NewEdit(Me._DataRecord.Items_Supplier, lc_ObjectsOBERON_Stock)

            myEx = frm_StockCard_Supplier_NewEdit._LoadValues(Me.fro_dgv_Suppliers, True)
            If myEx.Result = False Then
                Exa.Application.MsgBox(myEx.Description, myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitSub
            End If

            Exa.Application.ShowWindow(frm_StockCard_Supplier_NewEdit, True, Me)

ExitSub:
            If frm_StockCard_Supplier_NewEdit IsNot Nothing Then
                frm_StockCard_Supplier_NewEdit.Dispose()
                frm_StockCard_Supplier_NewEdit = Nothing
            End If

            Me.fro_dgv_Suppliers.Focus()

        End Sub

        Private Sub fro_btn_Suppliers_Delete_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_Suppliers_Delete.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me.fro_dgv_Suppliers._RowsCount = 0 Then Exit Sub

            ': Naozaj vymazať
            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None
            Dim m_SelRow As DataRow = Me._DataRecord.Items_Supplier.Object_Table.DatabaseTable_View(Me.fro_dgv_Suppliers._Selected_RowIndex).Row
            Dim tmp_StockCard_Supplier As StockCard_Supplier = Me._DataRecord.Items_Supplier.DataRecord(m_SelRow, True)


            m_DialogResult = Exa.Application.MsgBox(Exa.Application.TranslateTextEx("Vymazať dodávateľa '{0}'?", tmp_StockCard_Supplier.SupplierName), MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2)

            If m_DialogResult <> Windows.Forms.DialogResult.Yes Then
                tmp_StockCard_Supplier = Nothing
                Exit Sub
            End If


            '-- DELETE RECORD --
            ': Vymazanie z databázy
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me._DataRecord.Items_Supplier.DataRecord._Delete(tmp_StockCard_Supplier.ID)

            If m_ExaException.Result = False Then
                If m_ExaException.ErrNumber = Exa.Basic.Exceptions.enm_ErrNumbers.ActionCanceledByUser Then
                    '* Prerušenie vymazania - hlásenie sa zobrazilo nižšie
                Else
                    'Iná chyba, hlášku nezobrazuje DataRecord
                    Exa.Application.MsgBox("Chyba pri vymazaní záznamu, nie je možné pokračovať.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                End If
            End If

            tmp_StockCard_Supplier = Nothing


        End Sub



        Private Sub fro_btn_Rezervacie_Prijate_ev_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_btn_Rezervacie_Prijate.ev_Click

            On Error Resume Next

            Dim frm_OrderRecieved_Reservations As New Exa.OBERON.Stock.Forms.OrdersReceived.frm_OrdersRecieved_Items(Me.lc_ObjectsOBERON_Stock, Me._DataRecord)

            Exa.Application.ShowWindow(frm_OrderRecieved_Reservations, True, Me)

            If frm_OrderRecieved_Reservations IsNot Nothing Then frm_OrderRecieved_Reservations.Dispose()
            frm_OrderRecieved_Reservations = Nothing

        End Sub

        Private Sub fro_btn_Rezervacie_Vydane_ev_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_btn_Rezervacie_Vydane.ev_Click

            On Error Resume Next

            Dim frm_OrderIssued_Reservations As New Exa.OBERON.Stock.Forms.OrdersIssued.frm_OrdersIssued_Items(lc_ObjectsOBERON_Stock, Me._DataRecord)

            Exa.Application.ShowWindow(frm_OrderIssued_Reservations, True, Me)

            If frm_OrderIssued_Reservations IsNot Nothing Then frm_OrderIssued_Reservations.Dispose()
            frm_OrderIssued_Reservations = Nothing

        End Sub


        Private Sub fro_btn_RPOffline_Nastavit_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_RPOffline_Nastavit.ev_Click

            On Error Resume Next

            Dim f_StockCard_CashRegister_Flags As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_CashRegister_Flags(Me._DataRecord, lc_DeviceModelsList)

            Exa.Application.ShowWindow(f_StockCard_CashRegister_Flags, True, Me)

            If f_StockCard_CashRegister_Flags IsNot Nothing Then f_StockCard_CashRegister_Flags.Dispose()
            f_StockCard_CashRegister_Flags = Nothing

            'Aktualizuj zoznam položiek
            z_SetDataGrid_RPOffLine()

        End Sub

        Private Sub fro_btn_ZaradenieNaJedalnomListku_PridatAleboOdobrat_ev_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_btn_ZaradenieNaJedalnomListku_PridatAleboOdobrat.ev_Click

            On Error Resume Next

            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim tmp_StockCard_FoodMenu_List As Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_FoodMenu_List = Nothing
            Dim frm_Groups As Exa.Application.Forms.Options.frm_Groups = Nothing


            '-- LOAD GROUPS --
            ': Načítaj zoznam skupín,
            ': tento zoznam sa bude používať pre viac formulárov napr. udalosť 'eh_Form_GroupList_ev_EditButtonClick',
            tmp_StockCard_FoodMenu_List = New Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_FoodMenu_List(Me._DataRecord._AppConfiguration)

            m_ExaException = tmp_StockCard_FoodMenu_List._LoadData()

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní údajov z databázy, nie je možné pokračovať.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo g_ExitSub
            End If


            '-- SHOW WINDOW --
            ': Zobraz okno pre editovanie zoznamu skupín
            frm_Groups = New Exa.Application.Forms.Options.frm_Groups

            With frm_Groups
                ._DataSource = tmp_StockCard_FoodMenu_List
                ._DataMember = "Nazov"
                ._Selected_Groups = Me.lc_FoodMenu_SelectedList.ToArray
            End With

            ': Mapovanie udalostí potrebných pre úpravu zoznamu položirk
            RemoveHandler frm_Groups.ev_EditButtonClick, AddressOf Me.eh_Form_FoodMenuList_ev_EditButtonClick
            AddHandler frm_Groups.ev_EditButtonClick, AddressOf Me.eh_Form_FoodMenuList_ev_EditButtonClick

            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

            m_DialogResult = Exa.Application.ShowWindow(frm_Groups, True, Me)

            If m_DialogResult = Windows.Forms.DialogResult.OK Then
                'Aktualizuj zoznam položiek v DataGride a v lokálnej premennej
                lc_FoodMenu_SelectedList = New List(Of String)

                With Me.fro_dgv_ZaradenieNaJedalnomListku.Items
                    .Update_Begin()
                    .Clear()

                    For Each e_Group As String In frm_Groups._Selected_Groups
                        Me.lc_FoodMenu_SelectedList.Add(e_Group)
                        .Add(e_Group)
                    Next

                    .Update_End()
                End With
            End If



g_ExitSub:

            If tmp_StockCard_FoodMenu_List IsNot Nothing Then
                RemoveHandler frm_Groups.ev_EditButtonClick, AddressOf Me.eh_Form_FoodMenuList_ev_EditButtonClick
                tmp_StockCard_FoodMenu_List.Dispose()
            End If
            tmp_StockCard_FoodMenu_List = Nothing

            ': Zoznam je možné zrušiť len tu, nie napr. na child formulároch ktoré používajú tento DataList
            If tmp_StockCard_FoodMenu_List IsNot Nothing Then tmp_StockCard_FoodMenu_List.Dispose()
            tmp_StockCard_FoodMenu_List = Nothing

        End Sub

        Private Sub fro_btn_FileRepository_ev_Click(sender As System.Object, e As System.EventArgs) Handles fro_btn_FileRepository.ev_Click

            On Error Resume Next

            '-- VALIDATION --
            If Me._DataRecord.Items_FileRepository Is Nothing Then
                Exa.Basic.Exceptions.Throw("Objekt skladovej karty (StockCard DataRecord) nemá inicializované položky (vlastnosť 'Items_FileRepository'.")
                Exit Sub
            End If


            'Ak karta ešte nie je uložená je potrebné ju uložiť
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                m_ExaException = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)

                If m_ExaException.Result = False Then
                    Exit Sub
                End If
            End If

            'Je potrebné načítať zoznam položiek objektu 'Items_Images',
            'len ak údaje ešte neboli načítané (vlastnosť 'Object_Table' = Nothing)
            If Me._DataRecord.Items_FileRepository.Object_Table Is Nothing Then
                m_ExaException = Me._DataRecord.Items_FileRepository._LoadData(Me._DataRecord)

                If m_ExaException.Result = False Then
                    Exa.Application.MsgBox("Chyba pri načítaní pripojených dokumentov skladovej karty.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                    Exit Sub
                End If
            End If


            Dim frm_StockCard_FileRepositoryItem_List As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_FileRepositoryItem_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.List,
                                                                                                                                     Me.lc_ObjectsOBERON_Stock,
                                                                                                                                     Me._DataRecord,
                                                                                                                                     New Exa.OBERON.Shared.Stock.Stocks.Stock.cls_StockInfo() {Me._Selected_Stock})

            m_ExaException = frm_StockCard_FileRepositoryItem_List._LoadData()

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní údajov.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If

            Exa.Application.ShowWindow(frm_StockCard_FileRepositoryItem_List, True, Me)

            If frm_StockCard_FileRepositoryItem_List IsNot Nothing Then
                frm_StockCard_FileRepositoryItem_List.Dispose()
                frm_StockCard_FileRepositoryItem_List = Nothing
            End If

            'Nastaviť tlačítku tučné písmo, ak záznam obsahuje nejaké pripojené dokumenty.
            z_SetControlsFileRepository()

        End Sub

        Private Sub fro_btn_IObchod_PodrobnyPopis_ev_Click(sender As System.Object, e As System.EventArgs) Handles fro_btn_IObchod_PodrobnyPopis.ev_Click

            On Error Resume Next

            '--- Ak karta ešte nie je uložená je potrebné ju uložiť ---
            Dim myEx As Exa.Basic.Exceptions.ExaException = Nothing

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                '--- Nový záznam ---
                myEx = Me._DataRecord_Save(Database.Factory.DataRecord.enm_LockRecordTypes.Lock)
                If myEx.Result = False Then
                    Exit Sub
                End If
            End If

            If Me._DataRecord.ExtendedValues.IsLoaded = False Then
                '--- Externé vlastnosti ešte neboli načítané - načítať ---
                myEx = Me._DataRecord.ExtendedValues._Load()
                If myEx.Result = False Then
                    '--- ERR --
                    If myEx.ErrNumber = Exa.Database.Factory.enm_ErrNumbers.DatabaseRow_NotFound Then
                        '--- Záznam nebol nájdený (ani nemusí existovať)
                        '--- Nastaviť record na nový záznam
                        myEx = Me._DataRecord.ExtendedValues._New
                        If myEx.Result = False Then
                            '--- ERR --
                            Exa.Application.MsgBox(myEx.GetFullDescription, MsgBoxStyle.OkOnly Or MsgBoxStyle.Critical)
                            Exit Sub
                        End If

                        If (Me.lc_ObjectsOBERON_Stock._AppConfiguration.Data.IsLanguageData) Then
                            '-- LANGUAGE DATA --
                            ': Keď sa používa preklad údajov, je potrebné externé vlastnosti uložiť, pretože preklady potrebujú korektný identifikátor hodnôt pre prekladanie.
                            myEx = Me._DataRecord.ExtendedValues._Save()
                            If myEx.Result = False Then
                                Exa.Application.MsgBox(myEx.GetFullDescription, MsgBoxStyle.OkOnly Or MsgBoxStyle.Critical)
                                Exit Sub
                            End If
                        End If
                    Else
                        '--- ERR --
                        Exa.Application.MsgBox("Pri načítaní doplňujúcich údajov ku skladovej karte došlo k problému.", myEx, MsgBoxStyle.OkOnly Or MsgBoxStyle.Critical)
                        Exit Sub
                    End If
                End If
            End If

            Dim f_StockCard_DetailDescription As New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_DetailDescription(Me, frm_StockCard_DetailDescription.enm_EditFieldName.EShop)

            If Me.lc_Permission_IsAllControlsLocked = True Then
                Exa.Application.Forms.LockAllControls(f_StockCard_DetailDescription)
            End If

            Exa.Application.ShowWindow(f_StockCard_DetailDescription, True, Me)

            If f_StockCard_DetailDescription IsNot Nothing Then f_StockCard_DetailDescription.Dispose()
            f_StockCard_DetailDescription = Nothing


        End Sub

#End Region


#Region " EVENT HANDLERS - FORM GROUP LIST "

        Private Sub eh_Form_FoodMenuList_ev_EditButtonClick(ByVal sender As Object, ByVal e As Exa.Application.Forms.Options.frm_Groups.cls_EditButtonClickEventArgs)


            On Error Resume Next

            '--- Zobraziť číselník jedálnych lístkov 
            Dim frm_StockCard_FoodMenu_List As New Exa.OBERON.Stock.Forms.StockCards.Catalog.frm_StockCard_FoodMenu_List(lc_ObjectsOBERON_Stock._ObjectsOBERON)

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                GoTo g_ExitSub
            End If

            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

            m_DialogResult = Exa.Application.ShowWindow(frm_StockCard_FoodMenu_List, True, Me)

            If frm_StockCard_FoodMenu_List._DataList.HasEditChanges = True Then
                '--- Aktualizvať údaje načítanéí v control-e FRM_GROUPS
                DirectCast(e.DataSource, Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_FoodMenu_List).Object_Table._RefreshData(u_UseNewConnection:=False)
            End If


g_ExitSub:


            If frm_StockCard_FoodMenu_List IsNot Nothing Then
                frm_StockCard_FoodMenu_List.Dispose()
            End If
            frm_StockCard_FoodMenu_List = Nothing

        End Sub

        Private Sub fro_dgv_ZaradenieNaJedalnomListku_ev_Clipboard(sender As Object, e As Application.Controls.Simple.S_DataGrid.mod_DataGrid.cls_ClipboardEventArgs) Handles fro_dgv_ZaradenieNaJedalnomListku.ev_Clipboard

            On Error Resume Next

            '--- Príznak, ku ktorému patria údaje schránky.
            Dim tmp_FoodMenu_List_Flag As String = "StockCard_FoodMenu_List"

            e.Flag = tmp_FoodMenu_List_Flag

            Select Case e.ActionType
                Case Application.Controls.Simple.S_DataGrid.cls_ClipboardEventArgs.enm_ActionTypes.Copy
                    '--- KOPÍROAVNIE DO SCHRÁNKY ---
                    Me._DataList.DataRecord.CookRecipe_Menu_Names = Me.lc_FoodMenu_SelectedList.ToArray()

                    '--- Skopíruj údaje zaradenia do schránky 'Clipboard'.
                    e.ExaException = Me._DataList.DataRecord.CopyToClipboard(e.Object_Clipboard, e.Flag)
                    If e.ExaException.Result = False Then
                        e.ExaException = Exa.Basic.Exceptions.Get(Exa.Application.TranslateText("Kopírovanie údajov zaradenia skladovej karty do jedálnych lístkov do schránky sa nepodarilo."), e.ExaException, e.ExaException.ErrNumber, e.ExaException.ExceptionType)
                        Exit Sub
                    End If

                    e.Handled = True

                Case Application.Controls.Simple.S_DataGrid.cls_ClipboardEventArgs.enm_ActionTypes.Paste
                    '--- VLEPENIE ZO SCHRÁNKY ---

                    '--- Treba opätovne nastaviť príznak, pretože niekedy ho vymaže udalosť pre vlepením.
                    e.Flag = tmp_FoodMenu_List_Flag

                    '--- Načítaj údaje zaradenia podľa údajov zo schránky 'ClipBoard'.
                    e.ExaException = Me._DataList.DataRecord.PasteFromClipboard(e, Me.lc_ObjectsOBERON_Stock, e.Flag)
                    If e.ExaException.Result = False Then
                        '--- DÔLEŽITÉ: Prenášať pôvodný kód a typ chyby.
                        e.ExaException = Exa.Basic.Exceptions.Get(Exa.Application.TranslateText("Chyba pri prevode údajov zaradenia skladovej karty do jedálnych lístkov schránky 'Clipboard' do formátu údajov záznamu."), e.ExaException, e.ExaException.ErrNumber, e.ExaException.ExceptionType)
                        Exit Select
                    End If

                    e.Handled = True

                Case Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Paste_Completed

                    '--- Aktualizovanie premennej s údajmi zaradenia do jedálnych lístkov.
                    Me.lc_FoodMenu_SelectedList = Me._DataList.DataRecord.CookRecipe_Menu_Names.ToList()
                    If Me.lc_FoodMenu_SelectedList IsNot Nothing Then
                        '--- Aktualizovanie datagridu so zoznamom jedálnych lístkov.
                        With Me.fro_dgv_ZaradenieNaJedalnomListku.Items
                            .Update_Begin()
                            .Clear()

                            For Each mItem As String In Me.lc_FoodMenu_SelectedList
                                .Add(mItem)
                            Next

                            .Update_End()
                        End With
                    End If

                    '--- Refresh datagridu.
                    Me.fro_dgv_ZaradenieNaJedalnomListku.Refresh()
            End Select

        End Sub

        Private Sub fro_cmnu_FoodMenuList_Copy_Click(sender As System.Object, e As System.EventArgs) Handles fro_cmnu_FoodMenuList_Copy.Click
            On Error Resume Next

            Dim tmp_ClipboardEventArgs As Simple.S_DataGrid.mod_DataGrid.cls_ClipboardEventArgs = Nothing

            tmp_ClipboardEventArgs = New Simple.S_DataGrid.mod_DataGrid.cls_ClipboardEventArgs(New Exa.Basic.Application.Clipboard(Me.fro_dgv_ZaradenieNaJedalnomListku),
                                                                                               Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Copy)

            '--- Zavolanie metódy, ktorá vyvolá udalost skopírovania údajov do schránky.
            Me.fro_dgv_ZaradenieNaJedalnomListku_ev_Clipboard(Me, tmp_ClipboardEventArgs)

        End Sub

        Private Sub fro_cmnu_FoodMenuList_Paste_Click(sender As System.Object, e As System.EventArgs) Handles fro_cmnu_FoodMenuList_Paste.Click
            On Error Resume Next

            Dim tmp_ClipboardEventArgs As Simple.S_DataGrid.mod_DataGrid.cls_ClipboardEventArgs = Nothing

            tmp_ClipboardEventArgs = New Simple.S_DataGrid.mod_DataGrid.cls_ClipboardEventArgs(New Exa.Basic.Application.Clipboard(Me.fro_dgv_ZaradenieNaJedalnomListku),
                                                                                               Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Paste)

            '--- Zavolanie metódy, ktorá vyvolá udalost načítania údajov zo schránky.
            Me.fro_dgv_ZaradenieNaJedalnomListku_ev_Clipboard(Me, tmp_ClipboardEventArgs)

            If tmp_ClipboardEventArgs.ExaException.Result = True Then
                '--- REFRESH GRIDU (Zaradenia do jedálnych lístkov) ---
                tmp_ClipboardEventArgs = New Simple.S_DataGrid.mod_DataGrid.cls_ClipboardEventArgs(New Exa.Basic.Application.Clipboard(Me.fro_dgv_ZaradenieNaJedalnomListku),
                                                                                               Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Paste_Completed)

                '--- Po úspešnom vykonaní prilepenia údajov, vyvolaj udalosť dokončenia aby sa refreshli údaje v premennej so zoznamom jedálnych lístkov a refreshom datagridu.
                Me.fro_dgv_ZaradenieNaJedalnomListku_ev_Clipboard(Me, tmp_ClipboardEventArgs)
            End If
        End Sub

#End Region


#Region " EVENT HANDLERS - DATA RECORD "

        Private Sub eh_DataRecordPropertyChange(ByVal e As OBERON.Stock.StockCards.StockCard.cls_DataRecordPropertyChangeEventArgs)

            On Error Resume Next

            Dim m_PriceInputType As enm_PriceInputTypes = CType(Me.fro_cbo_PredajnaCena_Zadavanie._Selected_Item.Value, enm_PriceInputTypes)

            If e.Action = Exa.OBERON.Shared.TransportData.TransportData.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty Then
                '-------------------------------------------------------------------------------------------------------
                '--- Je potrebné nastaviť controly (textové polia) podľa recordu.
                '-------------------------------------------------------------------------------------------------------
                Select Case e.Control

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.VATRate

                        Me.fro_cbo_SadzbaDPH._SelectItem(Me._DataRecord.VATRate)
                        Me.fro_cbo_SadzbaDPH_PreNakup._SelectItem(Me._DataRecord.VATRateIncome)

                        '--- Zmena sadzby DPH - nastaviť aj ceny
                        Me.z_SetPrices(enm_PriceSetTargetTypes.Controls, m_PriceInputType, e.Price_Calculation)


                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate
                        'PriceCalculate

                        'Nastaviť controly podľa objektu 'DataRecord'.
                        Me.z_SetPrices(enm_PriceSetTargetTypes.Controls, m_PriceInputType, e.Price_Calculation)

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.Price_Discount_Type

                        If Me._DataRecord.Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Allow Then
                            Me.fro_rdb_ZlavyPredaj_Umoznit._Checked = True
                        ElseIf Me._DataRecord.Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Ask Then
                            Me.fro_rdb_ZlavyPredaj_Pytatsa._Checked = True
                        Else
                            Me.fro_rdb_ZlavyPredaj_Neumoznit._Checked = True
                        End If


                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.CashRegister_Change_Flags
                        'V 'DataGrid-e' zobraz príznaky Off-Line registračných pokladníc
                        Me.z_SetDataGrid_RPOffLine()

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.CashRegister_ItemFlag
                        Me.fro_cbo_RegPokladnica_ItemFlags._SelectItem(Me._DataRecord.CashRegister_ItemFlag, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceSupply
                        If Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = False Then
                            Me.fro_txt_Cena_Obstaravacia._Text = CStr(Me._DataRecord.Price_Supply_Unit)
                        End If

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceLastPurchase
                        If Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = False Then
                            Me.fro_txt_Cena_PoslednaNakupna._Text = CStr(Me._DataRecord.Price_LastPurchase)
                        End If

            '--- Minimálne a maximálne množstvá ---

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.AmountMinimal
                        Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMinimalne._Text = CStr(Me._DataRecord.Amount_Minimal)

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.AmountMaximal
                        Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMaximalne._Text = CStr(Me._DataRecord.Amount_Maximal)

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.MinimalOrderAmount
                        Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMaximalne._Text = CStr(Me._DataRecord.MinimalOrderAmount)

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.UnitBase
                        Me.fro_cbo_MJ._SelectItem(Me._DataRecord.Unit)

                        z_SetControls_UnitsForPriceInput_Labels()

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.TextAdditional
                        Me.fro_txt_DoplnujuciText._Text = Me._DataRecord.TextAdditional

                End Select

            ElseIf e.Action = Exa.OBERON.Shared.TransportData.TransportData.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty Then
                '-------------------------------------------------------------------------------------------------------
                '--- SetProperty - Je potrebné nastaviť record podľa hodnôt v controloch, napr. v textových poliach
                '-------------------------------------------------------------------------------------------------------

                Select Case e.Control

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.StockCardType

                        Me._DataRecord.CardType = CType(Me.fro_cbo_TypKarty._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType)

                        z_SetControls_StockCardType()
                    'PriceCalculate

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate
                        'Nastaviť objekt 'DataRecord' podľa controlov.
                        Me.z_SetPrices(enm_PriceSetTargetTypes.DataRecord, m_PriceInputType, e.Price_Calculation)

                        '--- Ak bola zmena ceny, potrebné aktualizovať cenu pri alternatívnch MJ
                        z_SetControls_UnitOthers()

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.CashRegister_Change_Flags
                        With Me._DataRecord
                            .VATRate = CByte(Me.fro_cbo_SadzbaDPH._Text)
                            .CashRegister_ItemFlag = CType(Me.fro_cbo_RegPokladnica_ItemFlags._Selected_Item.Value, Exa.OBERON.Stock.StockCards.StockCard.enm_CashRegister_ItemFlag)
                            .NumberLinkedItem = Me.fro_txt_NumberLinkedItem._Text
                        End With


                     'PriceSupply
                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceSupply
                        If Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = False Then
                            Me._DataRecord.Price_Supply_Unit = CDec(Me.fro_txt_Cena_Obstaravacia._Value)
                        End If

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.Price_Discount_MaxPercento
                        Me._DataRecord.Price_Discount_MaxPercento = CDec(Me.fro_txt_ZlavyPredaj_MaximalnaZlava._Value)


                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.Price_Discount_Type
                        If Me.fro_rdb_ZlavyPredaj_Umoznit._Checked = True Then
                            Me._DataRecord.Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Allow
                        ElseIf Me.fro_rdb_ZlavyPredaj_Pytatsa._Checked = True Then
                            Me._DataRecord.Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Ask
                        Else
                            Me._DataRecord.Prices_DiscountApplyMode = StockCard.enm_Prices_DiscountApplyMode.Disallow
                        End If


            '--- Minimálne a maximálne množstvá ---
                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.AmountMinimal
                        Me._DataRecord.Amount_Minimal = CDec(Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMinimalne._Value)



                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.AmountMaximal
                        Me._DataRecord.Amount_Maximal = CDec(Me.fro_txt_Objednavky_AutoTvorbaObj_MnozstvoMaximalne._Value)

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.MinimalOrderAmount
                        Me._DataRecord.MinimalOrderAmount = CDec(Me.fro_txt_MinimalOrderAmount._Value)

            'UnitBase
                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.UnitBase
                        Me._DataRecord.Unit = Me.fro_cbo_MJ._Text

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.IgnoreExtendedSalePricing
                        Me._DataRecord.Prices_IgnoreExtendedSalePricing = fro_chk_IgnoreExtendedSalePricing._Checked

                    Case StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.TextAdditional
                        Me._DataRecord.TextAdditional = Me.fro_txt_DoplnujuciText._Text


                End Select

            End If
        End Sub

#End Region


#Region " EVENT HANLDERS - DATAGRIDS "

        Private Sub fro_dgv_UnitOthers_ev_Cell_ValueNeeded(sender As Object, e As cls_CellValueNeededEventArgs) Handles fro_dgv_UnitOthers.ev_Cell_ValueNeeded

            Try

                Select Case e.Column_VisibleIndex

                    Case fro_cln_Unit_MovementType.VisibleIndex
                        If Me._DataRecord.UnitOthers(e.RowIndex).UnitMovementType = StockCard.enm_UnitMovementType.Incoming Then
                            e.Value = My.Resources.StockCard_Unit_In
                        ElseIf Me._DataRecord.UnitOthers(e.RowIndex).UnitMovementType = StockCard.enm_UnitMovementType.Outcoming Then
                            e.Value = My.Resources.StockCard_Unit_Out
                        ElseIf Me._DataRecord.UnitOthers(e.RowIndex).UnitMovementType = StockCard.enm_UnitMovementType.IncomingAndOutcoming Then
                            e.Value = My.Resources.StockCard_Unit_InOut
                        Else

                        End If

                    Case fro_cln_Unit_Name.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).UnitName

                    Case fro_cln_Unit_Coeficient.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).UnitCoeficient

                    Case fro_cln_Unit_ActualAmount.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).ActualAmount

                    Case fro_cln_Unit_PriceWithVAT.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).PriceWithVAT

                    Case fro_cln_Unit_Package.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).PackageStockCardNumber

                    'Case fro_cln_Unit_PackageMode.VisibleIndex
                       ' e.Value = Exa.Basic.CodeDom.Enum.EnumFindItem(Of StockCard.UnitInfo.enm_PackageMode)(Me._DataRecord.UnitOthers(e.RowIndex).PackageMode)

                    Case fro_cln_Unit_PriceCoeficient.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).PriceCoeficient

                    Case fro_cln_Unit_PriceWithVAT_Coef.VisibleIndex
                        e.Value = Me._DataRecord.UnitOthers(e.RowIndex).PriceWithVAT_Coeficient

                End Select


            Catch ex As Exception

            End Try

        End Sub

        Private Sub fro_dgv_UnitOthers_ev_Cell_Formatting(sender As Object, e As cls_CellFormattingEventArgs) Handles fro_dgv_UnitOthers.ev_Cell_Formatting

            Try

                Select Case e.Column_VisibleIndex


                    Case fro_cln_Unit_Name.VisibleIndex
                        If Me._DataRecord.UnitOthers(e.RowIndex).DefaultUnit = TriState.True Then
                            '--- Predvolená MJ
                            e.CellStyle.Font = New Drawing.Font(e.CellStyle.Font, newStyle:=Drawing.FontStyle.Bold)
                        End If

                End Select


            Catch ex As Exception

            End Try

        End Sub


        Private Sub fro_dgv_UnitOthers_ev_SortOrder_UserRowMoving(sender As Object, e As cls_SortOrderUserRowMovingEventArgs) Handles fro_dgv_UnitOthers.ev_SortOrder_UserRowMoving
            Try

                If e.MoveType = cls_SortOrderUserRowMovingEventArgs.enm_RowMoveDirection.First Then
                    Me._DataRecord.UnitOthers.MoveItem(e.CurrentRowIndex, StockCard_UnitOthers.enm_MoveDirection.First)

                ElseIf e.MoveType = cls_SortOrderUserRowMovingEventArgs.enm_RowMoveDirection.Up Then
                    Me._DataRecord.UnitOthers.MoveItem(e.CurrentRowIndex, StockCard_UnitOthers.enm_MoveDirection.Up)

                ElseIf e.MoveType = cls_SortOrderUserRowMovingEventArgs.enm_RowMoveDirection.Down Then
                    Me._DataRecord.UnitOthers.MoveItem(e.CurrentRowIndex, StockCard_UnitOthers.enm_MoveDirection.Down)

                ElseIf e.MoveType = cls_SortOrderUserRowMovingEventArgs.enm_RowMoveDirection.Last Then
                    Me._DataRecord.UnitOthers.MoveItem(e.CurrentRowIndex, StockCard_UnitOthers.enm_MoveDirection.Last)

                End If

            Catch ex As Exception

            End Try

        End Sub

        Private Sub fro_dgv_UnitOthers_ev_SortOrder_UserRowMoved(sender As Object, e As EventArgs) Handles fro_dgv_UnitOthers.ev_SortOrder_UserRowMoved

            Try
                fro_dgv_UnitOthers.Refresh()
            Catch ex As Exception
            End Try

        End Sub

        Private Sub fro_dgv_Variants_ev_Cell_Formatting(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_CellFormattingEventArgs) Handles fro_dgv_Variants.ev_Cell_Formatting

            On Error Resume Next

            '--- Načítanie údajov
            If lc_Variant_DataRecord_DataGridCellFormatting Is Nothing Or e.NeedLoadDataForRow = True OrElse lc_Variant_DataRecord_DataGridCellFormatting Is Nothing Then
                Dim m_Row As DataRow = Me._DataRecord.Items_Variant.Object_Table.DatabaseTable_View(e.RowIndex).Row
                lc_Variant_DataRecord_DataGridCellFormatting = Me._DataRecord.Items_Variant.DataRecord(m_Row, True)
            End If

            Select Case e.Column_VisibleIndex

                Case Me.cln_Variants_Name_Preklad.VisibleIndex

                    'Preklad názvu do cudzích jazykov.
                    e.Value = String.Empty
                    If lc_Variant_DataRecord_DataGridCellFormatting IsNot Nothing Then
                        Dim m_SelLangCode As String = Exa.Application.Language.SelectedDataLanguageCode(Application.Language.mod_Language.enm_SelectedDataLanguageTypes.Views) 'Vybraný kód jazyka v controloch typu View, napr. 'DataGrid'.
                        Dim m_Translation As String = lc_Variant_DataRecord_DataGridCellFormatting.NameTranslations.GetValue(m_SelLangCode, lc_Variant_DataRecord_DataGridCellFormatting.Name)

                        If (m_Translation <> lc_Variant_DataRecord_DataGridCellFormatting.Name) Then
                            'Zobraziť len ak bola hodnota preložená (iná ako slovenská).
                            e.Value = m_Translation
                        End If
                    End If

            End Select


            '--- Neaktívna a nedostupná varianta - zmena farby
            If lc_Variant_DataRecord_DataGridCellFormatting.Disabled = True Then
                e.CellStyle.ForeColor = Drawing.Color.Gray
            End If


        End Sub

        Private Sub fro_dgv_Variants_ev_SetCustomCell(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_SetCustomCellEventArgs) Handles fro_dgv_Variants.ev_SetCustomCell
            On Error Resume Next

            If e.Column_VisibleIndex = Me.cln_Variants_Details.VisibleIndex Then
                e.CustomCell = New cls_VarinatsDetailsCell
                e.Tag = Me
            End If

        End Sub

        Private Sub fro_dgv_Parameters_ev_Cell_Formatting(sender As Object, e As Application.Controls.Simple.S_DataGrid.cls_CellFormattingEventArgs) Handles fro_dgv_Parameters.ev_Cell_Formatting

            On Error Resume Next

            '--- Načítanie údajov
            If lc_Parameter_DataRecord_DataGridCellFormatting Is Nothing Or e.NeedLoadDataForRow = True OrElse lc_Parameter_DataRecord_DataGridCellFormatting Is Nothing Then
                Dim m_Row As DataRow = Me._DataRecord.Items_Parameter.Object_Table.DatabaseTable_View(e.RowIndex).Row
                lc_Parameter_DataRecord_DataGridCellFormatting = Me._DataRecord.Items_Parameter.DataRecord(m_Row, True)
            End If

            Select Case e.Column_VisibleIndex

                Case cln_Parameters_Value.VisibleIndex
                    '--- Hodnota ---
                    If lc_Parameter_DataRecord_DataGridCellFormatting IsNot Nothing Then
                        e.Value = lc_Parameter_DataRecord_DataGridCellFormatting.GetValue(u_ThousandSeparator:=True)
                    End If

                Case cln_Parameters_Name_Preklad.VisibleIndex
                    'Preklad názvu do cudzích jazykov.
                    e.Value = String.Empty
                    If lc_Parameter_DataRecord_DataGridCellFormatting IsNot Nothing Then
                        Dim m_SelLangCode As String = Exa.Application.Language.SelectedDataLanguageCode(Application.Language.mod_Language.enm_SelectedDataLanguageTypes.Views) 'Vybraný kód jazyka v controloch typu View, napr. 'DataGrid'.
                        Dim m_Translation As String = lc_Parameter_DataRecord_DataGridCellFormatting.NameTranslations.GetValue(m_SelLangCode, lc_Parameter_DataRecord_DataGridCellFormatting.Name)

                        If (m_Translation <> lc_Parameter_DataRecord_DataGridCellFormatting.Name) Then
                            'Zobraziť len ak bola hodnota preložená (iná ako slovenská).
                            e.Value = m_Translation
                        End If
                    End If

                Case cln_Parameters_Value_Preklad.VisibleIndex
                    'Preklad hodnoty do cudzích jazykov.
                    e.Value = String.Empty
                    If lc_Parameter_DataRecord_DataGridCellFormatting IsNot Nothing Then
                        Dim m_SelLangCode As String = Exa.Application.Language.SelectedDataLanguageCode(Application.Language.mod_Language.enm_SelectedDataLanguageTypes.Views) 'Vybraný kód jazyka v controloch typu View, napr. 'DataGrid'.
                        Dim m_Translation As String = lc_Parameter_DataRecord_DataGridCellFormatting.GetValue(u_ThousandSeparator:=True, u_LanguageCode:=m_SelLangCode)
                        Dim m_SlovakValue As String = lc_Parameter_DataRecord_DataGridCellFormatting.GetValue()

                        If (m_Translation <> m_SlovakValue) Then
                            'Zobraziť len ak bola hodnota preložená (iná ako slovenská).
                            e.Value = m_Translation
                        End If
                    End If

            End Select


        End Sub

        Private Sub fro_dgv_Parameters_ev_Clipboard(sender As Object, e As cls_ClipboardEventArgs) Handles fro_dgv_Parameters.ev_Clipboard
            Try
                '--- VALIDATION ---
                If Me._DataRecord Is Nothing Then
                    Exit Try
                End If

                Dim tmp_Flag As String = "StockCards_Parameters"
                e.Flag = tmp_Flag

                Select Case e.ActionType
                    Case Application.Controls.Simple.S_DataGrid.cls_ClipboardEventArgs.enm_ActionTypes.Copy
                        '--- KOPÍROAVNIE DO SCHRÁNKY ---

                        If Me.fro_dgv_Parameters._Selected_RowIndex = -1 Then
                            e.Handled = True
                            Exit Try
                        End If

                        If Me.fro_dgv_Parameters._RowsCount <= 0 Then
                            e.Handled = True
                            Exit Try
                        End If

                        '--- Skopíruj údaje zaradenia do schránky 'Clipboard'.
                        e.ExaException = Me._DataList.DataRecord.CopyToClipboard(e.Object_Clipboard, e.Flag, u_SelectedRowIndex:=Me.fro_dgv_Parameters._Selected_RowIndex)
                        If e.ExaException.Result = False Then
                            e.ExaException = Exa.Basic.Exceptions.Get(Exa.Application.TranslateText("Kopírovanie údajov paramertov skladovej karty do schránky sa nepodarilo."), e.ExaException, e.ExaException.ErrNumber, e.ExaException.ExceptionType)
                            Exit Sub
                        End If

                        e.Handled = True

                    Case Application.Controls.Simple.S_DataGrid.cls_ClipboardEventArgs.enm_ActionTypes.Paste
                        '--- VLEPENIE ZO SCHRÁNKY ---

                        If e.ClipboardData Is Nothing Then
                            Exit Sub
                        End If

                        If e.IsPasteSpecial = True Then
                            '--- Čo ak by bol e.ClipboardData Nothing?
                            If CType(e.ClipboardData, Exa.OBERON.Stock.StockCards.StockCard.cls_StockCardClipboardData).Parameters?.Count > 1 Then
                                Dim tmp_DialogResult As Windows.Forms.DialogResult = Exa.Application.MsgBox(Exa.Application.TranslateText("Chcete vložiť všetky parametre zo schránky?"), MsgBoxStyle.Question Or MsgBoxStyle.YesNoCancel)
                                If tmp_DialogResult = DialogResult.Cancel Then
                                    e.Handled = True
                                    Exit Sub
                                End If

                                If tmp_DialogResult = DialogResult.Yes Then
                                    '--- Vymaž identifikátor vybratého parametra - budú sa vkladať všetky parametre.
                                    CType(e.ClipboardData, Exa.OBERON.Stock.StockCards.StockCard.cls_StockCardClipboardData).RowIndex = -1
                                End If
                            End If
                        End If

                        '--- Načítaj údaje zaradenia podľa údajov zo schránky 'ClipBoard'.
                        e.ExaException = Me._DataList.DataRecord.PasteFromClipboard(e, Me.lc_ObjectsOBERON_Stock, e.Flag)
                        If e.ExaException.Result = False Then
                            '--- DÔLEŽITÉ: Prenášať pôvodný kód a typ chyby.
                            e.ExaException = Exa.Basic.Exceptions.Get(Exa.Application.TranslateText("Chyba pri prevode údajov paremetrov skladovej karty zo schránky 'Clipboard' do formátu údajov záznamu."), e.ExaException, e.ExaException.ErrNumber, e.ExaException.ExceptionType)
                            Exit Select
                        End If

                        e.Handled = True

                    Case Exa.Basic.Application.Clipboard.cls_ClipboardEventArgs.enm_ActionTypes.Paste_Completed

                        '--- Refresh datagridu.
                        Me.fro_dgv_Parameters.Refresh()
                End Select
            Catch ex As Exception

            End Try
        End Sub

#End Region


#Region " EVENT HANLDERS - DEVICE ENGINE "

        Private Sub eh_DeviceEngine_BarCodeScanner_Readed_Value(ByVal u_EventArgs As Exa.OBERON.Devices.BarcodeScanner.Driver_Common.BarCodeScanner_Readed_EventArgs)
            On Error Resume Next

            '-- VALIDATION --
            If Me.ContainsFocus = False Then Exit Sub


            '-- SET BAR CODE --
            ': Nastav čiarový kód
            Exa.Application.Cursor_Wait(Me)

            Select Case Me.fro_TabControl._Selected_PageIndex

                Case Me.fro_tab_Variants._Page_VisibleIndex
                    'Použiť čiarový kód pre vybratú variantu
                    If Me.fro_dgv_Variants._Selected_RowIndex >= 0 Then
                        Dim m_ExaException As EXC.ExaException
                        Dim m_Row As DataRow = Me._DataRecord.Items_Variant.Object_Table.DatabaseTable_View(Me.fro_dgv_Variants._Selected_RowIndex).Row

                        With Me._DataRecord.Items_Variant.DataRecord(m_Row)

                            m_ExaException = ._Load(.IDNum)
                            If m_ExaException.Result = False Then
                                Exa.Application.MsgBox("Chyba pri načítaní záznamu pre uloženie čiarového kódu.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Exit Select
                            End If

                            .Barcode = u_EventArgs.BarCode

                            m_ExaException = ._Save()
                            If m_ExaException.Result = False Then
                                Exa.Application.MsgBox("Chyba pri uložení čiarového kódu do záznamu.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                                Exit Select
                            End If
                        End With

                    End If


                Case Else

                    'Nastav aktívnu TAB na reg. pokladnice - čiarový kód
                    Me.fro_TabControl._Selected_PageIndex = Me.fro_tab_RegistracnePokladnice._Page_VisibleIndex

                    With Me.fro_txt_RPokladnice_CiarovyKod
                        If ._Text = Nothing AndAlso CStr(._Text).Trim.Length = 0 Then
                            '--- Pole je prázdne ---
                            ._Text = u_EventArgs.BarCode
                        Else
                            '--- Už je niečo zdané ---
                            If ._Text.Contains(u_EventArgs.BarCode) = False Then
                                '--- Tento kód sa nenachádza v poli ---				
                                If ._Text.Trim.Substring(._Text.Trim.Length - 1) = "," Then
                                    '--- Na konci je zadaný oddeľovač ---
                                    ._Text = ._Text.Trim & " " & u_EventArgs.BarCode
                                Else
                                    ._Text = ._Text & ", " & u_EventArgs.BarCode
                                End If
                            End If

                        End If
                        .Focus()
                    End With

            End Select

            Exa.Application.Cursor_Default(Me)

        End Sub

#End Region


#Region " EVENT HANLDERS - TAB "

        Private Sub fro_tab_Objednavky_ev_Page_BeforeShow(sender As Object, e As System.EventArgs) Handles fro_tab_Objednavky.ev_Page_BeforeShow
            '--- Vypočítať objednané množstvá ---
            z_Order_Calculate()
        End Sub

#End Region


#Region " CONTROLS - OTHERS (Základné) "

        Private Sub fro_txt_CisloKarty_ev_ButtonList_Click(sender As Object, e As Application.Controls.cls_ButtonListEventArgs) Handles fro_txt_CisloKarty.ev_ButtonList_Click

            On Error Resume Next

            'If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.Editing Then
            '    '--- Oprava karty - tu sa pýtať (pri novej sa netreba pýtať)
            '    Dim tmp_DialogResult As DialogResult
            '    Dim tmpStr$
            '    tmpStr$ = Exa.Application.TranslateText("Vygenerovať nové číslo skladovej karty?")
            '    tmp_DialogResult = Exa.Application.MsgBox(tmpStr$, MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2)
            '    If tmp_DialogResult <> Windows.Forms.DialogResult.Yes Then
            '        Exit Sub
            '    End If
            'End If

            Exa.Application.Cursor_Wait()

            Me._DataRecord.NumberGetNew(Me.lc_Selected_Stock,
                                        Me._DataRecord.Stock_Group,
                                        u_GenerateFromDatabase:=True,
                                        urf_StockCard_Number:=Me._DataRecord.Number)

            Me.fro_txt_CisloKarty._Text = Me._DataRecord.Number

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                '--- Nová karta
                If String.IsNullOrWhiteSpace(fro_txt_RPoklSFiskalom_KodPolozky.Text) = False Then
                    '--- Kód položky je už zadaný - pri novej karte a zmene čísla karty zmeniť aj tento kód
                    fro_txt_RPoklSFiskalom_KodPolozky.Text = Me.fro_txt_CisloKarty._Text
                End If
            End If

            Exa.Application.Cursor_Default()
            Me.fro_txt_CisloKarty.Focus()

        End Sub

        Private Sub fro_txt_CisloKarty_ev_UserInputFinished(sender As Object, e As cls_UserInputFinishedEventArgs) Handles fro_txt_CisloKarty.ev_UserInputFinished

            On Error Resume Next

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                '--- Nová karta
                If String.IsNullOrWhiteSpace(fro_txt_RPoklSFiskalom_KodPolozky.Text) = False Then
                    '--- Kód položky je už zadaný - pri novej karte a zmene čísla karty zmeniť aj tento kód
                    fro_txt_RPoklSFiskalom_KodPolozky.Text = Me.fro_txt_CisloKarty._Text
                End If
            End If

            Me._DataRecord.Number = fro_txt_CisloKarty._Text

        End Sub


        Private Sub fro_txt_Nazov_ev_UserInputFinished(sender As Object, e As System.EventArgs) Handles fro_txt_Nazov.ev_UserInputFinished

            '--- Do textu okna doplniť názov skladovej karty
            Me.Text_Notice = "  -  " & fro_txt_Nazov.TextSlovak

            Me._DataRecord.Name = fro_txt_Nazov._Text

        End Sub

        Private Sub fro_txt_Cena_Obstaravacia_ev_UserInputFinished(sender As Object, e As Application.Controls.cls_UserInputFinishedEventArgs) Handles fro_txt_Cena_Obstaravacia.ev_UserInputFinished
            On Error Resume Next

            '-- VALIDATION --
            If Me.IsHandleCreated = False Then Exit Sub


            'Prepočet cien, prepočet cien vykonaj len ak obstarávaciu cenu zmenil používateľ,
            'pričom musí byť v nastaveniach skladu zapnuté nastavenie prepočítavania cien podľa obstarávacej ceny
            If Me.fro_txt_Cena_Obstaravacia.IsTextChangedByUser = True And Me.lc_AppConfiguration.Stock.StockCard_Price_CalculateFrom = Exa.OBERON.ApplicationEnvironment.AppConfigurationObjects.AppConfiguration_Stock.enm_StockCard_Price_CalculateFrom.Supply Then
                '--- Podľa nastavení prepočtu predajnej ceny

                '--- Nastaví record podľa textových polí
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                              StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)


                If Me.fro_rdb_PrepocetCeny_Vzdy._Checked = True Then
                    '--- Vykonaj prepočet vždy
                    Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Markup, 0, True)

                ElseIf Me.fro_rdb_PrepocetCeny_PytatSa._Checked = True Then
                    '--- Zobraz hlášku či sa má cena prepočítať
                    Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                    m_DialogResult = Exa.Application.MsgBox("Prepočítať predajné ceny?", MsgBoxStyle.Question Or MsgBoxStyle.YesNo Or MsgBoxStyle.DefaultButton2)

                    If m_DialogResult = Windows.Forms.DialogResult.Yes Then
                        Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Markup, 0, True)
                    End If

                Else
                    '* Prepočet sa nebude vykonávať, pokračuj ďalej

                End If

                'TexBox-u resetuj text zadaný používateľom, po resetovaní bude vlastnosť 'IsTextChangedByUser' vracať hodnotu FALSE, pokiaľ používateľ znova nezmení obstarávaciu cenu 
                Me.fro_txt_Cena_Obstaravacia.ResetUserTextChange()
            End If

        End Sub

        Private Sub fro_txt_Cena_PoslednaNakupna_ev_UserInputFinished(sender As Object, e As Application.Controls.cls_UserInputFinishedEventArgs) Handles fro_txt_Cena_PoslednaNakupna.ev_UserInputFinished
            On Error Resume Next

            '-- VALIDATION --
            If Me.IsHandleCreated = False Then Exit Sub


            'Prepočet cien, prepočet cien vykonaj len ak poslednú nákupnú cenu zmenil používateľ,
            'pričom musí byť v nastaveniach skladu zapnuté nastavenie prepočítavania cien podľa poslednej nákupnej ceny
            If Me.fro_txt_Cena_PoslednaNakupna.IsTextChangedByUser = True And Me.lc_AppConfiguration.Stock.StockCard_Price_CalculateFrom = Exa.OBERON.ApplicationEnvironment.AppConfigurationObjects.AppConfiguration_Stock.enm_StockCard_Price_CalculateFrom.LastPurchase Then
                'Podľa nastavení prepočtu predajnej ceny

                '--- Nastaví navýšenie podľa textových polí
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                              StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

                If Me.fro_rdb_PrepocetCeny_Vzdy._Checked = True Then
                    'Vykonaj prepočet vždy
                    Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Markup, u_NoCalculate_Different:=0, u_ManualEntry:=True)

                ElseIf Me.fro_rdb_PrepocetCeny_PytatSa._Checked = True Then
                    'Zobraz hlášku či sa má cena prepočítať
                    Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                    m_DialogResult = Exa.Application.MsgBox("Prepočítať predajné ceny?", MsgBoxStyle.Question Or MsgBoxStyle.YesNo)

                    If m_DialogResult = Windows.Forms.DialogResult.Yes Then
                        Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Markup, 0, True)
                    End If

                Else
                    '* Prepočet sa nebude vykonávať, pokračuj ďaľej

                End If

                'TexBox-u resetuj text zadaný používateľom, po resetovaní bude vlastnosť 'IsTextChangedByUser' vracať hodnotu FALSE, pokiaľ používateľ znova nezmení obstarávaciu cenu 
                Me.fro_txt_Cena_PoslednaNakupna.ResetUserTextChange()
            End If

        End Sub

        Private Sub fro_txt_Cena_PoslednaNakupna_ev_ButtonList_Click(sender As Object, e As cls_ButtonListEventArgs) Handles fro_txt_Cena_PoslednaNakupna.ev_ButtonList_Click


            Dim frm_StockMovement_List As Forms.StockMovements.frm_StockMovement_List = Nothing
            Dim myEx As EXC.ExaException

            Try

                Exa.Application.Cursor_Wait(Me)

                '--- Formulár so skladovými pohybmy
                frm_StockMovement_List = New Forms.StockMovements.frm_StockMovement_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Preview,
                                                                                          Me._DataRecord._ObjectsOBERON_Stock,
                                                                                          Me.lc_DeviceEngine,
                                                                                          Me._DataRecord)
                If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                    Exit Try
                End If


                '--- Načíta údajov
                myEx = frm_StockMovement_List._LoadData(u_StockSelected_Name:=Me._DataRecord._Stock.Name, u_MustLoad:=True)

                If myEx.Result = False Then
                    If frm_StockMovement_List IsNot Nothing Then
                        frm_StockMovement_List.Dispose()
                    End If
                    frm_StockMovement_List = Nothing
                    Exa.Application.MsgBox("Chyba pri načítaní zoznamu skladových pohybov, nie je možné pokračovať.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                    Exit Try
                End If

                '--- Zobraziť  okno
                Exa.Application.ShowWindow(frm_StockMovement_List, True, Me.OptionsFormInfo.Object_Form)

            Catch ex As Exception

            Finally

                Exa.Application.Cursor_Default(Me)

                If frm_StockMovement_List IsNot Nothing Then
                    frm_StockMovement_List.Dispose()
                    frm_StockMovement_List = Nothing
                End If

            End Try

        End Sub



        Private Sub fro_cbo_Umiestnenie_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_Umiestnenie.ev_ButtonList_Click

            On Error Resume Next

            '-- SHOW SIMPLE LIST --
            ': Inicializácia zoznamu, údaje budú načítané automaticky v konštruktore formu
            Dim m_StockCard_Place_List As New Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_Place_List(Me.lc_AppConfiguration)

            ': Zobra okno ktoré umožňuje editovanie jednoduchého zoznamu položiek
            Dim f_SimpleList As New Exa.Application.Forms.Data.frm_DataList_Simple(m_StockCard_Place_List)

            f_SimpleList._Selected_ItemText = Me.fro_cbo_Umiestnenie._Text

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then GoTo g_ExitSub

            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

            m_DialogResult = Exa.Application.ShowWindow(f_SimpleList, True, Me)

            ': Aktualizovanie zoznamu položiek 
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_Umiestnenie._Items.AddRange(m_StockCard_Place_List, True)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Else
                If m_DialogResult = Windows.Forms.DialogResult.OK Then
                    Me.fro_cbo_Umiestnenie._Text = f_SimpleList._Selected_ItemText
                End If
            End If



g_ExitSub:

            If m_StockCard_Place_List IsNot Nothing Then m_StockCard_Place_List.Dispose()
            m_StockCard_Place_List = Nothing

            If f_SimpleList IsNot Nothing Then f_SimpleList.Dispose()
            f_SimpleList = Nothing

        End Sub

        Private Sub fro_cbo_Umiestnenie_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_Umiestnenie.ev_NeedLoadItems

            On Error Resume Next

            'Inicializácia zoznamu, údaje budú načítané automaticky v metóde 'AddRange'
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_Umiestnenie._Items.AddRange(lc_ObjectsOBERON_Stock._ObjectsOBERON.StockCatalogList_Place_List, False)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End If

        End Sub

        Private Sub fro_cbo_SadzbaDPH_ev_SelectedIndex_Changed(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_cbo_SadzbaDPH.ev_SelectedIndex_Changed

            On Error Resume Next

            '-- VALIDATION --
            If Me.IsHandleCreated = False Then Exit Sub


            'Zmena DPH, je potrebné prepočítať ceny ak sú zadané
            Static m_IsVatChanging As Boolean

            If m_IsVatChanging = False AndAlso (
               CDec(Me.fro_txt_PredajnaCena1_BezDPH._Value) <> 0 Or CDec(Me.fro_txt_PredajnaCena1_SDPH._Value) <> 0 Or
               CDec(Me.fro_txt_PredajnaCena2_BezDPH._Value) <> 0 Or CDec(Me.fro_txt_PredajnaCena2_SDPH._Value) <> 0 Or
               CDec(Me.fro_txt_PredajnaCena3_BezDPH._Value) <> 0 Or CDec(Me.fro_txt_PredajnaCena3_SDPH._Value) <> 0 Or
               CDec(Me.fro_txt_PredajnaCena4_BezDPH._Value) <> 0 Or CDec(Me.fro_txt_PredajnaCena4_SDPH._Value) <> 0) Then
                'Ceny sú zadané
                Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                m_DialogResult = Exa.Application.MsgBox("Bola zmenená sadzba DPH. Nasledovne budú prepočítané predajné ceny na tejto skladovej karte. Zachovať predajné ceny s DPH a dopočítať cenu bez DPH?", MsgBoxStyle.Question Or MsgBoxStyle.YesNoCancel Or MsgBoxStyle.DefaultButton3, "Poznámka:" & vbCrLf & "Pri prepočte nových predajných cien je možné zachovať ceny s DPH a dopočítať predajné ceny bez DPH alebo zachovať ceny bez DPH a dopočítať ceny s DPH.")

                Select Case m_DialogResult
                    Case Windows.Forms.DialogResult.Yes
                        'Vypočítať cenu bez DPH, cenu s DPH ponechať
                        Me._DataRecord.VATRateSET(CDec(Me.fro_cbo_SadzbaDPH._Text), True)

                    Case Windows.Forms.DialogResult.No
                        'Vypočítať cenu s DPH, cenu bez DPH ponechať
                        Me._DataRecord.VATRateSET(CDec(Me.fro_cbo_SadzbaDPH._Text), False)

                    Case Else
                        'Nastaviť pôvodnú DPH
                        m_IsVatChanging = True

                        Me.fro_cbo_SadzbaDPH._SelectItem(Me._DataRecord.VATRate)

                        m_IsVatChanging = False

                End Select
            End If

            'Aktualizovať príznaky OFF-Line registračných pokladníc 
            Me._DataRecord.CashRegister_Flags.Flags_Refresh()

        End Sub

        Private Sub fro_cbo_SkladovaSkupina_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_SkladovaSkupina.ev_ButtonList_Click

            On Error Resume Next

            Dim myEx As EXC.ExaException

            '-- VALIDATION --
            ': Kontrola práv používateľov.
            If lc_ObjectsOBERON_Stock._AppConfiguration._AppObjects._UserInfo.Privileges.Stock.StockCard_Group_Record = Exa.Database.Factory.DataRecord.enm_RecordPrivilegeTypes.Disabled Then
                Exa.Application.MsgBox(Exa.Application.Users.MsgBoxText_PrivilegeInsufficient, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly, , , Exa.Application.Forms.Message.enm_MessageIconTypes.Privilege)
                Exit Sub
            End If

            Dim frm_StockCard_Group_List As New Exa.OBERON.Stock.Forms.StockCards.Catalog.frm_StockCard_Group_List(Exa.Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select,
                                                                                                                 lc_ObjectsOBERON_Stock,
                                                                                                                 u_SelectedName:=fro_cbo_SkladovaSkupina.Text,
                                                                                                                 u_LoadDisabled:=True)
            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                GoTo ExitFunction
            End If
            myEx = frm_StockCard_Group_List._LoadData()
            If myEx.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní záznamov.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitFunction
            End If

            Dim tmp_DialogResult As DialogResult = DialogResult.None
            tmp_DialogResult = Exa.Application.ShowWindow(frm_StockCard_Group_List, True, Me)
            If tmp_DialogResult = DialogResult.OK Then
                fro_cbo_SkladovaSkupina.Text = frm_StockCard_Group_List._SelectedDataRecord.Name
            End If

ExitFunction:

            If frm_StockCard_Group_List IsNot Nothing Then
                frm_StockCard_Group_List.Dispose()
                frm_StockCard_Group_List = Nothing
            End If

            fro_cbo_SkladovaSkupina.ResetNeedLoadItems()

        End Sub

        Private Sub fro_cbo_SkladovaSkupina_ev_DropDown_ItemSelected(sender As Object, e As EventArgs) Handles fro_cbo_SkladovaSkupina.ev_DropDown_ItemSelected

            On Error Resume Next

            'Skopíruj preklady cudzích jazykov so zoznamu skupín podľa vybranej položky.
            If Exa.Application.Language.AllowDataTranslation = True Then
                Dim m_DataList_RowID As Long = Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_Group_List.GetRowID(Me._DataList._ObjectsOBERON_Stock._AppConfiguration._AppObjects._CommonData, Me.fro_cbo_SkladovaSkupina.TextSlovak)

                With Me.fro_cbo_SkladovaSkupina
                    .TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_CardGroups,
                                                 Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.Name,
                                                 m_DataList_RowID)
                    .DataTranslateValueRefresh()
                End With
            End If

        End Sub

        Private Sub fro_cbo_SkladovaSkupina_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_SkladovaSkupina.ev_NeedLoadItems

            On Error Resume Next

            Me.fro_cbo_SkladovaSkupina._Items.AddRange(lc_ObjectsOBERON_Stock._ObjectsOBERON.StockCatalogList_Groups_List, u_AutoLoadData:=False)

        End Sub

        Private Sub fro_cbo_TypKarty_ev_UserInputFinished(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_TypKarty.ev_UserInputFinished

            On Error Resume Next

            If Me.Visible = True Then
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                            StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.StockCardType)

            End If

        End Sub


        Private Sub fro_cbo_MJ_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_MJ.ev_ButtonList_Click

            On Error Resume Next

            'Zobrazenie formu a načítanie zoznamu merných jednotiek
            Dim f_Unit_List As New Exa.OBERON.Shared.Forms.Common.Units.frm_Unit_List(Me.lc_ObjectsOBERON_Stock._ObjectsOBERON)

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then GoTo g_ExitSub

            Exa.Application.ShowWindow(f_Unit_List, True, Me)

            'Aktualizovanie zoznamu položiek 
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_MJ._Items.AddRange(f_Unit_List._DataList, False)

            If m_ExaException.Result = True Then
                m_ExaException = Me.fro_cbo_NastaveniaMJ_MJPrePorovnanieCeny._Items.AddRange(f_Unit_List._DataList, False)
            End If

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu merných jednotiek.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Else
                'Vybranie položky z formu
                'Me.fro_cbo_Stat._Text = f_Countries._Selected_ItemText
                '* Položku nevyberaj, pretože na forme chýba tlačítko OK,
                '  položku nie je možné vybrať keď sa form zatvorí 'Cancel', pre používateľa otravné
                '  napr. menilo by už vybranú položku aj keď by to používateľ nechcel 
            End If



g_ExitSub:

            If f_Unit_List IsNot Nothing Then f_Unit_List.Dispose()
            f_Unit_List = Nothing

        End Sub

        Private Sub fro_cbo_MJ_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_MJ.ev_NeedLoadItems

            On Error Resume Next

            'Inicializácia zoznamu, údaje budú načítané automaticky v metóde 'AddRange'
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_MJ._Items.AddRange(Me.lc_ObjectsOBERON_Stock._ObjectsOBERON.Unit_List, False)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu merných jednotiek.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End If

        End Sub

        Private Sub fro_cbo_MJ_ev_UserInputFinished(sender As Object, e As EventArgs) Handles fro_cbo_MJ.ev_UserInputFinished
            On Error Resume Next

            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                            StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.UnitBase)

            Me.z_SetControls_UnitsForPriceInput_ComboBox()
            Me.z_SetControls_UnitsForPriceInput_Labels()



        End Sub

        Private Sub fro_cbo_MJ_ev_DropDown_ItemSelected(sender As Object, e As EventArgs) Handles fro_cbo_MJ.ev_DropDown_ItemSelected
            On Error Resume Next

            'Skopíruj preklady cudzích jazykov so zoznamu merných jednotiek podľa vybranej MJ.
            If Exa.Application.Language.AllowDataTranslation = True Then
                Dim m_DataList_RowID As Long = Exa.OBERON.Shared.Common.Units.Unit_List.GetRowID(Me._DataList._ObjectsOBERON_Stock._AppConfiguration._AppObjects._CommonData, Me.fro_cbo_MJ.TextSlovak)

                With Me.fro_cbo_MJ
                    .TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Units,
                                                 Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.Name,
                                                 m_DataList_RowID)
                    .DataTranslateValueRefresh()
                End With
            End If

        End Sub


        Private Sub fro_txt_NumberLinkedItem_ev_ButtonList_Click(sender As Object, e As cls_ButtonListEventArgs) Handles fro_txt_NumberLinkedItem.ev_ButtonList_Click

            On Error Resume Next

            Dim tmp_frm_StockCard_Select As StockCards.frm_StockCard_Select = Nothing

            '--- STOCK CARD LIST FORM --            
            If tmp_frm_StockCard_Select Is Nothing Then
                tmp_frm_StockCard_Select = New StockCards.frm_StockCard_Select(Me._DataRecord._ObjectsOBERON_Stock,
                                                                                 u_DeviceEngine:=Me._DataRecord._DeviceEngine,
                                                                                 u_PriceSupplyVisible:=False)

                '--- Umožniť vybrať len z tohto skladu
                tmp_frm_StockCard_Select._AllowChange_Stock = False
                tmp_frm_StockCard_Select._AllowSelect_AllStocks = False
                tmp_frm_StockCard_Select._RaiseEventOnButtonOk = False
            End If

            '--- Načítanie skladových kariet podľa aktuálne vybraného skladu,
            '--- údaje budú načítané len raz (funkcia automaticky kontroluje napr. zmenu skladu, pokiaľ sa sklad nezmení položky sa načítavať nebudú)
            Dim myEx As Exa.Basic.Exceptions.ExaException = Nothing

            '--- Nastaviť zoznam dostupných skladov s ktorým môže formulár pracovať ---
            myEx = tmp_frm_StockCard_Select._Stocks_Available_SET(Me._DataRecord._Stock)
            If myEx.Result = False Then
                Exa.Application.MsgBox("Chyba pri nastavení skladu v zozname skladových kariet s ktorým sa má pracovať, nie je možné pokračovať.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If

            '--- Načítať data - inteligentne, nie vždy načítanie ide 
            myEx = tmp_frm_StockCard_Select._LoadData(Me._DataRecord._Stock,
                                                       StockCard_List.enum_LoadData_Option.Only_ReturnablePackagingCards,
                                                       u_MustLoad:=False,
                                                       u_PriceLevel:=1)

            If myEx.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu skladových kariet, nie je možné pokračovať.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If

            '--- Zobraziť okno ktoré zostáva v pamäti
            Dim tmp_DialogResult As DialogResult = Windows.Forms.DialogResult.None
            tmp_frm_StockCard_Select._SelectDataGridRow_ByNumber(fro_txt_NumberLinkedItem._Text)
            tmp_DialogResult = Exa.Application.ShowWindow(tmp_frm_StockCard_Select, True, Me)

            If tmp_DialogResult = DialogResult.OK Then
                '--- OK
                fro_txt_NumberLinkedItem._Text = tmp_frm_StockCard_Select._SelectedRow_StockCard_Number

                Me._DataRecord.CashRegister_Flags.Flags_Refresh()

            End If

            If tmp_frm_StockCard_Select IsNot Nothing Then
                tmp_frm_StockCard_Select.Dispose()
            End If
            tmp_frm_StockCard_Select = Nothing



        End Sub

        Private Sub fro_txt_NumberLinkedItem_ev_TextChanged_ByUser(sender As Object, e As EventArgs) Handles fro_txt_NumberLinkedItem.ev_TextChanged_ByUser

            On Error Resume Next

            Me._DataRecord.CashRegister_Flags.Flags_Refresh()

        End Sub


        Private Sub fro_cbo_NastaveniaMJ_MJPrePorovnanieCeny_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_NastaveniaMJ_MJPrePorovnanieCeny.ev_NeedLoadItems

            On Error Resume Next

            'Inicializácia zoznamu, údaje budú načítané automaticky v metóde 'AddRange'
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_NastaveniaMJ_MJPrePorovnanieCeny._Items.AddRange(Me.lc_ObjectsOBERON_Stock._ObjectsOBERON.Unit_List, False)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu merných jednotiek.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End If

        End Sub


        Private Sub fro_txt_RPokladnice_CiarovyKod_ev_ButtonList_Click(sender As Object, e As Application.Controls.cls_ButtonListEventArgs) Handles fro_txt_RPokladnice_CiarovyKod.ev_ButtonList_Click
            On Error Resume Next

            Dim myex As EXC.ExaException
            Dim m_BarCodeGenerator As Exa.OBERON.Shared.Features.BarCodeGenerator = Nothing
            Dim m_GeneratedCode$ = ""

            If String.IsNullOrWhiteSpace(Me.fro_txt_RPokladnice_CiarovyKod._Text) = False AndAlso
                (Me.fro_txt_RPokladnice_CiarovyKod._Text.StartsWith(Exa.OBERON.Shared.Features.BarCodeGenerator.C_BarCodeEvidence_Prefix_StockCards) OrElse
               Me.fro_txt_RPokladnice_CiarovyKod._Text.Contains(", " & Exa.OBERON.Shared.Features.BarCodeGenerator.C_BarCodeEvidence_Prefix_StockCards)) Then
                '--- je zadaný čiarový kód a obsahuje prefix
                Dim m_DlgResult As DialogResult
                m_DlgResult = Exa.Application.MsgBox("Skladová karta už obsahuje čiarový kód s prefixom '" & Exa.OBERON.Shared.Features.BarCodeGenerator.C_BarCodeEvidence_Prefix_StockCards & "' je zadaný. Vygenerovať ďalší čiarový kód?", MsgBoxStyle.YesNo Or MsgBoxStyle.Question Or MsgBoxStyle.DefaultButton2)
                If m_DlgResult <> Windows.Forms.DialogResult.Yes Then
                    GoTo ExitSub
                End If
            End If

            m_BarCodeGenerator = New Exa.OBERON.Shared.Features.BarCodeGenerator(Me._DataRecord._AppConfiguration, Exa.OBERON.Shared.Features.BarCodeGenerator.enm_BarCodeGeneratorEvidence.StockCards)
            m_BarCodeGenerator.OverrideDataCodeWithDefaultCode = True

            myex = m_BarCodeGenerator.GenerateCode(Exa.OBERON.Shared.Features.BarCodeGenerator.enm_BarCodeType.GTIN13,
                                                    Me._DataRecord._RecordSettings.TableName,
                                                    m_GeneratedCode,
                                                    Me._DataRecord.Number,
                                                    True)
            If myex.Result = False Then
                Exa.Application.MsgBox("Chyba pri generovaní čiarového kódu.", myex, MsgBoxStyle.YesNo Or MsgBoxStyle.Critical)
                GoTo ExitSub
            End If

            '--- predať hodnotu
            Dim m_Index% = -1
            If String.IsNullOrWhiteSpace(Me.fro_txt_RPokladnice_CiarovyKod._Text) = False Then
                '--- nie sú žiadne čiarové kódy

                Me.fro_txt_RPokladnice_CiarovyKod._Text = m_GeneratedCode

            Else
                '--- nejaké kódy sú zadané
                'Me.fro_txt_RPokladnice_CiarovyKod._Text
                Dim m_BarCodesArray() As String = Exa.Basic.Strings.Convert_To_ArrayString(Me.fro_txt_RPokladnice_CiarovyKod._Text, Exa.Basic.Strings.enm_StringSeparator_UsingTypes.Behind, CChar(","), True)

                For i As Integer = 0 To m_BarCodesArray.Length - 1
                    If m_BarCodesArray(i).StartsWith(Exa.OBERON.Shared.Features.BarCodeGenerator.C_BarCodeEvidence_Prefix_StockCards) Then
                        m_Index = i
                        Exit For
                    End If
                Next

                If m_Index = -1 Then
                    '--- nie je taký kód

                    If String.IsNullOrWhiteSpace(Me.fro_txt_RPokladnice_CiarovyKod._Text) = False Then
                        Me.fro_txt_RPokladnice_CiarovyKod._Text &= ", "
                    End If

                    Me.fro_txt_RPokladnice_CiarovyKod._Text &= m_GeneratedCode

                Else
                    '--- je tak nahradiť
                    m_BarCodesArray(m_Index) = m_GeneratedCode

                    Me.fro_txt_RPokladnice_CiarovyKod._Text = Exa.Basic.Strings.Convert_From_Array(Me._DataRecord.BarCodes, Exa.Basic.Strings.enm_StringSeparator_UsingTypes.Behind, ", ", True)

                End If

            End If


ExitSub:

            If m_BarCodeGenerator IsNot Nothing Then
                m_BarCodeGenerator.Dispose()
                m_BarCodeGenerator = Nothing
            End If

        End Sub

#End Region


#Region " CONTROLS - OTHERS (Ceny) "

        Private Sub eh_TvorbaPredajnejCeny_ev_CheckedChanged(sender As System.Object, e As Exa.Application.Controls.Simple.S_OptionButton.BaseControls.S_OptionButton_Win32.cls_CheckedChangedEventArgs) Handles fro_rdb_TvorbaCeny_NavysenieVSume.ev_CheckedChanged, fro_rdb_TvorbaCeny_NavysenieVPercentach.ev_CheckedChanged, fro_rdb_TvorbaCeny_PevnaPredajnaCena.ev_CheckedChanged, fro_rdb_TvorbaCeny_ZlavaZDoporucenejCeny.ev_CheckedChanged
            On Error Resume Next

            If e.IsChangedByUser = True Then
                Me.z_PriceChangeType(u_PriceCalculation:=True)
            End If

        End Sub

        Private Sub eh_PrepocetCeny_Vzdy_ev_CheckedChanged(sender As System.Object, e As Exa.Application.Controls.Simple.S_OptionButton.BaseControls.S_OptionButton_Win32.cls_CheckedChangedEventArgs) Handles fro_rdb_PrepocetCeny_PytatSa.ev_CheckedChanged, fro_rdb_PrepocetCeny_Vzdy.ev_CheckedChanged, fro_rdb_PrepocetCeny_Nikdy.ev_CheckedChanged
            On Error Resume Next

            If e.IsChangedByUser = True Then
                If Me.fro_rdb_PrepocetCeny_Vzdy._Checked = True Then
                    Me.lc_UserValue_PricesCalculationType = StockCard.enm_Prices_SellCalculationMode.Always
                ElseIf Me.fro_rdb_PrepocetCeny_PytatSa._Checked = True Then
                    Me.lc_UserValue_PricesCalculationType = StockCard.enm_Prices_SellCalculationMode.Ask_Before
                Else
                    Me.lc_UserValue_PricesCalculationType = StockCard.enm_Prices_SellCalculationMode.Never
                End If
            End If

        End Sub

        Private Sub fro_cbo_PredajnaCena_Zadavanie_ev_SelectedIndex_Changed(sender As System.Object, e As System.EventArgs) Handles fro_cbo_PredajnaCena_Zadavanie.ev_SelectedIndex_Changed
            On Error Resume Next

            Me.z_SetControls_UnitsForPriceInput_Labels()

            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                            StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            'Ulož nastavenia vybratej MJ pre zadávanie ceny.
            If Me.IsHandleCreated = True AndAlso Me.fro_cbo_PredajnaCena_Zadavanie.ReadOnly = False Then
                Dim m_PriceInputType As enm_PriceInputTypes = CType(Me.fro_cbo_PredajnaCena_Zadavanie._Selected_Item.Value, enm_PriceInputTypes)
                Exa.Application.Environment.Settings_Controls._Write(
                                                                     "Forms.StockCards.frm_StockCard_NewEdit",
                                                                     "PriceInputType",
                                                                     m_PriceInputType)
            End If

        End Sub

        Private Sub fro_txt_PredajnaCena_Navysenie_ev_TextChanged_ByUser(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_PredajnaCena1_Navysenie.ev_TextChanged_ByUser, fro_txt_PredajnaCena2_Navysenie.ev_TextChanged_ByUser, fro_txt_PredajnaCena3_Navysenie.ev_TextChanged_ByUser, fro_txt_PredajnaCena4_Navysenie.ev_TextChanged_ByUser

            On Error Resume Next

            Dim m_TextBoxEx As Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32 = CType(sender, Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32)

            '--- Nastaví record podľa textových polí
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                         StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Me._DataRecord.Price_Calculation(CByte(m_TextBoxEx.Tag), StockCard.enm_Price_Calculation.Change_Markup, 0, True)

        End Sub

        Private Sub eh_PredajneCeny_BezDPH_ev_TextChanged_ByUser(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_PredajnaCena1_BezDPH.ev_TextChanged_ByUser, fro_txt_PredajnaCena2_BezDPH.ev_TextChanged_ByUser, fro_txt_PredajnaCena3_BezDPH.ev_TextChanged_ByUser, fro_txt_PredajnaCena4_BezDPH.ev_TextChanged_ByUser

            On Error Resume Next

            Dim m_TextBoxEx As Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32 = CType(sender, Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32)

            '--- Nastaví record podľa textových polí
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                         StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Me._DataRecord.Price_Calculation(CByte(m_TextBoxEx.Tag), StockCard.enm_Price_Calculation.Change_Price_Without_VAT, 0, True)

        End Sub

        Private Sub eh_PredajneCeny_SDPHX_ev_TextChanged_ByUser(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_PredajnaCena1_SDPH.ev_TextChanged_ByUser,
                                                                                                                            fro_txt_PredajnaCena2_SDPH.ev_TextChanged_ByUser,
                                                                                                                            fro_txt_PredajnaCena3_SDPH.ev_TextChanged_ByUser,
                                                                                                                            fro_txt_PredajnaCena4_SDPH.ev_TextChanged_ByUser

            On Error Resume Next

            Dim m_TextBoxEx As Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32 = CType(sender, Exa.Application.Controls.Simple.S_TextBox.BaseControls.S_TextBoxEx_Win32)

            '--- Nastaví record podľa textových polí
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                         StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Me._DataRecord.Price_Calculation(CByte(m_TextBoxEx.Tag), StockCard.enm_Price_Calculation.Change_Price_With_VAT, 0, True)

        End Sub

        Private Sub eh_PredajnaCenaX_SDPH_ev_UserInputFinished(sender As Object, e As cls_UserInputFinishedEventArgs) Handles fro_txt_PredajnaCena1_SDPH.ev_UserInputFinished,
                                                                                                                                   fro_txt_PredajnaCena2_SDPH.ev_UserInputFinished,
                                                                                                                                   fro_txt_PredajnaCena3_SDPH.ev_UserInputFinished,
                                                                                                                                   fro_txt_PredajnaCena4_SDPH.ev_UserInputFinished

            Try
                '--- Dokončenie zadávania - pri zadávaní mohla byť napr. cena zaokrúhlená, došlo aj k prepočítaniu, ale pole sa nenastavilo (lebo by sa nedalo zadavať)
                '--- Tu opätovne zobraziť prípadnú prepočítaná cenu

                '--- Nastaví polia podľa recordu
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                             StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Catch ex As Exception
            End Try

        End Sub

        Private Sub eh_PredajnaCenaX_BezDPH_ev_UserInputFinished(sender As Object, e As cls_UserInputFinishedEventArgs) Handles fro_txt_PredajnaCena1_BezDPH.ev_UserInputFinished,
                                                                                                                                   fro_txt_PredajnaCena2_BezDPH.ev_UserInputFinished,
                                                                                                                                   fro_txt_PredajnaCena3_BezDPH.ev_UserInputFinished,
                                                                                                                                   fro_txt_PredajnaCena4_BezDPH.ev_UserInputFinished

            Try
                '--- Dokončenie zadávania - pri zadávaní mohla byť napr. cena zaokrúhlená, došlo aj k prepočítaniu, ale pole sa nenastavilo (lebo by sa nedalo zadavať)
                '--- Tu opätovne zobraziť prípadnú prepočítaná cenu

                '--- Nastaví polia podľa recordu
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.GetFromProperty,
                                                             StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Catch ex As Exception
            End Try

        End Sub


        Private Sub fro_txt_PredajnaCena_Doporucena_ev_TextChanged_ByUser(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_PredajnaCena_Doporucena.ev_TextChanged_ByUser

            On Error Resume Next

            '-- VALIDATION --
            If Me.IsHandleCreated = False Then Exit Sub

            '--- Nastaví record podľa textových polí
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                         StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Price_WithVAT_Recommended, 0, True)

        End Sub


        Private Sub fro_cbo_PredajnaCena_Zaokruhlenie_ev_UserInputFinished(sender As Object, e As Application.Controls.cls_UserInputFinishedEventArgs) Handles fro_cbo_PredajnaCena_Zaokruhlenie.ev_UserInputFinished
            On Error Resume Next

            '--- Nastaví record podľa textových polí
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                         StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

            Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Round, 0, True)

        End Sub


        Private Sub fro_chk_IgnoreExtendedSalePricing_ev_CheckedChanged_ByUser(sender As Object, e As EventArgs) Handles fro_chk_IgnoreExtendedSalePricing.ev_CheckedChanged_ByUser

            On Error Resume Next
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.IgnoreExtendedSalePricing)


        End Sub


        Private Sub fro_btn_ExtendedPrices_ev_Click(sender As Object, e As EventArgs) Handles fro_btn_ExtendedPrices.ev_Click

            On Error Resume Next

            If Me._DataRecord.ExtendedSalePricing_GeneratePrices Is Nothing Then
                Exa.Application.MsgBox("Formulár so zoznamom ďalších predajných cien rozšírenej cenotvorby nie je možné zobraziť, formulár skladovej karty ho v tomto režime zobrazenia nepodporuje.", MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If

            Dim myEx As EXC.ExaException
            Dim frm_ShowItemRules As Exa.OBERON.Stock.Forms.ExtendedSalePricing.frm_ShowItemRules = Nothing

            Exa.Application.Cursor_Wait(Me)

            '--- Načítať pravidlá rozšírenej cenotvorby k položke dokladu ---
            Dim Arg As New Exa.OBERON.Stock.ExtendedSalePricing.GeneratePrices.cls_GetDocumentItemRuleArg
            Arg.StockCardBaseInfo.FromStockCard(Me._DataRecord)
            Arg.Amount = 0  '--- Množstvo sa nebude posudzovať ----
            Arg.Barcodes = Me._DataRecord.BarCodes  '--- Uviesť aj čiarový kód - aby zobrazilo pravidlá na test čiarového kódu

            '--- Zobraziť formulár ---
            frm_ShowItemRules = New Exa.OBERON.Stock.Forms.ExtendedSalePricing.frm_ShowItemRules(lc_ObjectsOBERON_Stock,
                                                                                                 Me._DataRecord.ExtendedSalePricing_GeneratePrices,
                                                                                                 Me._DataRecord,
                                                                                                 False)
            myEx = frm_ShowItemRules._LoadData(Arg)
            If myEx.Result = False Then
                '--- ERR ---
                If myEx.ErrNumber = EXC.enm_ErrNumbers.ReturnValueIsEmpty Then
                    Exa.Application.MsgBox(myEx.GetFullDescription, MsgBoxStyle.Exclamation Or MsgBoxStyle.OkOnly)
                Else
                    Exa.Application.MsgBox("Pri zobrazení pravidiel rozšírenej cenotvorby sa vyskytol problém.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                End If
                GoTo ExitSub_ExtendedSalePricing
            End If

            Exa.Application.ShowWindow(frm_ShowItemRules, True, Me)

ExitSub_ExtendedSalePricing:

            If frm_ShowItemRules IsNot Nothing Then
                frm_ShowItemRules.Dispose()
                frm_ShowItemRules = Nothing
            End If

            Exa.Application.Cursor_Default(Me)


        End Sub



        Private Sub fro_txt_ZlavyPredaj_MaximalnaZlava_ev_UserInputFinished(sender As Object, e As Application.Controls.cls_UserInputFinishedEventArgs) Handles fro_txt_ZlavyPredaj_MaximalnaZlava.ev_UserInputFinished
            On Error Resume Next
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.Price_Discount_MaxPercento)


        End Sub


        Private Sub fro_rdb_ZlavyPredaj_Umoznit_ev_CheckedChanged(sender As Object, e As Application.Controls.Simple.S_OptionButton.BaseControls.S_OptionButton_Win32.cls_CheckedChangedEventArgs) Handles fro_rdb_ZlavyPredaj_Umoznit.ev_CheckedChanged
            On Error Resume Next

            If Me.fro_rdb_ZlavyPredaj_Umoznit._Checked = True Then
                Me.fro_txt_ZlavyPredaj_MaximalnaZlava.Enabled = True
            End If

        End Sub

        Private Sub fro_rdb_ZlavyPredaj_Pytatsa_ev_CheckedChanged(sender As Object, e As Application.Controls.Simple.S_OptionButton.BaseControls.S_OptionButton_Win32.cls_CheckedChangedEventArgs) Handles fro_rdb_ZlavyPredaj_Pytatsa.ev_CheckedChanged
            On Error Resume Next

            If Me.fro_rdb_ZlavyPredaj_Pytatsa._Checked = True Then
                Me.fro_txt_ZlavyPredaj_MaximalnaZlava.Enabled = True
            End If

        End Sub

        Private Sub fro_rdb_ZlavyPredaj_Neumoznit_ev_CheckedChanged(sender As Object, e As Application.Controls.Simple.S_OptionButton.BaseControls.S_OptionButton_Win32.cls_CheckedChangedEventArgs) Handles fro_rdb_ZlavyPredaj_Neumoznit.ev_CheckedChanged
            On Error Resume Next

            If Me.fro_rdb_ZlavyPredaj_Neumoznit._Checked = True Then
                Me.fro_txt_ZlavyPredaj_MaximalnaZlava.Enabled = False
            End If

        End Sub

        Private Sub fro_rdb_ZlavyPredaj_CONTROLS_ev_CheckedChanged_ByUser(sender As Object, e As EventArgs) Handles fro_rdb_ZlavyPredaj_Umoznit.ev_CheckedChanged_ByUser,
                                                                                                                    fro_rdb_ZlavyPredaj_Pytatsa.ev_CheckedChanged_ByUser,
                                                                                                                    fro_rdb_ZlavyPredaj_Neumoznit.ev_CheckedChanged_ByUser

            On Error Resume Next
            Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                          StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.Price_Discount_Type)


        End Sub


#End Region


#Region " CONTROLS - OTHERS (Doplňujúce údaje) "

        Private Sub fro_cbo_DoplnUdaje_VyrobneSerioveCisla_ev_DropDown_ItemSelected(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_DoplnUdaje_SerialNumbersMode.ev_DropDown_ItemSelected

            On Error Resume Next

            Me.z_SetControls_SerialNumbers()

        End Sub

        Private Sub fro_txt_Uctovanie_Predkontacia_Cislo_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_Uctovanie_Predkontacia_Cislo.ev_ButtonList_Click

            On Error Resume Next

            If lc_ObjectsOBERON_Stock._AppConfiguration.Common.OBERONDatabaseType = ApplicationEnvironment.Common.AppConstants.enm_OBERON_DatabaseType.UCJ Then
                '--- UCJ ---

                '--- Zobrazenie formu.
                Dim frm_AccountCoding_List As New Exa.OBERON.Shared.Forms.AccSingle.AccountCodings.frm_AccountCoding_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select,
                                                                                                                          lc_ObjectsOBERON_Stock._ObjectsOBERON,
                                                                                                                          lc_ObjectsOBERON_Stock._ObjectsOBERON.AccSingle.AccountCoding_List_Form,
                                                                                                                          CInt(Me.fro_txt_Uctovanie_Predkontacia_Cislo._Value))

                If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                    frm_AccountCoding_List.Dispose()
                    frm_AccountCoding_List = Nothing
                    Exit Sub
                End If

                '--- LoadData --
                Dim myEx As EXC.ExaException
                myEx = frm_AccountCoding_List._LoadData()
                If myEx.Result = False Then
                    '--- ERR --
                    Exa.Application.MsgBox("Chyba pri načítaní údajov.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)

                Else
                    '--- OK --
                    Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                    m_DialogResult = Exa.Application.ShowWindow(frm_AccountCoding_List, True, Me)

                    If m_DialogResult = Windows.Forms.DialogResult.OK Then
                        Me.fro_txt_Uctovanie_Predkontacia_Cislo._Text = CStr(frm_AccountCoding_List._SelectedRow_AccountCoding)
                    End If
                End If

                If frm_AccountCoding_List IsNot Nothing Then frm_AccountCoding_List.Dispose()
                frm_AccountCoding_List = Nothing

            Else
                '--- UCP ---

                '--- Zobrazenie formu.
                Dim frm_AccountCoding_List As New Exa.OBERON.Shared.Forms.AccDouble.AccountCodings.frm_AccountCoding_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select,
                                                                                                                          lc_ObjectsOBERON_Stock._ObjectsOBERON,
                                                                                                                          lc_ObjectsOBERON_Stock._ObjectsOBERON.AccDouble.AccountCoding_List_Form,
                                                                                                                          CInt(Me.fro_txt_Uctovanie_Predkontacia_Cislo._Value))

                If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                    frm_AccountCoding_List.Dispose()
                    frm_AccountCoding_List = Nothing
                    Exit Sub
                End If

                '--- LoadData --
                Dim myEx As EXC.ExaException
                myEx = frm_AccountCoding_List._LoadData()
                If myEx.Result = False Then
                    '--- ERR --
                    Exa.Application.MsgBox("Chyba pri načítaní údajov.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)

                Else
                    '--- OK --
                    Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

                    m_DialogResult = Exa.Application.ShowWindow(frm_AccountCoding_List, True, Me)

                    If frm_AccountCoding_List._AccountCoding.Type <> [Shared].AccDouble.AccountCodings.AccountCoding.enm_Type.Stocks Then
                        Exa.Application.MsgBox("Na skladovej karte je možné použiť len predkontáciu typu 'Skladová predkontácia'.", MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                    Else
                        Me.fro_txt_Uctovanie_Predkontacia_Cislo._Text = CStr(frm_AccountCoding_List._SelectedRow_AccountCoding)
                    End If

                    z_SetControls_UctovaniePredkontaciaText()

                End If

                If frm_AccountCoding_List IsNot Nothing Then frm_AccountCoding_List.Dispose()
                frm_AccountCoding_List = Nothing

            End If


        End Sub

        Private Sub fro_txt_Uctovanie_Predkontacia_Cislo_ev_UserInputFinished(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_Uctovanie_Predkontacia_Cislo.ev_UserInputFinished

            On Error Resume Next
            z_SetControls_UctovaniePredkontaciaText()

        End Sub


        Private Sub fro_txt_CustomsTariffCode_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_CustomsTariffCode.ev_ButtonList_Click

            On Error Resume Next

            'Zobrazenie formu.
            Dim frm_CustomsTariff_List As New Exa.OBERON.Shared.Forms.Stock.CustomsTariffs.frmW_CustomsTariff_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select, Me.lc_ObjectsOBERON_Stock._ObjectsOBERON, CStr(Me.fro_txt_CustomsTariffCode._Value))

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then
                frm_CustomsTariff_List.Dispose()
                frm_CustomsTariff_List = Nothing
                Exit Sub
            End If

            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

            m_DialogResult = Exa.Application.ShowWindow(frm_CustomsTariff_List, True, Me)

            If m_DialogResult = Windows.Forms.DialogResult.OK Then
                Me.fro_txt_CustomsTariffCode._Text = CStr(frm_CustomsTariff_List._SelectedRow_CustomsTariffCode)
                z_SetControls_CustomsTariffCodeText()
            End If

            If frm_CustomsTariff_List IsNot Nothing Then
                frm_CustomsTariff_List.Dispose()
                frm_CustomsTariff_List = Nothing
            End If


        End Sub

        Private Sub fro_txt_CustomsTariffCode_ev_UserInputFinished(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_CustomsTariffCode.ev_UserInputFinished

            On Error Resume Next
            z_SetControls_CustomsTariffCodeText()

        End Sub


#End Region


#Region " CONTROLS - OTHERS (Internetový obchod) "

        Private Sub fro_txt_IObchod_Nazov_ev_ButtonList_Click(sender As Object, e As Application.Controls.cls_ButtonListEventArgs) Handles fro_txt_IObchod_Nazov.ev_ButtonList_Click
            On Error Resume Next

            Me.fro_txt_IObchod_Nazov._Text = Me.fro_txt_Nazov.TextSlovak

        End Sub

        Private Sub fro_cbo_IObchod_Vyrobca_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_IObchod_Vyrobca.ev_NeedLoadItems,
                                                                                                                        fro_cbo_IObchod_Web.ev_NeedLoadItems

            On Error Resume Next

            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_FieldData As List(Of String) = Nothing

            'Načítaj už nastavené SK doby dodania

            Dim m_TableName$ = String.Format("{0}{1}", StockCard.CONST_TableName_StockCards, Me._DataRecord._Stock.DatabaseTable_Number)
            Dim m_ComboBox As Exa.Application.Controls.Simple.S_ComboBox.BaseControls.S_ComboBoxEx_Win32 = TryCast(sender, Exa.Application.Controls.Simple.S_ComboBox.BaseControls.S_ComboBoxEx_Win32)

            m_ExaException = Me._DataRecord._RecordSettings.CommonData.GetFieldData(Of String)(m_TableName$, m_ComboBox.DatabaseFieldSettings.Name, True, m_FieldData, Nothing, SortOrder.Ascending)

            If m_ExaException.Result = True Then
                With m_ComboBox._Items
                    .Update_Begin()
                    .Clear()
                    For Each e_FieldData As String In m_FieldData
                        .Add(e_FieldData)
                    Next
                    .Update_End()
                End With
            End If

        End Sub

        Private Sub fro_cbo_IObchod_DobaDodania_ev_NeedLoadItems(sender As Object, e As EventArgs) Handles fro_cbo_IObchod_DobaDodania_Skladom.ev_NeedLoadItems,
                                                                                                           fro_cbo_IObchod_DobaDodania_Nulove.ev_NeedLoadItems
            On Error Resume Next

            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_FieldData As List(Of String) = Nothing
            Dim m_ExistingValues = New List(Of String)

            ' Načítaj zoznam už nastavených dodaní na kartách.
            Dim m_TableName = $"{StockCard.CONST_TableName_StockCards}{Me._DataRecord._Stock.DatabaseTable_Number}"
            m_ExaException = Me._DataRecord._RecordSettings.CommonData.GetFieldData(Of String)(m_TableName$, fro_cbo_IObchod_DobaDodania_Skladom.DatabaseFieldSettings.Name, True, m_FieldData, Nothing, SortOrder.Ascending)

            '--- Špecialita - 2 hodnoty v jednom fielde
            If m_FieldData IsNot Nothing Then
                For i As Integer = 0 To m_FieldData.Count - 1
                    Dim tmp_2Values() As String
                    tmp_2Values = m_FieldData(i)?.Split("|"c)
                    Dim tmp_Value1 As String = Nothing
                    Dim tmp_Value2 As String = Nothing
                    If tmp_2Values Is Nothing OrElse tmp_2Values.Length = 1 Then
                        '--- Len jedna hodnota
                        tmp_Value1 = m_FieldData(i)
                    Else
                        '--- 2 Hodnoty
                        tmp_Value1 = tmp_2Values(0)
                        tmp_Value2 = tmp_2Values(1)
                    End If

                    '--- Pridať
                    If String.IsNullOrWhiteSpace(tmp_Value1) = False Then
                        If m_ExistingValues.Contains(tmp_Value1) = False Then
                            m_ExistingValues.Add(tmp_Value1)
                        End If
                    End If

                    '--- Pridať
                    If String.IsNullOrWhiteSpace(tmp_Value2) = False Then
                        If m_ExistingValues.Contains(tmp_Value2) = False Then
                            m_ExistingValues.Add(tmp_Value2)
                        End If
                    End If

                Next
            End If

            'Pridaj default hodnoty
            Dim m_Vaules = m_ExistingValues.Union({"1 deň", "2 dni", "3 dni", "4 dni", "5 dní", "6 dní", "1 týždeň", "10 dní", "2 týždne", "Tovar na objednávku", "Tovar na dopyt"}).
                                       OrderBy(Function(m) m).ToArray

            fro_cbo_IObchod_DobaDodania_Skladom._Items.AddRange(m_Vaules, u_ClearExistingItems:=True)
            fro_cbo_IObchod_DobaDodania_Nulove._Items.AddRange(m_Vaules, u_ClearExistingItems:=True)

            'Použi nastavený preklad
            fro_cbo_IObchod_DobaDodania_Skladom.TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_Card,
                                                 Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.EShop_DeliveryTerm,
                                                 Me._DataList.DataRecord.IDNum)

            'Použi nastavený preklad
            fro_cbo_IObchod_DobaDodania_Nulove.TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_Card,
                                                 Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.EShop_DeliveryTermOnZeroAmount,
                                                 Me._DataList.DataRecord.IDNum)

        End Sub


        Private Sub fro_cbo_IObchod_DobaDodania_ev_DropDown_ItemSelected(sender As Object, e As EventArgs) Handles fro_cbo_IObchod_DobaDodania_Skladom.ev_DropDown_ItemSelected
            On Error Resume Next

            'Skopíruj preklady cudzích jazykov so zoznamu skupín podľa vybranej položky.
            If Exa.Application.Language.AllowDataTranslation = True Then

                With Me.fro_cbo_IObchod_DobaDodania_Skladom.TextTranslations

                    Dim m_LangRec = .LanguageDataList._FindTranslationRecord(
                                    u_Evidence:= .Evidence,
                                    u_EvidenceField:= .EvidenceField,
                                    u_Language:=Nothing,
                                    u_TextSlovak:=fro_cbo_IObchod_DobaDodania_Skladom._Text)

                    If m_LangRec IsNot Nothing Then
                        .CopyValuesFrom(m_LangRec)
                    Else
                        .DeleteValue(.LanguageDataList)
                    End If
                End With

                Me.fro_cbo_IObchod_DobaDodania_Skladom.DataTranslateValueRefresh()

            End If

        End Sub


        Private Sub fro_cbo_IObchod_DobaDodania_Nulove_ev_DropDown_ItemSelected(sender As Object, e As EventArgs) Handles fro_cbo_IObchod_DobaDodania_Nulove.ev_DropDown_ItemSelected
            On Error Resume Next

            'Skopíruj preklady cudzích jazykov so zoznamu skupín podľa vybranej položky.
            If Exa.Application.Language.AllowDataTranslation = True Then

                With Me.fro_cbo_IObchod_DobaDodania_Nulove.TextTranslations

                    Dim m_LangRec = .LanguageDataList._FindTranslationRecord(
                                    u_Evidence:= .Evidence,
                                    u_EvidenceField:= .EvidenceField,
                                    u_Language:=Nothing,
                                    u_TextSlovak:=fro_cbo_IObchod_DobaDodania_Nulove._Text)

                    If m_LangRec IsNot Nothing Then
                        .CopyValuesFrom(m_LangRec)
                    Else
                        .DeleteValue(.LanguageDataList)
                    End If
                End With

                Me.fro_cbo_IObchod_DobaDodania_Nulove.DataTranslateValueRefresh()

            End If

        End Sub


#End Region


#Region " CONTROLS - OTHERS (Registračné pokladnice) "

        Private Sub fro_cbo_RegPokladnica_ItemFlags_ev_UserInputFinished(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_cbo_RegPokladnica_ItemFlags.ev_UserInputFinished

            On Error Resume Next

            '-- VALIDATION --
            If Me.IsHandleCreated = False Then Exit Sub


            'Aktualizovať príznaky OFF-Line registračných pokladníc.
            Me._DataRecord.CashRegister_Flags.Flags_Refresh()

        End Sub


        Private Sub fro_cbo_RPoklSFiskalom_TovarovaSkupina_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_RPoklSFiskalom_TovarovaSkupina.ev_ButtonList_Click

            On Error Resume Next

            '-- SHOW SIMPLE LIST --
            ': Inicializácia zoznamu, údaje budú načítané automaticky v konštruktore formu
            Dim m_StockCard_ComodityGroup_List As New Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_ComodityGroup_List(Me.lc_AppConfiguration)

            ': Zobra okno ktoré umožňuje editovanie jednoduchého zoznamu položiek
            Dim f_SimpleList As New Exa.Application.Forms.Data.frm_DataList_Simple(m_StockCard_ComodityGroup_List)

            f_SimpleList._Selected_ItemText = Me.fro_cbo_RPoklSFiskalom_TovarovaSkupina._Text

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then GoTo g_ExitSub

            f_SimpleList._ShowRowReorder = True

            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

            m_DialogResult = Exa.Application.ShowWindow(f_SimpleList, True, Me)

            ': Aktualizovanie zoznamu položiek 
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_RPoklSFiskalom_TovarovaSkupina._Items.AddRange(m_StockCard_ComodityGroup_List, False)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu tovarových skupín.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Else
                If m_DialogResult = Windows.Forms.DialogResult.OK Then
                    Me.fro_cbo_RPoklSFiskalom_TovarovaSkupina._Text = f_SimpleList._Selected_ItemText
                End If
            End If



g_ExitSub:

            If m_StockCard_ComodityGroup_List IsNot Nothing Then m_StockCard_ComodityGroup_List.Dispose()
            m_StockCard_ComodityGroup_List = Nothing

            If f_SimpleList IsNot Nothing Then f_SimpleList.Dispose()
            f_SimpleList = Nothing

        End Sub

        Private Sub fro_cbo_RPoklSFiskalom_TovarovaSkupina_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_RPoklSFiskalom_TovarovaSkupina.ev_NeedLoadItems

            On Error Resume Next

            'Inicializácia zoznamu, údaje budú načítané automaticky v metóde 'AddRange'
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_StockCard_ComodityGroup_List As New Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_ComodityGroup_List(Me.lc_AppConfiguration)

            m_ExaException = Me.fro_cbo_RPoklSFiskalom_TovarovaSkupina._Items.AddRange(m_StockCard_ComodityGroup_List, True)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu tovarových skupín.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End If

            If m_StockCard_ComodityGroup_List IsNot Nothing Then m_StockCard_ComodityGroup_List.Dispose()
            m_StockCard_ComodityGroup_List = Nothing

        End Sub

        Private Sub fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici_ev_CheckedChanged(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici.ev_CheckedChanged
            On Error Resume Next

            'Nastav nezadaný kód položky podľa čísla karty.
            Me.z_SetCashregisterItemFromItem()

        End Sub

        Private Sub fro_txt_RPoklSFiskalom_KodPolozky_ev_GotFocus(sender As Object, e As EventArgs) Handles fro_txt_RPoklSFiskalom_KodPolozky.ev_GotFocus
            On Error Resume Next

            'Nastav nezadaný kód položky podľa čísla karty.
            Me.z_SetCashregisterItemFromItem()

        End Sub

        Private Sub fro_cbo_RegPokladnica_CleneniePoloziek_Skupina_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_RegPokladnica_CashRegisterGroup.ev_ButtonList_Click

            On Error Resume Next

            '-- SHOW FOOD MENU GROP LIST WINDOW --
            ': Zobraz okno ktoré umožňuje editovanie zoznamu skupín v jedálnom lístku
            Dim f_StockCard_FoodMenuGroup_List As New Catalog.frm_StockCard_CashRegisterGroup_List(Me.lc_AppConfiguration, Me.fro_cbo_RegPokladnica_CashRegisterGroup.TextSlovak)

            If Err.Number = Exa.Basic.Exceptions.enm_ErrNumbers.FormConstructorError Then GoTo g_ExitSub

            Dim m_DialogResult As DialogResult = Windows.Forms.DialogResult.None

            m_DialogResult = Exa.Application.ShowWindow(f_StockCard_FoodMenuGroup_List, True, Me)

            ': Aktualizovanie zoznamu položiek 
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            m_ExaException = Me.fro_cbo_RegPokladnica_CashRegisterGroup._Items.AddRange(f_StockCard_FoodMenuGroup_List._DataList, False)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu skupín v pokladnici.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            Else
                If m_DialogResult = Windows.Forms.DialogResult.OK Then
                    Me.fro_cbo_RegPokladnica_CashRegisterGroup.TextSlovak = f_StockCard_FoodMenuGroup_List._Selected_ItemText

                    'Skopírovanie prekladov z číselníka skupín do prekladov skupinu na skladovej karte.
                    If Exa.Application.Language.AllowDataTranslation = True Then
                        With Me.fro_cbo_RegPokladnica_CashRegisterGroup
                            .TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_FoodMenuGroup,
                                                         Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.Name,
                                                         f_StockCard_FoodMenuGroup_List._Selected_RowID)
                            .DataTranslateValueRefresh()
                        End With
                    End If

                End If
            End If

g_ExitSub:

            If f_StockCard_FoodMenuGroup_List IsNot Nothing Then f_StockCard_FoodMenuGroup_List.Dispose()
            f_StockCard_FoodMenuGroup_List = Nothing

        End Sub

        Private Sub fro_cbo_RegPokladnica_CleneniePoloziek_Skupina_ev_DropDown_ItemSelected(sender As Object, e As EventArgs) Handles fro_cbo_RegPokladnica_CashRegisterGroup.ev_DropDown_ItemSelected

            On Error Resume Next

            'Skopíruj preklady cudzích jazykov so zoznamu skupín podľa vybranej položky.
            If Exa.Application.Language.AllowDataTranslation = True Then
                Dim m_DataList_RowID As Long = Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_CashRegisterGroup_List.GetRowID(Me._DataList._ObjectsOBERON_Stock._AppConfiguration._AppObjects._CommonData, Me.fro_cbo_RegPokladnica_CashRegisterGroup.TextSlovak)

                With Me.fro_cbo_RegPokladnica_CashRegisterGroup
                    .TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_FoodMenuGroup,
                                                 Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.Name,
                                                 m_DataList_RowID)
                    .DataTranslateValueRefresh()
                End With
            End If

        End Sub

        Private Sub fro_cbo_RegPokladnica_CleneniePoloziek_Skupina_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_RegPokladnica_CashRegisterGroup.ev_NeedLoadItems

            On Error Resume Next

            'Inicializácia zoznamu, údaje budú načítané automaticky v metóde 'AddRange'
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_StockCard_FoodMenuGroup_List As New Exa.OBERON.Shared.Stock.StockCards.Catalog.StockCard_CashRegisterGroup_List(Me.lc_AppConfiguration)

            m_ExaException = Me.fro_cbo_RegPokladnica_CashRegisterGroup._Items.AddRange(m_StockCard_FoodMenuGroup_List, True)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu skupín v pokladnici.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End If

            If m_StockCard_FoodMenuGroup_List IsNot Nothing Then m_StockCard_FoodMenuGroup_List.Dispose()
            m_StockCard_FoodMenuGroup_List = Nothing

        End Sub

        Private Sub fro_txt_RPokladnica_NazovPolozky_ev_ButtonList_Click(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_txt_RPokladnica_NazovPolozky.ev_ButtonList_Click

            On Error Resume Next

            fro_txt_RPokladnica_NazovPolozky.TextSlovak = fro_txt_Nazov.TextSlovak

            'Skopírovanie prekladov z názvu skladovej karty.
            If Exa.Application.Language.AllowDataTranslation = True Then
                With Me.fro_txt_RPokladnica_NazovPolozky
                    .TextTranslations.CopyValues(Exa.OBERON.Basic.Common.LanguageDataTranslation.Evidence.Stock_Card,
                                                 Exa.OBERON.Basic.Common.LanguageDataTranslation.EvidenceField.Name,
                                                 Me._DataRecord.IDNum)
                    .DataTranslateValueRefresh()
                End With
            End If

        End Sub

        Private Sub fro_cbo_RPOffline_CisloPLU_ev_NeedLoadItems(ByVal sender As Object, ByVal e As System.EventArgs) Handles fro_cbo_RPOffline_CisloPLU.ev_NeedLoadItems

            On Error Resume Next

            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_PLU_Max As Integer = 100 'Default keby nebola v systéme žiadna pokladnica definovaná


            'Nájdi zariadenie z najvyšším počtom PLU položiek
            Dim m_Device As Exa.OBERON.Devices.Base.Device = Nothing

            For Each eRow As Data.DataRow In Me.lc_DeviceEngine.DeviceList.Object_Table.DatabaseTable_Data.Rows
                m_Device = Me.lc_DeviceEngine.DeviceList.DataRecord(eRow, True)

                If m_Device Is Nothing Then
                    Continue For
                End If

                If m_Device.Device_Type = Devices.enm_Devices_Type.CashRegister Then
                    If m_PLU_Max < m_Device.Communication.CashRegister_PLU_Max Then
                        m_PLU_Max = m_Device.Communication.CashRegister_PLU_Max
                    End If
                End If
            Next

            If m_Device IsNot Nothing Then m_Device.Dispose()
            m_Device = Nothing


            '--- Načítanie len aktívnych kariet a takých ktoré majú zadané PLU
            Dim m_PLU_Reserved() As Integer = Nothing
            Dim tmp_DataTable As System.Data.DataTable = Nothing
            Dim m_SQLSelect As String = "SELECT RPPLU AS PLU FROM " & StockCard.CONST_TableName_StockCards & Me._DataRecord._Stock.DatabaseTable_Number & " WHERE RPPLU > 0 AND (Disabled <> 1 OR Disabled IS NULL)"

            m_ExaException = Me._DataRecord._AppConfiguration._AppObjects._CommonData.ExecuteQuery(m_SQLSelect, tmp_DataTable)
            If m_ExaException.Result = False Then
                Exit Sub
            End If

            m_PLU_Reserved = New Integer() {}

            For Each e_Row As DataRow In tmp_DataTable.Rows
                ReDim Preserve m_PLU_Reserved(m_PLU_Reserved.Length)
                m_PLU_Reserved(m_PLU_Reserved.Length - 1) = CInt(Exa.Database.ConvertFunctions.ReplaceDBNull(e_Row.Item("PLU"), 0))
                If Err.Number <> 0 Then
                    Err.Clear()
                End If
            Next

            If tmp_DataTable IsNot Nothing Then tmp_DataTable.Dispose()
            tmp_DataTable = Nothing


            'Naplnenie ComboBox-u z ktorého je možné vyberať PLU čísla
            With Me.fro_cbo_RPOffline_CisloPLU._Items
                .Update_Begin()
                .Clear()

                For i As Integer = 1 To m_PLU_Max
                    'Len ak PLU číslo nie je už použité na inej skladovej karte
                    If Array.IndexOf(m_PLU_Reserved, i) > -1 Then
                        '--- Našlo sa PLU
                        Continue For
                    End If

                    .Add(CStr(i))
                Next

                'Pridanie položky z tejto karty, 
                'pretože pri vyčítaní použitých PLU sa nevynecháva aktuálna karta (ak je v stave edit a mala nastavené plu)
                If Me._DataRecord.CashRegister_Flags.PLU_Number > 0 AndAlso Array.IndexOf(m_PLU_Reserved, Me._DataRecord.CashRegister_Flags.PLU_Number) < 0 Then
                    .Add(CStr(Me._DataRecord.CashRegister_Flags.PLU_Number))
                End If

                .Update_End()
            End With

        End Sub

        Private Sub fro_cbo_RPOffline_CisloPLU_ev_TextChanged_ByUser(sender As Object, e As System.EventArgs) Handles fro_cbo_RPOffline_CisloPLU.ev_TextChanged_ByUser

            On Error Resume Next

            'Aktualizovať príznaky OFF-Line registračných pokladníc.
            Me._DataRecord.CashRegister_Flags.Flags_Refresh()

        End Sub

        Private Sub fro_cbo_AutomatickaTlacEtikety_ev_NeedLoadItems(sender As Object, e As EventArgs) Handles fro_cbo_AutomatickaTlacEtikety.ev_NeedLoadItems
            On Error Resume Next

            'Načítaj zoznam tlačových výstupov pre tlač štítkov na registračnej pokladnici.
            Me.z_SetControls_LoadPrinterReports_CashRegisterTags()

        End Sub

        Private Sub fro_cbo_AutomatickaTlacEtikety_ev_ButtonList_Click(sender As Object, e As Application.Controls.cls_ButtonListEventArgs) Handles fro_cbo_AutomatickaTlacEtikety.ev_ButtonList_Click
            On Error Resume Next

            '-- SHOW PRINT DIALOG --
            ': Zobraz okno pre úpravu tlačových výstupov štítkov skladovej karty.
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing
            Dim m_StockCard_Reports_CashRegisterTags As New Exa.OBERON.Stock.StockCards.Reports.StockCard_Reports_CashRegisterTags(Me.lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)
            Dim m_ModuleBooksAndReports As New Exa.Application.Reports.Report_List.cls_ModuleBookWithReportsIDCollection

            With m_ModuleBooksAndReports
                .Add(Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_Report_Module_Stock.StockCard_CashRegister_Tags,
                        Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_ReportID_StockCards_CashRegister_Tags.Etikety_1ksNaList,
                        Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_ReportID_StockCards_CashRegister_Tags.Etikety_Landscape_1ksNaList)
            End With

            Dim m_SelectedRow_IDNum& = Me._DataRecord.IDNum
            Dim m_CashRegisterReportItemList As New List(Of Exa.OBERON.Stock.StockCards.Reports.StockCard_Reports_CashRegisterTags.cls_CashRegisterItem)

            m_CashRegisterReportItemList.Add(New Exa.OBERON.Stock.StockCards.Reports.StockCard_Reports_CashRegisterTags.cls_CashRegisterItem(Me._DataRecord, Nothing, "", Nothing, Nothing))

            'Nastav zdroj údajov etikety túto skladovú kartu.
            m_StockCard_Reports_CashRegisterTags._CashRegisterItemList = m_CashRegisterReportItemList

            m_ExaException = m_StockCard_Reports_CashRegisterTags.ShowPrintDialog(m_SelectedRow_IDNum&,
                                                                                    Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.Stock,
                                                                                    m_ModuleBooksAndReports,
                                                                                    New Drawing.Size(500, 350),
                                                                                    Me,
                                                                                    Windows.Forms.HelpNavigator.TopicId,
                                                                                    Exa.OBERON.ApplicationEnvironment.Common.AppConstants.Help_TopicID_PrinterDialog,
                                                                                    "CashRegisterTags",
                                                                                    Me.fro_cbo_AutomatickaTlacEtikety._Text)

            If m_ExaException.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu tlačových výstupov.", m_ExaException, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End If

            If m_StockCard_Reports_CashRegisterTags IsNot Nothing Then m_StockCard_Reports_CashRegisterTags.Dispose()
            m_StockCard_Reports_CashRegisterTags = Nothing

            'Znova načítať zoznam tlačových výstupov a vybrať položku podľa IDNum, pretože tlačový výstup mohol byť premenovaný.
            Dim m_SelIDNum& = CLng(Me.fro_cbo_AutomatickaTlacEtikety._Selected_Item.Value)

            Me.z_SetControls_LoadPrinterReports_CashRegisterTags()

            Me.fro_cbo_AutomatickaTlacEtikety._SelectItem(m_SelIDNum&, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

ExitFunction:

            m_CashRegisterReportItemList.Clear()
            m_CashRegisterReportItemList = Nothing

        End Sub


        Private Sub fro_txt_CookRecipe_Menu_SideDishCodes_ev_ButtonList_Click(sender As Object, e As cls_ButtonListEventArgs) Handles fro_txt_CookRecipe_Menu_SideDishCodes.ev_ButtonList_Click

            On Error Resume Next

            Dim myEx As EXC.ExaException

            Dim tmp_Form_StockCard_List As Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_List

            tmp_Form_StockCard_List = New Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_List(Application.Forms.Data.Factory.Form_DataList_Win32.enm_FormDataViewTypes.Select,
                                                                        Me.lc_ObjectsOBERON_Stock,
                                                                        Me.lc_DeviceEngine)

            tmp_Form_StockCard_List._AllowChange_Stock = True
            tmp_Form_StockCard_List._AllowSelect_AllStocks = True

            '--- Nastaviť zoznam dostupných skladov s ktorým môže formulár pracovať ---	
            myEx = tmp_Form_StockCard_List._Stocks_Available_SET(u_LoadExternalStocks:=False)
            If myEx.Result = False Then
                Exa.Application.MsgBox(Exa.Application.TranslateText("Chyba pri nastavení skladu v zozname skladových kariet s ktorým sa má pracovať, nie je možné pokračovať."), myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitFunction
            End If

            '--- Mapovanie udalostí
            AddHandler tmp_Form_StockCard_List.ev_Button_OK_Click, AddressOf Me.eh_StockCard_Item_Select_ev_Button_OK_Click


            Dim m_StockInfoValues As New Exa.OBERON.Shared.Stock.Stocks.Stock_List.stc_Stock_Or_StockGroup_Item()
            With m_StockInfoValues
                .Flag = Exa.OBERON.Shared.Stock.Stocks.Stock_List.stc_Stock_Or_StockGroup_Item.enum_FlagItem.Stock
                .Name = String.Empty  '--- Vybere default sklad alebo naposledy použitý
            End With


            '--- Načítať data - inteligentne, nie vždy načítanie ide 
            myEx = tmp_Form_StockCard_List._LoadData(m_StockInfoValues, OBERON.Stock.StockCards.StockCard_List.enum_LoadData_Option.Only_CashRegister_Cards,
                                                            False,
                                                            u_PriceLevel:=0)
            If myEx.Result = False Then
                Exa.Application.MsgBox("Chyba pri načítaní zoznamu skladových kariet, nie je možné pokračovať.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If

            Exa.Application.ShowWindow(tmp_Form_StockCard_List, True, Me)


ExitFunction:

            If tmp_Form_StockCard_List IsNot Nothing Then
                RemoveHandler tmp_Form_StockCard_List.ev_Button_OK_Click, AddressOf Me.eh_StockCard_Item_Select_ev_Button_OK_Click
                tmp_Form_StockCard_List.Dispose()
                tmp_Form_StockCard_List = Nothing
            End If

        End Sub


        Private Sub fro_txt_CookRecipe_Menu_Specification_ev_ButtonList_Click(sender As Object, e As cls_ButtonListEventArgs) Handles fro_txt_CookRecipe_Menu_Specification.ev_ButtonList_Click

            On Error Resume Next

            Dim myEx As EXC.ExaException

            Dim frm_Notice_OrderKitchen_List As New Exa.OBERON.Shared.Forms.Stock.StockCards.frm_Notice_OrderKitchen_List(Me.lc_AppConfiguration, u_SelectedItem_Text:=String.Empty)

            Dim m_DialogResult As DialogResult = Exa.Application.ShowWindow(frm_Notice_OrderKitchen_List, True, Me)

            If m_DialogResult = Windows.Forms.DialogResult.OK Then
                '--- OK
                fro_txt_CookRecipe_Menu_Specification._Text = Exa.Basic.Strings.StringApendValue(fro_txt_CookRecipe_Menu_Specification._Text,
                                                                                                frm_Notice_OrderKitchen_List._SelectedItem_Text,
                                                                                                u_Separator:=", ",
                                                                                                u_IgnoreIfExists:=True)
            End If


ExitFunction:

            If frm_Notice_OrderKitchen_List IsNot Nothing Then
                frm_Notice_OrderKitchen_List.Dispose()
                frm_Notice_OrderKitchen_List = Nothing
            End If


        End Sub


        Private Sub eh_StockCard_Item_Select_ev_Button_OK_Click(ByVal u_Form_StockCard_List As Exa.OBERON.Stock.Forms.StockCards.frm_StockCard_List, ByRef urf_DialogResult As DialogResult)

            On Error Resume Next

            '--- NEW DATA RECORD (_ITEMS) - 'DataRecord' priprav na pridanie nového záznamu
            Dim m_ExaException As Exa.Basic.Exceptions.ExaException = Nothing

            If u_Form_StockCard_List._SelectedRow_StockCard_IDNum = 0 Then
                Exit Sub
            End If

            fro_txt_CookRecipe_Menu_SideDishCodes._Text = Exa.Basic.Strings.StringApendValue(fro_txt_CookRecipe_Menu_SideDishCodes._Text,
                                                                                             u_Form_StockCard_List._SelectedRow_StockCard_Code,
                                                                                             u_Separator:=", ",
                                                                                             u_IgnoreIfExists:=True)

            If u_Form_StockCard_List._SelectedRow_StockCard_Code = String.Empty Then
                Exa.Application.MsgBox(Exa.Application.TranslateTextEx("Skladová položka '{0}' nemá zadaný kód položky pre predaj na Pokladnici OBERON.", u_Form_StockCard_List._SelectedRow_StockCard_Code), MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                urf_DialogResult = Windows.Forms.DialogResult.Cancel
            Else
                urf_DialogResult = Windows.Forms.DialogResult.OK
            End If

        End Sub


#End Region


#Region " METHODS - PRIVATE "

        Private Sub z_SetControlsFileRepository()

            Try

                'Nastaviť tlačítku tučné písmo, ak záznam obsahuje nejaké pripojené dokumenty.
                If Me._DataRecord.FileRepositoryAttachments = True Then
                    Me.fro_btn_FileRepository.Font = New Drawing.Font(Me.fro_btn_FileRepository.Font, Drawing.FontStyle.Bold)
                Else
                    Me.fro_btn_FileRepository.Font = New Drawing.Font(Me.fro_btn_FileRepository.Font, Drawing.FontStyle.Regular)
                End If

            Catch ex As Exception
            End Try

        End Sub

        ''' <summary>
        ''' Nastaví tlačítko Sériové/Výrobné čísla podľa nastavení skladovej karty 'fro_cbo_DoplnUdaje_VyrobneSerioveCisla'.
        ''' </summary>
        Private Sub z_SetControls_SerialNumbers()

            On Error Resume Next

            Dim m_Mode As Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode = Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode.None

            m_Mode = CType(Me.fro_cbo_DoplnUdaje_SerialNumbersMode._Selected_Item.Value, Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode)

            If m_Mode = Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode.ProductionNumber Then
                Me.fro_btn_VyrobneCisla._Text = Exa.Application.TranslateText("Výrobné &čísla")
                Me.fro_btn_VyrobneCisla.Enabled = True
                Me.fro_btn_VyrobneCisla.Visible = True
                Me.M_Panel3.Visible = True

            ElseIf m_Mode = Exa.OBERON.Stock.SerialNumbers.SerialNumber.enm_StockCard_SerialNumbers_Mode.SerialNumber Then
                Me.fro_btn_VyrobneCisla._Text = Exa.Application.TranslateText("Sériové &čísla")
                Me.fro_btn_VyrobneCisla.Enabled = True
                Me.fro_btn_VyrobneCisla.Visible = True
                Me.M_Panel3.Visible = True

            Else
                Me.fro_btn_VyrobneCisla.Enabled = False
                Me.fro_btn_VyrobneCisla.Visible = False
                Me.M_Panel3.Visible = False

            End If

        End Sub

        ''' <summary>
        ''' Otestuje a nastaví varovanie pre test celkového množstva variantov a množstva na skladovej karte.
        ''' </summary>
        Private Sub z_SetControls_VariantsCheckAmountInfo()

            On Error Resume Next

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew _
                Or Me._DataRecord.Items_Variant Is Nothing _
                Or Me._DataRecord.Items_Variant.Count <= 0 Then
                '--- Nový záznam, alebo nie sú varianty ---
                Me.fro_lbl_VariantCheckAmountInfo.Visible = False

            Else
                '--- Nie nový záznam ---
                Dim tmp_AmountVariant As Decimal = Me._DataRecord.Items_Variant.GetAmountTotal
                If Me._DataRecord.Amount = tmp_AmountVariant Then
                    Me.fro_lbl_VariantCheckAmountInfo.Visible = False
                Else
                    Me.fro_lbl_VariantCheckAmountInfo._Text = Exa.Application.TranslateTextEx("Množstvo na skladovej karte:  {0}, množstvo vo variantoch:  {1}", Exa.Basic.Numerics.Format(Me._DataRecord.Amount, 3),
                                                                                                                                                                 Exa.Basic.Numerics.Format(tmp_AmountVariant, 3))
                    Me.fro_lbl_VariantCheckAmountInfo.Visible = True
                End If

            End If

        End Sub


        ''' <summary>
        ''' Povolí alebo zakáže combo Typ karty
        ''' </summary>
        Private Sub z_SetControls_StockCardType()

            On Error Resume Next

            Dim tmp_StockCardTypeEnabled As Boolean = True
            Dim tmp_IsExistsMovement As Boolean = True

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                '--- Nový záznam - skladová karta

                tmp_StockCardTypeEnabled = True
                tmp_IsExistsMovement = False

            Else
                '--- Oprava záznamu  

                '--- Test či je právo aktualizovať --
                Dim myEx As Exa.Basic.Exceptions.ExaException
                myEx = Me._DataRecord._Permission.GetPermissionActual(ApplicationEnvironment.enm_Permission_RecordAction.Save)
                If myEx.Result = False Then
                    '--- Nemá právo ---
                    tmp_StockCardTypeEnabled = False
                Else
                    '--- Má právo ---

                    '--- Test na existenciu pohybu                    
                    Me._DataRecord.StockMovements_Exists(tmp_IsExistsMovement)


                    '--- Typ karty - receptúry a výrobky
                    If tmp_IsExistsMovement = True _
                            And (Me._DataRecord.CardType = StockCard.enm_StockCardType.Simple _
                                Or Me._DataRecord.CardType = StockCard.enm_StockCardType.ReturnablePackaging) Then
                        '--- Jednoduchá karta alebo obal - tu umožniť zmeniť typ vždy medzi tými to dvomi

                        '--- Odstrániť z Comba položky, ktoré tam nesmú byť
                        Me.fro_cbo_TypKarty._Items.Remove(CStr(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Service), Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                        Me.fro_cbo_TypKarty._Items.Remove(CStr(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Collection), Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                        Me.fro_cbo_TypKarty._Items.Remove(CStr(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Product), Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                        Me.fro_cbo_TypKarty._Items.Remove(CStr(Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Recipe), Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                        tmp_StockCardTypeEnabled = True

                        GoTo EndFunction
                    End If


                    '--- Test na množstvo (pre istotu)
                    If Me._DataRecord.Amount <> 0 Then
                        tmp_StockCardTypeEnabled = False
                        GoTo EndFunction
                    End If

                    '--- Typ karty - receptúry a výrobky
                    If Me._DataRecord.CardType = StockCard.enm_StockCardType.Product _
                        Or Me._DataRecord.CardType = StockCard.enm_StockCardType.Recipe _
                        Or Me._DataRecord.CardType = StockCard.enm_StockCardType.Collection Then
                        '--- Sada, výrobok alebo receptúra
                        If Me._DataRecord.Items_Product.Object_Table.DatabaseTable_Data.Rows.Count <> 0 Then
                            '--- Už je zadaná aspoň jedna položka receptúry /výrobku /
                            tmp_StockCardTypeEnabled = False
                            GoTo EndFunction
                        End If
                    End If

                    '--- Test na existenciu sklad. pohybu
                    If tmp_IsExistsMovement = True Then
                        '--- Je pohyb
                        tmp_StockCardTypeEnabled = False
                        GoTo EndFunction
                    End If


                    '--- Povoliť typ karty
                    tmp_StockCardTypeEnabled = True
                End If

            End If

EndFunction:

            '--- Nastavenie  typu karty
            Me.fro_cbo_TypKarty.Enabled = tmp_StockCardTypeEnabled

            '--- Nastavenie zmeny obstarávacej a poslednej nákupnej ceny 
            If tmp_StockCardTypeEnabled = True Then
                '--- Umožniť meniť typ karty
                If tmp_IsExistsMovement = False Then
                    '--- Bez skladového pohybu - umožniť meniť obstar. cenu
                    Me.fro_txt_Cena_Obstaravacia.ReadOnly = False
                Else
                    '--- So skladovým pohybom - neumožniť meniť cenu
                    Me.fro_txt_Cena_Obstaravacia.ReadOnly = True
                End If

            Else
                '--- Neumožniť meniť typ karty

                '--- Neumožniť meniť cenu
                Me.fro_txt_Cena_Obstaravacia.ReadOnly = True

            End If

            If Me._DataRecord.CardType = Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Recipe _
                Or Me._DataRecord.CardType = Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Product _
                Or Me._DataRecord.CardType = Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Collection Then
                Me.fro_btn_Zlozenie.Enabled = True
            Else
                Me.fro_btn_Zlozenie.Enabled = False
            End If

            '--- Predajná cena
            Dim tmp_SelPriceReadOnly As Boolean = False
            If Me._DataRecord.CardType = Exa.OBERON.Stock.StockCards.StockCard.enm_StockCardType.Collection Then
                '--- Sada - tu sa predajné ceny nezadávajú
                tmp_SelPriceReadOnly = True

                Me.fro_txt_Cena_Obstaravacia.ReadOnly = tmp_SelPriceReadOnly
                Me.fro_txt_Cena_PoslednaNakupna.ReadOnly = tmp_SelPriceReadOnly

            End If

            Me.fro_txt_PredajnaCena1_Navysenie.ReadOnly = If(Me.fro_rdb_TvorbaCeny_PevnaPredajnaCena._Checked = True, True, tmp_SelPriceReadOnly)
            Me.fro_txt_PredajnaCena1_BezDPH.ReadOnly = tmp_SelPriceReadOnly
            Me.fro_txt_PredajnaCena1_SDPH.ReadOnly = tmp_SelPriceReadOnly

            Me.fro_txt_PredajnaCena2_Navysenie.ReadOnly = If(Me.fro_rdb_TvorbaCeny_PevnaPredajnaCena._Checked = True, True, tmp_SelPriceReadOnly)
            Me.fro_txt_PredajnaCena2_BezDPH.ReadOnly = tmp_SelPriceReadOnly
            Me.fro_txt_PredajnaCena2_SDPH.ReadOnly = tmp_SelPriceReadOnly

            Me.fro_txt_PredajnaCena3_Navysenie.ReadOnly = If(Me.fro_rdb_TvorbaCeny_PevnaPredajnaCena._Checked = True, True, tmp_SelPriceReadOnly)
            Me.fro_txt_PredajnaCena3_BezDPH.ReadOnly = tmp_SelPriceReadOnly
            Me.fro_txt_PredajnaCena3_SDPH.ReadOnly = tmp_SelPriceReadOnly

            Me.fro_txt_PredajnaCena4_Navysenie.ReadOnly = If(Me.fro_rdb_TvorbaCeny_PevnaPredajnaCena._Checked = True, True, tmp_SelPriceReadOnly)
            Me.fro_txt_PredajnaCena4_BezDPH.ReadOnly = tmp_SelPriceReadOnly
            Me.fro_txt_PredajnaCena4_SDPH.ReadOnly = tmp_SelPriceReadOnly

            Me.fro_txt_PredajnaCena_Doporucena.ReadOnly = tmp_SelPriceReadOnly

            If Me._DataRecord._AppConfiguration.Stock.Using_Firm_StockCard_Variants = True Then
                '--- Používajú sa varianty ---

                If Me._DataRecord.CardType = StockCard.enm_StockCardType.Simple Then
                    '--- Jednoduchá karta
                    fro_btn_Variants_New.Enabled = True
                    fro_btn_Variants_Edit.Enabled = True
                    fro_btn_Variants_Delete.Enabled = True

                Else
                    '--- Iné ako jednoduchá karta
                    fro_btn_Variants_New.Enabled = False
                    fro_btn_Variants_Edit.Enabled = False
                    fro_btn_Variants_Delete.Enabled = False
                End If

            End If



        End Sub



        ''' <summary>
        ''' Nastaví grid s alternatívnymi mernými jednotkami.
        ''' </summary>
        Private Sub z_SetControls_UnitOthers()

            On Error Resume Next
            Me._DataRecord.UnitOthers.PrepareForUse(Me._DataRecord, u_PriceLevel:=1)
            fro_dgv_UnitOthers._RowsCount = Me._DataRecord.UnitOthers.Count

            If Me._DataRecord.UnitOthers.Count <= 0 _
                And Me._DataRecord._AppConfiguration.Stock.Using_Firm_UnitOther = False Then
                '--- Počet MJ je nulový a zároveň firma nepoužíva alternatívne MJ
                fro_Panel_UnitOther.Visible = False
            Else
                fro_Panel_UnitOther.Visible = True
            End If


        End Sub



        ''' <summary>
        ''' Nastaví 'DataGrid' ktorý zobrazuje príznaky Off-Line registračných pokladníc.
        ''' </summary>
        Private Sub z_SetDataGrid_RPOffLine()

            On Error Resume Next

            '-- VALIDATION --
            If Me.lc_DeviceModelsList Is Nothing Then Exit Sub
            If Me.lc_DeviceModelsList.Count = 0 Then Exit Sub


            With Me.fro_dgv_RPOffline_PokladnicePriznaky.Items
                .Update_Begin()
                .Clear()
            End With


            'EURO 50TE Mini a EURO 50T Mini
            If Me.lc_DeviceModelsList.Contains(Devices.enm_CashRegister_Model.Elcom_EURO_50_TE_eKasa) = True Then

                Dim m_Row As New Exa.Application.Controls.Simple.S_DataGrid.DataGridItemsCollection.cls_DataGridItem_Row

                With m_Row.Values
                    .Add("PokladnicaName", "EURO 50 Mini")
                    .Add("Priznak1", Me._DataRecord.CashRegister_Flags.Flag_Euro50Mini)
                End With

                Me.fro_dgv_RPOffline_PokladnicePriznaky.Items.Add(m_Row)
            End If

            'EURO 150 Flexy
            If Me.lc_DeviceModelsList.Contains(Devices.enm_CashRegister_Model.Elcom_EURO_150_TE_eKasa) = True Then
                Dim m_Row As New Exa.Application.Controls.Simple.S_DataGrid.DataGridItemsCollection.cls_DataGridItem_Row

                With m_Row.Values
                    .Add("PokladnicaName", "EURO 150 Flexy")
                    .Add("Priznak1", Me._DataRecord.CashRegister_Flags.Flag_Euro150Flexy)
                End With

                Me.fro_dgv_RPOffline_PokladnicePriznaky.Items.Add(m_Row)
            End If

            Me.fro_dgv_RPOffline_PokladnicePriznaky.Items.Update_End()

        End Sub

        ''' <summary>
        ''' Nastaví ceny (hodnoty controlov) podľa objektu 'DataRecord', alebo opačne (podľa údajov objektu 'DataRecord' nastaví controly).
        ''' </summary>
        Private Sub z_SetPrices(ByVal u_Target As enm_PriceSetTargetTypes,
                                ByVal u_PriceInput As enm_PriceInputTypes,
                                Optional ByVal u_PriceCalculation As StockCard.enm_Price_Calculation = StockCard.enm_Price_Calculation.None_SetAll)
            On Error Resume Next

            Select Case u_Target
                Case enm_PriceSetTargetTypes.Controls

                    '°° SET CONTROLS °°
                    '
                    '--- Nastaviť controly podľa objektu 'DataRecord'.
                    With Me._DataRecord

                        '---------------------------------------------------------------------------------------------------------------------------------------------------
                        '--- Formátovanie predajných cien - podľa zaokrúhľovania (aby bola podpora aj čísla na 4 miesta a zároveň nemal každý 4 nuly - bude podľa potreby)
                        '---------------------------------------------------------------------------------------------------------------------------------------------------
                        Dim tmp_DecimalPrice As SByte = 3
                        tmp_DecimalPrice = .Price_RoundingDecimalPlaces
                        '--- Formátovať na potrebné miesta

                        If Me.fro_txt_PredajnaCena1_SDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice Then
                            Me.fro_txt_PredajnaCena1_SDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice
                        End If
                        If Me.fro_txt_PredajnaCena2_SDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice Then
                            Me.fro_txt_PredajnaCena2_SDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice
                        End If
                        If Me.fro_txt_PredajnaCena3_SDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice Then
                            Me.fro_txt_PredajnaCena3_SDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice
                        End If
                        If Me.fro_txt_PredajnaCena4_SDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice Then
                            Me.fro_txt_PredajnaCena4_SDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice
                        End If

                        Me.fro_txt_PredajnaCena1_SDPH.ValueSettings.Allow_Decimal_Number = CBool(Me.fro_txt_PredajnaCena1_SDPH.ValueSettings.Format_Number_Precision > 0)
                        Me.fro_txt_PredajnaCena2_SDPH.ValueSettings.Allow_Decimal_Number = CBool(Me.fro_txt_PredajnaCena2_SDPH.ValueSettings.Format_Number_Precision > 0)
                        Me.fro_txt_PredajnaCena3_SDPH.ValueSettings.Allow_Decimal_Number = CBool(Me.fro_txt_PredajnaCena3_SDPH.ValueSettings.Format_Number_Precision > 0)
                        Me.fro_txt_PredajnaCena4_SDPH.ValueSettings.Allow_Decimal_Number = CBool(Me.fro_txt_PredajnaCena4_SDPH.ValueSettings.Format_Number_Precision > 0)

                        Dim tmp_DecimalPrice_BezDPH As Byte
                        tmp_DecimalPrice_BezDPH = CByte(tmp_DecimalPrice + 1)
                        If tmp_DecimalPrice_BezDPH < 3 Then
                            '--- Suma Bez DPH musí byť minimálne vždy na 3 miesta (nemôže byť na celé EUR)
                            '--- Pri 2 miests DPH bez DPH musí byť 3 (2 je málo)
                            tmp_DecimalPrice_BezDPH = 3
                        End If

                        If Me.fro_txt_PredajnaCena1_BezDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice_BezDPH Then
                            Me.fro_txt_PredajnaCena1_BezDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice_BezDPH
                        End If
                        If Me.fro_txt_PredajnaCena2_BezDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice_BezDPH Then
                            Me.fro_txt_PredajnaCena2_BezDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice_BezDPH
                        End If
                        If Me.fro_txt_PredajnaCena3_BezDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice_BezDPH Then
                            Me.fro_txt_PredajnaCena3_BezDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice_BezDPH
                        End If
                        If Me.fro_txt_PredajnaCena4_BezDPH.ValueSettings.Format_Number_Precision <> tmp_DecimalPrice_BezDPH Then
                            Me.fro_txt_PredajnaCena4_BezDPH.ValueSettings.Format_Number_Precision = tmp_DecimalPrice_BezDPH
                        End If

                        '---------------------------------------------------------------------------------------------------------------------------------------------------
                        '--- Hodnoty ---
                        '---------------------------------------------------------------------------------------------------------------------------------------------------
                        If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Markup Then
                            'Ak je prepočet predajnej ceny nastavený na hodnotu 'Pevná predajná cena',
                            'hodnotu navýšenia nie je možné zmeniť 'ReadOnly = True', avšak zobraz informačnú hodnotu vypočítaného navýšenia.
                            If .Price_Type = StockCard.enm_Prices_Type.Fixed_Price Then

                                Dim tmp_PriceSupply As Decimal = Me._DataRecord.Price_Supply_Unit
                                If Me._DataRecord._AppConfiguration.Stock.StockCard_Price_CalculateFrom = ApplicationEnvironment.AppConfigurationObjects.AppConfiguration_Stock.enm_StockCard_Price_CalculateFrom.LastPurchase Then
                                    '--- Počítať z poslednej nákupnej ceny ---
                                    If Me._DataRecord.Price_LastPurchase <> 0 Then
                                        tmp_PriceSupply = Me._DataRecord.Price_LastPurchase
                                    End If
                                End If

                                Me.fro_txt_PredajnaCena1_Navysenie._Text = CStr(New Exa.OBERON.Shared.Common.Document.Item_Profit_Calculating() With
                                                                                    {.Price_Supply_WithoutVAT = tmp_PriceSupply,
                                                                                     .Price_WithoutVAT = Me._DataRecord.Price1_WithoutVAT}.Markup_Percento)

                                Me.fro_txt_PredajnaCena2_Navysenie._Text = CStr(New Exa.OBERON.Shared.Common.Document.Item_Profit_Calculating() With
                                                                                    {.Price_Supply_WithoutVAT = tmp_PriceSupply,
                                                                                     .Price_WithoutVAT = Me._DataRecord.Price2_WithoutVAT}.Markup_Percento)

                                Me.fro_txt_PredajnaCena3_Navysenie._Text = CStr(New Exa.OBERON.Shared.Common.Document.Item_Profit_Calculating() With
                                                                                    {.Price_Supply_WithoutVAT = tmp_PriceSupply,
                                                                                     .Price_WithoutVAT = Me._DataRecord.Price3_WithoutVAT}.Markup_Percento)

                                Me.fro_txt_PredajnaCena4_Navysenie._Text = CStr(New Exa.OBERON.Shared.Common.Document.Item_Profit_Calculating() With
                                                                                    {.Price_Supply_WithoutVAT = tmp_PriceSupply,
                                                                                     .Price_WithoutVAT = Me._DataRecord.Price4_WithoutVAT}.Markup_Percento)
                            Else
                                Me.fro_txt_PredajnaCena1_Navysenie._Text = CStr(.Price1_Markup)
                                Me.fro_txt_PredajnaCena2_Navysenie._Text = CStr(.Price2_Markup)
                                Me.fro_txt_PredajnaCena3_Navysenie._Text = CStr(.Price3_Markup)
                                Me.fro_txt_PredajnaCena4_Navysenie._Text = CStr(.Price4_Markup)
                            End If
                        End If

                        Dim tmp_UnitIndex As Integer = Me._DataRecord.UnitOthers.IndexDefaultOutcoming
                        Dim m_UnitCalcCoef_Out@ = 0
                        If tmp_UnitIndex >= 0 Then
                            '--- Existuje alternatívna MJ
                            m_UnitCalcCoef_Out@ = Me._DataRecord.UnitOthers(tmp_UnitIndex).UnitCoeficient
                        End If

                        If m_UnitCalcCoef_Out@ <> 0 And u_PriceInput = enm_PriceInputTypes.OutgoingUnit Then

                            'Zobrazí cenu za alternatívnu MJ.
                            If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Price_Without_VAT Then
                                Me.fro_txt_PredajnaCena1_BezDPH._Text = CStr(.Price_Get(1, False, m_UnitCalcCoef_Out@))
                                Me.fro_txt_PredajnaCena2_BezDPH._Text = CStr(.Price_Get(2, False, m_UnitCalcCoef_Out@))
                                Me.fro_txt_PredajnaCena3_BezDPH._Text = CStr(.Price_Get(3, False, m_UnitCalcCoef_Out@))
                                Me.fro_txt_PredajnaCena4_BezDPH._Text = CStr(.Price_Get(4, False, m_UnitCalcCoef_Out@))
                            End If

                            If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Price_With_VAT Then
                                Me.fro_txt_PredajnaCena1_SDPH._Text = CStr(.Price_Get(1, True, m_UnitCalcCoef_Out@))
                                Me.fro_txt_PredajnaCena2_SDPH._Text = CStr(.Price_Get(2, True, m_UnitCalcCoef_Out@))
                                Me.fro_txt_PredajnaCena3_SDPH._Text = CStr(.Price_Get(3, True, m_UnitCalcCoef_Out@))
                                Me.fro_txt_PredajnaCena4_SDPH._Text = CStr(.Price_Get(4, True, m_UnitCalcCoef_Out@))
                            End If

                            If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Price_WithVAT_Recommended Then
                                Me.fro_txt_PredajnaCena_Doporucena._Text = CStr(.Price_Get(StockCard.CONST_PriceLevelRecommended, True, m_UnitCalcCoef_Out@))
                            End If

                        Else
                            'Zobrazí štandardné ceny (za základnú MJ).
                            If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Price_Without_VAT Then
                                Me.fro_txt_PredajnaCena1_BezDPH._Text = CStr(.Price1_WithoutVAT) : Me.fro_txt_PredajnaCena1_BezDPH.FormatValue()
                                Me.fro_txt_PredajnaCena2_BezDPH._Text = CStr(.Price2_WithoutVAT) : Me.fro_txt_PredajnaCena2_BezDPH.FormatValue()
                                Me.fro_txt_PredajnaCena3_BezDPH._Text = CStr(.Price3_WithoutVAT) : Me.fro_txt_PredajnaCena3_BezDPH.FormatValue()
                                Me.fro_txt_PredajnaCena4_BezDPH._Text = CStr(.Price4_WithoutVAT) : Me.fro_txt_PredajnaCena4_BezDPH.FormatValue()
                            End If

                            If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Price_With_VAT Then
                                Me.fro_txt_PredajnaCena1_SDPH._Text = CStr(.Price1_WithVAT) : Me.fro_txt_PredajnaCena1_SDPH.FormatValue()
                                Me.fro_txt_PredajnaCena2_SDPH._Text = CStr(.Price2_WithVAT) : Me.fro_txt_PredajnaCena2_SDPH.FormatValue()
                                Me.fro_txt_PredajnaCena3_SDPH._Text = CStr(.Price3_WithVAT) : Me.fro_txt_PredajnaCena3_SDPH.FormatValue()
                                Me.fro_txt_PredajnaCena4_SDPH._Text = CStr(.Price4_WithVAT) : Me.fro_txt_PredajnaCena4_SDPH.FormatValue()
                            End If

                            If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Price_WithVAT_Recommended Then
                                Me.fro_txt_PredajnaCena_Doporucena._Text = CStr(.Price_WithVAT_Recommended)
                            End If

                        End If

                        If u_PriceCalculation <> StockCard.enm_Price_Calculation.Change_Round Then
                            Me.fro_cbo_PredajnaCena_Zaokruhlenie._SelectItem(.Price_Rounding, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)
                        End If

                        Me.fro_txt_DateTimeLastChangeSalesPrices._Text = String.Empty
                        If .DateTime_LastUpdate_SalePrices <> Nothing Then
                            Me.fro_txt_DateTimeLastChangeSalesPrices._Text = .DateTime_LastUpdate_SalePrices.ToLocalTime.ToString("dd.MM.yy HH:mm")
                        End If

                    End With

                Case enm_PriceSetTargetTypes.DataRecord

                    '°° SET DATA RECORD °°
                    '
                    'Nastaviť objekt 'DataRecord' podľa controlov.
                    With Me._DataRecord
                        If Me.fro_txt_Cena_Obstaravacia.ReadOnly = False AndAlso
                           Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = False Then 'Pre pochopenie tejto podmienky pozri udalosť Form_Load
                            .Price_Supply_Unit = CDec(Me.fro_txt_Cena_Obstaravacia._Value)
                        End If

                        If Me.fro_txt_Cena_PoslednaNakupna.ReadOnly = False AndAlso
                           Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = False Then 'Pre pochopenie tejto podmienky pozri udalosť Form_Load
                            .Price_LastPurchase = CDec(Me.fro_txt_Cena_PoslednaNakupna._Value)
                        End If

                        If Me.fro_rdb_TvorbaCeny_NavysenieVPercentach._Checked = True Then
                            .Price_Type = StockCard.enm_Prices_Type.Markup_Percentage
                        ElseIf Me.fro_rdb_TvorbaCeny_ZlavaZDoporucenejCeny._Checked = True Then
                            .Price_Type = StockCard.enm_Prices_Type.RecomendedPrice
                        ElseIf Me.fro_rdb_TvorbaCeny_NavysenieVSume._Checked = True Then
                            .Price_Type = StockCard.enm_Prices_Type.Markup_Value
                        Else
                            .Price_Type = StockCard.enm_Prices_Type.Fixed_Price
                        End If

                        .Price1_Markup = CDec(CDbl(Me.fro_txt_PredajnaCena1_Navysenie._Value))
                        .Price2_Markup = CDec(CDbl(Me.fro_txt_PredajnaCena2_Navysenie._Value))
                        .Price3_Markup = CDec(CDbl(Me.fro_txt_PredajnaCena3_Navysenie._Value))
                        .Price4_Markup = CDec(CDbl(Me.fro_txt_PredajnaCena4_Navysenie._Value))

                        '--- Vyhľadať MJ pre výdaj
                        Dim tmp_UnitIndex As Integer = .UnitOthers.IndexDefaultOutcoming
                        Dim m_UnitCalcCoef_Out@ = 0
                        If tmp_UnitIndex >= 0 Then
                            '--- Našla sa MJ pre výdaj
                            m_UnitCalcCoef_Out = CDec(.UnitOthers(tmp_UnitIndex).UnitCoeficient)
                        End If

                        If u_PriceInput = enm_PriceInputTypes.OutgoingUnit AndAlso m_UnitCalcCoef_Out@ <> 0 AndAlso m_UnitCalcCoef_Out@ <> 1 Then
                            'Nastav cenu za alternatívnu MJ.
                            If u_PriceCalculation = StockCard.enm_Price_Calculation.Change_Price_Without_VAT Then
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena1_BezDPH._Value), 1, set_price_WithoutVAT, m_UnitCalcCoef_Out@)
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena2_BezDPH._Value), 2, set_price_WithoutVAT, m_UnitCalcCoef_Out@)
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena3_BezDPH._Value), 3, set_price_WithoutVAT, m_UnitCalcCoef_Out@)
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena4_BezDPH._Value), 4, set_price_WithoutVAT, m_UnitCalcCoef_Out@)
                            End If

                            If u_PriceCalculation = StockCard.enm_Price_Calculation.Change_Price_With_VAT _
                                Or u_PriceCalculation = StockCard.enm_Price_Calculation.None_SetAll Then
                                '--- ... alebo len nastaviť 
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena1_SDPH._Value), 1, set_price_WithVAT, m_UnitCalcCoef_Out@)
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena2_SDPH._Value), 2, set_price_WithVAT, m_UnitCalcCoef_Out@)
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena3_SDPH._Value), 3, set_price_WithVAT, m_UnitCalcCoef_Out@)
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena4_SDPH._Value), 4, set_price_WithVAT, m_UnitCalcCoef_Out@)

                            End If

                            If u_PriceCalculation = StockCard.enm_Price_Calculation.Change_Price_WithVAT_Recommended _
                                Or u_PriceCalculation = StockCard.enm_Price_Calculation.None_SetAll Then
                                '--- ... alebo len nastaviť 
                                .Price_SET(CDec(Me.fro_txt_PredajnaCena_Doporucena._Value), StockCard.CONST_PriceLevelRecommended, set_price_WithVAT, m_UnitCalcCoef_Out@)

                            End If

                        Else
                            'Nastav štandardné ceny (za základnú MJ).
                            If u_PriceCalculation = StockCard.enm_Price_Calculation.Change_Price_Without_VAT _
                                Or u_PriceCalculation = StockCard.enm_Price_Calculation.None_SetAll Then
                                '--- ... alebo len nastaviť 
                                .Price1_WithoutVAT = CDec(Me.fro_txt_PredajnaCena1_BezDPH._Value)
                                .Price2_WithoutVAT = CDec(Me.fro_txt_PredajnaCena2_BezDPH._Value)
                                .Price3_WithoutVAT = CDec(Me.fro_txt_PredajnaCena3_BezDPH._Value)
                                .Price4_WithoutVAT = CDec(Me.fro_txt_PredajnaCena4_BezDPH._Value)
                            End If

                            If u_PriceCalculation = StockCard.enm_Price_Calculation.Change_Price_With_VAT _
                                Or u_PriceCalculation = StockCard.enm_Price_Calculation.None_SetAll Then
                                '--- ... alebo len nastaviť  Then
                                .Price1_WithVAT = CDec(Me.fro_txt_PredajnaCena1_SDPH._Value)
                                .Price2_WithVAT = CDec(Me.fro_txt_PredajnaCena2_SDPH._Value)
                                .Price3_WithVAT = CDec(Me.fro_txt_PredajnaCena3_SDPH._Value)
                                .Price4_WithVAT = CDec(Me.fro_txt_PredajnaCena4_SDPH._Value)

                            End If
                            If u_PriceCalculation = StockCard.enm_Price_Calculation.Change_Price_WithVAT_Recommended _
                                Or u_PriceCalculation = StockCard.enm_Price_Calculation.None_SetAll Then
                                '--- ... alebo len nastaviť 
                                .Price_WithVAT_Recommended = CDec(Me.fro_txt_PredajnaCena_Doporucena._Value)

                            End If

                        End If

                        .Price_Rounding = CType(Me.fro_cbo_PredajnaCena_Zaokruhlenie._Selected_Item.Value, StockCard.enm_Prices_Rounding)
                    End With

            End Select

        End Sub

        Private Sub z_Order_Calculate()

            On Error Resume Next

            Exa.Application.Cursor_Wait()

            '--- Zistiť objednané množstvá ---
            Dim tmp_OrderReceived_Features As Exa.OBERON.Stock.OrdersReceived.Features = Nothing
            Dim tmp_OrdersIssued_Features As Exa.OBERON.Stock.OrdersIssued.Features = Nothing
            Dim tmp_OrdersIssued_Values As New Exa.OBERON.Stock.OrdersIssued.Features.cls_OrdersValue
            Dim tmp_OrdersValues_Dict As Dictionary(Of Long, OBERON.Stock.OrdersReceived.Features.cls_OrdersValue) = Nothing

            Dim myEx As Exa.Basic.Exceptions.ExaException

            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                '--- Nový záznam ---
                '--- Nemá význam typočítavať objednané množstvá
                GoTo EndFunction
            End If

            '-------------------------
            '--- Objednávky prijaté --
            '-------------------------
            tmp_OrderReceived_Features = New Exa.OBERON.Stock.OrdersReceived.Features(lc_ObjectsOBERON_Stock)

            '--- Vypočíta objednané množstvá
            myEx = tmp_OrderReceived_Features.Get_AmountOrders_StockCard(Me._DataRecord.IDNum, Date.Now, tmp_OrdersValues_Dict)
            If myEx.Result = False Then
                Exa.Application.MsgBox("Chyba pri výpočte objednaných množstiev skladovej karty.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitFunction
            End If

            '-------------------------
            '--- Objednávky vydané --
            '-------------------------
            tmp_OrdersIssued_Features = New Exa.OBERON.Stock.OrdersIssued.Features(lc_AppConfiguration)


            '--- Vypočíta objednané množstvá
            myEx = tmp_OrdersIssued_Features.Get_AmountOrders_StockCard(Me._DataRecord.IDNum, tmp_OrdersIssued_Values)
            If myEx.Result = False Then
                Exa.Application.MsgBox("Chyba pri výpočte objednaných množstiev skladovej karty.", myEx, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                GoTo ExitFunction
            End If

EndFunction:

            'fro_txt_Objednavky_Mnozstvo_SkladovaKarta._Text = CStr(Me._DataRecord.Amount)
            If tmp_OrdersValues_Dict IsNot Nothing AndAlso tmp_OrdersValues_Dict.Count > 0 Then
                With tmp_OrdersValues_Dict(0)
                    fro_txt_ObjednavkyPrijate_Mnozstvo_Objednane._Text = CStr(.Amount_Orders - .Amount_Delivery)
                    fro_txt_ObjednavkyPrijate_Mnozstvo_Rezervovane._Text = CStr(.Amount_Reservation)
                End With
            End If

            fro_txt_ObjednavkyVydane_Mnozstvo_Objednane._Text = CStr(tmp_OrdersIssued_Values.Amount_Orders - tmp_OrdersIssued_Values.Amount_Delivery)

ExitFunction:

            tmp_OrdersIssued_Values = Nothing

            If tmp_OrdersValues_Dict IsNot Nothing Then
                tmp_OrdersValues_Dict.Clear()
                tmp_OrdersValues_Dict = Nothing
            End If

            If tmp_OrderReceived_Features IsNot Nothing Then
                tmp_OrderReceived_Features.Dispose()
                tmp_OrderReceived_Features = Nothing
            End If

            If tmp_OrdersIssued_Features IsNot Nothing Then
                tmp_OrdersIssued_Features.Dispose()
                tmp_OrdersIssued_Features = Nothing
            End If

            Exa.Application.Cursor_Default()

        End Sub

        Private Sub z_PriceChangeType(ByVal u_PriceCalculation As Boolean)
            On Error Resume Next

            If Me._DataRecord Is Nothing Then Exit Sub


            Dim m_ReadOnly_MarkUp As Boolean = False

            If fro_rdb_TvorbaCeny_NavysenieVSume._Checked = True Then
                Me.fro_lbl_PredajnaCena_Text.Text = Exa.Application.TranslateTextEx("Navýšenie v{0}",
                                                                                    vbCrLf & Me._DataRecord._AppConfiguration.Common.CurrencyCode)
                Me.fro_grp_PrepocetPredajnejCeny.Enabled = True

                Me.z_SetControls_Price_Calculation()

            ElseIf fro_rdb_TvorbaCeny_NavysenieVPercentach._Checked = True Then
                Me.fro_lbl_PredajnaCena_Text.Text = Exa.Application.TranslateTextEx("Navýšenie %")
                Me.fro_grp_PrepocetPredajnejCeny.Enabled = True

                Me.z_SetControls_Price_Calculation()

            ElseIf Me.fro_rdb_TvorbaCeny_ZlavaZDoporucenejCeny._Checked = True Then
                Me.fro_lbl_PredajnaCena_Text.Text = Exa.Application.TranslateTextEx("Zľava %")
                Me.fro_grp_PrepocetPredajnejCeny.Enabled = False

                Me.z_SetControls_Price_Calculation()

            Else
                Me.fro_lbl_PredajnaCena_Text.Text = Exa.Application.TranslateTextEx("Navýšenie %")
                Me.fro_grp_PrepocetPredajnejCeny.Enabled = False
                m_ReadOnly_MarkUp = True

                Me.z_SetControls_Price_Calculation()

            End If

            Me.fro_txt_PredajnaCena1_Navysenie.ReadOnly = m_ReadOnly_MarkUp
            Me.fro_txt_PredajnaCena2_Navysenie.ReadOnly = m_ReadOnly_MarkUp
            Me.fro_txt_PredajnaCena3_Navysenie.ReadOnly = m_ReadOnly_MarkUp
            Me.fro_txt_PredajnaCena4_Navysenie.ReadOnly = m_ReadOnly_MarkUp

            If u_PriceCalculation = True Then

                '--- Nastaví record podľa textových polí
                Me._DataRecord.on_ev_DataRecordPropertyChange(StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Action.SetProperty,
                                                              StockCard.cls_DataRecordPropertyChangeEventArgs.enm_Control.PriceCalculate)

                Me._DataRecord.Price_Calculation(0, StockCard.enm_Price_Calculation.Change_Price_With_VAT, 0, True)
            End If

        End Sub

        Private Sub z_SetControls_Price_Calculation()
            On Error Resume Next

            'If Me.IsHandleCreated = True Then Exit Sub

            If Me.fro_rdb_TvorbaCeny_NavysenieVSume._Checked = True Or Me.fro_rdb_TvorbaCeny_NavysenieVPercentach._Checked = True Then
                'Nastav prepočet predajnej ceny podľa pôvodne alebo používateľom zvolenej hodnoty.
                Select Case Me.lc_UserValue_PricesCalculationType
                    Case StockCard.enm_Prices_SellCalculationMode.Always : Me.fro_rdb_PrepocetCeny_Vzdy._Checked = True
                    Case StockCard.enm_Prices_SellCalculationMode.Ask_Before : Me.fro_rdb_PrepocetCeny_PytatSa._Checked = True
                    Case StockCard.enm_Prices_SellCalculationMode.Never : Me.fro_rdb_PrepocetCeny_Nikdy._Checked = True
                End Select
            Else
                'Zakáž prepočet predajnej ceny pre tiekto možnosti.
                Me.fro_rdb_PrepocetCeny_Nikdy._Checked = True
            End If

        End Sub

        Private Sub z_SetControls_Price_ButtonExtendedPrices()

            On Error Resume Next

            Dim tmp_FoundRules As Boolean = False

            If Me._DataRecord.ExtendedSalePricing_GeneratePrices IsNot Nothing _
                AndAlso Me._DataRecord.Name <> String.Empty Then
                '--- Je aktívna cenotvorba a je známa skladová karta ---

                Dim myEx As EXC.ExaException
                Dim frm_ShowItemRules As Exa.OBERON.Stock.Forms.ExtendedSalePricing.frm_ShowItemRules = Nothing

                '--- Načítať pravidlá rozšírenej cenotvorby k položke dokladu ---
                Dim Arg As New Exa.OBERON.Stock.ExtendedSalePricing.GeneratePrices.cls_GetDocumentItemRuleArg
                Arg.StockCardBaseInfo.FromStockCard(Me._DataRecord)
                Arg.Amount = 0  '--- Množstvo sa nebude posudzovať ----

                '--- Načítaj zoznam pravidiel ---
                Dim tmp_DocumentItemRuleArg As Exa.OBERON.Stock.ExtendedSalePricing.GeneratePrices.cls_GetDocumentItemRuleArg = New Exa.OBERON.Stock.ExtendedSalePricing.GeneratePrices.cls_GetDocumentItemRuleArg
                tmp_DocumentItemRuleArg.DocumentDateTime = Now
                tmp_DocumentItemRuleArg.StockCardBaseInfo = Arg.StockCardBaseInfo
                tmp_DocumentItemRuleArg.Barcodes = Me._DataRecord.BarCodes
                Dim tmp_RuleListRetValue As List(Of Exa.OBERON.Stock.ExtendedSalePricing.GeneratePrices.cls_RuleItem) = Nothing
                myEx = Me._DataRecord.ExtendedSalePricing_GeneratePrices.GetDocumentItemRules(tmp_DocumentItemRuleArg,
                                                                                              u_GetAllAvailableRules:=True,
                                                                                              urf_ReturnRules:=tmp_RuleListRetValue)
                If myEx.Result = True Then
                    If tmp_RuleListRetValue IsNot Nothing _
                        AndAlso tmp_RuleListRetValue.Count > 0 Then
                        '--- Existuje aspoň jedno pravidlo ---
                        tmp_FoundRules = True
                    End If
                End If

                tmp_RuleListRetValue = Nothing
                Arg = Nothing

            End If


            '--- Nastaviť font Bold ---
            If tmp_FoundRules = True Then
                fro_btn_ExtendedPrices.Font = New Drawing.Font(fro_btn_ExtendedPrices.Font, Drawing.FontStyle.Bold)
            Else
                If fro_btn_ExtendedPrices.Font.Bold = True Then
                    fro_btn_ExtendedPrices.Font = New Drawing.Font(fro_btn_ExtendedPrices.Font, Drawing.FontStyle.Regular)
                End If
            End If

        End Sub

        ''' <summary>
        ''' Metóda povolí /zakáže/ CONTROLY s cenotvorbou. Príznak povolenia/zakázania sa detekuje automaticky podľa režimu formulára a práv používateľa.
        ''' </summary>
        Private Sub z_SetControls_Price_Privileges()
            On Error Resume Next

            Dim tmp_LockPriceControls As Boolean = False
            Dim tmp_VisiblePriceValue As Boolean = True


            If Me._DataRecord.RecordState_Application = Database.Factory.DataRecord.enm_RecordStateTypes.CreateNew Then
                '--- Nový záznam - všetko povoliť ---
                tmp_LockPriceControls = False
                tmp_VisiblePriceValue = True

            Else
                '--- Oprava (načítanie)

                If lc_Permission_IsAllControlsLocked = True Then
                    '--- Formulár má byť zamknutý (užívateľ nemá práva) ----
                    tmp_LockPriceControls = True

                    If Me._DataRecord._AppConfiguration._AppObjects._UserInfo.Privileges.Stock.StockCard_PricesSupply_Visible = False Then
                        '--- Nemá sa zobraziť obstarávacia cena ---
                        '--- Potrebné skryť hodnoty ---
                        tmp_VisiblePriceValue = False
                    Else
                        '--- Hodnoty sa môžu zobraziť ---
                        tmp_VisiblePriceValue = True
                    End If
                Else
                    '--- Formulár má byť celý povolený (užívateľ má práva povolené)

                    If Me._DataRecord._AppConfiguration._AppObjects._UserInfo.Privileges.Stock.StockCard_PricesSale_Change = True Then
                        '--- Povolená zmena predajnej ceny ----
                        tmp_LockPriceControls = False
                    Else
                        '--- Zakázaná zmena predajnej ceny ----
                        tmp_LockPriceControls = True
                    End If


                    If Me._DataRecord._AppConfiguration._AppObjects._UserInfo.Privileges.Stock.StockCard_PricesSupply_Visible = False Then
                        '--- Nemá sa zobraziť obstarávacia cena ---
                        '--- Potrebné skryť hodnoty ---
                        tmp_VisiblePriceValue = False
                    Else
                        '--- Hodnoty sa môžu zobraziť ---
                        tmp_VisiblePriceValue = True
                    End If

                End If



            End If

            '-----------------------------------
            '--- Nastavenie práv ---
            '-----------------------------------

            '--- Kontroly cenotvorby pre zamknutie ---
            Dim tmp_LockControls() As Windows.Forms.Control = New Control() {fro_txt_PredajnaCena1_Navysenie,
                                                                                fro_txt_PredajnaCena2_Navysenie,
                                                                                fro_txt_PredajnaCena3_Navysenie,
                                                                                fro_txt_PredajnaCena4_Navysenie,
                                                                                fro_txt_PredajnaCena1_BezDPH,
                                                                                fro_txt_PredajnaCena2_BezDPH,
                                                                                fro_txt_PredajnaCena3_BezDPH,
                                                                                fro_txt_PredajnaCena4_BezDPH,
                                                                                fro_txt_PredajnaCena1_SDPH,
                                                                                fro_txt_PredajnaCena2_SDPH,
                                                                                fro_txt_PredajnaCena3_SDPH,
                                                                                fro_txt_PredajnaCena4_SDPH,
                                                                                fro_txt_ZlavyPredaj_MaximalnaZlava,
                                                                                fro_cbo_PredajnaCena_Zaokruhlenie,
                                                                                fro_cbo_SadzbaDPH,
                                                                                fro_btn_Ceny_Prepocitat}


            If tmp_LockPriceControls = True Then
                '--- Z a k á z a ť   kontroly s cenotvorbou ---

                If tmp_VisiblePriceValue = True Then
                    '--- Zobraziť hodnoty (navýšenie)

                    '--- Zrušiť príznak pre skrývanie hodnôt ----			


                    Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = False
                    Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = False

                    Me.fro_txt_PredajnaCena1_Navysenie.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena2_Navysenie.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena3_Navysenie.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena4_Navysenie.PrivilegeLock = False

                    If lc_Permission_IsAllControlsLocked = True Then
                        '--- Formulár má byť zamknutý (užívateľ nemá práva) ----
                        Me.fro_grp_TvorbaPredajnejCeny.PrivilegeLock = False
                        Me.fro_grp_PredajnaCena.PrivilegeLock = False
                        Me.fro_grp_Discount.PrivilegeLock = False
                    Else
                        '--- Odopreté právo len na cenotvorbu ---
                        Me.fro_grp_TvorbaPredajnejCeny.PrivilegeLock = True
                        Me.fro_grp_PredajnaCena.PrivilegeLock = True
                        Me.fro_grp_Discount.PrivilegeLock = True
                    End If


                    Exa.Application.Forms.LockControls(tmp_LockControls)

                Else
                    '--- Skryť hodnoty (navýšenie) ---

                    Me.fro_grp_TvorbaPredajnejCeny.PrivilegeLock = True
                    Me.fro_grp_PredajnaCena.PrivilegeLock = True
                    Me.fro_grp_Discount.PrivilegeLock = True

                    Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = True
                    Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena1_Navysenie.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena2_Navysenie.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena3_Navysenie.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena4_Navysenie.PrivilegeLock = True

                    '--- Zamknúť kontroly ---		
                    Exa.Application.Forms.LockControls(tmp_LockControls)
                End If


            Else
                '--- Povoliť kontroly s cenotvorbou --
                '--- Kontroly sú štandardne po načítaní okna povolené - netreba opätovne povoľovať

                Me.fro_grp_PredajnaCena.PrivilegeLock = False
                Me.fro_grp_Discount.PrivilegeLock = False

                If tmp_VisiblePriceValue = True Then
                    '--- Zobraziť hodnoty (navýšenie)

                    '--- Zrušiť príznak pre skrývanie hodnôt ----
                    Me.fro_grp_TvorbaPredajnejCeny.PrivilegeLock = False

                    Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = False
                    Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena1_Navysenie.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena2_Navysenie.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena3_Navysenie.PrivilegeLock = False
                    Me.fro_txt_PredajnaCena4_Navysenie.PrivilegeLock = False

                Else
                    '--- Skryť hodnoty (navýšenie) ---

                    Me.fro_grp_TvorbaPredajnejCeny.PrivilegeLock = True

                    Me.fro_txt_Cena_PoslednaNakupna.PrivilegeLock = True
                    Me.fro_txt_Cena_Obstaravacia.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena1_Navysenie.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena2_Navysenie.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena3_Navysenie.PrivilegeLock = True
                    Me.fro_txt_PredajnaCena4_Navysenie.PrivilegeLock = True

                End If

            End If


        End Sub

        ''' <summary>
        ''' Nastaví (pridá zoznam položiek a načíta nastavenia) control 'ComboBox' pre zadávanie ceny.
        ''' </summary>
        Private Sub z_SetControls_UnitsForPriceInput_ComboBox()
            On Error Resume Next



            'Načítaj zoznam merných jednotiek, podľa nastavení skladovej karty.
            With Me.fro_cbo_PredajnaCena_Zadavanie._Items
                .Update_Begin()
                .Clear()
                .Add(Me._DataRecord.Unit, enm_PriceInputTypes.BaseUnit)

                For Each e_UnitOther As Exa.OBERON.Stock.StockCards.StockCard.UnitInfo In Me._DataRecord.UnitOthers
                    If e_UnitOther.UnitMovementType = StockCard.enm_UnitMovementType.Incoming Then
                        Continue For
                    End If
                    '--- Našla sa alternatívna MJ
                    If e_UnitOther.PriceCoeficient <> 0 Then
                        '--- Je nastavený koeficient prepočtu ceny podľa MJ (balenia) 
                        '--- Tu nemumožniť pracovať a zadávať cenu

                    Else

                        .Add(e_UnitOther.UnitName,
                                    enm_PriceInputTypes.OutgoingUnit,
                                    u_SubText1:=String.Format("= {0} {1}", CStr(e_UnitOther.UnitCoeficient), Me._DataRecord.Unit))

                    End If



                Next
                .Update_End()

            End With

            Dim tmp_UnitIndex As Integer = Me._DataRecord.UnitOthers.IndexDefaultOutcoming

            With Me.fro_cbo_PredajnaCena_Zadavanie

                If tmp_UnitIndex >= 0 Then
                    '--- Našla sa alternatívna MJ
                    'Umožni zmenu zadávania MJ, kedže je nastavený prepočet MJ pre výdaj.

                    Dim m_PriceInputType As enm_PriceInputTypes = CType(Exa.Application.Environment.
                                                                                  Settings_Controls._Read("Forms.StockCards.frm_StockCard_NewEdit",
                                                                                  "PriceInputType",
                                                                                  enm_PriceInputTypes.BaseUnit), enm_PriceInputTypes)

                    ._SelectItem(m_PriceInputType, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                Else
                    'Zakáž zmenu zadávania MJ, pretože je nastavená len základná MJ.
                    ._SelectItem(enm_PriceInputTypes.BaseUnit, Application.Controls.Simple.S_ComboBox.enm_ItemValueTypes.Value)

                End If
            End With

        End Sub

        ''' <summary>
        ''' Nastaví controly typu 'Label', ktoré zobrazujú MJ pre zadávanie ceny.
        ''' </summary>
        Private Sub z_SetControls_UnitsForPriceInput_Labels()
            On Error Resume Next


            Dim m_ToolTipText$ = Nothing
            Dim m_PriceInputType As enm_PriceInputTypes = CType(Me.fro_cbo_PredajnaCena_Zadavanie._Selected_Item.Value, enm_PriceInputTypes)

            If m_PriceInputType = enm_PriceInputTypes.BaseUnit Then
                m_ToolTipText$ = Exa.Application.TranslateText("Základná merná jednotka")
            ElseIf m_PriceInputType = enm_PriceInputTypes.OutgoingUnit Then
                m_ToolTipText$ = Exa.Application.TranslateText("Merná jednotka pre výdaj")
            End If

            Dim m_PriceInput_MJ$ = Me.fro_cbo_PredajnaCena_Zadavanie._Text

            With Me.fro_lbl_PredajnaCena_MJ2
                ._Text = m_PriceInput_MJ$
                .ToolTipText = m_ToolTipText$
            End With

            With Me.fro_lbl_PredajnaCena_MJ3
                ._Text = m_PriceInput_MJ$
                .ToolTipText = m_ToolTipText$
            End With

            With Me.fro_lbl_PredajnaCena_MJ4
                ._Text = m_PriceInput_MJ$
                .ToolTipText = m_ToolTipText$
            End With

            With Me.fro_lbl_PredajnaCena_MJ_Doporucena
                ._Text = m_PriceInput_MJ$
                .ToolTipText = m_ToolTipText$
            End With

            '--- Nastaviť ešte MJ pri aktuálnom množstve na sklade
            fro_lbl_Amount_UnitBaseName._Text = Me.fro_cbo_MJ._Text

        End Sub

        Private Sub z_SetControls_UctovaniePredkontaciaText()

            On Error Resume Next

            Dim LANG$ = "<Text nenájdený>"
            Dim tmp_Str$ = Exa.Application.TranslateText(LANG)

            If lc_AppConfiguration.Common.AvailableModules.IndexOf(Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.AccountingDouble) < 0 Then
                '--- Nie je podvojné účtovníctvo ---
                Exit Sub
            End If

            Dim tmp_CisloPredkontacie% = CInt(Me.fro_txt_Uctovanie_Predkontacia_Cislo._Value)

            Dim tmp_Color As Drawing.Color = Exa.Application.Theme.Colors.Alternate.Text

            If tmp_CisloPredkontacie% = 0 Then
                '--- Nie je zadaná ---
                fro_txt_Uctovanie_Predkontacia_Text._Text = String.Empty
            Else
                '--- Je zadaná --

                Dim myEx As Exa.Basic.Exceptions.ExaException
                Dim tmp_AccountCoding As Exa.OBERON.Shared.AccDouble.AccountCodings.AccountCoding = Nothing
                myEx = Me.lc_ObjectsOBERON_Stock._ObjectsOBERON.AccDouble.AccountCoding_List_Internal.GetAccountCoding(tmp_CisloPredkontacie%, tmp_AccountCoding)
                If myEx.Result = False Then
                    fro_txt_Uctovanie_Predkontacia_Text._Text = tmp_Str$
                    tmp_Color = Drawing.Color.Red
                Else
                    fro_txt_Uctovanie_Predkontacia_Text._Text = tmp_AccountCoding.Name
                    If tmp_AccountCoding.Type <> [Shared].AccDouble.AccountCodings.AccountCoding.enm_Type.Stocks Then
                        tmp_Color = Drawing.Color.Red
                    End If
                End If
                tmp_AccountCoding = Nothing

            End If

            fro_txt_Uctovanie_Predkontacia_Cislo.ForeColor = tmp_Color
            fro_txt_Uctovanie_Predkontacia_Text.ForeColor = tmp_Color

        End Sub

        Private Sub z_SetControls_CustomsTariffCodeText()

            On Error Resume Next

            Dim LANG$ = "<názov nenájdený>"
            Dim tmp_Str$ = Exa.Application.TranslateText(LANG)


            Dim tmp_CustomsTariffCode As String = Trim(CStr(Me.fro_txt_CustomsTariffCode._Value))

            If tmp_CustomsTariffCode = String.Empty Then
                '--- Nie je zadaná ---
                fro_txt_CustomsTariffCode_Text._Text = String.Empty
            Else
                '--- Je zadaná --
                Dim myEx As Exa.Basic.Exceptions.ExaException
                Dim tmp_CustomsTariff As Exa.OBERON.Shared.Stock.CustomsTariffs.CustomsTariff = Nothing
                myEx = Me.lc_ObjectsOBERON_Stock._ObjectsOBERON.CustomsTariff_List_Internal.GetCustomsTariff(tmp_CustomsTariffCode, tmp_CustomsTariff)
                If myEx.Result = False Then
                    fro_txt_CustomsTariffCode_Text._Text = tmp_Str$
                Else
                    fro_txt_CustomsTariffCode_Text._Text = tmp_CustomsTariff.Name
                End If
                tmp_CustomsTariff = Nothing
            End If

            '--- Do tooltipu vložiť text - môže byť zobrazený na viac riadkov
            fro_txt_CustomsTariffCode_Text.ToolTipText = fro_txt_CustomsTariffCode_Text._Text

        End Sub

        ''' <summary>
        ''' Nastaví kód položky podľa čísla karty, avšak len ak je okno zobrazené.
        ''' </summary>
        Private Sub z_SetCashregisterItemFromItem()
            On Error Resume Next

            'Nastav nezadaný kód položky podľa čísla karty
            If Me.IsFormShown = True _
                AndAlso Me.fro_chk_RPoklSFisklom_UmoznitPredavatNaPokladnici._Checked = True _
                AndAlso Me.fro_txt_RPoklSFiskalom_KodPolozky._Text = String.Empty Then
                '--- Číslo karty (kód položky)
                Me.fro_txt_RPoklSFiskalom_KodPolozky._Text = Me.fro_txt_CisloKarty._Text
            End If

        End Sub

        ''' <summary>
        ''' Načíta alebo aktualizuje cache pre vykresľovanie variánt.
        ''' </summary>
        Private Sub z_LoadDrawingCache_Variants()
            On Error Resume Next

            If Me.lc_StockCard_Cache Is Nothing Then
                Me.lc_StockCard_Cache = New StockCard_Cache(Me._DataRecord._ObjectsOBERON_Stock)
            Else
                Me.lc_StockCard_Cache.Refresh(u_Refresh_StockCardVariant:=True,
                                                u_Refresh_StockCardFileRepository:=False,
                                                u_RefreshDataLanguage:=False)
            End If

            'Načítanie údajov definícií variant do objektu 'HashTable' pre rýchle zobrazovanie (vykresľovanie) v 'DataGride'.
            Me.lc_HashTable_VariantDefinition = New Hashtable

            For Each e_Row As DataRow In Me.lc_StockCard_Cache.StockCard_VariantDefinition_List.Object_Table.DatabaseTable_Data.Rows
                Me.lc_HashTable_VariantDefinition.Add(CLng(e_Row("IDNum")), e_Row)
            Next

        End Sub

        ''' <summary>
        ''' Načíta zoznam tlačových výstupov pre tlač štítkov na registračnej pokladnici.
        ''' </summary>
        Private Sub z_SetControls_LoadPrinterReports_CashRegisterTags()
            On Error Resume Next

            Dim m_ExaException As EXC.ExaException = Nothing
            Dim m_StockCard_Reports_CashRegisterTags As New Exa.OBERON.Stock.StockCards.Reports.StockCard_Reports_CashRegisterTags(Me.lc_ObjectsOBERON_Stock, Me.lc_DeviceEngine)
            Dim m_ModuleBooksAndReports As New Exa.Application.Reports.Report_List.cls_ModuleBookWithReportsIDCollection

            With m_ModuleBooksAndReports
                .Add(Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_Report_Module_Stock.StockCard_CashRegister_Tags,
                     Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_ReportID_StockCards_CashRegister_Tags.Etikety_1ksNaList,
                     Exa.OBERON.Shared.Common.AppReportsEngineOBERON.enum_App_ReportID_StockCards_CashRegister_Tags.Etikety_Landscape_1ksNaList)
            End With

            Dim m_ReportList As Exa.Application.Reports.Report_List = Nothing

            m_ExaException = m_StockCard_Reports_CashRegisterTags.LoadReportList(Exa.OBERON.ApplicationEnvironment.Common.AppConstants.enm_OBERON_modules.Stock,
                                                                                 m_ModuleBooksAndReports,
                                                                                 m_ReportList)

            If m_ExaException.Result = True AndAlso m_ReportList IsNot Nothing AndAlso m_ReportList.Object_Table IsNot Nothing Then
                With Me.fro_cbo_AutomatickaTlacEtikety._Items
                    .Update_Begin()
                    .Clear()
                    .Add(String.Empty) '* Položka pre výber keď tlačový výstup nie je zadaný ...

                    For Each e_Row As DataRow In m_ReportList.Object_Table.DatabaseTable_Data.Rows
                        Dim m_Report As Exa.Application.Reports.Report = m_ReportList.DataRecord(e_Row, True)
                        Dim m_Image As Drawing.Image = Exa.Application.Reports.GetReportItemImage(CType(m_Report.Image_Number, Exa.Application.Reports.enm_ReportItemImageTypes))
                        Dim m_IsLocked As Boolean = False

                        'If m_Report.UserPrivileges = String.Empty OrElse m_Report.UserPrivileges.Contains("\" & u_User_IDNum & "\") = False Then
                        '    m_IsLocked = True
                        'End If
                        '* Zrušené, nepoužíva sa zatiaľ ...

                        .Add(m_Report.Name, m_Report.IDNum, m_Image)
                    Next

                    .Update_End()
                End With
            End If

            If m_ReportList IsNot Nothing Then m_ReportList.Dispose()
            m_ReportList = Nothing

            If m_StockCard_Reports_CashRegisterTags IsNot Nothing Then m_StockCard_Reports_CashRegisterTags.Dispose()
            m_StockCard_Reports_CashRegisterTags = Nothing

        End Sub

        Private Sub z_SetVariantDataGrid_SearchPanel()

            On Error Resume Next

            If Me._DataRecord.Items_Variant.Object_Table IsNot Nothing AndAlso Me._DataRecord._AppConfiguration.Common.SystemSettings.Document_ShowFindControl_ItemsCount > Me._DataRecord.Items_Variant.Object_Table.DatabaseTable_Data.Rows.Count Then
                Me.fro_pan_DataGrid_Search.Visible = False
            Else
                Me.fro_pan_DataGrid_Search.Visible = True
            End If

        End Sub

#End Region


#Region " IMPLEMENTS - FORM OPTIONS "

        Private Sub fro_btn_Moznosti_ev_Click(sender As Object, e As EventArgs) Handles fro_btn_Moznosti.ev_Click
            On Error Resume Next

            Using f_Options As New Exa.Application.Forms.Options.frm_Options(Me)
                Exa.Application.ShowWindow(f_Options, True, Me)
            End Using

            Me.fro_dgv_Variants.Focus()
        End Sub

        Public Property OptionsFormInfo As frm_Options.stc_FormInfoValues Implements frm_Options.IFormOptions.OptionsFormInfo

        Public ReadOnly Property OptionsItems As frm_Options.cls_OptionsItemsCollection Implements frm_Options.IFormOptions.OptionsItems
            Get
                On Error Resume Next

                Dim m_OptionsItems As New Application.Forms.Options.frm_Options.cls_OptionsItemsCollection

                With m_OptionsItems
                    .AddEx("VariantGenerator", "Generátor variantov pre skladovú kartu",
                            My.Resources.Documents_AutoGenerate,
                            u_ShowInContextMenu:=True,
                            u_ShortcutKeys:=Keys.Control Or Keys.G,
                            u_ShowInToolbar:=True,
                            u_IsVisible_WhenRowIsNotSelected:=False,
                            u_IsVisible_OnLockedForm:=True)
                    .AddSeparator()

                End With

                Return m_OptionsItems

            End Get
        End Property


        Public Sub OnOptionsItemSelected(e As frm_Options.cls_ItemSelectedEventArgs) Implements frm_Options.IFormOptions.OnOptionsItemSelected
            On Error Resume Next

            Dim m_ObjectsOBERON As Exa.OBERON.Shared.Common.ObjectsOBERON = TryCast(Me.OptionsFormInfo.Parameters(0), Exa.OBERON.Shared.Common.ObjectsOBERON)

            Exa.Application.Cursor_Wait(Me.OptionsFormInfo.Object_Form)

            Select Case e.SelectedItem.Name
                Case "VariantGenerator"
                    Using m_frmW_VariantGenerator As New Wizards.frmW_VariantGenerator(Me._DataRecord, lc_StockCard_Cache)
                        Exa.Application.ShowWindow(m_frmW_VariantGenerator, True, Me)
                    End Using

            End Select

            Exa.Application.Cursor_Default(Me.OptionsFormInfo.Object_Form)

        End Sub

        Public Sub CallOptionsItem(u_ItemName As String) Implements frm_Options.IFormOptions.CallOptionsItem
            On Error Resume Next
            Me.OnOptionsItemSelected(New Application.Forms.Options.frm_Options.cls_ItemSelectedEventArgs(New Application.Forms.Options.frm_Options.cls_OptionsItemsCollection.cls_OptionsItemValues(u_ItemName)))
        End Sub

        ''' <summary>
        ''' Odošle údaje na elektronické cenovky pre 3 rôzne veľkosti displejov.
        ''' Každá cenovka používa inú šablónu (StyleId) podľa typu displeja.
        ''' </summary>
        Private Async Sub SendPriceTag_Click(sender As Object, e As EventArgs) Handles SendPriceTag.Click

            '--- VALIDATION ---
            If Me._DataRecord Is Nothing Then
                Exa.Application.MsgBox("Nie je načítaná žiadna skladová karta.", MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                Exit Sub
            End If

            Exa.Application.Cursor_Wait(Me)

            ' Status 1: Default/Normal - button appearance before sending
            ResetSendPriceTagToDefault()

            Try
                Exa.Basic.Debug.Console._Write("[SendPriceTag_Click] START - Začínám aktualizovať cenovky", Nothing, "ESL_DEBUG", Exa.Basic.Debug.cls_Console.enm_MessageTypes.Info, Exa.Basic.Debug.cls_Console.enm_CategoryTypes.Interface)

                ' ========================================================================
                ' KROK 1: Definovať zoznam cenoviek s MAC adresami a šablónami
                ' ========================================================================
                Dim priceTagConfigs As New List(Of Tuple(Of String, String, Integer)) From {
                    New Tuple(Of String, String, Integer)("92.13.73.60", "SF21BasePriceTag_V1", 1),   ' 2.1" B/W/R - 250x132
                    New Tuple(Of String, String, Integer)("92.96.61.18", "S21BasePriceTag_V1", 2),     ' 2.1" B/W - 250x122
                    New Tuple(Of String, String, Integer)("92.81.18.41", "S29BasePriceTag_V1", 3)      ' 2.9" B/W/R - 296x128
                }

                ' ========================================================================
                ' KROK 2: Vytvoriť zoznam všetkých PriceTagData
                ' ========================================================================
                Dim baseUrl As String = "http://192.168.16.251"
                Dim allPriceTags As New List(Of Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagData)

                For Each config In priceTagConfigs
                    Dim mac As String = config.Item1
                    Dim templateName As String = config.Item2
                    Dim templateType As Integer = config.Item3

                    Dim styleId As Integer
                    Dim mappingType As Integer
                    Select Case templateType
                        Case 1
                            styleId = Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagConstants.CONST_StyleId_SF21BasePriceTag_V1
                            mappingType = Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagConstants.CONST_MappingType_SF21BasePriceTag_V1
                        Case 2
                            styleId = Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagConstants.CONST_StyleId_S21BasePriceTag_V1
                            mappingType = Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagConstants.CONST_MappingType_S21BasePriceTag_V1
                        Case 3
                            styleId = Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagConstants.CONST_StyleId_S29BasePriceTag_V1
                            mappingType = Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagConstants.CONST_MappingType_S29BasePriceTag_V1
                    End Select

                    Dim priceTagData As New Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.Models.PriceTagData With {
                        .Mac = mac,
                        .MappingType = mappingType,
                        .StyleId = styleId
                    }

                    priceTagData.Fields.Add("NameUnitMJ", $"Cena za 1{Me._DataRecord.Unit}")
                    priceTagData.Fields.Add("PriceRetail", Me._DataRecord.Price1_WithVAT.ToString("N2").Replace(".", ","))
                    priceTagData.Fields.Add("Name", Me._DataRecord.Name)
                    priceTagData.Fields.Add("CodeCashRegister", Me._DataRecord.CashRegister_Code)
                    If Me._DataRecord.Unit_Calculation_PriceCompare_Coefficient > 0 Then
                        priceTagData.Fields.Add("MJPorovnanieCenyKoef", $"{Me._DataRecord.Unit_Calculation_PriceCompare_Coefficient:N2}€|kg")
                    End If

                    allPriceTags.Add(priceTagData)
                Next

                ' Status 2: In Progress - update in progress
                SendPriceTag.BackColor = Drawing.Color.Yellow
                SendPriceTag.ForeColor = Drawing.Color.Black
                SendPriceTag.Text = "Pošli údaje štítku (Posielam...)"

                ' ========================================================================
                ' KROK 3: Poslať VŠETKY cenovky v jednom batchi
                ' ========================================================================
                Dim client As New Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.OBERON_ESL_2026Client()
                client.prp_BaseUrl = baseUrl
                Dim myEx As EXC.ExaException = Await client.SendPriceTagAsync(allPriceTags)

                If myEx.Result = True Then
                    ' Spusti monitorovanie statusu cez PriceTagStatusMonitor v samostatnom vlákne
                    If lc_StatusMonitor Is Nothing Then
                        lc_StatusMonitor = New Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.PriceTagStatusMonitor(New Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.OBERON_ESL_2026Client() With {.prp_BaseUrl = baseUrl})
                    End If

                    ' Nastav zoznam MAC adries pre monitorovanie
                    Dim macAddresses As New List(Of String) From {
                        "92.13.73.60",
                        "92.97.83.93",
                        "92.81.18.41"
                    }
                    lc_StatusMonitor.StartMonitoring(macAddresses)

                    ' Priradenie event handlera
                    RemoveHandler lc_StatusMonitor.StatusChanged, AddressOf StatusMonitor_StatusChanged
                    AddHandler lc_StatusMonitor.StatusChanged, AddressOf StatusMonitor_StatusChanged

                    RemoveHandler lc_StatusMonitor.MonitoringCompleted, AddressOf StatusMonitor_MonitoringCompleted
                    AddHandler lc_StatusMonitor.MonitoringCompleted, AddressOf StatusMonitor_MonitoringCompleted

                    ' Nastaviť interval na 2 sekundy
                    lc_StatusMonitor.CheckIntervalMs = 2000
                Else
                    ' Status 3: Update zlyhal (update failed)
                    SendPriceTag.BackColor = Drawing.Color.Red
                    SendPriceTag.ForeColor = Drawing.Color.White
                    SendPriceTag.Text = "Pošli údaje štítku (Chyba)"
                    Exa.Application.MsgBox(myEx.GetFullDescription, MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
                End If

            Catch ex As Exception
                ' Status 3: Update zlyhal (update failed)
                SendPriceTag.BackColor = Drawing.Color.Red
                SendPriceTag.ForeColor = Drawing.Color.White
                SendPriceTag.Text = "Pošli údaje štítku (Chyba)"
                Exa.Application.MsgBox($"Neočakávaná chyba pri odosielaní údajov na cenovku.{vbCrLf}{ex.GetBaseException.Message}", MsgBoxStyle.Critical Or MsgBoxStyle.OkOnly)
            End Try

            Exa.Application.Cursor_Default(Me)

        End Sub

        ''' <summary>
        ''' Reset button to default (normal) state
        ''' </summary>
        Private Sub ResetSendPriceTagToDefault()
            SendPriceTag.BackColor = System.Drawing.SystemColors.Control
            SendPriceTag.ForeColor = System.Drawing.SystemColors.ControlText
            SendPriceTag.Text = "Pošli údaje štítku"
        End Sub

        ''' <summary>
        ''' Event handler pre StatusChanged event z PriceTagStatusMonitor.
        ''' Aktualizuje tlačidlo podľa najnovšieho statusu cenovky.
        ''' Priorita farieb: Chyba (3) > Úspech (4) > Chyba čítania (-1) > In Progress (2) > Normal (1)
        ''' </summary>
        Private Sub StatusMonitor_StatusChanged(ByVal sender As Object, ByVal e As Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.StatusChangedEventArgs)
            ' Kontrola či formulár ešte existuje (nie je zrušený)
            If Me.IsDisposed OrElse Me.Disposing Then
                Return
            End If

            If Me.InvokeRequired Then
                ' Kontrola či handle ešte existuje a formulár nie je zrušený
                If Me.IsHandleCreated AndAlso Not Me.IsDisposed Then
                    Try
                        Me.Invoke(New Action(Of Object, StatusChangedEventArgs)(AddressOf StatusMonitor_StatusChanged), sender, e)
                    Catch ex As ObjectDisposedException
                        ' Formulár bol zrušený medzi kontrolami IsHandleCreated/IsDisposed a Invoke volaním
                        ' Toto je bežný jav pri rýchlom zatváraní formulára
                    Catch ex As InvalidOperationException
                        ' Handle sa zmenšilo medzi kontrolami - tiež bežný jav pri zatváraní
                    End Try
                End If
                Return
            End If

            ' Zmena textu tlačidla a farby podľa statusu
            ' Priorita farieb: Chyba (3) > Úspech (4) > Chyba čítania (-1) > In Progress (2) > Normal (1)
            If e.Status.HasValue Then
                Select Case e.Status.Value
                    Case 3 ' Update zlyhal - najvyššia priorita (červená)
                        SendPriceTag.BackColor = Drawing.Color.Red
                        SendPriceTag.ForeColor = Drawing.Color.White
                        SendPriceTag.Text = "Pošli údaje štítku (Chyba)"
                    Case 4 ' Update úspešný (zelená)
                        SendPriceTag.BackColor = Drawing.Color.LimeGreen
                        SendPriceTag.ForeColor = Drawing.Color.White
                        SendPriceTag.Text = "Pošli údaje štítku (Úspech)"
                    Case 2 ' In Progress (žltá)
                        SendPriceTag.BackColor = Drawing.Color.Yellow
                        SendPriceTag.ForeColor = Drawing.Color.Black
                        SendPriceTag.Text = "Pošli údaje štítku (Posielam...)"
                    Case -1 ' Chyba pri čítaní (oranžová)
                        SendPriceTag.BackColor = Drawing.Color.Orange
                        SendPriceTag.ForeColor = Drawing.Color.Black
                        SendPriceTag.Text = "Pošli údaje štítku (Chyba čítania)"
                    Case 1 ' Normal / Default (predvolená)
                        SendPriceTag.BackColor = System.Drawing.SystemColors.Control
                        SendPriceTag.ForeColor = System.Drawing.SystemColors.ControlText
                        SendPriceTag.Text = "Pošli údaje štítku"
                End Select
            End If
        End Sub

        ''' <summary>
        ''' Event handler pre MonitoringCompleted event z PriceTagStatusMonitor.
        ''' </summary>
        Private Sub StatusMonitor_MonitoringCompleted(ByVal sender As Object, ByVal e As Exa.OBERON.Devices.PriceLabels.OBERON_ESL_2026.MonitoringCompletedEventArgs)
            ' Kontrola či formulár ešte existuje (nie je zrušený)
            If Me.IsDisposed OrElse Me.Disposing Then
                Return
            End If

            ' Zastavi monitorovanie a uvoľni zdroje
            If lc_StatusMonitor IsNot Nothing Then
                lc_StatusMonitor.StopMonitoring()
                lc_StatusMonitor.Dispose()
                lc_StatusMonitor = Nothing
            End If

            ' Reset tlačidla po dokončení monitorovania
            SendPriceTag.BackColor = System.Drawing.SystemColors.Control
            SendPriceTag.ForeColor = System.Drawing.SystemColors.ControlText
            SendPriceTag.Text = "Pošli údaje štítku"
        End Sub



#End Region


    End Class

End Namespace