var STATS_INTERVAL = 60000;

define("stomp/widgets/reports/metrics", [
    "dojo/_base/declare",
    "dojo/text!./metrics.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "dojo/_base/lang",
    "dojo/dom-construct",
    "dojo/request/xhr",
    "dojo/topic",
    "stomp/widgets/graph-utils"

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
       graphUtils
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   widget.plotGraph();
               },
               plotGraph: function() {
                   var widget = this;
                   chartLinesOptions = graphUtils.getGraphOptions("line");
                   chartLinesOptions.xaxis.show = !1;
                   chartLinesOptions.xaxis.mode = null;
                   chartLinesOptions.yaxis.axisLabel = "# jobs";
                   chartLinesOptions.grid.color = '#d5d5d5';
                   chartLinesOptions.grid.borderWidth = {top: 0, bottom:1, left:0, right:0};
                   data = [];
                   POINTS = 100;
                   var j = 0;
                   while (j < POINTS) {
                          if (j < 10) {
   			    val = 2;
                          } else if (j > 10 && j < 20) {
			    val = 5;
		          } else if (j > 30 && j < 40) {
			    val = 3;
		          } else if (j > 40 && j < 45) {
			    val = 8;
		          } else if (j > 45 && j < 80) {
			    val = 3;
		          } else {
			    val = 1;
                          }
                       data[j] = [j, val];
                       j++;
                   };
                   $.plot($("#chart"), [data], chartLinesOptions);
               }
           });
});
