Namespace Forms

    <Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
    Partial Class frm_ElectronicPriceTags_List
        Inherits Exa.Application.Forms.Form_Win32

        'Form overrides dispose to clean up the component list.
        <System.Diagnostics.DebuggerNonUserCode()>
        Protected Overrides Sub Dispose(ByVal disposing As Boolean)
            Try
                If disposing AndAlso components IsNot Nothing Then
                    components.Dispose()
                End If
            Finally
                MyBase.Dispose(disposing)
            End Try
        End Sub

        'Required by the Windows Form Designer
        Private components As System.ComponentModel.IContainer

        'NOTE: The following procedure is required by the Windows Form Designer
        'It can be modified using the Windows Form Designer.  
        'Do not modify it using the code editor.
        <System.Diagnostics.DebuggerStepThrough()>
        Private Sub InitializeComponent()
            Me.components = New System.ComponentModel.Container()
            Me.TabControl_Main = New System.Windows.Forms.TabControl()
            Me.Tab_PriceTagData = New System.Windows.Forms.TabPage()
            Me.fro_dgv_PriceTagData = New Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32()
            Me.cln_PriceTag_mac = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_ido = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_routerid = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_status = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_rssi = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_power = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_styleId = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_width = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_PriceTag_height = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.fro_btn_Load_PriceTagData = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.pan_PriceTagData_ButtonPanel = New System.Windows.Forms.Panel()
            Me.Tab_RouterInfo = New System.Windows.Forms.TabPage()
            Me.fro_dgv_RouterInfo = New Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32()
            Me.cln_Router_routerID = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_routerIP = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_hardwareVersion = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_softwareVersion = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_freq = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_state = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_tagQuanty = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Router_lastHeartbeatTime = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.fro_btn_Load_RouterInfo = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.Tab_StyleMsgArray = New System.Windows.Forms.TabPage()
            Me.fro_dgv_StyleMsgArray = New Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32()
            Me.cln_Style_id = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Style_name = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Style_type = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Style_width = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Style_height = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Style_backgroundID = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Style_updateTime = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
             Me.fro_btn_Load_StyleMsgArray = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
             Me.fro_btn_Load_StyleMsgById = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
             Me.Tab_PhotoInfo = New System.Windows.Forms.TabPage()
            Me.fro_dgv_PhotoInfo = New Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32()
            Me.cln_Photo_id = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Photo_name = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Photo_width = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
            Me.cln_Photo_height = New Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn()
             Me.fro_btn_Load_PhotoInfo = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
             Me.fro_btn_Load_PhotoImage = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
             Me.fro_btn_UploadPhoto = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.fro_btn_DeletePhoto = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.fro_btn_DeleteTagsByMac = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.pan_StatusBar = New Exa.Application.Controls.Microsoft.M_Panel()
            Me.fro_lbl_Status = New Exa.Application.Controls.Simple.S_Label.BaseControls.S_Label_Win32()
            Me.fro_btn_Zatvorit = New Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32()
            Me.pan_PriceTagData_ButtonPanel = New System.Windows.Forms.Panel()
            Me.pan_RouterInfo_ButtonPanel = New System.Windows.Forms.Panel()
            Me.pan_StyleMsgArray_ButtonPanel = New System.Windows.Forms.Panel()
            Me.pan_PhotoInfo_ButtonPanel = New System.Windows.Forms.Panel()
            Me.TabControl_Main.SuspendLayout()
            Me.Tab_PriceTagData.SuspendLayout()
            Me.Tab_RouterInfo.SuspendLayout()
            Me.Tab_StyleMsgArray.SuspendLayout()
            Me.Tab_PhotoInfo.SuspendLayout()
            Me.pan_StatusBar.SuspendLayout()
            Me.pan_PriceTagData_ButtonPanel.SuspendLayout()
            Me.pan_RouterInfo_ButtonPanel.SuspendLayout()
            Me.pan_StyleMsgArray_ButtonPanel.SuspendLayout()
            Me.pan_PhotoInfo_ButtonPanel.SuspendLayout()
            Me.SuspendLayout()
            '
            'TabControl_Main
            '
            Me.TabControl_Main.Controls.Add(Me.Tab_PriceTagData)
            Me.TabControl_Main.Controls.Add(Me.Tab_RouterInfo)
            Me.TabControl_Main.Controls.Add(Me.Tab_StyleMsgArray)
            Me.TabControl_Main.Controls.Add(Me.Tab_PhotoInfo)
            Me.TabControl_Main.Dock = System.Windows.Forms.DockStyle.Fill
            Me.TabControl_Main.Location = New System.Drawing.Point(0, 0)
            Me.TabControl_Main.Name = "TabControl_Main"
            Me.TabControl_Main.SelectedIndex = 0
            Me.TabControl_Main.Size = New System.Drawing.Size(800, 450)
            Me.TabControl_Main.TabIndex = 0
            '
             'Tab_PriceTagData
             '
             Me.Tab_PriceTagData.Controls.Add(Me.fro_dgv_PriceTagData)
             Me.Tab_PriceTagData.Controls.Add(Me.fro_btn_DeleteTagsByMac)
             Me.Tab_PriceTagData.Controls.Add(Me.fro_btn_Load_PriceTagData)
            Me.Tab_PriceTagData.Location = New System.Drawing.Point(4, 22)
            Me.Tab_PriceTagData.Name = "Tab_PriceTagData"
            Me.Tab_PriceTagData.Padding = New System.Windows.Forms.Padding(3)
            Me.Tab_PriceTagData.Size = New System.Drawing.Size(792, 424)
            Me.Tab_PriceTagData.TabIndex = 0
            Me.Tab_PriceTagData.Text = "Cenovky"
            Me.Tab_PriceTagData.UseVisualStyleBackColor = True
            '
            'fro_dgv_PriceTagData
            '
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_mac)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_ido)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_routerid)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_status)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_rssi)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_power)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_styleId)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_width)
            Me.fro_dgv_PriceTagData._Columns.Add(Me.cln_PriceTag_height)
            Me.fro_dgv_PriceTagData.DataList_UseColumns = True
            Me.fro_dgv_PriceTagData.Dock = System.Windows.Forms.DockStyle.Bottom
            Me.fro_dgv_PriceTagData.Location = New System.Drawing.Point(3, 39)
            Me.fro_dgv_PriceTagData.Name = "fro_dgv_PriceTagData"
            Me.fro_dgv_PriceTagData.Size = New System.Drawing.Size(786, 382)
            Me.fro_dgv_PriceTagData.TabIndex = 0
            Me.fro_dgv_PriceTagData.SourceType = Exa.Application.Controls.Simple.S_DataGrid.mod_DataGrid.enm_SourceTypes.VirtualMode
            Me.fro_dgv_PriceTagData.Visible = True
            '
             'fro_btn_Load_PriceTagData
             '
             Me.fro_btn_Load_PriceTagData._Text = "Načítať cenovky"
             Me.fro_btn_Load_PriceTagData.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_Load_PriceTagData.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_Load_PriceTagData.Location = New System.Drawing.Point(686, 6)
             Me.fro_btn_Load_PriceTagData.Name = "fro_btn_Load_PriceTagData"
             Me.fro_btn_Load_PriceTagData.Size = New System.Drawing.Size(103, 28)
             Me.fro_btn_Load_PriceTagData.TabIndex = 1
             Me.fro_btn_Load_PriceTagData.Visible = True
             '
             'fro_btn_DeleteTagsByMac
             '
             Me.fro_btn_DeleteTagsByMac._Text = "Zmazať cenovky"
             Me.fro_btn_DeleteTagsByMac.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_DeleteTagsByMac.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_DeleteTagsByMac.Location = New System.Drawing.Point(580, 6)
             Me.fro_btn_DeleteTagsByMac.Name = "fro_btn_DeleteTagsByMac"
             Me.fro_btn_DeleteTagsByMac.Size = New System.Drawing.Size(100, 28)
            Me.fro_btn_DeleteTagsByMac.TabIndex = 2
            Me.fro_btn_DeleteTagsByMac.Visible = True
            '
            'cln_PriceTag_mac


            '
            Me.cln_PriceTag_mac.DatabaseField = "mac"
            Me.cln_PriceTag_mac.Name = "cln_PriceTag_mac"
            Me.cln_PriceTag_mac.Text = "MAC Adresa"
            Me.cln_PriceTag_mac.Width = 120
            '
            'cln_PriceTag_ido
            '
            Me.cln_PriceTag_ido.DatabaseField = "ido"
            Me.cln_PriceTag_ido.Name = "cln_PriceTag_ido"
            Me.cln_PriceTag_ido.Text = "ID"
            Me.cln_PriceTag_ido.Width = 60
            '
            'cln_PriceTag_routerid
            '
            Me.cln_PriceTag_routerid.DatabaseField = "routerid"
            Me.cln_PriceTag_routerid.Name = "cln_PriceTag_routerid"
            Me.cln_PriceTag_routerid.Text = "Router ID"
            Me.cln_PriceTag_routerid.Width = 100
            '
            'cln_PriceTag_status
            '
            Me.cln_PriceTag_status.DatabaseField = "status"
            Me.cln_PriceTag_status.Name = "cln_PriceTag_status"
            Me.cln_PriceTag_status.Text = "Stav"
            Me.cln_PriceTag_status.Width = 60
            '
            'cln_PriceTag_rssi
            '
            Me.cln_PriceTag_rssi.DatabaseField = "rssi"
            Me.cln_PriceTag_rssi.Name = "cln_PriceTag_rssi"
            Me.cln_PriceTag_rssi.Text = "RSSI"
            Me.cln_PriceTag_rssi.Width = 80
            '
            'cln_PriceTag_power
            '
            Me.cln_PriceTag_power.DatabaseField = "power"
            Me.cln_PriceTag_power.Name = "cln_PriceTag_power"
            Me.cln_PriceTag_power.Text = "Napájanie"
            Me.cln_PriceTag_power.Width = 80
            '
            'cln_PriceTag_styleId
            '
            Me.cln_PriceTag_styleId.DatabaseField = "styleId"
            Me.cln_PriceTag_styleId.Name = "cln_PriceTag_styleId"
            Me.cln_PriceTag_styleId.Text = "Šablóna ID"
            Me.cln_PriceTag_styleId.Width = 90
            '
            'cln_PriceTag_width
            '
            Me.cln_PriceTag_width.DatabaseField = "width"
            Me.cln_PriceTag_width.Name = "cln_PriceTag_width"
            Me.cln_PriceTag_width.Text = "Šírka"
            Me.cln_PriceTag_width.Width = 70
            '
            'cln_PriceTag_height
            '
            Me.cln_PriceTag_height.DatabaseField = "height"
            Me.cln_PriceTag_height.Name = "cln_PriceTag_height"
            Me.cln_PriceTag_height.Text = "Výška"
            Me.cln_PriceTag_height.Width = 70
            '
            'Tab_RouterInfo
            '
            Me.Tab_RouterInfo.Controls.Add(Me.fro_dgv_RouterInfo)
            Me.Tab_RouterInfo.Controls.Add(Me.pan_RouterInfo_ButtonPanel)
            Me.Tab_RouterInfo.Location = New System.Drawing.Point(4, 22)
            Me.Tab_RouterInfo.Name = "Tab_RouterInfo"
            Me.Tab_RouterInfo.Padding = New System.Windows.Forms.Padding(3)
            Me.Tab_RouterInfo.Size = New System.Drawing.Size(792, 424)
            Me.Tab_RouterInfo.TabIndex = 1
            Me.Tab_RouterInfo.Text = "Routre"
            Me.Tab_RouterInfo.UseVisualStyleBackColor = True
            '
            'fro_dgv_RouterInfo
            '
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_routerID)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_routerIP)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_hardwareVersion)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_softwareVersion)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_freq)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_state)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_tagQuanty)
            Me.fro_dgv_RouterInfo._Columns.Add(Me.cln_Router_lastHeartbeatTime)
            Me.fro_dgv_RouterInfo.DataList_UseColumns = True
            Me.fro_dgv_RouterInfo.Dock = System.Windows.Forms.DockStyle.Fill
            Me.fro_dgv_RouterInfo.Location = New System.Drawing.Point(3, 3)
            Me.fro_dgv_RouterInfo.Name = "fro_dgv_RouterInfo"
            Me.fro_dgv_RouterInfo.Size = New System.Drawing.Size(786, 377)
            Me.fro_dgv_RouterInfo.TabIndex = 0
            Me.fro_dgv_RouterInfo.SourceType = Exa.Application.Controls.Simple.S_DataGrid.mod_DataGrid.enm_SourceTypes.VirtualMode
            Me.fro_dgv_RouterInfo.Visible = True
            '
            'pan_RouterInfo_ButtonPanel
            '
            Me.pan_RouterInfo_ButtonPanel.Controls.Add(Me.fro_btn_Load_RouterInfo)
            Me.pan_RouterInfo_ButtonPanel.Dock = System.Windows.Forms.DockStyle.Top
            Me.pan_RouterInfo_ButtonPanel.Location = New System.Drawing.Point(3, 3)
            Me.pan_RouterInfo_ButtonPanel.Name = "pan_RouterInfo_ButtonPanel"
            Me.pan_RouterInfo_ButtonPanel.Size = New System.Drawing.Size(786, 36)
            Me.pan_RouterInfo_ButtonPanel.TabIndex = 2
            '
            'fro_btn_Load_RouterInfo
            '
            Me.fro_btn_Load_RouterInfo._Text = "Načítať routre"
            Me.fro_btn_Load_RouterInfo.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Load_RouterInfo.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
            Me.fro_btn_Load_RouterInfo.Location = New System.Drawing.Point(686, 6)
            Me.fro_btn_Load_RouterInfo.Name = "fro_btn_Load_RouterInfo"
            Me.fro_btn_Load_RouterInfo.Size = New System.Drawing.Size(103, 28)
            Me.fro_btn_Load_RouterInfo.TabIndex = 0
            Me.fro_btn_Load_RouterInfo.Visible = True
            '
            'cln_Router_routerID
            '
            Me.cln_Router_routerID.DatabaseField = "routerID"
            Me.cln_Router_routerID.Name = "cln_Router_routerID"
            Me.cln_Router_routerID.Text = "Router ID"
            Me.cln_Router_routerID.Width = 80
            '
            'cln_Router_routerIP
            '
            Me.cln_Router_routerIP.DatabaseField = "routerIP"
            Me.cln_Router_routerIP.Name = "cln_Router_routerIP"
            Me.cln_Router_routerIP.Text = "IP Adresa"
            Me.cln_Router_routerIP.Width = 120
            '
            'cln_Router_hardwareVersion
            '
            Me.cln_Router_hardwareVersion.DatabaseField = "hardwareVersion"
            Me.cln_Router_hardwareVersion.Name = "cln_Router_hardwareVersion"
            Me.cln_Router_hardwareVersion.Text = "HW Verzia"
            Me.cln_Router_hardwareVersion.Width = 100
            '
            'cln_Router_softwareVersion
            '
            Me.cln_Router_softwareVersion.DatabaseField = "softwareVersion"
            Me.cln_Router_softwareVersion.Name = "cln_Router_softwareVersion"
            Me.cln_Router_softwareVersion.Text = "SW Verzia"
            Me.cln_Router_softwareVersion.Width = 100
            '
            'cln_Router_freq
            '
            Me.cln_Router_freq.DatabaseField = "freq"
            Me.cln_Router_freq.Name = "cln_Router_freq"
            Me.cln_Router_freq.Text = "Frekvencia"
            Me.cln_Router_freq.Width = 80
            '
            'cln_Router_state
            '
            Me.cln_Router_state.DatabaseField = "state"
            Me.cln_Router_state.Name = "cln_Router_state"
            Me.cln_Router_state.Text = "Stav"
            Me.cln_Router_state.Width = 60
            '
            'cln_Router_tagQuanty
            '
            Me.cln_Router_tagQuanty.DatabaseField = "tagQuanty"
            Me.cln_Router_tagQuanty.Name = "cln_Router_tagQuanty"
            Me.cln_Router_tagQuanty.Text = "Počet cenoviek"
            Me.cln_Router_tagQuanty.Width = 100
            '
            'cln_Router_lastHeartbeatTime
            '
            Me.cln_Router_lastHeartbeatTime.DatabaseField = "lastHeartbeatTime"
            Me.cln_Router_lastHeartbeatTime.Name = "cln_Router_lastHeartbeatTime"
            Me.cln_Router_lastHeartbeatTime.Text = "Posledný heartbeat"
            Me.cln_Router_lastHeartbeatTime.Width = 130
            '
            'fro_btn_Load_RouterInfo
            '
            Me.fro_btn_Load_RouterInfo._Text = "Načítať routre"
            Me.fro_btn_Load_RouterInfo.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Load_RouterInfo.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
            Me.fro_btn_Load_RouterInfo.Location = New System.Drawing.Point(686, 3)
            Me.fro_btn_Load_RouterInfo.Name = "fro_btn_Load_RouterInfo"
            Me.fro_btn_Load_RouterInfo.Size = New System.Drawing.Size(103, 28)
            Me.fro_btn_Load_RouterInfo.TabIndex = 1
            '
            'Tab_StyleMsgArray
            '
            Me.Tab_StyleMsgArray.Controls.Add(Me.fro_dgv_StyleMsgArray)
            Me.Tab_StyleMsgArray.Controls.Add(Me.pan_StyleMsgArray_ButtonPanel)
            Me.Tab_StyleMsgArray.Location = New System.Drawing.Point(4, 22)
            Me.Tab_StyleMsgArray.Name = "Tab_StyleMsgArray"
            Me.Tab_StyleMsgArray.Padding = New System.Windows.Forms.Padding(3)
            Me.Tab_StyleMsgArray.Size = New System.Drawing.Size(792, 424)
            Me.Tab_StyleMsgArray.TabIndex = 2
            Me.Tab_StyleMsgArray.Text = "Šablóny"
            Me.Tab_StyleMsgArray.UseVisualStyleBackColor = True
            '
            'fro_dgv_StyleMsgArray
            '
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_id)
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_name)
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_type)
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_width)
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_height)
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_backgroundID)
            Me.fro_dgv_StyleMsgArray._Columns.Add(Me.cln_Style_updateTime)
            Me.fro_dgv_StyleMsgArray.DataList_UseColumns = True
            Me.fro_dgv_StyleMsgArray.Dock = System.Windows.Forms.DockStyle.Fill
            Me.fro_dgv_StyleMsgArray.Location = New System.Drawing.Point(3, 3)
            Me.fro_dgv_StyleMsgArray.Name = "fro_dgv_StyleMsgArray"
            Me.fro_dgv_StyleMsgArray.Size = New System.Drawing.Size(786, 377)
            Me.fro_dgv_StyleMsgArray.TabIndex = 0
            Me.fro_dgv_StyleMsgArray.SourceType = Exa.Application.Controls.Simple.S_DataGrid.mod_DataGrid.enm_SourceTypes.VirtualMode
            Me.fro_dgv_StyleMsgArray.Visible = True
            '
             'pan_StyleMsgArray_ButtonPanel
             '
             Me.pan_StyleMsgArray_ButtonPanel.Controls.Add(Me.fro_btn_Load_StyleMsgArray)
             Me.pan_StyleMsgArray_ButtonPanel.Controls.Add(Me.fro_btn_Load_StyleMsgById)
             Me.pan_StyleMsgArray_ButtonPanel.Dock = System.Windows.Forms.DockStyle.Top
             Me.pan_StyleMsgArray_ButtonPanel.Location = New System.Drawing.Point(3, 3)
             Me.pan_StyleMsgArray_ButtonPanel.Name = "pan_StyleMsgArray_ButtonPanel"
             Me.pan_StyleMsgArray_ButtonPanel.Size = New System.Drawing.Size(786, 36)
             Me.pan_StyleMsgArray_ButtonPanel.TabIndex = 2
             '
             'fro_btn_Load_StyleMsgArray
             '
             Me.fro_btn_Load_StyleMsgArray._Text = "Načítať šablóny"
             Me.fro_btn_Load_StyleMsgArray.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_Load_StyleMsgArray.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_Load_StyleMsgArray.Location = New System.Drawing.Point(580, 6)
             Me.fro_btn_Load_StyleMsgArray.Name = "fro_btn_Load_StyleMsgArray"
             Me.fro_btn_Load_StyleMsgArray.Size = New System.Drawing.Size(100, 28)
             Me.fro_btn_Load_StyleMsgArray.TabIndex = 0
             Me.fro_btn_Load_StyleMsgArray.Visible = True
             '
             'fro_btn_Load_StyleMsgById
             '
             Me.fro_btn_Load_StyleMsgById._Text = "Detail šablóny"
             Me.fro_btn_Load_StyleMsgById.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_Load_StyleMsgById.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
            Me.fro_btn_Load_StyleMsgById.Location = New System.Drawing.Point(386, 3)
            Me.fro_btn_Load_StyleMsgById.Name = "fro_btn_Load_StyleMsgById"
             Me.fro_btn_Load_StyleMsgById.Size = New System.Drawing.Size(100, 28)
             Me.fro_btn_Load_StyleMsgById.TabIndex = 1
             Me.fro_btn_Load_StyleMsgById.Visible = True
            '
            'cln_Style_id
            '
            Me.cln_Style_id.DatabaseField = "id"
            Me.cln_Style_id.Name = "cln_Style_id"
            Me.cln_Style_id.Text = "ID Šablóny"
            Me.cln_Style_id.Width = 90
            '
            'cln_Style_name
            '
            Me.cln_Style_name.DatabaseField = "name"
            Me.cln_Style_name.Name = "cln_Style_name"
            Me.cln_Style_name.Text = "Názov"
            Me.cln_Style_name.Width = 200
            '
            'cln_Style_type
            '
            Me.cln_Style_type.DatabaseField = "type"
            Me.cln_Style_type.Name = "cln_Style_type"
            Me.cln_Style_type.Text = "Typ"
            Me.cln_Style_type.Width = 60
            '
            'cln_Style_width
            '
            Me.cln_Style_width.DatabaseField = "width"
            Me.cln_Style_width.Name = "cln_Style_width"
            Me.cln_Style_width.Text = "Šírka"
            Me.cln_Style_width.Width = 70
            '
            'cln_Style_height
            '
            Me.cln_Style_height.DatabaseField = "height"
            Me.cln_Style_height.Name = "cln_Style_height"
            Me.cln_Style_height.Text = "Výška"
            Me.cln_Style_height.Width = 70
            '
            'cln_Style_backgroundID
            '
            Me.cln_Style_backgroundID.DatabaseField = "backgroundID"
            Me.cln_Style_backgroundID.Name = "cln_Style_backgroundID"
            Me.cln_Style_backgroundID.Text = "Pozadie ID"
            Me.cln_Style_backgroundID.Width = 90
            '
            'cln_Style_updateTime
            '
            Me.cln_Style_updateTime.DatabaseField = "updateTime"
            Me.cln_Style_updateTime.Name = "cln_Style_updateTime"
            Me.cln_Style_updateTime.Text = "Aktualizácia"
            Me.cln_Style_updateTime.Width = 140
            '
            'fro_btn_Load_StyleMsgArray
            '
            Me.fro_btn_Load_StyleMsgArray._Text = "Načítať šablóny"
            Me.fro_btn_Load_StyleMsgArray.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Load_StyleMsgArray.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
            Me.fro_btn_Load_StyleMsgArray.Location = New System.Drawing.Point(186, 3)
            Me.fro_btn_Load_StyleMsgArray.Name = "fro_btn_Load_StyleMsgArray"
            Me.fro_btn_Load_StyleMsgArray.Size = New System.Drawing.Size(103, 28)
            Me.fro_btn_Load_StyleMsgArray.TabIndex = 1
            '
            'Tab_PhotoInfo
            '
            Me.Tab_PhotoInfo.Controls.Add(Me.fro_dgv_PhotoInfo)
            Me.Tab_PhotoInfo.Controls.Add(Me.pan_PhotoInfo_ButtonPanel)
            Me.Tab_PhotoInfo.Location = New System.Drawing.Point(4, 22)
            Me.Tab_PhotoInfo.Name = "Tab_PhotoInfo"
            Me.Tab_PhotoInfo.Padding = New System.Windows.Forms.Padding(3)
            Me.Tab_PhotoInfo.Size = New System.Drawing.Size(792, 424)
            Me.Tab_PhotoInfo.TabIndex = 3
            Me.Tab_PhotoInfo.Text = "Obrázky"
            Me.Tab_PhotoInfo.UseVisualStyleBackColor = True
            '
            'fro_dgv_PhotoInfo
            '
            Me.fro_dgv_PhotoInfo._Columns.Add(Me.cln_Photo_id)
            Me.fro_dgv_PhotoInfo._Columns.Add(Me.cln_Photo_name)
            Me.fro_dgv_PhotoInfo._Columns.Add(Me.cln_Photo_width)
            Me.fro_dgv_PhotoInfo._Columns.Add(Me.cln_Photo_height)
            Me.fro_dgv_PhotoInfo.DataList_UseColumns = True
            Me.fro_dgv_PhotoInfo.Dock = System.Windows.Forms.DockStyle.Fill
            Me.fro_dgv_PhotoInfo.Location = New System.Drawing.Point(3, 3)
            Me.fro_dgv_PhotoInfo.Name = "fro_dgv_PhotoInfo"
            Me.fro_dgv_PhotoInfo.Size = New System.Drawing.Size(786, 377)
            Me.fro_dgv_PhotoInfo.TabIndex = 0
            Me.fro_dgv_PhotoInfo.SourceType = Exa.Application.Controls.Simple.S_DataGrid.mod_DataGrid.enm_SourceTypes.VirtualMode
            Me.fro_dgv_PhotoInfo.Visible = True
            '
             'pan_PhotoInfo_ButtonPanel
             '
             Me.pan_PhotoInfo_ButtonPanel.Controls.Add(Me.fro_btn_DeletePhoto)
             Me.pan_PhotoInfo_ButtonPanel.Controls.Add(Me.fro_btn_UploadPhoto)
             Me.pan_PhotoInfo_ButtonPanel.Controls.Add(Me.fro_btn_Load_PhotoImage)
             Me.pan_PhotoInfo_ButtonPanel.Controls.Add(Me.fro_btn_Load_PhotoInfo)
             Me.pan_PhotoInfo_ButtonPanel.Dock = System.Windows.Forms.DockStyle.Top
             Me.pan_PhotoInfo_ButtonPanel.Location = New System.Drawing.Point(3, 3)
             Me.pan_PhotoInfo_ButtonPanel.Name = "pan_PhotoInfo_ButtonPanel"
             Me.pan_PhotoInfo_ButtonPanel.Size = New System.Drawing.Size(786, 36)
             Me.pan_PhotoInfo_ButtonPanel.TabIndex = 2
             '
             'fro_btn_UploadPhoto
             '
             Me.fro_btn_UploadPhoto._Text = "Nahrať obrázok"
             Me.fro_btn_UploadPhoto.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_UploadPhoto.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_UploadPhoto.Location = New System.Drawing.Point(480, 3)
             Me.fro_btn_UploadPhoto.Name = "fro_btn_UploadPhoto"
             Me.fro_btn_UploadPhoto.Size = New System.Drawing.Size(100, 28)
             Me.fro_btn_UploadPhoto.TabIndex = 3
             Me.fro_btn_UploadPhoto.Visible = True
             '
             'fro_btn_DeletePhoto
             '
             Me.fro_btn_DeletePhoto._Text = "Vymazať obrázok"
             Me.fro_btn_DeletePhoto.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_DeletePhoto.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_DeletePhoto.Location = New System.Drawing.Point(380, 3)
             Me.fro_btn_DeletePhoto.Name = "fro_btn_DeletePhoto"
             Me.fro_btn_DeletePhoto.Size = New System.Drawing.Size(100, 28)
             Me.fro_btn_DeletePhoto.TabIndex = 4
             Me.fro_btn_DeletePhoto.Visible = True
             '
             'fro_btn_Load_PhotoInfo

            '
            Me.fro_btn_Load_PhotoInfo._Text = "Načítať obrázky"
            Me.fro_btn_Load_PhotoInfo.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Load_PhotoInfo.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
            Me.fro_btn_Load_PhotoInfo.Location = New System.Drawing.Point(686, 6)
            Me.fro_btn_Load_PhotoInfo.Name = "fro_btn_Load_PhotoInfo"
            Me.fro_btn_Load_PhotoInfo.Size = New System.Drawing.Size(103, 28)
            Me.fro_btn_Load_PhotoInfo.TabIndex = 0
            Me.fro_btn_Load_PhotoInfo.Visible = True
            '
            'cln_Photo_id
            '
            Me.cln_Photo_id.DatabaseField = "id"
            Me.cln_Photo_id.Name = "cln_Photo_id"
            Me.cln_Photo_id.Text = "ID"
            Me.cln_Photo_id.Width = 60
            '
            'cln_Photo_name
            '
            Me.cln_Photo_name.DatabaseField = "name"
            Me.cln_Photo_name.Name = "cln_Photo_name"
            Me.cln_Photo_name.Text = "Názov obrázku"
            Me.cln_Photo_name.Width = 250
            '
            'cln_Photo_width
            '
            Me.cln_Photo_width.DatabaseField = "width"
            Me.cln_Photo_width.Name = "cln_Photo_width"
            Me.cln_Photo_width.Text = "Šírka"
            Me.cln_Photo_width.Width = 70
            '
            'cln_Photo_height
            '
            Me.cln_Photo_height.DatabaseField = "height"
            Me.cln_Photo_height.Name = "cln_Photo_height"
            Me.cln_Photo_height.Text = "Výška"
            Me.cln_Photo_height.Width = 70
            '
             'fro_btn_Load_PhotoInfo
             '
             Me.fro_btn_Load_PhotoInfo._Text = "Načítať obrázky"
             Me.fro_btn_Load_PhotoInfo.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_Load_PhotoInfo.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_Load_PhotoInfo.Location = New System.Drawing.Point(686, 3)
             Me.fro_btn_Load_PhotoInfo.Name = "fro_btn_Load_PhotoInfo"
             Me.fro_btn_Load_PhotoInfo.Size = New System.Drawing.Size(103, 28)
             Me.fro_btn_Load_PhotoInfo.TabIndex = 1
             '
             'fro_btn_Load_PhotoImage
             '
             Me.fro_btn_Load_PhotoImage._Text = "Načítať obrázok"
             Me.fro_btn_Load_PhotoImage.Anchor = CType(System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
             Me.fro_btn_Load_PhotoImage.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.None
             Me.fro_btn_Load_PhotoImage.Location = New System.Drawing.Point(580, 3)
             Me.fro_btn_Load_PhotoImage.Name = "fro_btn_Load_PhotoImage"
             Me.fro_btn_Load_PhotoImage.Size = New System.Drawing.Size(100, 28)
             Me.fro_btn_Load_PhotoImage.TabIndex = 2
             Me.fro_btn_Load_PhotoImage.Visible = True
             '
            'pan_StatusBar
            '
            Me.pan_StatusBar.Controls.Add(Me.fro_lbl_Status)
            Me.pan_StatusBar.Controls.Add(Me.fro_btn_Zatvorit)
            Me.pan_StatusBar.Dock = System.Windows.Forms.DockStyle.Bottom
            Me.pan_StatusBar.Location = New System.Drawing.Point(0, 450)
            Me.pan_StatusBar.Name = "pan_StatusBar"
            Me.pan_StatusBar.Size = New System.Drawing.Size(800, 35)
            Me.pan_StatusBar.TabIndex = 1
            '
            'fro_lbl_Status
            '
            Me.fro_lbl_Status.AutoSize = True
            Me.fro_lbl_Status.Location = New System.Drawing.Point(10, 10)
            Me.fro_lbl_Status.Name = "fro_lbl_Status"
            Me.fro_lbl_Status.Size = New System.Drawing.Size(50, 13)
            Me.fro_lbl_Status.TabIndex = 0
            Me.fro_lbl_Status.Text = "Pripravené"
            '
            'fro_btn_Zatvorit
            '
            Me.fro_btn_Zatvorit._Text = "Zatvoriť"
            Me.fro_btn_Zatvorit.Anchor = CType(System.Windows.Forms.AnchorStyles.Bottom Or System.Windows.Forms.AnchorStyles.Right, System.Windows.Forms.AnchorStyles)
            Me.fro_btn_Zatvorit.ButtonAction = Exa.Application.Controls.Simple.S_Button.mod_Button.enm_ActionTypes.Cancel
            Me.fro_btn_Zatvorit.Location = New System.Drawing.Point(704, 4)
            Me.fro_btn_Zatvorit.Name = "fro_btn_Zatvorit"
            Me.fro_btn_Zatvorit.Size = New System.Drawing.Size(90, 28)
            Me.fro_btn_Zatvorit.TabIndex = 1
            '
            'frm_ElectronicPriceTags_List
            '
            Me.AutoScaleDimensions = New System.Drawing.SizeF(6.0!, 13.0!)
            Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
            Me.ClientSize = New System.Drawing.Size(800, 485)
            Me.Controls.Add(Me.TabControl_Main)
            Me.Controls.Add(Me.pan_StatusBar)
            Me.Name = "frm_ElectronicPriceTags_List"
            Me.Text = "Elektronické cenovky"
            Me.TabControl_Main.ResumeLayout(False)
            Me.Tab_PriceTagData.ResumeLayout(False)
            Me.Tab_RouterInfo.ResumeLayout(False)
            Me.Tab_StyleMsgArray.ResumeLayout(False)
            Me.Tab_PhotoInfo.ResumeLayout(False)
            Me.pan_StatusBar.ResumeLayout(False)
            Me.pan_StatusBar.PerformLayout()
            Me.ResumeLayout(False)

        End Sub

        'Windows Form Designer generated code end

        Friend WithEvents TabControl_Main As System.Windows.Forms.TabControl
        Friend WithEvents Tab_PriceTagData As System.Windows.Forms.TabPage
        Friend WithEvents Tab_RouterInfo As System.Windows.Forms.TabPage
        Friend WithEvents Tab_StyleMsgArray As System.Windows.Forms.TabPage
        Friend WithEvents Tab_PhotoInfo As System.Windows.Forms.TabPage
        Friend WithEvents pan_StatusBar As Exa.Application.Controls.Microsoft.M_Panel
        Friend WithEvents fro_lbl_Status As Exa.Application.Controls.Simple.S_Label.BaseControls.S_Label_Win32
        Friend WithEvents fro_btn_Zatvorit As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
        Friend WithEvents pan_PriceTagData_ButtonPanel As System.Windows.Forms.Panel
        Friend WithEvents pan_RouterInfo_ButtonPanel As System.Windows.Forms.Panel
        Friend WithEvents pan_StyleMsgArray_ButtonPanel As System.Windows.Forms.Panel
        Friend WithEvents pan_PhotoInfo_ButtonPanel As System.Windows.Forms.Panel

        ' PriceTagData columns
        Friend WithEvents fro_dgv_PriceTagData As Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32
        Friend WithEvents cln_PriceTag_mac As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_ido As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_routerid As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_status As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_rssi As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_power As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_styleId As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_width As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_PriceTag_height As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
         Friend WithEvents fro_btn_Load_PriceTagData As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
         Friend WithEvents fro_btn_DeleteTagsByMac As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32


        ' RouterInfo columns
        Friend WithEvents fro_dgv_RouterInfo As Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32
        Friend WithEvents cln_Router_routerID As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_routerIP As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_hardwareVersion As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_softwareVersion As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_freq As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_state As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_tagQuanty As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Router_lastHeartbeatTime As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents fro_btn_Load_RouterInfo As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32

        ' StyleMsgArray columns
        Friend WithEvents fro_dgv_StyleMsgArray As Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32
        Friend WithEvents cln_Style_id As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Style_name As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Style_type As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Style_width As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Style_height As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Style_backgroundID As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Style_updateTime As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents fro_btn_Load_StyleMsgArray As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
        Friend WithEvents fro_btn_Load_StyleMsgById As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32

        ' PhotoInfo columns
        Friend WithEvents fro_dgv_PhotoInfo As Exa.Application.Controls.Simple.S_DataGrid.BaseControls.S_DataGrid_Win32
        Friend WithEvents cln_Photo_id As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Photo_name As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Photo_width As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
        Friend WithEvents cln_Photo_height As Exa.Application.Controls.Simple.S_DataGrid.DataGridColumnCollection.cls_DataGridColumn
         Friend WithEvents fro_btn_Load_PhotoInfo As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
         Friend WithEvents fro_btn_Load_PhotoImage As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
         Friend WithEvents fro_btn_UploadPhoto As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32
         Friend WithEvents fro_btn_DeletePhoto As Exa.Application.Controls.Simple.S_Button.BaseControls.S_Button_Win32



    End Class

End Namespace
