define("stomp/widgets/dashboard", [
    "dojo/_base/declare",
    "dojo/text!./templates/dashboard.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "dojo/_base/lang",
    "dojo/dom-construct",
    "dojo/request/xhr",
    "dojo/topic"
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
       topic
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   widget.showDashboard();
               },
               showDashboard: function () {
                   var widget = this;

                   var d = $("#dashboard").css('display');
                   var v = $("#dashboard").css('visibility');
                   if (d == 'none') {
                         $("#dashboard").css('display', 'block');
                         $("#dashboard").css('visibility', 'hidden');
                   }
                   $("#dashboard").css('display', d);
                   $("#dashboard").css('visibility', v);
               }
           });
});
