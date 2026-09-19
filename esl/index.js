$(function() {
	App.init();

	var Index = (function() {
		var me = {};

		// 处理一级菜单点击
		me.handleMenuClick = function() {
			$('#page-sidebar-menu li').click(function(e) {
				var menu = $('#page-sidebar-menu');
				var li = menu.find('li.active').removeClass('active');
				// 添加选中 打开的样式
				$(this).addClass('active');
			});
		};

		// 处理子菜单点击
		me.handleSubMenuClick = function() {
			$('#page-sidebar-menu li a').click(function(e) {
				$(this).partent.addClass('active');
			});
		};

		me.init = function() {
			me.handleMenuClick();
			me.handleSubMenuClick();
		};

		return me;
	})();

	Index.init();
});

$(document)
		.ready(
				function() {
					$(".page-sidebar-menu li:gt(0)")
							.click(
									function() {
										$(".page-sidebar-menu li:gt(0)")
												.removeClass("active");
										if ($(this).attr("class") === "start") {
											$(".page-sidebar-menu")
													.find("li")
													.each(
															function() {
																$(this)
																		.removeClass(
																				"open");
																$(this)
																		.find(
																				"ul[class='sub-menu']")
																		.attr(
																				"style",
																				"dispaly:none;");
																$(this)
																		.find(
																				"a>span[class='arrow open']")
																		.removeClass(
																				"open");
															});
										}
										$(this).addClass("open");
									});
					$(".page-sidebar-menu li:gt(0) ul li").click(
							function() {
								$(".page-sidebar-menu li:gt(0) ul li")
										.removeClass("open");
								$(this).addClass("open");
							});

					loadIframe();

					$("#transHtml").bind("click", function(event) {
						translate(this.value);
					});

				});

function loadIframe() {
	var co = document.cookie;
	var arryCookie = co.split(";");
	var value = "";
	for (var i = 0; i < arryCookie.length; i++) {
		var array = arryCookie[i].split("=");
		if ("url" == array[0].trim()) {
			value = array[1];
		}
	}
	$(".page-sidebar-menu li:gt(0) ul li a").each(function() {
		if ($(this).attr("href") == value) {
			$(".page-sidebar-menu li:gt(0)").removeClass("active");
			$(this).parent().addClass("open");
			$(this).parent().parent().attr("style", "display:block");
			$(this).parent().parent().parent().addClass("open");
		}
	})
	if (value != "") {
		$("#ifrUrl").attr("src", value);
	}
}

// 首页
function getIndex() {
	var language = $("#language").val();
	var url = null;
	if (language == "en_US") {
		$("#ifrUrl").attr("src", "/esls_new/index/english.html");
		$("#index_switch").attr("href", "/esls_new/index/english.html");
		url = "/esls_new/index/english.html";
	} else if (language == "zh_CN") {
		$("#ifrUrl").attr("src", "/esls_new/index/index.html");
		$("#index_switch").attr("href", "/esls_new/index/index.html");
		url = "/esls_new/index/index.html";
	} else if (language == "zh_HK") {
		$("#ifrUrl").attr("src", "/esls_new/index/indexHK.html");
		$("#index_switch").attr("href", "/esls_new/index/indexHK.html");
		url = "/esls_new/index/indexHK.html";
	} else if (language == "ja_JP") {
		$("#ifrUrl").attr("src", "/esls_new/index/japanese.html");
		$("#index_switch").attr("href", "/esls_new/index/japanese.html");
		url = "/esls_new/index/japanese.html";
	} else if (language == "ko_KR") {
		$("#ifrUrl").attr("src", "/esls_new/index/korean.html");
		$("#index_switch").attr("href", "/esls_new/index/korean.html");
		url = "/esls_new/index/korean.html";
	}else if(language = "vi_VN"){
		$("#ifrUrl").attr("src", "/esls_new/index/Vietnamese.html");
		$("#index_switch").attr("href", "/esls_new/index/Vietnamese.html");
		url = "/esls_new/index/Vietnamese.html";
	}
	getUrl(url);
}

function getUrl(url) {
	var date = new Date();
	document.cookie = "url=" + url;
}

function changeLanguage(val) {
	var co = document.cookie;
	var arryCookie = co.split(";");
	var value = "";
	if (val == "en_US") {
		localStorage.setItem("language", 2);
	} else if (val == "zh_CN") {
		localStorage.setItem("language", 0);
	} else if (val == "zh_HK") {
		localStorage.setItem("language", 1);
	} else if (val == "ja_JP") {
		localStorage.setItem("language", 3);
	} else if (val == "ko_KR") {
		localStorage.setItem("language", 4);
	}else if (val == "vi") {
		localStorage.setItem("language", 5);
	}
	for (var i = 0; i < arryCookie.length; i++) {
		var array = arryCookie[i].split("=");
		if ("url" == array[0].trim()) {
			value = array[1];
		}
	}
	if (value.endsWith("html")) {
		var language = $("#language").val();
		var url = "";
		if (language == "en_US") {
			url = '/esls_new/index/english.html';
			localStorage.setItem("language", 2);
		} else if (language == "zh_CN") {
			url = '/esls_new/index/index.html';
			localStorage.setItem("language", 0);
		} else if (language == "zh_HK") {
			url = '/esls_new/index/indexHK.html';
			localStorage.setItem("language", 1);
		} else if (language == "ja_JP") {
			url = '/esls_new/index/japanese.html';
			localStorage.setItem("language", 3);
		} else if (language == "ko_KR") {
			url = '/esls_new/index/korean.html';
			localStorage.setItem("language", 4);
		} else if (language == "vi") {
			url = '/esls_new/index/Vietnamese.html';
			localStorage.setItem("language", 5);
		}
		getUrl(url);
	}
	window.location = "login/language?lang=" + val;
}
