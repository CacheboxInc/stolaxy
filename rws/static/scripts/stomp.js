var utc_offset = null;
var selected_menu = 'dashboard';

function ws_open() {
    console.log("Websocket has been connected");
}

function ws_message(evt) {
    console.log("Message from web_socket: " + evt.data);
}

function ws_close() {
    console.log("Websocket closed");
}

function initialize() {

    require([
        "stomp/widgets/dashboard",
        "stomp/widgets/hosts/host-list",
        "stomp/widgets/reports/cluster-stats",
        "stomp/widgets/application/application-usage",
        "stomp/widgets/policy/workload-manager",
        "stomp/widgets/reports/metrics",
        "stomp/widgets/reports/event-logs",
        "stomp/widgets/application/application-list",
        "stomp/widgets/groups/group-list",
        "stomp/widgets/users/user-list",
        "stomp/widgets/storage/storage-list",
        "stomp/widgets/application/application-content",
        "stomp/widgets/groups/group-content",
        "stomp/widgets/users/user-content",
        "stomp/widgets/storage/storage-content",
        "stomp/widgets/util",
        "dojo/request/xhr",
        "dojo/topic",
        "dojo/ready",
        "dojo/_base/lang",
        "dojox/widget/Toaster",
        "dojo/dom-construct"
       ],
        function(
                 dashboard,
                 hostList, 
                 clusterStats, 
                 appUsage, 
                 workloadManager, 
                 metrics, 
                 eventLogs,
                 appList,
                 groupList, 
                 userList, 
                 storageList, 
                 appContent, 
                 groupContent, 
                 userContent, 
                 storageContent, 
                 util,
                 xhr,
                 topic,
                 ready,
                 lang,
                 notify,
                 dc
        ) {
            // publish error/warnings/messages
            ready(function() {
                util.start_load("Initializing dashboard...");
                var error = new notify({
                    positionDirection: 'tr-down',
                    messageTopic: '/stomp/error',
                    duration: 12000
                });
                var info = new notify({
                    messageTopic: '/stomp/info',
                    positionDirection: 'br-up',
                    duration: 12000
                });

                if (role != 'admin') {
                    role = undefined;
                }

                var ws = new WebSocket("ws://"+ window.location.hostname +":9786");
                ws.onopen = ws_open();
                ws.onmessage = function(evt) { ws_message(evt); };
                ws.onclose = ws_close;

                new dashboard({ 'node':'content', 'id': 'dashboard'});

                if (role == 'admin') {

                    new appContent({ 'node':'content', 'id': 'applications'});
                    new groupContent({ 'node':'content', 'id': 'groups'});
                    new userContent({ 'node':'content', 'id': 'users'});

                    new hostList({ 'node': 'control_panel', 'id': 'hosts_panel'});
                    $('#dashboard_panel_button').trigger('click');

                    new appList({ 'node': 'control_panel', 'id': 'applications_panel', 'role': role});
                    new groupList({ 'node':'control_panel', 'id': 'groups_panel'});
                    new userList({ 'node':'control_panel', 'id': 'users_panel'});

                    var cluster_stats = dc.create("div", {"class" : "row"}, "dashcontent");
                    new clusterStats({ 'node': cluster_stats, 'id': 'clusterstats'});
                    new workloadManager({ 'node': cluster_stats, 'id': 'workloadmanager'});

                    //var metric = dc.create("div", {"class" : "row"}, "dashcontent");
                    //new metrics({ 'node': metric, 'id': 'metrics'});

		} else {
                    new appList({ 'node': 'control_panel', 'id': 'applications_panel', 'role': role});
                    $('#applications_panel_button').trigger('click');
                    new appContent({ 'node':'content', 'id': 'applications'});
                    $("#dashboard").css("display", "none");
                }

                new storageList({ 'node':'control_panel', 'id': 'storages_panel', 'role': role});
                new storageContent({ 'node':'content', 'id': 'storages'});

                //var event_logs = dc.create("div", {"class" : "row"}, "dashcontent");
                //new eventLogs({ 'node': event_logs, 'id': 'eventlogs'});


                util.stop_load();
            });
        });
}

function show_content(id, element, event) {
    $("#" + id).fadeIn(400).siblings(':visible').fadeOut(100);
    if (role != 'admin' && id == 'dashboard') {
        if (selected_menu == 'dashboard') {
            selected_menu = 'applications';
        }
        id = 'applications';
    }
    if (id != selected_menu) {
        $("#" + id + "_panel_button").parent("div").parent("div").children("div").siblings().removeClass("in").fadeOut(300);
        $("#" + id + "_panel_button").trigger("click");
    }
    $("#" + id).siblings().css("display", "none");
    $("#" + id).css("display", "block");
    $("#" + id).children().children().children().css("display", "none");
    $($("#" + id).children().children().children().toArray()[0]).css("display", "block");
    selected_menu = id;
}
$(document).on('click', 'input[name=selectAll]', function(e) {
    var table= $(e.target).closest('table');
    // toggle checked prop and trigger change event
    $('td input:checkbox', table).prop('checked', this.checked).change();
});
$(document).on("click", ".nav-menu a", function (event) {
    event.preventDefault();
    event.stopPropagation();
    $(this).parent('li').addClass("active").children('ul').toggle("collapse");
    $(this).parent('li').siblings().removeClass('active').find('ul').hide(400);
    $(".menu li").siblings().removeClass('active').find('ul').hide(400);
});
$(document).on("click", ".menu a", function (event) {
    event.preventDefault();
    event.stopPropagation();
    $(this).parent('li').addClass("active").children('ul').toggle("collapse");
    $(this).parent('li').siblings().removeClass('active').find('ul').hide(400);
    $(".nav-menu li").removeClass('active');
});

$(document).on("click", ".panel-title a", function (event) {
    event.preventDefault();
    event.stopPropagation();
    $(this).parent("h4").parent('div').addClass("selected");
    $(this).parent("h4").parent('div').parent('div').siblings().children().removeClass('selected');
});
initialize();
