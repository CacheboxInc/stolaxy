define("stomp/widgets/hosts/host-list", [
    "dojo/_base/declare",
    "dojo/text!./host-list.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "dojo/_base/lang",
    "dojo/dom-construct",
    "dojo/request/xhr",
    "dojo/topic",
    "dojo/_base/array",
    "stomp/widgets/msgbox",
    "stomp/widgets/util",
    "stomp/widgets/hosts/host-opr",
    "stomp/widgets/hosts/host-row",

], function (
       declare,
       template,
       WidgetBase,
       TemplatedMixin,
       dtl,
       Context,
       lang,
       dc,
       xhr,
       topic,
       array,
       msgbox,
       util,
       oprHost,
       rowHost
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   topic.subscribe("/stomp/host_create", lang.hitch(widget, 'hostCreate'));
                   topic.subscribe("/stomp/host_change", lang.hitch(widget, 'hostChange'));
                   topic.subscribe("/stomp/host_delete", lang.hitch(widget, 'hostDelete'));
                   
                   xhr('/host/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           dojo.forEach(response.hosts, function (host, index) {
                               new rowHost({
                                             'host': host,
                                             'node': "host_list",
                                             'pos': 'last'
                                          });
                           });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onCreate : function () {
                   var widget = this;
                   new oprHost({'id': 'dialog',
                                'opr': 'create'
                             });
               },
               hostCreate : function(data) {
                   var title = '<h3>Succussfully created</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.hosts, function (host, index) {
                       new rowHost({
                                    'host': host,
                                    'pos': 'last',
                                    'node': "host_list"
                                  });
                   });
               },
               hostChange : function(data) {
                   var title = '<h3>Succussfully updated</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.hosts, function (host, index) {
                       new rowHost({
                                    'host': host,
                                    'node': host.old_ipaddress + "_app_row",
                                    'pos': 'replace'
                                  });
                   });
               },
               hostDelete : function(response, ip) {
                  var title = '<h3>Succussfully deleted</h3>';
                  var body = '<p>' + response.msg + '</p>';
                  topic.publish("/stomp/info", title + body);
                  dc.destroy(ip + "_host_row");
               }
           });
});
