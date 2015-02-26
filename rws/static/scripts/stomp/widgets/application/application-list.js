define("stomp/widgets/application/application-list", [
    "dojo/_base/declare",
    "dojo/text!./application-list.html",
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
    "stomp/widgets/application/application-add",
    "stomp/widgets/application/application-row"
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
       addApplication,
       rowApplication
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   if (widget.role != 'admin') {
                       widget.role = null;
                   }
                   topic.subscribe("/stomp/app_create", lang.hitch(widget, 'applicationCreate'));
                   topic.subscribe("/stomp/app_change", lang.hitch(widget, 'applicationChange'));
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   
                   xhr('/application/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           dojo.forEach(response.applications, function (app, index) {
                              var opr = "pause";
                              if (app.astate != "running") {
                                  opr = "play";
                              }
                              new rowApplication({
                                                  'app': app,
                                                  'node': 'application_list',
                                                  'pos': 'last',
                                                  'opr': opr,
                                                  'role': widget.role
                                                });
                           });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onCreate : function () {
                   var widget = this;
                   applications = ['mapreduce', "spark", "hadoop", "hive", "pig"];
                   xhr('/storage/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                             new addApplication({'id': 'dialog',
                                                 'applications': applications,
                                                 'storages': response.storages
                                      });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               applicationCreate : function(data) {
                   var widget = this;
                   var title = '<h3>Succussfully created</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.applications, function (application, index) {
                         var opr = "pause";
                         if (application.astate != "running") {
                             opr = "play";
                         }
                         new rowApplication({
                                             'app': application,
                                             'node': 'application_list',
                                             'pos': 'last',
                                             'opr': opr,
                                             'role': widget.role
                                           });
                   });
               },
               applicationChange : function(data) {
                   var widget = this;
                   var title = '<h3>Succussfully updated</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.applications, function (application, index) {
                          var opr = "pause";
                          if (application.astate != "running") {
                              opr = "play";
                          }

                          new rowApplication({
                                              'app': application,
                                              'node': application.cluster_id + '_app_row',
                                              'pos': 'replace',
                                              'opr': opr,
                                              'role': widget.role
                                            });
                   });
               },
           });
});
