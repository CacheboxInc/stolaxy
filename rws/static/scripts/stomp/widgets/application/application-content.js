define("stomp/widgets/application/application-content", [
    "dojo/_base/declare",
    "dojo/text!./application-content.html",
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
    "stomp/widgets/application/application-add"
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
               }
           });
});
