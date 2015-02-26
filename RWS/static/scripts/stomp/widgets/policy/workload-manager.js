var STATS_INTERVAL = 60000;

define("stomp/widgets/policy/workload-manager", [
    "dojo/_base/declare",
    "dojo/text!./workload-manager.html",
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
               plotPolicyDistribution : function(stats) {
                   var widget = this;
                   widget.pieOptions = graphUtils.getGraphOptions("pie");
                   $.plot($("#policy_distribution"), stats, widget.pieOptions);
               },
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   var stats = [
                                {'label': 'platinum', 'data' : 12},
                                {'label': 'gold', 'data' : 32},
                                {'label': 'silver', 'data' : 23},
                                {'label': 'bronze', 'data' : 31}
                               ]
                   widget.plotPolicyDistribution(stats);
               }
           });
});
