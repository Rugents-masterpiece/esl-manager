var pageType = "";
var localStorge = 0;

var tableHead = [];
var currentPage = 1;

var tagHead = ["序号", "桌牌地址", "所属基站", "电池电量", "样式名称", "操作"];
var tagHeadAdd = ["序号", "桌牌地址"];
var routerHead = ["序号", "基站地址", "基站IP", "所属公司", "描述", "状态", "桌牌信息", "注册开关", "操作"];
var meetingHead = ["序号", "会议名称", "会议室", "开始时间", "结束时间", "模板", "桌牌数量", "尺寸",
    "创建时间", "操作"];
var meetingByPhoneHead = ["序号", "会议名称", "区域", "操作"];
var tagsByMeetHead = ["序号", "桌牌地址", "显示信息", "标签状态"];
var tableData = {};

var tagColumnConvert = {
    "id": "序号",
    "mac": "桌牌地址",
    "routerMac": "所属基站",
    "power": "电池电量",
    "state": "绑定状态",
    "updateProgress": "标签状态",
    "tags": "标签信息",
    "styleName": "样式名称"
};
var tagsByMeetColumnConvert = {
    "id": "序号",
    "mac": "桌牌地址",
    "sdata": "显示信息",
    /* "power" : "电池电量", */
    "state": "标签状态",
};

var routerColumnConvert = {
    "id": "序号",
    "mac": "基站地址",
    "ip": "基站IP",
    "shopName": "所属公司",
    "state": "状态",
    "description": "描述",
    "tagRegisterEN": "注册开关",
    "tags": "桌牌信息"
};

var meetingColumnConvert = {
    "id": "序号",
    "meetingName": "会议名称",
    "meetingRoom": "会议室",
    "startTime": "开始时间",
    "endTime": "结束时间",
    "modelName": "模板",
    "tagNum": "桌牌数量",
    "styleLen": "尺寸",
    "createTime": "创建时间"
};

// ///////////////////////////////////////////////////////////////////////////////////////////////////////////

// 弹窗内容
var popData = [];
// 弹窗操作内容
var opreateFunc = ['popSave()', 'popCannel()'];

// 创建Input内容
function createInputContent(obj) {
    return `<div class="div-input-style"><span class="span-input-title">${obj.label}</span>
        <input type="text" class="input-style-text" name="${obj.name}" id="${obj.id}" value="${obj.value}" /></div>`;
}

// 创建操作按钮内容
function createOpreateContent(opreateFunc) {
    return `<div class="div-opreate-style"><button class="pop-window-save" onclick="${opreateFunc[0]}" type="button">
    确定</button><button class="pop-window-cannel" onclick="${opreateFunc[1]}" type="button">取消</button></div>`;
}

// 创建弹窗内容
function addPopData(tid) {
    var textValue = document.getElementById(tid).value;
    var textArr = textValue.replace(/'/g, '').split(",");
    var alen = textArr.length;
    for (var i = 0; i < alen; i++) {
        var textOneArr = textArr[i].split(":");
        var popDataOne = {};
        popDataOne.id = "id_" + textOneArr[0];
        popDataOne.name = "name_" + textOneArr[0];
        popDataOne.label = textOneArr[0];
        popDataOne.value = textOneArr[1];
        popData[i] = popDataOne;
    }
    return popData;
}

// 创建添加弹窗
function createPopWindow(tid) {
    var data = addPopData("textarea" + tid);
    var len = data.length;
    if (!len) {
        return;
    }
    var usingData = "";
    var smappingtype = mappingtype.value;
    $
        .ajax({
            url: 'mms/queryUsingColumn?&tid=' + tid
                + '&mappingtype=' + smappingtype,
            type: "get",
            contentType: 'application/json; charset=UTF-8',
            dataType: "json",
            success: function (sdata) {
                usingData = sdata.data;
                console.log(sdata);
                var MacValue = getDoc(tid + "Mac").innerText;
                var ihtml = `<div class="pop-window-content"><input style="display:none" id="pop_id" value="${tid}" ><h3>${MacValue}</h3>`;
                for (var i = 0; i < len; i++) {
                    if (usingData.indexOf(data[i].label) > -1) {
                        ihtml += createInputContent(data[i]);
                    }
                }
                ihtml += createOpreateContent(opreateFunc);
                ihtml += '</div>';
                document.getElementById("popWindow").innerHTML = ihtml;
            },
            error: function (err) {
                console.log(err);
            }
        });

}

// 取消按钮
function popCannel() {
    document.getElementById("popWindow").innerHTML = "";
}

// 选中按钮
function popSave() {
    var finalText = "";
    var mid = getDoc("pop_id").value;
    var textValue = document.getElementById("textarea" + mid).value;
    var textArr = textValue.split(",");
    var alen = textArr.length;
    for (var i = 0; i < alen; i++) {
        var textOneArr = textArr[i].split(":");
        var textTittle = textOneArr[0].replace(/'/g, '');
        try {
            finalText += "'" + textTittle + "':'"
                + getDoc("id_" + textTittle).value + "',";
        } catch (e) {
            finalText += "'" + textTittle + "':'" + " " + "',";
        }

    }
    finalText = finalText.substring(0, finalText.length - 1);
    document.getElementById(mid).checked = true;
    document.getElementById("textarea" + mid).value = finalText;
    document.getElementById("popWindow").innerHTML = "";
}

function getDoc(id) {
    return document.getElementById(id);
}

function getDocDisplay(id) {
    return getDoc(id).style.display;
}

function setDocDisplay(id) {
    if (getDocDisplay(id) != "block") {
        document.getElementById(id).style.display = "block";
    } else {
        document.getElementById(id).style.display = "none";
    }
}

// 根据百分比绘制点亮
function percentPower(tid, percent) {
    document.getElementById(tid + "_container").style.width = (2.5 * percent)
        / 100 + "rem";
    if (percent < 20) {
        document.getElementById(tid + "_out").style.borderColor = "#e73453";
        document.getElementById(tid + "_top").style.background = "#e73453";
        document.getElementById(tid + "_container").style.background = " linear-gradient(45deg, #e74353,#e74353 )";
    }
}

// 绘制表格背景
function setTbodyBg() {
    try {
        var len = document.getElementById("main_tb").tBodies[0].rows.length;
        for (var i = 0; i < len; i++) {
            if (i % 2 != 0) {
                document.getElementById("main_tb").tBodies[0].rows[i].style.background = "Seashell";
            }
        }
    } catch (e) {
        console.log(e);
    }
}

// 加载分页
function loadPageNum(page) {
    var ihtml = "<ul><li  onclick='selectPage(1)'>首页</li>";
    for (var i = 0; i < page.totalPages; i++) {
        ihtml += '<li class="style-page-num" onclick="selectPage( ' + (i + 1)
            + ' )" id="pg_' + (i + 1) + '">' + (i + 1) + '</li>';
    }
    ihtml += "<li onclick='selectPage(" + page.totalPages + ")'>尾页</li><li><span>共</span>"
        + page.totalPages + "<span>页</span></li></ul>";
    document.getElementById("pageContainer").innerHTML = ihtml;
    document.getElementById("pg_" + page.currentPage).style.background = "lightsteelblue";
    document.getElementById("pg_" + page.currentPage).style.color = "ghostwhite";
}

// 加载分页
function loadPageNum(page, type) {
    var pageProps = {
        li_id: "pg_",
        li_class: "style-page-num",
        container_id: "pageContainer",
        funcName: "selectPage",
    };
    if (type === "Add") {
        pageProps.funcName = "selectPageAddChose";
    } else if (type === "refresh") {
        pageProps.funcName = "selectPageRefresh";
        pageProps.container_id = "pageContainer-refresh";
        pageProps.li_class = "style-page-num-refresh";
        pageProps.li_id = "pg_refresh";
    } else if (type === "meetTag") {
        pageProps.container_id = "pageContainer-Add";
        pageProps.li_class = "style-page-num-Add";
        pageProps.li_id = "pg_Add";
    }
    var ihtml = `<ul><li onclick="${pageProps.funcName}(1)">首页</li>`;
    if (page.totalPages > 8) {
        var i = page.currentPage > 3 ? page.currentPage - 3 : 0;
        for (; i < page.currentPage + 2; i++) {
            if (i > page.totalPages - 1) {
                break;
            }
            ihtml += `<li class="${pageProps.li_class}" onclick="${pageProps.funcName}(${(i + 1)})"
             id="${pageProps.li_id}${(i + 1)}">${(i + 1)}</li>`;
        }
        if (page.currentPage + 3 < page.totalPages) {
            ihtml += `<li class="${pageProps.li_class}" onclick="${pageProps.funcName}(${(page.currentPage + 2)})">...</li>`;
        }
    } else {
        for (var i = 0; i < page.totalPages; i++) {
            ihtml += `<li class="${pageProps.li_class}" onclick="${pageProps.funcName}(${(i + 1)})"
             id="${pageProps.li_id}${(i + 1)}">${(i + 1)}</li>`;
        }
    }
    ihtml += `<li onclick="${pageProps.funcName}(${page.totalPages})">尾页</li><li><span>共</span>${page.totalPages}<span>页</span></li></ul>`;
    document.getElementById(pageProps.container_id).innerHTML = ihtml;
    document.getElementById(pageProps.li_id + page.currentPage).style.background = "lightsteelblue";
    document.getElementById(pageProps.li_id + page.currentPage).style.color = "ghostwhite";
}

// 选中分页按钮事件
function selectPage(current) {
    var pageProps = {
        li_class: "style-page-num",
        li_id: "pg_"
    };
    var len;
    pageType = localStorage.getItem("pageType");
    currentPage = current;
    if (pageType == "tagsByMeet") {
        pageProps.li_class = "style-page-num-Add";
        pageProps.li_id = "pg_Add";
    }
    len = document.getElementsByClassName(pageProps.className).length;
    for (var i = 0; i < len; i++) {
        if (!document.getElementById(pageProps.li_id + (i + 1))) {
            continue;
        }
        document.getElementById(pageProps.li_id + (i + 1)).style.background = "";
        document.getElementById(pageProps.li_id + (i + 1)).style.color = "cornflowerblue";
    }
    if (pageType == "tag") {
        loadTag(current);
    } else if (pageType == "router") {
        loadRouter(current);
    } else if (pageType == "meeting") {
        if (location.pathname.indexOf('meetingByPhone') > -1) {
            loadMeetingByPhone(current);
        } else {
            loadMeeting(current);
        }
    } else if (pageType == "chooseStyle") {
        loadchooseStyle(current);
    } else if (pageType == "tagsByMeet") {
        LoadTagsByMeeting(current);
    }
    if (document.getElementById(pageProps.li_id + current)) {
        document.getElementById(pageProps.li_id + current).style.background = "lightsteelblue";
        document.getElementById(pageProps.li_id + current).style.color = "ghostwhite";
    }
}

// 选中（添加桌牌页面的）
function selectPageAddChose(current) {
    pageType = localStorage.getItem("pageType");
    var len = document.getElementsByClassName("style-page-num").length;
    for (var i = 0; i < len; i++) {
        if (!document.getElementById("pg_" + (i + 1))) {
            continue;
        }
        document.getElementById("pg_" + (i + 1)).style.background = "";
        document.getElementById("pg_" + (i + 1)).style.color = "cornflowerblue";
    }
    if (pageType == "tag") {
        loadTagAdd(current);
    } else if (pageType == "router") {
        loadRouter(current);
    } else if (pageType == "meeting") {
        loadMeeting(current);
    } else if (pageType == "chooseStyle") {
        loadchooseStyle(current);
    } else if (pageType == "tagsByMeet") {
        LoadTagsByMeeting(current);
    }
    document.getElementById("pg_" + current).style.background = "lightsteelblue";
    document.getElementById("pg_" + current).style.color = "ghostwhite";

}

// 加载表格容器
function loadTableContainer(curl, currentPage) {
    if (curl == "mms/tag") {
        loadTag(currentPage);
    } else if (curl == "mms/router") {
        loadRouter(currentPage);
    } else if (curl == "mms/meeting") {
        loadMeeting(currentPage);
    } else if (curl == "mms/chooseStyle") {
        loadchooseStyle(currentPage);
    }
}

//绘制表格头
function setTableHead(headStyle, type) {
    var headHtml = "<tr>";
    if (headStyle == "tag") {
        tableHead = tagHead;
        pageType = "tag";
        localStorage.setItem("pageType", "tag");
        if (type == "Add") {
            tableHead = tagHeadAdd;
            headHtml += "<td class='tb-head-style'><input id='selectAllAdd' type='checkbox' onclick='checkAddTag(id)'/></td>";
        }
        setTagContent("我的标签");
    } else if (headStyle == "router") {
        tableHead = routerHead;
        pageType = "router";
        localStorage.setItem("pageType", "router");
        setTagContent("我的基站");
    } else if (headStyle == "meeting" && type == "loadMeetingByPhone") {
        tableHead = meetingByPhoneHead;
        pageType = "meeting";
        localStorage.setItem("pageType", "meeting");
    } else if (headStyle == "meeting") {
        tableHead = meetingHead;
        pageType = "meeting";
        localStorage.setItem("pageType", "meeting");
        setTagContent("会议管理");
    } else if (headStyle == "tagsByMeet") {
        if (typeof (useColumn) == "undefined") {
            return;
        }
        var useColumnArr = useColumn.split(",");
        var tlen = tagsByMeetHead.length;
        for (var j = 0; j < tagsByMeetHead.length; j++) {
            tableHead[j] = tagsByMeetHead[j];
        }
        for (var i = 0; i < useColumnArr.length - 1; i++) {
            tableHead[tlen + i] = useColumnArr[i];
        }
        pageType = "tagsByMeet";
        localStorage.setItem("pageType", "tagsByMeet");
        headHtml += "<td class='tb-head-style'><input id='selectAllAddUpd' type='checkbox'  onclick='checkAddTagUpd(id)'/></td>";
    }
    var len = tableHead.length;
    for (var i = 0; i < len; i++) {
        if (pageType = "tagsByMeet" && tableHead[i] == "显示信息") {
            headHtml += "<td style='display:none' class='tb-head-style'>"
                + tableHead[i] + "</td>";
        } else {
            headHtml += "<td class='tb-head-style' style='white-space: nowrap;'>"
                + getLanguageContent(tableHead[i]) + "</td>";
        }
    }
    headHtml += "</tr>";
    if (headStyle == "tagsByMeet") {
        document.getElementById("tableHead-Add").innerHTML = headHtml;
    } else {
        document.getElementById("tableHead").innerHTML = headHtml;
    }
}

//绘制表格数据
function getTableProps(updFunc, delFunc, tableConvert, renderType, clientType) {
    return {
        updFunc: updFunc,// 修改方法名
        delFunc: delFunc, // 删除方法名
        tableConvert: tableConvert,//转换映射
        renderType: renderType, //渲染类型
        clientType: clientType, //科幻段类型
        power_s: [], //电量数组
        useColumnArr: [],
    };
}

const createTableColumns = {
    tag: (tableHeadCol, tableData, tableProps, index) => {
        let _html = ``;
        for (let key in tableData[index]) {
            let mapKey = tableProps.tableConvert[key];
            if (mapKey === tableHeadCol) {
                if (mapKey === "电池电量") {
                    _html += `<td><div style=" display: flex; justify-content: center;"><div id="power${(index + 1)}_out" class="erli-i bar-container">
                            <div id="power${(index + 1)}_container" class="bar-container-in">${tableData[index][key]}%
                            </div></div><li id="power${(index + 1)}_top" class="erli-i bar-top"></li></div></td>`;
                    tableProps.power_s[index] = tableData[index][key];
                } else if (mapKey === "序号") {
                    _html += `<td class=''>${(index + 1)}</td>`;
                } else if (mapKey === "桌牌信息" || mapKey === "标签信息" || mapKey === "桌牌地址" || mapKey === "标签地址") {
                    _html += `<td class="tableMac" id="${tableData[index].id}Mac">
                            ${formatTagAddress(tableData[index][key], "")}</td>`;
                } else if (mapKey == "AP地址" || mapKey == "所属AP" || mapKey == "基站地址" || mapKey == "所属基站") {
                    _html += `<td class="">${formatRouter(tableData[index][key])}</td>`;
                } else {
                    _html += `<td class="">${tableData[index][key]}</td>`;
                }
            }
        }
        return _html;
    },
    router: (tableHeadCol, tableData, tableProps, index) => {
        let _html = ``;
        for (let key in tableData[index]) {
            let mapKey = tableProps.tableConvert[key];
            if (mapKey === tableHeadCol) {
                if (mapKey === "序号") {
                    _html += `<td class=''>${(index + 1)}</td>`;
                } else if (mapKey == "AP地址" || mapKey == "基站地址") {
                    _html += `<td class="">${formatRouter(tableData[index][key])}</td>`;
                } else if (mapKey == "所属AP" || mapKey == "所属基站") {
                    _html += `<td class="">${formatRouter(tableData[index][key])}</td>`;
                } else if (mapKey === "桌牌信息" || mapKey === "标签信息") {
                    _html += createSelectTag(tableData[index][key]);
                } else if (mapKey === "注册开关") {
                    _html += getRegisterENDOM(Number(tableData[index][key]), Number(tableData[index].mac));
                } else {
                    _html += `<td class="">${tableData[index][key]}</td>`;
                }
            }
        }
        return _html;
    }
    ,
    meeting: (tableHeadCol, tableData, tableProps, index) => {
        let _html = ``;
        for (let key in tableData[index]) {
            let mapKey = tableProps.tableConvert[key];
            if (mapKey === tableHeadCol) {
                if (mapKey === "序号") {
                    _html += `<td class=''>${(index + 1)}</td>`;
                } else if (mapKey == "AP地址" || mapKey == "基站地址") {
                    _html += `<td class="">${formatRouter(tableData[index][key])}</td>`;
                } else if (mapKey === "桌牌地址" || mapKey == "标签地址") {
                    _html += createSelectTag(tableData[index][key]);
                } else {
                    _html += `<td class="">${tableData[index][key]}</td>`;
                }
            }
        }
        return _html;
    },
    tagsByMeet:
        (tableHeadCol, tableData, tableProps, index) => {
            let _html = ``;
            for (let key in tableData[index]) {
                let mapKey = tableProps.tableConvert[key];
                if (mapKey === tableHeadCol) {
                    if (mapKey === "序号") {
                        _html += `<td class=''>${(index + 1)}</td>`;
                    } else if (mapKey === "桌牌地址" || mapKey == "标签地址") {
                        _html += `<td class="tableMac" id="${tableData[index].id}Mac">
                        ${formatTagAddress(tableData[index][key], "")}</td>`;
                    } else if (mapKey == "AP地址" || mapKey == "所属AP" || mapKey == "基站地址" || mapKey == "所属基站") {
                        _html += `<td class="">${formatRouter(tableData[index][key])}</td>`;
                    } else if (mapKey === "桌牌信息" || mapKey === "标签信息") {
                        _html += createSelectTag(tableData[index][key]);
                    } else if (mapKey === "显示信息") {
                        _html += `<td style="display:none" class=""><textarea style="display:none"
                        id="textarea${tableData[index].id}" type="text" value="${tableData[index][key]}">
                        ${tableData[index][key]}</textarea><button style="display:none" class="updatedata-style"
                         onclick="createPopWindow(${tableData[index].id})">修改屏幕内容</button></td>`;
                    } else if (mapKey === "标签状态") {
                        _html += `<td id="${tableData[index].id}_style" class="" style="${turnStateColor(tableData[index][key])}">
                        ${formateState(tableData[index][key])}<img class="loadingState" style="display:none"
                        src="assets/img/loadingState.gif" width="15px" height="15px"></td>`;
                    } else if (tableProps.useColumnArr.indexOf(mapKey) > -1) {
                        _html += `<td class=""><input class="columnContentClass" style="width: 60px;height: 20px;"
                    id="${tableData[index].id}_${key}" placeholder="${key}" value="${tableData[index][key]}"
                    onchange="saveColumnContent(${tableData[index].id},value,placeholder)"></td>`;
                    } else if (mapKey == "状态") {
                        _html += `<td id="${tableData[index].id}"_style" class="" style="${turnColor(tableData[index][key])}">
                        ${formateOnline(tableData[index][key])}</td>`;
                    } else {
                        _html += `<td class="">${tableData[index][key]}</td>`;
                    }
                }
            }
            return _html;
        },
    tagAdd:
        (tableHeadCol, tableData, tableProps, index) => {
            let _html = ``;
            for (let key in tableData[index]) {
                let mapKey = tableProps.tableConvert[key];
                if (mapKey === tableHeadCol) {
                    if (mapKey === "电池电量") {
                        _html += `<td><div></div><div id="power${(index + 1)}_out" class="erli-i bar-container">
                            <div id="power${(index + 1)}_container" class="bar-container-in">${tableData[index][key]}%
                            </div></div><li id="power${(index + 1)}_top" class="erli-i bar-top"></li></div>`;
                        tableProps.power_s[index] = tableData[index][key];
                    } else if (mapKey === "序号") {
                        _html += `<td class=''>${(index + 1)}</td>`;
                    } else if (mapKey === "桌牌地址" || mapKey == "标签地址") {
                        _html += `<td class="tableMac" id="${tableData[index].id}Mac">
                            ${formatTagAddress(tableData[index][key], "")}</td>`;
                    } else if (mapKey == "AP地址" || mapKey == "所属AP" || mapKey == "基站地址" || mapKey == "所属基站") {
                        _html += `<td class="">${formatRouter(tableData[index][key])}</td>`;
                    } else {
                        _html += `<td class="">${tableData[index][key]}</td>`;
                    }
                }
            }
            return _html;
        }
}

const createColHead = {
    tag: (tableData, index) => {
        return `<tr style='height:48px;'>`;
    },
    router: (tableData, index) => {
        return `<tr style='height:48px;'>`;
    },
    meeting: (tableData, index) => {
        return `<tr style='height:48px;'>`;
    },
    tagsByMeet: (tableData, index) => {
        return `<tr style='height:36px;'><td><input id="${tableData[index].id}" type="checkbox" onclick="checkAddTagUpd(id)" class="checkbox-tg" />`;
    },
    tagAdd: (tableData, index) => {
        return `<tr style='height:36px;'><td><input id="${tableData[index].id}" type="checkbox" onclick="checkAddTag(id)" class="checkbox-ck" />`;
    }
};

const baseColOperation = (tableData, tableProps, index) => {
    return `<td> <button class="fa fa-pencil update-style-small" onClick="${tableProps.updFunc}(${tableData[index].id})"> </button> <button class="fa fa-trash-o del-style-small" onClick="${tableProps.delFunc}(${tableData[index].id})"></button> <td></tr>`;
};

const createColOperation = {
    tag: (tableData, tableProps, index) => {
        return baseColOperation(tableData, tableProps, index);
    },
    router: (tableData, tableProps, index) => {
        return baseColOperation(tableData, tableProps, index);
    },
    meeting: (tableData, tableProps, index) => {
        if (tableProps.clientType !== "loadMeetingByPhone") {
            return `<td><button class="update-style-small" onclick="${tableProps.updFunc}(${tableData[index].id})">
                        ${getLanguageContent("修改标牌内容")}</button>&nbsp;<button class="fa fa-trash-o del-style-small" onclick="
                        ${tableProps.delFunc}(${tableData[index].id})"></button><td>`;
        } else {
            return `<td><button style="width:108px" class="update-style-small" onclick="${tableProps.updFunc}(${tableData[index].id})">
                        ${getLanguageContent("修改标牌内容")}</button><td>`;
        }
    },
    tagsByMeet: (tableData, tableProps, index) => {
        return `</td>`;
    },
    tagAdd: (tableData, tableProps, index) => {
        return `</td>`;
    }
}

const createColumns = (tableHead, tableData, tableProps, index) => {
    let bodyHtml = "";
    bodyHtml += createColHead[tableProps.renderType](tableData, index);
    for (let j = 0; j < tableHead.length; j++) {
        bodyHtml += createTableColumns[tableProps.renderType](tableHead[j], tableData, tableProps, index);
    }
    bodyHtml += createColOperation[tableProps.renderType](tableData, tableProps, index);
    return bodyHtml;
}

function setTableData(data, type) {
    let bodyHtml = "";
    let containerId = "tableData";
    let tableData = data.datalist;
    // 判断表格类型
    let tableProps = {};
    if (data.data === "tag") {
        if (type === "Add") {
            tableProps = getTableProps("tagUpdate", "tagDel", tagColumnConvert, "tagAdd", type);
        } else {
            tableProps = getTableProps("tagUpdate", "tagDel", tagColumnConvert, "tag", type);
        }
    } else if (data.data === "router") {
        tableProps = getTableProps("routerUpdate", "routerDel", routerColumnConvert, "router", type);
    } else if (data.data === "meeting") {
        tableProps = getTableProps("meetingUpdate", "meetingDel", meetingColumnConvert, "meeting", type);
    } else if (data.data === "tagsByMeet") {
        containerId = "tableData-Add";
        if (typeof (useColumn) === "undefined") {
            return;
        }
        let useColumnArr = useColumn.split(",");
        for (let i = 0; i < useColumnArr.length - 1; i++) {
            tagsByMeetColumnConvert[useColumnArr[i]] = useColumnArr[i];
        }
        localStorage.setItem("refreshContent", data.datalist[0]?.sdata);
        tableProps = getTableProps("tagsByMeetUpdate", "tagsByMeetDel", tagsByMeetColumnConvert, "tagsByMeet", type);
        tableProps.useColumnArr = useColumn.split(",");
    }
    for (let i = 0; i < tableData.length; i++) {
        bodyHtml += createColumns(tableHead, tableData, tableProps, i);
    }
    document.getElementById(containerId).innerHTML = bodyHtml;
    if (tableProps.power_s && tableProps.power_s.length > 0) {
        for (let cc = 0; cc < tableProps.power_s.length; cc++) {
            percentPower("power" + (cc + 1), tableProps.power_s[cc])
        }
    }
}

// function setTableData(data, type) {
//     // 判断表格类型
//     var tableProps = {};
//     if (data.data === "tag") {
//         tableProps = getTableProps("tagUpdate","tagDel",tagColumnConvert);
//     } else if (data.data === "router") {
//         tableProps = getTableProps("routerUpdate","routerDel",routerColumnConvert);
//     } else if (data.data === "meeting") {
//         tableProps = getTableProps("meetingUpdate","meetingDel",meetingColumnConvert);
//     } else if (data.data === "tagsByMeet") {
//         if (typeof (useColumn) === "undefined") {
//             return;
//         }
//         var useColumnArr = useColumn.split(",");
//         for (var i = 0; i < useColumnArr.length - 1; i++) {
//             tagsByMeetColumnConvert[useColumnArr[i]] = useColumnArr[i];
//         }
//         localStorage.setItem("refreshContent", data.datalist[0].sdata);
//         tableProps = getTableProps("tagsByMeetUpdate","tagsByMeetDel",tagsByMeetColumnConvert);
//     }
//     tableData = data.datalist;
//     var bodyHtml = " ";
//     var blen = tableData.length;
//     var hlen = tableHead.length;
//     var power_s = [];
//     for (var i = 0; i < blen; i++) {
//         if (type === "Add") {
//             bodyHtml += `<tr style='height:36px;'><td>
//             <input id="${tableData[i].id}" type="checkbox" onclick="checkAddTag(id)" class="checkbox-ck" />`;
//         } else if (data.data === "tagsByMeet") {
//             bodyHtml += `<tr style='height:48px;'><td><input id="${tableData[i].id}" type="checkbox"
//             onclick="checkAddTagUpd(id)" class="checkbox-tg" />`;
//         } else {
//             bodyHtml += `<tr style='height:48px;'>`;
//         }
//         for (var j = 0; j < hlen; j++) {
//             for (var key in tableData[i]) {
//                 var mapKey = tableProps.tableConvert[key];
//                 if (mapKey === tableHead[j]) {
//                     if (mapKey === "电池电量") {
//                         bodyHtml += `<td><div id="power${(i + 1)}_out" class="erli-i bar-container">
//                             <div id="power${(i + 1)}_container" class="bar-container-in">${tableData[i][key]}%
//                             </div></div><li id="power${(i + 1)}_top" class="erli-i bar-top"></li>`;
//                         power_s[i] = tableData[i][key];
//                     } else if (mapKey === "序号") {
//                         bodyHtml += `<td class=''>${(i + 1)}</td>`;
//                     } else if (mapKey === "桌牌地址") {
//                         bodyHtml += `<td class="tableMac" id="${tableData[i].id}Mac">
//                             ${formatTagAddress(tableData[i][key],"")}</td>`;
//                     } else if (mapKey == "AP地址" || mapKey == "所属AP") {
//                         bodyHtml += `<td class="">${formatRouter(tableData[i][key])}</td>`;
//                     } else if (mapKey === "桌牌信息") {
//                         bodyHtml += createSelectTag(tableData[i][key]);
//                     } else if (mapKey === "显示信息") {
//                         if (data.data === "tagsByMeet") {
//                             bodyHtml += `<td style="display:none" class=""><textarea style="display:none"
//                                 id="textarea${tableData[i].id}" type="text" value="${tableData[i][key]}">
//                                 ${tableData[i][key]}</textarea><button style="display:none" class="updatedata-style"
//                                  onclick="createPopWindow(${tableData[i].id})">修改屏幕内容</button></td>`;
//                         } else {
//                             bodyHtml += `<td class=""><textarea style="display:none" id="textarea${tableData[i].id}"
//                                 type="text" value="${tableData[i][key]}">${tableData[i][key]}</textarea><button
//                                 class="updatedata-style' onclick="createPopWindow(${tableData[i].id})">修改屏幕内容</button></td>`;
//                         }
//                     } else if (mapKey === "标签状态") {
//                         bodyHtml += `<td id="${tableData[i].id}_style" class="" style="${turnStateColor(tableData[i][key])}">
//                             ${formateState(tableData[i][key])}<img class="loadingState" style="display:none"
//                             src="assets/img/loadingState.gif" width="15px" height="15px"></td>`;
//                     } else if (data.data === "tagsByMeet" && useColumnArr.indexOf(mapKey) > -1) {
//                         bodyHtml += `<td class=""><input class="columnContentClass" style="width: 60px;height: 20px;"
//                         id="${tableData[i].id}_${key}" placeholder="${key}" value="${tableData[i][key]}"
//                         onchange="saveColumnContent(${tableData[i].id},value,placeholder)"></td>`;
//                     } else if (mapKey == "状态") {
//                         bodyHtml += `<td id="${tableData[i].id}"_style" class="" style="${turnColor(tableData[i][key])}">
//                             ${formateOnline(tableData[i][key])}</td>`;
//                     } else if (mapKey == "描述") {
//                         bodyHtml += `<td><input style="width:90px;height:20px;" id="${tableData[i].id}" class=""
//                          value="${(tableData[i][key])}" onchange="updateRouterMsg(id,value)" /></td>`;
//                     } else {
//                         bodyHtml += `<td class="">${tableData[i][key]}</td>`;
//                     }
//                 }
//             }
//         }
//         if (data.data === "tagsByMeet") {
//             document.getElementById("tableData-Add").innerHTML = bodyHtml;
//             for (var cc = 0; cc < power_s.length; cc++) {
//                 percentPower("power" + (cc + 1), power_s[cc])
//             }
//         } else if (data.data === "meeting" && type !== "loadMeetingByPhone") {
//             bodyHtml += `<td><button class="update-style-small" onclick="${tableProps.updFunc}(${tableData[i].id})">
//                     ${getLanguageContent("修改标牌内容")}</button>&nbsp;<button class="fa fa-trash-o del-style-small" onclick="
//                     ${tableProps.delFunc}(${tableData[i].id})"></button><td>`;
//         } else if (data.data === "meeting" && type === "loadMeetingByPhone") {
//             bodyHtml += `<td><button style="width:108px" class="update-style-small" onclick="${tableProps.updFunc}(${tableData[i].id})">
//                 ${getLanguageContent("修改标牌内容")}</button><td>`;
//         } else if (data.data == "tag" && type == "Add") {
//
//         } else {
//             bodyHtml += `<td><button class="fa fa-pencil update-style-small" onclick="${tableProps.updFunc}(${tableData[i].id})">
//             </button><button class="fa fa-trash-o del-style-small" onclick="${tableProps.delFunc}(${tableData[i].id})"></button><td>`;
//         }
//         bodyHtml += `</tr>`;
//     }
//     document.getElementById("tableData").innerHTML = bodyHtml;
//     for (var cc = 0; cc < power_s.length; cc++) {
//         percentPower("power" + (cc + 1), power_s[cc])
//     }
// }

// 创建select标签信息框
function createSelectTag(data) {
    var dataArr = data.split(",");
    var dataHtml = "<td><select style='border: none;'>";
    for (var i = 0; i < dataArr.length; i++) {
        dataHtml += "<option>" + formatTagAddress(dataArr[i], "CWT")
            + "</option>";
    }
    dataHtml += "</select></td>";
    return dataHtml;
}

//基站开关dom
const getRegisterENDOM = (val, mac) => {
    let style = "";
    return `<td class=""><a style="color:${val === 1 ? "#d4380d" : "green"}" onclick="setRegisterEN(${mac},${val})">
                            ${getLanguageContent(val === 1 ? "关闭" : "开启")}</a></td>`;
}

// ////////////////////////////////////////////////////////////////////////////////////////////////////
var sImgId = "";
var dataLiArr = [{
    "id": 1,
    "isrc": "https://www.baidu.com/img/baidu_jgylogo3.gif",
    "iname": "4.2屏幕（红）",
    "styleLen": "800x480",
    "updateTime": "2019-08-26 19:23:46",
}, {
    "id": 2,
    "isrc": "https://www.baidu.com/img/baidu_jgylogo3.gif",
    "iname": "4.2屏幕（红）",
    "styleLen": "800x480",
    "updateTime": "2019-08-26 19:23:46",
}, {
    "id": 3,
    "isrc": "https://www.baidu.com/img/baidu_jgylogo3.gif",
    "iname": "4.2屏幕（红）",
    "styleLen": "800x480",
    "updateTime": "2019-08-26 19:23:46",
}, {
    "id": 4,
    "isrc": "https://www.baidu.com/img/baidu_jgylogo3.gif",
    "iname": "4.2屏幕（红）",
    "styleLen": "800x480",
    "updateTime": "2019-08-26 19:23:46",
}];

// 创建li
function createLi(data, type) {
    // setLanguageMData();
    dataLiArr = data;
    var iinerHtml = "";
    if (type == "refresh") {
        var dstyleArr = dataLiArr[0].styleLen.split("x");
        var dwidth = dstyleArr[0];
        var dheight = dstyleArr[1];
        localStorage.setItem("pageType", "");
        iinerHtml += `<li class="li-img-list"><div style="background:gray;text-align: center;" class="img-mediu">
            <img id="img-default" class="img-mediu" src="assets/img/tjImg.png" style="width:${
            260 * (dwidth / 640) * (dheight / dwidth)
        }px;
            height:${
            260 * (dwidth / 640) * (dheight / dwidth)
        }px;box-shadow: none;border: none;" onclick="createAndOpenComponent()" /></div>
            <div id="name-default" class="left-style blackstyle font-small"></div><div class="right-style blackstyle font-small"></div>
            <br /><div class="left-style blackstyle font-small"></div></li>`;
        for (var i = 0; i < dataLiArr.length; i++) {
            var styleArr = dataLiArr[i].styleLen.split("x");
            var width = styleArr[0];
            var height = styleArr[1];
            if (width > 640) {
                height = height * (540 / width);
                width = 540;
            }
            iinerHtml += `<li class="li-img-list"><div style="background:gray;text-align: center;" class="img-mediu">
                <img id="img${dataLiArr[i].id}" class="" src="${
                dataLiArr[i].src
            }?m=${Math.random()}" style="width:${260 * (width / 640)}px;
                height:${
                260 * (width / 640) * (height / width)
            }px" onclick="choose(${dataLiArr[i].id},1)" /></div>
                <div id="name${
                dataLiArr[i].id
            }" class="left-style blackstyle font-small">${
                dataLiArr[i].name
            }</div>
                <div class="right-style blackstyle font-small">${
                dataLiArr[i].styleLen
            }</div><br /><div class="left-style
                 blackstyle font-small">${dataLiArr[i].updateTime} </div></li>`;
        }
    } else {
        pageType = "chooseStyle";
        localStorage.setItem("pageType", "chooseStyle");
        for (var i = 0; i < dataLiArr.length; i++) {
            var styleArr = dataLiArr[i].styleLen.split("x");
            var width = styleArr[0];
            var height = styleArr[1];
            if (width > 640) {
                height = height * (540 / width);
                width = 540;
            }
            iinerHtml += `<li class="li-img-list">
      <div class="chose-img-div">
      <img id="img${dataLiArr[i].id}" class="" style="width: ${
                450 * (width / 640)
            }px;height: ${450 * (width / 640) * (height / width)}px;
        margin-top:${
                (280 - 450 * (width / 640) * (height / width)) / 2
            }px;" src="${dataLiArr[i].src}?m=${Math.random()}"
        onclick="choose(${dataLiArr[i].id})" /></div><div id="name${
                dataLiArr[i].id
            }" class="left-style blackstyle font-small"
         style="width: 80%;font-weight:bold">${
                dataLiArr[i].name
            }</div><div class="right-style blackstyle font-small">
       ${
                dataLiArr[i].styleLen
            }</div><br /><div class="left-style blackstyle font-small">${
                dataLiArr[i].updateTime
            }</div>
       <div class="right-style-button blackstyle font-small"><td><button class="fa fa-pencil update-style-small button-group-left" 
       onclick="choose(${
                dataLiArr[i].id
            })"></button><button class="fa fa-trash-o del-style-small button-group-right" 
       onclick="delStyles(${
                dataLiArr[i].id
            },'${dataLiArr[i].name}')"></button></div></li>`;
        }
    }
    document.getElementById("img-ul").innerHTML = iinerHtml;
}

// 创建IMG标签
function createImgTag(src, name, type) {
    var selectFuncName = "selectThisModel()";
    if (type == "1") {
        selectFuncName = "selectAnotherModel()";
    }
    return "<img class='img-tag-Large' src='" + src + '?m=' + Math.random()
        + "' /><br /><center><h4>" + getLanguageContent("模板") + "：" + name + "</h4><center/><center>"
        + createBlueButton(getLanguageContent("选择"), selectFuncName) + "  "
        + createCancelButton(getLanguageContent("取消"), "closeFun()") + "<center/>";
}

// 选择模板
function selectThisModel() {
    openComponent(sImgId);
    closeFun();
}

// 选择模板
function selectAnotherModel() {
    var mid = getDocValue("meetid");
    selectStyleById(mid, sImgId);
    closeFun();
}

// 打开样式配置页面
function openComponent(id) {
    window
        .open(
            'mms/getDispMs?id=' + id + '',
            'newWindow',
            'width='
            + (window.screen.availWidth)
            * 0.9
            + ',height='
            + (window.screen.availHeight)
            * 0.8
            + ',top=40,left=40,toolbar=no,menubar=no,scrollbars=no, resizable=no,location=no, status=no');
}

// 打开样式配置页面
function openOrSaveComponent() {
    var stylealignId = templateTypeAdd.value;
    if (!stylealignId) {
        return;
    }
    addColumnPop.style.display = "none";
    window
        .open(
            'mms/addStyles?id=' + 0 + '&stylealignId=' + stylealignId,
            'newWindow',
            'width='
            + (window.screen.availWidth)
            * 0.9
            + ',height='
            + (window.screen.availHeight)
            * 0.8
            + ',top=40,left=40,toolbar=no,menubar=no,scrollbars=no, resizable=no,location=no, status=no');
}

// 打开样式配置页面
function createAndOpenComponent() {
    var isCreated = confirm(getLanguageContent("是否添加新模板?"));
    if (!isCreated) {
        return;
    }
    var stylealignId = templateType.value;
    window
        .open(
            'mms/addStyles?id=' + 0 + '&stylealignId=' + stylealignId,
            'newWindow',
            'width='
            + (window.screen.availWidth)
            * 0.9
            + ',height='
            + (window.screen.availHeight)
            * 0.8
            + ',top=40,left=40,toolbar=no,menubar=no,scrollbars=no, resizable=no,location=no, status=no');
}

//
function closePop() {
    addColumnPop.style.display = "none";
}

// 发送请求，打开或者创建样式（）
function openOrSaveStyle(styleid) {
    addColumnPop.style.display = "block";
}

// 刪除樣式
function delStyles(sid, name) {
    var isdelete = confirm(getLanguageContent("是否删除") + name + "?");
    if (!isdelete) {
        return;
    }
    $.ajax({
        url: "style/deleteStyles?styleid=" + sid,
        dataType: "json",
        success: function (data) {
            if (data.resultCode != 10) {
                alert(data.data);
                return;
            }
            selectPage(currentPage);
        }
    });
}

// 关闭弹窗
function closeFun() {
    document.getElementById("pop-window").style.display = "none";
}

// 创建蓝色按钮
function createBlueButton(text, clickFun) {
    return "<button class='blue-button-mediu mediu-left del-top-small' onclick='"
        + clickFun + "'>" + text + "</button>"
}

// 创建取消按钮
function createCancelButton(text, clickFun) {
    return "<button class='cancel-button-mediu mediu-left del-top-small' onclick='"
        + clickFun + "'>" + text + "</button>"
}

// 获取dom节点（根据ID）
function getDoc(id) {
    return document.getElementById(id);
}

function getDocValue(id) {
    return document.getElementById(id).value;
}

// 获取dom节点是否隐藏属性（根据ID）
function getDocDisplay(id) {
    return getDoc(id).style.display;
}

// 设置dom节点样式的显示隐藏
function setDocDisplay(id) {
    if (getDocDisplay(id) != "block") {
        document.getElementById(id).style.display = "block";
    } else {
        document.getElementById(id).style.display = "none";
    }
}

// 设置dom节点显示
function setDocDisplayTrue(id) {
    document.getElementById(id).style.display = "block";
}

// 选中
function choose(id, type) {
    var csrc = document.getElementById("img" + id).src;
    var cname = document.getElementById("name" + id).innerText;
    setDocDisplay("pop-window");
    getDoc("pop-window").innerHTML = createImgTag(csrc, cname, type);
    if (id != sImgId) {
        setDocDisplayTrue("pop-window");
    }
    this.sImgId = id;
}

// /////////////////////////////////////////////////////////////////////////////////

// 格式化标签
function formatTagAddress(mac, str) {
    function format(val) {
        return val < 10 ? val = "0" + val : val;
    }

    str += format(mac >> 24 & 0xff);
    str += ".";
    str += format(mac >> 16 & 0xff);
    str += ".";
    str += format(mac >> 8 & 0xff);
    str += ".";
    str += format(mac & 0xff);
    return str;
}

// 格式化路由器名称
function formatRouter(mac) {
    var str = "CWR";
    var idStr = mac + "";
    var length = idStr.length;
    for (var i = 0; i < 6 - length; i++) {
        str = str + "0";
    }
    return str + mac;
}

// 复选事件
function checkAddTag(id) {
    if (id == "selectAllAdd") {
        var clen = document.getElementsByClassName("checkbox-ck").length;
        if (getDoc(id).checked) {
            for (var i = 0; i < clen; i++) {
                document.getElementsByClassName("checkbox-ck")[i].checked = true;
            }
        } else {
            for (var j = 0; j < clen; j++) {
                document.getElementsByClassName("checkbox-ck")[j].checked = false;
            }
        }
    }
}

function turnStateColor(state) {
    var style = "color:dimgray;white-space: nowrap;";
    switch (state) {
        case "0":
            style = "color:orange;white-space: nowrap;";
            break;
        case "1":
            style = "color:orange;white-space: nowrap;";
            break;
        case "2":
            style = "color:orange;white-space: nowrap;";
            break;
        case "3":
            style = "color:red;white-space: nowrap;";
            break;
        case "4":
            style = "color:green;white-space: nowrap;";
            break;
        default:
            style = "color:orange;white-space: nowrap;";
            break;
    }
    return style;
}

// 判断状态
function formateState(state) {
    switch (state) {
        case "1":
            state = getLanguageContent("等待更新");
            setLoadingGifDisplay("none");
            break;
        case "2":
            state = getLanguageContent("正在更新");
            setLoadingGifDisplay("block");
            break;
        case "3":
            state = getLanguageContent("更新失败");
            setLoadingGifDisplay("none");
            break;
        case "4":
            state = getLanguageContent("更新完成");
            setLoadingGifDisplay("none");
            break;
        default:
            state = getLanguageContent("未更新");
            setLoadingGifDisplay("none");
            break;
    }
    return state;
}

// 判断状态
function formateOnline(state) {
    switch (state) {
        case "true":
            state = `<span>${getLanguageContent("在线")}</span>`;
            break;
        case "false":
            state = `<span>${getLanguageContent("离线")}</span>`;
            break;
        default:
            state = `<span>${getLanguageContent("离线")}</span>`;
            break;
    }
    return state;
}

// 在线离线颜色
function turnColor(state) {
    var style = "color:dimgray";
    switch (state) {
        case "true":
            style = "color:green";
            break;
        case "false":
            style = "color:black";
            break;
        default:
            style = "color:black";
            break;
    }
    return style;
}

// 选择更新标签
function checkAddTagUpd(id) {
    if (id == "selectAllAddUpd") {
        var clen = document.getElementsByClassName("checkbox-tg").length;
        if (getDoc(id).checked) {
            for (var i = 0; i < clen; i++) {
                document.getElementsByClassName("checkbox-tg")[i].checked = true;
            }
        } else {
            for (var j = 0; j < clen; j++) {
                document.getElementsByClassName("checkbox-tg")[j].checked = false;
            }
        }
    }
    setInputToTextarea(id);
}

// 从输入框(input)将内容填入隐藏的文本框（textarea）
function setInputToTextarea(id) {
    try {
        var useColumnArr = useColumn.split(",");
        for (var j = 0; j < useColumnArr.length - 1; j++) {
            var jval = document.getElementById(id + "_" + useColumnArr[j]).value;
            var icontent = document.getElementById("textarea" + id).value;
            icontent = icontent.replace(useColumnArr[j] + "Content", jval);
            document.getElementById("textarea" + id).value = icontent;
            if (localStorage.getItem(useColumnArr[j])) {
                localStorage.removeItem(useColumnArr[j]);
            }
            localStorage.setItem(useColumnArr[j], jval);
        }
    } catch (e) {
        console.log(e);
    }
}


// 刷新标签状态
function setTableStatus(data) {
    var tableData = data.datalist;
    var tlen = tableData.length;
    for (var i = 0; i < tlen; i++) {
        setTrBgColor();
        if (tableData[i].state == 2) {
            document.getElementById(tableData[i].id + "_style").parentNode.style.background = "powderblue";
        } else if (tableData[i].state == 2 || tableData[i].state == 3) {
            document.getElementById(tableData[i].id + "_style").parentNode.style.background = "lightcoral";
        } else {
            if (i % 2 == 0) {
                document.getElementById(tableData[i].id + "_style").parentNode.style.background = "";
            } else {
                document.getElementById(tableData[i].id + "_style").parentNode.style.background = "seashell";
            }
        }
        document.getElementById(tableData[i].id + "_style").innerText = formateState(tableData[i].state);
        document.getElementById(tableData[i].id + "_style").style = turnStateColor(tableData[i].state);
    }
}

// 保存标签填入内容(){
function saveColumnContent(tid, val, columnName) {
    var meetid = document.getElementById("meetid").value;
    document.getElementById("textarea" + tid).value = localStorage
        .getItem("refreshContent");
    if (columnName != val) {
        document.getElementById(tid).checked = true;
        checkAddTagUpd(tid);
    }
    $
        .ajax({
            url: "mms/saveColumnContent",
            type: "POST",
            data: {
                tid: tid,
                meetid: meetid,
                columnName: columnName,
                columnContent: val
            },
            success: function (resp) {
                var icontent = document.getElementById("textarea" + tid).value;
                icontent = icontent.replace(columnName + "Content", val);
                document.getElementById("textarea" + tid).value = icontent;
                document.getElementById(tid + "_style").innerText = getLanguageContent("等待更新");
                document.getElementById(tid + "_style").style = "color:orange";
                document.getElementById(tid + "_style").style = "color:orange";
                document.getElementById(tid + "_style").parentNode.style.background = "powderblue";
            }
        });
}

// 修改路由器描述
function updateRouterMsg(rid, val) {
    $.ajax({
        url: "router/updateRouterDescription",
        type: "POST",
        data: {
            rid: rid,
            description: val
        },
        success: function (resp) {
        }
    });
}

// 根据ID删除会议
function meetingDel(meetid) {
    var con = confirm(getLanguageContent("确认要删除吗?"));
    if (!con) {
        return;
    }
    $.ajax({
        url: "mms/delMeeting",
        type: "POST",
        data: {
            mid: meetid,
        },
        success: function (resp) {
            alert(getLanguageContent("删除成功"));
            loadMeeting(1);
        }, error: function (err) {
            alert(getLanguageContent("删除失败"));
            console.log(err);
        }
    });

}

// 设置Gif Loading图的显示隐藏
function setLoadingGifDisplay(state) {
    var clen = document.getElementsByClassName("loadingState").length;
    for (var i = 0; i < clen; i++) {
        document.getElementsByClassName("loadingState")[i].style.display = '"'
            + state + '"';
    }
}


// 中英文切換
function setLanguageMData() {
    var clen = document.getElementsByClassName("textMsg").length;
    for (var i = 0; i < clen; i++) {
        var itext = document.getElementsByClassName("textMsg")[i].innerText;
        document.getElementsByClassName("textMsg")[i].innerText = getLanguageContent(itext);
    }
    var ival = divtext.value;
    try {
        divtext.value = getLanguageContent(ival);
    } catch (e) {
        console.log(e);
    }
}

// 提示翻页文字选择
function setPageLan() {
    try {
        for (var i = 0; i < document.getElementById("pageContainer").children[0].children.length; i++) {
            var textContont = document.getElementById("pageContainer").children[0].children[i].innerText
                .replace("*", "").replace(/\s+/g, '');
            textContont = getLanguageContent(textContont);
            document.getElementById("pageContainer").children[0].children[i].innerText = ""
                + textContont;
        }
    } catch (e) {
// console.log();
    }
}

function setTrBgColor() {

}

// 删除标签
function tagDel(id) {
    var con = confirm(getLanguageContent("确认要删除吗?"));
    if (!con) {
        return;
    }
    $.ajax({
        url: "mms/deleteTag",
        type: "POST",
        data: {
            tagid: id,
        },
        success: function (resp) {
            if (resp == 1) {
                alert(getLanguageContent("删除成功"));
                loadTag(1);
                return;
            }
            alert(getLanguageContent("删除失败"));
        }
    });
}

// 删除所有标签
function deleteAllTag() {
    var con = confirm(getLanguageContent("确认要删除所有标签吗?"));
    if (!con) {
        return;
    }
    $.ajax({
        url: "mms/deleteAllTag",
        type: "POST",
        data: {},
        success: function (resp) {
            if (resp == 1) {
                alert(getLanguageContent("删除成功"));
                loadTag(1);
                return;
            }
            alert(getLanguageContent("删除失败"));
        }
    });
}

//设置基站注册开关
function setRegisterEN(mac, val) {
    var con = confirm(val == 1 ? getLanguageContent("是否开启注册开关?") : getLanguageContent("是否关闭注册开关?"));
    if (!con) {
        return;
    }
    $.ajax({
        url: "router/updateTagRegisterEN?mac=" + mac,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        success: function (resp) {
            let res = JSON.parse(resp);
            if (res.resultCode === 10) {
                loadRouter(currentPage);
                return;
            }
            alert("error");
        }
    });
}

// 删除路由器
function routerDel(id) {
    var con = confirm(getLanguageContent("确认要删除吗?"));
    if (!con) {
        return;
    }
    $.ajax({
        url: "mms/deleteRouter",
        type: "POST",
        data: {
            routerid: id,
        },
        success: function (resp) {
            if (resp == 1) {
                alert(getLanguageContent("删除成功"));
                loadRouter(1);
                return;
            }
            alert(getLanguageContent("删除失败"));
        }
    });
}

function tagUpdate(id) {
    $.ajax({
        url: "tag/getTagById",
        data: {
            id: id,
        },
        contentType: 'application/json; charset=UTF-8',
        dataType: "json",
        success: function (resp) {
            var tagEntity = resp.tag;
            try {
                input_mac.value = formatTagAddress(tagEntity.mac, "");
                input_style.value = tagEntity.style.name;
                input_width.value = tagEntity.width;
                input_height.value = tagEntity.height;
                input_power.value = tagEntity.power + "%";
                input_rssi.value = tagEntity.rssi;
                input_hardwareVersion.value = formatVersion(tagEntity.hardwareVersion);
                input_softwareVersion.value = formatVersion(tagEntity.softwareVersion);
                input_serialNumber.value = tagEntity.serialNumber;
                input_productionBatch.value = tagEntity.productionBatch;
                input_routerMac.value = tagEntity.router.mac;
            } catch (e) {
                console.log(e);
            }
            addColumnPop.style.display = "block";
        }
    });
}

// 格式化版本格式
function formatVersion(version) {
    if (isNaN(version)) {
        return version;
    }
    var ver1 = version >> 4 & 0x0f;
    var ver2 = version & 0x0f;
    return ver1 + "." + ver2;
}

// 從localStorage裡面取出
function getLocalStorage(name) {
    return localStorage.getItem(name);
}

// 存入localStorage
function setLocalStorage(name, val) {
    localStorage.setItem(name, val);
}

// 加载下拉选择框（模板类型）
function setStyleAlignOptionContent() {
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
            for (var i = 0; i < datalist.length; i++) {
                ihtml += '<option id="op' + datalist[i].id
                    + '"" value="' + datalist[i].id + '">'
                    + datalist[i].description + '</option>';
            }
            try {
                templateType.innerHTML = ihtml;
                templateTypeAdd.innerHTML = ihtml;
            } catch (e) {
            }
        }
    });
}

// 取消格式化标签
function cancelFormatTag(num) {
    var mac = 0;
    var str = num.substr(0, 3);
    var array = new Array();
    array = num.split(".");
    for (var i = 0; i < array.length; i++) {
        if (array[i] != 0) {
            mac += array[i] << (array.length - i - 1) * 8;
        }
    }
    return mac;
}

//加载周期信息
function loadPeriod() {
    $.ajax({
        url: "router/getOneRouter",
        dataType: "json",
        success: function (resp) {
            var period = resp.longPeriod;
            $("#wake_period").val(period);
            $("#out_time").val(period * 2);
        }
    });
}

function setLongPeriod() {
    var wakePeriod = $("#wake_period").val();
    var outTime = $("#out_time").val();
    $.ajax({
        url: 'associate/tagWakePeriod',
        data: {
            wakePeriod: wakePeriod,
            outTime: outTime
        },
        dataType: "JSON",
        success: function (resp) {
            if (resp == "user") {
                alert(getLanguageContent("登录超时，请重新登录！"));
            }
            if (resp == "true") {
                document.getElementById("safeStay").style.display = "block";
                document.getElementById("warning").style.display = "block";
                wakingUp = setInterval(function () {
                    outTime--;
                    $("#wake_timing").val(outTime);
                    if (outTime < 0) {
                        document.getElementById("safeStay").style.display = "none";
                        document.getElementById("warning").style.display = "none";
                        clearInterval(wakingUp);
                    }
                }, 1000);
            } else if (resp == "router") {
                alert(getLanguageContent("路由器离线，请检查路由器状态！"));
            }
        }
    });
}



