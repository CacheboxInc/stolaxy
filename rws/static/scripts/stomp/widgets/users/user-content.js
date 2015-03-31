define("stomp/widgets/users/user-content", [
    "dojo/_base/declare",
    "dojo/text!./user-content.html",
    "dojo/text!./user-profile.html",
    "dojo/text!./user-content-all.html",
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
    "stomp/widgets/users/user-opr",
    "stomp/widgets/graph-utils"
], function (
       declare,
       template,
       profile_template,
       allusers_template,
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
       addOpr,
       graphUtils
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(widget.node, widget.pos);
                   widget.template = new dtl.Template(widget.templateString);
                   if (widget.opr == "show-individual") {
                       var data = [
                           {data: [[0,1]], color: "#3c763d"},
                           {data: [[1,1]], color: "#ffff66"},
                           {data: [[2,2]], color: "#a94442"},
                       ];
                       widget.plotContainerBar(data); 
                   } else {
                       var data = [];
                       if (typeof widget.users !== 'undefined') {
                           $.each(widget.users, function(index, obj){
                               var temp = {}
                               temp['label'] = obj.fullname;
                               temp['data'] = Object.keys(obj.applications).length;
                               data.push(temp);
                           });
                           widget.plotApplicationPie(data);
                       }
                   }
               },
               postMixInProperties: function () {
                   var widget = this;
                   if (widget.opr == 'show-individual') {
                       widget.templateString = profile_template;    
                   } else if (widget.opr == 'show-all') {
                       widget.templateString = allusers_template
                   }
               },
               plotContainerBar : function(app_stats) {
                    var widget = this;
                    widget.barOpts = graphUtils.getGraphOptions("bar");
                    widget.barOpts.yaxis.axisLabel = '<span class="fa" style="font-size:10px;"># Applications</span>';
                    widget.barOpts.series.bars.barWidth = 1;
                    widget.barOpts.series.bars.zero = false;
                    widget.barOpts.xaxis.axisLabelPadding = 100;
                    widget.barOpts.xaxis.ticks = [
                           [-1, '<i class="fa fa-play"></i>'],
                           [1, '<i class="fa fa-pause"></i>'],
                           [3, '<i class="fa fa-stop"></i>']
                    ];

                    var plot = $.plot($("#user_app_stat_container"), app_stats, widget.barOpts);
               },
               showAllUsers: function (evt) {
                   var widget = this;
                   topic.publish("/stomp/users_content");
               },
               plotApplicationPie: function(app_stats) { 
                   var widget = this;
                   widget.pieOpts = graphUtils.getGraphOptions("pie");
                   widget.pieOpts.series.pie.label.formatter = function (label, series) {
                       return '<div style="font-size:8pt;text-align:center;padding:5px;color:white;">' + series.data[0][1] +  '</div>';
                   }
                   widget.pieOpts.tooltipOpts.content = function(label, xval, yval, flotItem) {
                       return yval[0][1] + " application(s)";
                   }
                   $.plot($("#all_users_stats_pie_container"), app_stats, widget.pieOpts);
               },
               plotApplicationLine: function(app_stats) { 
                   var widget = this;
                   widget.lineOpts = graphUtils.getGraphOptions("line");
                   $.plot($("#all_users_stats_line_container"), app_stats, widget.lineOpts);
               }
           });
});
