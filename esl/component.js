document.oncontextmenu = function (e) {
    e.preventDefault();
};

var bgData = "";
var moveid = "";
var photoDatas = "";

$(document).ready(function () {
    $("#editpanel").attr('tabindex', 1).keydown(function (event) {
        console.log(event.which);
        if (event.which == 46) {
            deleteData(moveObj.moveNode[0].id.replace('moveNode_', ''));
        }
    });
});

// 关闭添加字体模态框
function closeFont() {
    document.getElementById("zzk-div").style.display = "none";
    document.getElementById("addFont").style.display = "none";
}

// 打开添加字体模态框
function openFont() {
    document.getElementById("zzk-div").style.display = "block";
    document.getElementById("addFont").style.display = "block";
}

// 上传字体
function uploadFontFile() {
    // uploadFile就是后台接收的文件参数名称
    $("#fileForm").ajaxSubmit({
        url: "mms/uploadFont?filePath=" + $("#font-path").val() + "&fontName=" + $("#font-Name").val(),
        type: 'post',
        data: $("#fileForm").serialize(),
        dataType: "JSON",
        success: function (data) {
            alert(data.data);
            if (data.resultCode == -1) {
                return;
            }
            closeFont();
            console.log(data);
            location.reload();
        }
    })
}

$(function () {
    //localStorage.setItem("language","2");
    loadTable();
    moveEvent();
    checkEvent();
    var width = $("#sytleWidth").val();
    var height = $("#sytleHeight").val();
    $("#editpanel").css("width", width);
    $("#editpanel").css("height", height);
    initPhotoList();
    initStyleEvent();
    renderStyle();
    setStyleAlignOptionContent();
    setPhotoBglist();
    getPhotoByte();
    setUpdateScreenCode();
    try {
        setLanguageMData();
    } catch (e) {

    } finally {
        /*
         * ifontSize.innerHTML = "<option><button value='自定义'>自定义</button></option>" +
         * ifontSize.innerHTML;
         */
    }
});

/*
 * function setBySelf(val){ if(val == "自定义"){ div_fontSize.innerHTML = '<input
 * width="120px" class="select2 form-control" data-t="stylesel"
 * data-flag="font-size">'; } }
 */

function AddFontStyle() {
    var ihtml = fontStyleSelect.innerHTML;
    ihtml += '<option class="textMsg">' + fontStyleAdd.value + '</option>';
    document.getElementById("fontStyleSelect").innerHTML = ihtml;
}

var tid = 0;

// 初始化圖片數據
function initPhotoList() {
    var stylealignId = 0;
    var bgId = 0;
    try {
        stylealignId = stylealign.value;
        bgId = backgroundId.value;
    } catch (e) {
        return;
    }
    // 圖片名字
    var mobjName = "";
    try {
        mobjName = moveObj.moveNode[0].innerText;
    } catch (e) {
    }
    $.ajax({
        url: "style/getPhotoName?stylealignId=" + stylealignId + "&&styleid=" + parseInt(location.search.replace('?id=', '')),
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            photoDatas = resp.datalist;
            loadTable();
        },
        error: function (e) {
            console.log(e);
        }
    });
}

// 圖片列表
function setPhotolist() {
    var stylealignId = 0;
    var bgId = 0;
    try {
        stylealignId = stylealign.value;
        bgId = backgroundId.value;
    } catch (e) {
        return;
    }
    // 圖片名字
    var mobjName = "";
    try {
        mobjName = moveObj.moveNode[0].innerText;
    } catch (e) {
    }
    $.ajax({
        url: "style/getPhotoName?stylealignId=" + stylealignId + "&&styleid=" + parseInt(location.search.replace('?id=', '')),
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            var clen = resp.datalist.length;
            var vhtml = "<option value='0'>-</option>";
            for (let i = 0; i < clen; i++) {
                if (resp.datalist[i].name == mobjName) {
                    vhtml += "<option selected='selected' value='" + resp.datalist[i].id + "' >" + resp.datalist[i].name + "</option>";
                } else {
                    vhtml += "<option value='" + resp.datalist[i].id + "' >" + resp.datalist[i].name + "</option>";
                }
            }
            selectImgName.innerHTML = vhtml;
        },
        error: function (e) {
            console.log(e);
        }
    });
}

// 加載刷新屏幕代碼
function setUpdateScreenCode() {
    var mptype = 0;
    try {
        mptype = mappingtype.value;
    } catch (e) {
        return;
    }
    var styid = sytleId.value;
    var iText = '[{';
    iText += '"mac":"99.96.19.64"'
    iText += ',"mappingtype":' + mptype;
    iText += ',"styleid":' + styid;
    for (var key in datas) {
        var data = datas[key];
        iText += ',"' + data.mpname + '":"' + data.text + '"';
    }
    iText += '}]';
    interfaceCode.value = iText;
    interfaceAddr.value = location.protocol + "//" + location.hostname + "/esls_new/associate/updateScreen"
}

// 获取背景下拉框
function setPhotoBglist() {
    var stylealignId = 0;
    var bgId = 0;
    try {
        stylealignId = stylealign.value;
        bgId = backgroundId.value;
    } catch (e) {
        return;
    }
    $.ajax({
        url: "style/getBgMsg?stylealignId=" + stylealignId,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            var clen = resp.datalist.length;
            var vhtml = "<option value='0'>-</option>";
            for (let i = 0; i < clen; i++) {
                if (resp.datalist[i].id == bgId) {
                    vhtml += "<option selected='selected' value='" + resp.datalist[i].id + "' >" + resp.datalist[i].name + "</option>";
                } else {
                    vhtml += "<option value='" + resp.datalist[i].id + "' >" + resp.datalist[i].name + "</option>";
                }

            }
            backgroundImg.innerHTML = vhtml;
        },
        error: function (e) {
            console.log(e);
        }
    });
}

// 获取图片数据
function getPhotoDataByte(val) {
    var cval = selectImgName.selectedOptions[0].innerText;
    divtext.value = cval;
    var ckey = moveObj.moveNode[0].dataset.flag;
    datas[ckey].text = cval;
    document.getElementById("input_" + ckey).value = cval;
    $.ajax({
        url: "style/getBgImg?ImgId=" + val,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        success: function (resp) {
            moveObj.moveNode[0].style.background = "url(data:img/png;base64," + resp.datalist[0] + ")";
            moveObj.moveNode[0].style.backgroundSize = "100% 100%";
        },
        error: function (e) {
            console.log(e);
        }
    });
}

// 获取背景圖片數據(byte)
function getPhotoByte(val) {
    if (val == 0) {
        $
            .ajax({
                url: "style/removeBackground?mappingtype=" + mappingtype.value + "&styleid=" + sytleId.value,
                type: "POST",
                dataType: 'json',
                contentType: 'application/json',
                success: function (data) {
                    location.reload();
                },
                error: function (e) {
                    alert("getStylesData error");
                    console.log(e);
                }
            });
        return;
    }
    var stylealignId = 0;
    var bgId = 0;
    try {
        stylealignId = stylealign.value;
        bgId = backgroundId.value;
    } catch (e) {
        return;
    }
    if (backgroundImg.value == 0) {
        dBgId = backgroundId.value;
    } else {
        dBgId = backgroundImg.value;
    }
    if (dBgId == 0) {
        return;
    }
    bgData = "";
    $
        .ajax({
            url: "style/getBgImg?ImgId=" + dBgId,
            type: "POST",
            contentType: 'application/json; charset=UTF-8',
            dataType: "json",
            data: {},
            success: function (resp) {
                bgData = resp.datalist[0];
                $
                    .ajax({
                        url: "style/addColumnAndGood?columnName=background&mappingText=" + backgroundImg.selectedOptions[0].innerText + "&mappingtype=" + mappingtype.value + "&styleid=" + sytleId.value,
                        type: "POST",
                        dataType: 'json',
                        contentType: 'application/json',
                        success: function (data) {
                            loadTable();
                            addColumnPop.style.display = "none";
                        },
                        error: function (e) {
                            alert("getStylesData error");
                            console.log(e);
                        }
                    });
            },
            error: function (e) {
                console.log(e);
            }
        });
}

// 隐藏添加字段弹框
function closePop() {
    addColumnPop.style.display = "none";
    document.getElementById("zzk-div").style.display = "none";
}

// 显示添加字段弹框
function blockPop(dtype) {
    dmappingType.value = mappingtype.value;
    dmappingText.value = getLanguageContent(dtype);
    dcolumnName.value = dtype;
    /*
     * $.ajax({ url : "columnAndGood/getColumnAndGoodData", type : "POST",
     * dataType : 'json', contentType : 'application/json', success :
     * function(data) { var textList = data['textList']; var ihtml = ""; var
     * clen = textList.length; for (let i = 0; i < clen; i++) { ihtml += "<option
     * value='" + textList[i] + "'>" + textList[i] + "</option>"; }
     * mappingTextContent.innerHTML = ihtml; }, error : function() {
     * alert("getStylesData error"); } });
     */
    addColumnPop.style.display = "block";
    document.getElementById("zzk-div").style.display = "block";
}

// 添加字段保存
function addColumnAndGood() {
    var mappingtype = dmappingType.value;
    var columnName = dcolumnName.value;
    var mappingText = dmappingText.value;
    var dstyleid = sytleId.value;
    if (!mappingText) {
        alert(getLanguageContent("请添加字段名！"));
        return;
    }
    var list = [];
    for (var key in datas) {
        var data = datas[key];
        data.id = key;
        list.push(data);
    }
    $.ajax({
        url: "style/addColumnAndGood?columnName=" + columnName + "&mappingText=" + mappingText + "&mappingtype=" + mappingtype + "&styleid=" + dstyleid,
        type: "POST",
        dataType: 'json',
        contentType: 'application/json',
        success: function (data) {
            if (data == 0) {
                alert(getLanguageContent("该字段名已存在"));
                return;
            }
            $.ajax({
                type: "POST",
                url: "mms/updateDispMData?id=" + dstyleid,
                data: "orderJson=" + JSON.stringify(list),
                success: function (result) {
                    loadTable();
                    // caches.delete;
                    // Bootstrap Modal对话框（保存模板）关闭时触发事件
                },
                error: function (e) {
                    console.log(e);
                }
            });
            addColumnPop.style.display = "none";
            document.getElementById("zzk-div").style.display = "none";
        },
        error: function (e) {
            alert("getStylesData error");
            console.log(e);
        }
    });
}

// 保存樣式屬性{}
function saveStyle(sid) {
    var styleName = sytleNameAdd.value;
    var stylealign = stylealignId.value;
    $.ajax({
        url: "style/updateStyleAlign?styleid=" + sid + "&stylealign=" + stylealign + "&styleName=" + styleName,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            if (resp == 0) {
                return 0;
            }
            if (resp == 2) {
                alert(getLanguageContent("模板名称不能重复，请填写其他模板名称！"));
                return 2;
            }
            openComponent(sid);
        },
        error: function (e) {
            console.log(e);
        }
    });

}

// 保存样式属性（只保存不刷新）
function saveStyleAligns(sid) {
    var styleName = sytleNameAdd.value;
    var stylealign = stylealignId.value;
    $.ajax({
        url: "style/updateStyleAlign?styleid=" + sid + "&stylealign=" + stylealign + "&styleName=" + styleName,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            if (resp == 0) {
                return;
            }
        },
        error: function (e) {
            console.log(e);
        }
    });
}

// 打开样式配置页面
function openComponent(id) {
    window
        .open('mms/getDispMs?id=' + id + '', 'newWindow', 'width=' + (window.screen.availWidth) * 0.9 + ',height=' + (window.screen.availHeight) * 0.8 + ',top=40,left=40,toolbar=no,menubar=no,scrollbars=no, resizable=no,location=no, status=no');
}

// 弹出上传背景框
function blockBgPop() {
    var width = WidthAdd.value;
    var height = HeightAdd.value;
    ImgWidth.value = width;
    ImgHeight.value = height;
    addBgPop.style.display = "block";
}

// 弹出上传圖片框
function blockImgPop() {
    addImgPop.style.display = "block";
}

// 隱藏上傳圖片框
function hiddenImgPop() {
    addImgPop.style.display = "none";
}

// 隱藏上傳背景框
function hiddenBgPop() {
    addBgPop.style.display = "none";
}

function uploadImg() {
    $("#upload_PhotoImg").ajaxSubmit({
        url: "style/uploadPhoto",
        type: "post",
        data: $("#upload_PhotoImg").serialize(),
        dataType: "JSON",
        success: function (resp) {
            // 关闭所有弹出层
            hiddenImgPop();
            if (resp == 1) {
                alert(getLanguageContent("上传成功！"));
            } else if (resp == 0) {
                alert(getLanguageContent("上传失败！"));
            }
        }
    });
}

function uploadBgImg() {
    $("#upload_Photo").ajaxSubmit({
        url: "style/uploadPhoto",
        type: "post",
        data: $("#upload_Photo").serialize(),
        dataType: "JSON",
        success: function (resp) {
            // 关闭所有弹出层
            hiddenBgPop();
            if (resp == 1) {
                alert(getLanguageContent("上传成功！"));
                setPhotoBglist();
            } else if (resp == 0) {
                alert(getLanguageContent("上传失败！"));
            }
        }
    });
}

// 加载下拉选择框（模板类型）
function setStyleAlignOptionContent() {
    try {
        var d = stylealign.value;
    } catch (e) {
        return;
    }
    $.ajax({
        url: "mms/queryStyleAlign",
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            var data = resp;
            var datalist = data.datalist;
            var ihtml = "";
            for (let i = 0; i < datalist.length; i++) {
                if (datalist[i].id == stylealign.value) {
                    ihtml += '<option id="op' + datalist[i].id + '" value="' + datalist[i].id + '"  selected="selected">' + datalist[i].description + ' </option>';
                } else {
                    ihtml += '<option id="op' + datalist[i].id + '" value="' + datalist[i].id + '">' + datalist[i].description + '</option>';
                }
            }
            try {
                stylealignId.innerHTML = ihtml;
            } catch (e) {

            }
        }
    });
}

function initStyleEvent() {
    /*
     * $("#fontcolor, #backcolor").ColorPicker({ onSubmit : function(hsb, hex,
     * rgb, el) { $(el).val("#" + hex); $(el).ColorPickerHide(); renderStyle(); },
     * onBeforeShow : function() { $(this).ColorPickerSetColor(this.value); }
     * }).bind('keyup', function() { $(this).ColorPickerSetColor(this.value);
     * });
     */

    $("#styleSetPanel").find('input').blur(function () {
        renderStyle();
    });

    $("#stylefontw").click(function () {
        renderStyle();
    });

    $("#self-reacting").click(function () {
        renderStyle();
    });

    $("#text-decoration").click(function () {
        renderStyle();
    });

    $("#styleSetPanel").find('select[data-t="stylesel"]').change(function () {
        renderStyle();
    });

    $("#styleSetPanel").find('input[data-t="stylesel"]').change(function () {
        renderStyle();
    });
}

function getStyle() {
    var inputs = $("#styleSetPanel").find('input[data-t="styleinput"]');
    var css = {};
    for (var i = 0; i < inputs.size(); i++) {
        var input = inputs.eq(i);
        var flag = input.attr("data-flag");
        css[flag] = input.val() + "px";
    }
    var inputs = $("#styleSetPanel").find('input[data-t="stylecolor"]');
    for (var i = 0; i < inputs.size(); i++) {
        var input = inputs.eq(i);
        var flag = input.attr("data-flag");
        css[flag] = input.val();
    }

    var inputs = $("#styleSetPanel").find('select[data-t="stylesel"]');
    for (var i = 0; i < inputs.size(); i++) {
        var input = inputs.eq(i);
        var flag = input.attr("data-flag");
        css[flag] = input.val();
    }

    var inputs = $("#styleSetPanel").find('input[data-t="stylesel"]');
    for (var i = 0; i < inputs.size(); i++) {
        var input = inputs.eq(i);
        var flag = input.attr("data-flag");
        css[flag] = input.val() + "px";
    }

    try {
        if (css["text-align"] == "center") {
            // css["padding-top"] = ((parseInt(css["height"]) -
            // parseInt(css["font-size"]) ) / 2);
            // css["padding-top"] += "px";
            css["line-height"] = css["height"] + "px";
        } else {
            css["line-height"] = "";
        }
    } catch (e) {

    }

    css["font-weight"] = $('#stylefontw').is(':checked') ? "700" : "400";
    css["text-decoration"] = $('#text-decoration').is(':checked') ? "line-through" : "none";
    var prefix = $("#prefix").val();
    var suffix = $("#suffix").val();
    var text = $("#divtext").val();
    // var autoReacting = $("#self-reacting").val();
    if ($('#self-reacting').is(':checked')) {
        let fontsizeInt = parseInt(css["font-size"]);
        let widthInt = parseInt(css["width"])
        if (fontsizeInt * text.length > widthInt) {
            css["font-size"] = parseInt((widthInt - 5) / text.length) + "px";
        }
        css["autoReacting"] = $('#self-reacting').is(':checked') ? true : false;
    }

    var obj = {
        text: text, suffix: suffix, prefix: prefix, style: css
    }
    return obj;
}

// 处理图片控件属性
function setPhotoProperties() {
    if (moveObj.moveNodeData.type == "qrcode" || moveObj.moveNodeData.type == "barcode") {
        moreProperties.style.display = "none";
        selectImgData.style.display = "none";
        selectInputTextData.style.display = "block";

    } else if (moveObj.moveNodeData.type == "photo") {
        setPhotolist();
        selectImgData.style.display = "block";
        moreProperties.style.display = "none";
        selectInputTextData.style.display = "none";
    } else {
        moreProperties.style.display = "block";
        selectImgData.style.display = "none";
        selectInputTextData.style.display = "block";
    }
}

function renderStyle() {
    if (!moveObj.moveNode) {
        return;
        return;
    }
    var data = getStyle();

    for (var key in data) {
        moveObj.moveNodeData[key] = data[key];
    }
    var text = "";
    if (data.prefix) {
        text += data.prefix;
    }
    if (data.text) {
        text += data.text;
    }
    if (data.suffix) {
        text += data.suffix;
    }
    moveObj.moveNode[0].onmousedown = function (e) {
        console.log(e.button);
    }
    moveObj.moveNode.html(text + '<div class="scaleNode"></div>');
    moveObj.moveNode.css(data.style);
}

var datas = {
    "1": {
        name: "商品名字",
        table: "tb_tagsandgoods",
        feil: "name",
        type: "字符串",
        prefix: "",
        text: "商品名字",
        suffix: "",
        status: true,
        style: {
            "width": "100px",
            "height": "30px",
            "left": "0px",
            "top": "0px",
            "border-width": "1px",
            "background-color": "#000000",
            "color": "#ffffff",
            "font-size": "13px",
            "font-family": "宋体",
            "text-align": "left",
            "font-weight": "400"
        }
    }, "2": {
        name: "商品产地",
        table: "tb_tagsandgoods",
        feil: "orgin",
        type: "字符串",
        prefix: "",
        text: "商品产地",
        suffix: "",
        status: false,
        style: {
            left: "100px",
            top: "0px",
            width: "100px",
            height: "30px",
            "border-width": "1px",
            "color": "#000000",
            "background-color": "#ffffff",
            "font-size": "13px",
            "font-family": "宋体",
            "text-align": "left",
            "font-weight": "400"
        }
    }
}

function loadDatas() {
    var id = $("#sytleId").val();
    if (location.search == "?id=0") {
        location.href = location.origin + location.pathname + "?id=" + id;
    }
    $.ajax({
        async: false,
        type: "POST",
        url: "style/getDispMsData?id=" + id,
        dataType: 'json',
        contentType: 'application/json',
        success: function (data) {
            var data = eval('(' + data + ')');
            idatas = [];
            datas = [];
            $.each(data, function (key, obj) {
                datas[obj.id] = obj;
                datas[obj.id].text = obj.text;
            });
        },
        error: function (e) {
            alert("error");
        }
    });
}

function loadTable() {
    loadDatas();

    var editpanel = $("#editpanel").empty();
    var tbody = $("#grid-tbody").empty();

    for (var key in datas) {
        var data = datas[key];
        addData(editpanel, tbody, data, key);
    }
}

function addData(editpanel, tbody, data, key) {
    var html = [];

    // alert("key:" + key + " name:"+ data.name+" table:"+data.table + "
    // status:"+data.status);
    html.push('<tr id="row_' + key + '">');
    if (data.status) {
        html
            .push('	<td><input type="checkbox" checked="checked" data-sel="sel" data-flag="' + key + '"> </td>');
    } else {
        html.push('	<td><input type="checkbox" data-flag="' + key + '"> </td>');
    }
    /* html.push(' <td>' + data.name + '</td>'); */
    html.push('	<td>' + data.mpname + '</td>');
    html.push('	<td><input id="input_' + key + '" value="' + data.mpname + '"></td>');
    /*
     * html.push(' <td>' + data.table + '</td>'); html.push(' <td>' +
     * data.feil + '</td>'); html.push(' <td>' + data.type + '</td>');
     */
    html.push('	<td><button onclick="deleteData(\'' + key + '\')">‘' + getLanguageContent("删除") + '</button></td>');
    html.push('</tr>');
    tbody.append(html.join(""));

    var text = "";
    if (data.prefix) {
        text += data.prefix;
    }
    if (data.text) {
        text += data.text;
    }
    if (data.suffix) {
        text += data.suffix;
    }
    var css = data.style;
    var style = "";
    for (var _key in css) {
        style += _key + ":" + css[_key] + ";"
    }

    if (data.status) {
        html = [];
        if (data.type == "photo") {
            var phData = "";
            if (!data.text) {
                phData = "assets/img/defaultImg.jpg";
            } else {
                for (let i = 0; i < photoDatas.length; i++) {
                    if (data.text == photoDatas[i].name && photoDatas[i].bylist.length > 0) {
                        phData = "data:image/png;base64," + photoDatas[i].bylist[0];
                    }
                }
            }
            html.push('<div id="moveNode_' + key + '"  data-flag="' + key + '" title="' + data.name + '" class="portlet-body moveNode" style="' + style + ";background:url(" + phData + ");background-size: 100% 100%;z-index:2;" + '"  onclick="selectedNode(' + key + ')">');
            html.push('<div class="scaleNode"></div>');
            html.push('</div>');
        } else if (data.type == "background") {
            html.push('<div id="moveNode_' + key + '"  data-flag="' + key + '" title="' + data.name + '" class="" style="' + style + ";background:url(data:image/png;base64," + bgData + ");background-size: 100% 100%;z-index:1;" + '"  onclick="selectedNode(' + key + ')">');
            html.push('<div class="scaleNode"></div>');
            html.push('</div>');
        } else if (data.type == "qrcode") {
            html
                .push('<div id="moveNode_' + key + '"  data-flag="' + key + '" title="' + data.name + '" class="portlet-body moveNode" style="' + style + ";background:url(assets/img/defaultQrcode.jpg);background-size: 100% 100%;z-index:2;" + '"  onclick="selectedNode(' + key + ')">');
            html.push('<div class="scaleNode"></div>');
            html.push('</div>');

        } else if (data.type == "barcode") {
            html
                .push('<div id="moveNode_' + key + '"  data-flag="' + key + '" title="' + data.name + '" class="portlet-body moveNode" style="' + style + ";background:url(assets/img/defaultBarcode.jpg);background-size: 100% 100%;z-index:2;" + '"  onclick="selectedNode(' + key + ')">');
            html.push('<div class="scaleNode"></div>');
            html.push('</div>');

        } else {
            html.push('<div id="moveNode_' + key + '" data-flag="' + key + '" title="' + data.name + '" class="portlet-body moveNode" style="' + style + ';z-index:2;"  onclick="selectedNode(' + key + ')">');
            html.push(text);
            html.push('<div class="scaleNode"></div>');
            html.push('</div>');
        }
        editpanel.append(html.join(""))
    }
}

function deleteData(flag) {
    $("#moveNode_" + flag).remove();
    $("#row_" + flag).remove();
    if (moveObj.moveNodeData == datas[flag]) {
        moveObj = {};
    }
    delete datas[flag];
    $.ajax({
        url: 'style/delDismp',
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        data: JSON.stringify(flag),
        dataType: "json",
        success: function (data) {

        },
        error: function (err) {
            console.log(err);
        }
    });
}

function showMoveInfo() {
    // $("#moveInfo").text(JSON.stringify(moveObj.moveNodeData.style));
    $("#show_width").val(parseInt(moveObj.moveNodeData.style.width));
    $("#show_height").val(parseInt(moveObj.moveNodeData.style.height));
    $("#show_left").val(parseInt(moveObj.moveNodeData.style.left));
    $("#show_top").val(parseInt(moveObj.moveNodeData.style.top));
}

var moveObj = {};

function moveEvent() {
    $(".editpanel")
        .mousemove(function (e) {
            if (moveObj.isMove) {
                if (moveObj.type == "move") {
                    moveObj.moveLeft = moveObj.moveLeft + e.clientX - moveObj.moveDownX;
                    moveObj.moveTop = moveObj.moveTop + e.clientY - moveObj.moveDownY;
                    moveObj.moveDownX = e.clientX;
                    moveObj.moveDownY = e.clientY;
                    moveObj.moveNode.css({
                        left: moveObj.moveLeft + "px", top: moveObj.moveTop + "px"
                    });
                    renderPostion();
                } else if (moveObj.type == "resize") {
                    if (moveObj.moveNodeData.type == "qrcode") {
                        var mS;
                        if (moveObj.moveDownX > moveObj.moveDownY) {
                            mS = moveObj.moveDownX;
                        } else {
                            mS = moveObj.moveDownY;
                        }
                        moveObj.width = moveObj.width + e.clientX - mS;
                        moveObj.height = moveObj.width + e.clientX - mS;
                    } else {
                        moveObj.width = moveObj.width + e.clientX - moveObj.moveDownX;
                        moveObj.height = moveObj.height + e.clientY - moveObj.moveDownY;
                    }
                    if (moveObj.width < 10) {
                        moveObj.width = 10;
                    }
                    if (moveObj.height < 10) {
                        moveObj.height = 10;
                    }
                    moveObj.moveDownX = e.clientX;
                    moveObj.moveDownY = e.clientY;
                    moveObj.moveNode.width(moveObj.width).height(moveObj.height);
                    renderSize();
                }
            }
        })
        .mousedown(function (e) {
            var target = $(e.target);
            if (target.is(".moveNode")) {
                moveObj.type = "move";
                moveObj.isMove = true;
                moveObj.moveDownX = e.clientX;
                moveObj.moveDownY = e.clientY;
                moveObj.moveNode = target;
                moveObj.moveNodeData = datas[moveObj.moveNode
                    .attr("data-flag")];
                moveObj.moveLeft = parseInt(target.css("left"));
                moveObj.moveTop = parseInt(target.css("top"));
                showMoveInfo();
                moveObj.moveNode.css("border-color", "red");
                setProperties();
            } else if (target.is(".scaleNode")) {
                moveObj.type = "resize";
                moveObj.isMove = true;
                moveObj.moveNode = target.parent();
                moveObj.moveNodeData = datas[moveObj.moveNode
                    .attr("data-flag")];
                moveObj.moveDownX = e.clientX;
                moveObj.moveDownY = e.clientY;
                moveObj.width = moveObj.moveNode.width();
                moveObj.height = moveObj.moveNode.height();
                showMoveInfo();
                moveObj.moveNode.css("border-color", "red");
                setProperties();
            }
        })
        .mouseup(function (e) {
            try {
                moveObj.isMove = false;
                moveObj.moveNode.css("border-color", "#808080");
            } catch (e) {

            }
        })
        .mouseleave(function (e) {
            try {
                moveObj.isMove = false;
                // moveObj.moveNode.css("border-color", "#808080");
            } catch (e) {

            }
        })
        .mousedown(function (e) {
            try {
                setPhotoProperties();
                if (e.button == 2) {
                    var ehtml = e.target.innerHTML;
                    if (ehtml.indexOf("e-menu") > -1) {
                        return;
                    }
                    if (e.target.id.indexOf("moveNode") < 0) {
                        return;
                    }
                    e.target.innerHTML = ehtml + `<div class='e-menu' onclick='deleteData(` + e.target.id.replace('moveNode_', '') + `)'>${getLanguageContent("删除")}</div>`;
                }
            } catch (e) {

            }
        })
        .click(function (e) {
            try {
                var clen = document
                    .getElementsByClassName("moveNode").length;
                for (let i = 0; i < clen; i++) {
                    document.getElementsByClassName("moveNode")[i].style.border = "1px solid rgb(128, 128, 128)";
                }
                moveObj.moveNode[0].style.border = "3px dashed blue";
            } catch (e) {
            }

        });
}

function setProperties() {
    var data = moveObj.moveNodeData;
    $("#obj-title").text(`${data.name}-${getLanguageContent("属性")}(${data.mpname})`);
    $("#divtext").val(data.text);
    $("#prefix").val(data.prefix);
    $("#suffix").val(data.suffix);

    var style = moveObj.moveNodeData.style;
    var stylePanel = $("#styleSetPanel");
    if (style["font-size"]) {
        try {
            stylePanel.find('input[data-flag="font-size"]').val(parseInt(style["font-size"]));

        } catch (e) {
            stylePanel.find('select[data-flag="font-size"]').val(parseInt(style["font-size"]));
        }
    }

    if (style["color"]) {
        stylePanel.find('select[data-flag="color"]').val(style["color"]);
        stylePanel.find('input[data-flag="color"]').val(style["color"]);
    }

    if (style["background-color"]) {
        stylePanel.find('select[data-flag="background-color"]').val(style["background-color"]);
        stylePanel.find('input[data-flag="background-color"]').val(style["background-color"]);
    }

    if (style["font-family"]) {
        stylePanel.find('select[data-flag="font-family"]').val(style["font-family"]);
    }

    if (style["font-family"]) {
        stylePanel.find('select[data-flag="writing-mode"]').val(style["writing-mode"]);
    }

    if (style["text-align"]) {
        stylePanel.find('select[data-flag="text-align"]').val(style["text-align"]);
    }

    if (style["border-width"]) {
        stylePanel.find('input[data-flag="border-width"]').val(parseInt(style["border-width"]));
    }

    if (style["font-weight"] && style["font-weight"] == 700) {
        if (!$("#stylefontw").is(':checked')) {
            $("#stylefontw").click();
        }

    } else {
        if ($("#stylefontw").is(':checked')) {
            $("#stylefontw").click();
        }
    }

    if (style["text-decoration"] && style["text-decoration"] == "line-through") {
        if (!$("#text-decoration").is(':checked')) {
            $("#text-decoration").click();
        }
    } else {
        if ($("#text-decoration").is(':checked')) {
            $("#text-decoration").click();
        }
    }
    if (style["autoReacting"] && style["autoReacting"] == true) {
        if (!$("#self-reacting").is(':checked')) {
            $("#self-reacting").click();
        }
    } else {
        if ($("#self-reacting").is(':checked')) {
            $("#self-reacting").click();
        }
    }
}

function renderPostion() {
    moveObj.moveNodeData.style.left = moveObj.moveLeft + "px";
    moveObj.moveNodeData.style.top = moveObj.moveTop + "px";
    showMoveInfo();
}

function renderSize() {
    moveObj.moveNodeData.style.width = moveObj.width + "px";
    moveObj.moveNodeData.style.height = moveObj.height + "px";
    showMoveInfo();
}

function checkEvent() {
    $("#grid-tbody").click(function (e) {
        var target = $(e.target);
        if (target.is("input")) {
            var flag = target.attr("data-flag");
            var sel = target.attr("data-sel");
            if (sel == "sel") {
                var data = datas[flag];
                data.status = false;
                $("#moveNode_" + flag).remove();
                target.removeAttr("data-sel");
            } else {
                var data = datas[flag];
                target.attr("data-sel", "sel");
                var editpanel = $("#editpanel");
                data.status = true;
                var text = "";
                if (data.prefix) {
                    text += data.prefix;
                }
                if (data.text) {
                    text += data.text;
                }
                if (data.suffix) {
                    text += data.suffix;
                }
                var css = data.style;
                var style = "";
                if (style.width == 0) {
                    style.width = 20;
                }
                if (style.height == 0) {
                    style.height = 20;
                }
                for (var _key in css) {
                    style += _key + ":" + css[_key] + ";"
                }
                var html = [];
                html.push('<div id="moveNode_' + flag + '" title="' + data.name + '" class="moveNode" style="' + style + '"  data-flag="' + flag + '" onclick="selectedNode(' + flag + ')">');
                html.push(text);
                html.push('<div class="scaleNode"></div>');
                html.push('</div>');
                editpanel.append(html.join(""))
            }
        }
    });
}

function addToServer(id) {
    var list = [];
    for (var key in datas) {
        var data = datas[key];
        data.id = key;
        list.push(data);
    }
    // alert(JSON.stringify(list));
    $.ajax({
        type: "POST",
        url: "style/updateDispMData?id=" + id,
        data: "orderJson=" + JSON.stringify(list),
        success: function (result) {
            $('#myModalLabel').text(getLanguageContent("保存模板"));
            $('#myModalLabelInfo').text($('#sytleName').val() + getLanguageContent("保存成功!"));
            $("#myModal").modal({
                show: true, backdrop: false
            });
            $("#myModal").on('hide.bs.modal', function () {
                window.close();
            });
            // Bootstrap Modal对话框（保存模板）关闭时触发事件
        },
        error: function (e) {
            $('#myModalLabel').text(getLanguageContent("保存模板"));
            $('#myModalLabelInfo').text($('#sytleName').val() + getLanguageContent("保存失败!"));
            $("#myModal").modal({
                show: true, backdrop: false
            });
            $("#myModal").on('hide.bs.modal', function () {
                window.close();
            });
        }
    });
}

// ///////new 保存模板
function addToServerNew(id) {
    saveStyleAligns(id);
    var styleName = sytleNameAdd.value;
    var stylealign = stylealignId.value;
    $.ajax({
        url: "style/updateStyleAlign?styleid=" + id + "&stylealign=" + stylealign + "&styleName=" + styleName,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        data: {},
        success: function (resp) {
            if (resp == 0) {
                return;
            }
            if (resp == 2) {
                alert(getLanguageContent("模板名称不能重复，请填写其他模板名称！"));
                return;
            }
            var list = [];
            for (var key in datas) {
                if (datas[key] != null) {
                    var data = datas[key];
                    data.id = key;
                    list.push(data);
                }
            }
            // alert(JSON.stringify(list));
            $.ajax({
                type: "POST",
                url: "mms/updateDispMData?id=" + id,
                data: "orderJson=" + JSON.stringify(list),
                success: function (result) {
                    $('#myModalLabel').text(getLanguageContent("保存模板"));
                    $('#myModalLabelInfo')
                        .text($('#sytleName').val() + getLanguageContent("保存成功!"));
                    $("#myModal").modal({
                        show: true, backdrop: false
                    });
                    $("#myModal").on('hide.bs.modal', function () {
                        window.close();
                    });
                    // caches.delete;
                    // Bootstrap Modal对话框（保存模板）关闭时触发事件

                },
                error: function (e) {
                    $('#myModalLabel').text(getLanguageContent("保存模板"));
                    $('#myModalLabelInfo')
                        .text($('#sytleName').val() + getLanguageContent("保存失败!"));
                    $("#myModal").modal({
                        show: true, backdrop: false
                    });
                    $("#myModal").on('hide.bs.modal', function () {
                        window.close();
                    });
                }
            });
            openComponent(sid);
        },
        error: function (e) {
            console.log(e);
        }
    });
    if (res == 2) {
        return;
    }

}

function addRow() {
    $("#grid-tbody").append($("#addRow").val());
}

function addRowCancle(el) {
    var el = $(el);
    var row = el.parent().parent();
    row.remove();
}

function addRowOk(el) {
    var el = $(el);
    var row = el.parent().parent();
    var inputs = row.find("input");
    var obj = {
        prefix: "", text: "文本预览", suffix: "", style: {
            left: "0px",
            top: "0px",
            width: "100px",
            height: "100px",
            "border-width": "1px",
            "color": "#000000",
            "background-color": "#ffffff",
            "font-size": "13px",
            "font-family": "宋体",
            "text-align": "left",
            "font-weight": "400"
        }
    }
    inputs.each(function (i) {
        var el = $(this);
        var key = el.attr("name");
        var val = el.val();
        obj[key] = val;
    });
    var key = "d" + Math.round(Math.random() * 100000);
    datas[key] = obj;
    row.remove();
    var editpanel = $("#editpanel");
    var tbody = $("#grid-tbody");
    addData(editpanel, tbody, obj, key);
}

// 界面预览
function review() {
    if (document.getElementById("review").innerText == getLanguageContent("取消预览")) {
        document.getElementById("review").innerText = getLanguageContent("预览");
    } else {
        document.getElementById("review").innerText = getLanguageContent("取消预览");
    }
    for (key in datas) {
        var kval = document.getElementById("input_" + key).value;
        try {
            document.getElementById("moveNode_" + key).innerText = kval;
            if (document.getElementById("moveNode_" + key).style.border != "none") {
                document.getElementById("moveNode_" + key).style.border = "none";

            } else {
                document.getElementById("moveNode_" + key).style.border = "1px solid black";
            }

        } catch (e) {
            continue;
        }
    }
}

// 预览
function showPreview(id) {
    /*
     * for (key in datas) { let kval = document.getElementById("input_" +
     * key).value; datas[key].text = kval; }
     */
    var list = [];
    for (var key in datas) {
        if (key != null) {
            var data = datas[key];
            // data.id = key;
            list.push(data);
        }
    }
    $("#preview_model").show();
    // $("#preview_img").attr("src","style/previewImg?id=" + id+"?orderJson=" +
    // JSON.stringify(list));
    $.ajax({
        url: "style/previewImg?id=" + id,
        type: "POST",
        data: "orderJson=" + JSON.stringify(list),
        dataType: "json",
        responseType: "blob",
        success: function (data) {
            // alert(data);
            var sdata = data.replace('"', '').replace('"', '');
            var simg = "data:image/png;base64," + sdata;
            $("#preview_img").attr("src", simg);
            // $("#preview_img").attr("src", src);
        },
        error: function (e) {

        }
    });
}

// 隐藏
function hidePreview() {
    $("#preview_model").hide();
}

function selectedNode(sid) {
    this.tid = sid;
}

function changeText() {
    document.getElementById("input_" + tid).value = divtext.value;
}