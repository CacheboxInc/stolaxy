define("stomp/widgets/application/application-row", [
    "dojo/_base/declare",
    "dojo/text!./application-row.html",
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
       addApplication
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   if (widget.role != 'admin') {
                       widget.role = null;
                   }
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);
               },
               onChange : function(evt) {
                   var widget = this;
                   var op = evt.target.name;
                   var application = $(evt.target).parent().attr("name");
                   var app_id = application.split("|")[0];
                   var app_name = application.split("|")[1];
                   var op = application.split("|")[2]
                   if (op == 'play') {
                       op = 'start';
                   }

                   data = {'apps': [app_id]};

                   util.start_load("Please wait while we " + op +" application");
                   xhr('/application/' + op, {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       },
                       data: dojo.toJson(data)
                   }).then(
                       function (response) {
                           util.stop_load();
                           topic.publish("/stomp/app_change", response);
                           if (op == "delete") {
                               dc.destroy(app_id + "_app_row");
                           }
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
           });
});
