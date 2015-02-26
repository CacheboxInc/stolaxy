var STATS_INTERVAL = 60000;

define("stomp/widgets/hosts/host-content", [
    "dojo/_base/declare",
    "dojo/text!./host-content.html",
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
               plotContainerBar : function(app_stats) {
                    var widget = this;
                    widget.barOpts = graphUtils.getGraphOptions("bar");
                    widget.barOpts.yaxis.axisLabel = '<span class="fa" style="font-size:10px;"># Containers</span>';
                    widget.barOpts.series.bars.barWidth = 1;
                    widget.barOpts.series.bars.zero = false;
                    widget.barOpts.xaxis.axisLabelPadding = 100;
                    widget.barOpts.xaxis.ticks = [
                           [-1, '<i class="fa fa-play"></i>'],
                           [1, '<i class="fa fa-pause"></i>'],
                           [3, '<i class="fa fa-stop"></i>']
                    ];

                    var plot = $.plot($("#containers"), app_stats, widget.barOpts);
               },
               updateStats: function(cpu, storage, network, memory) {
                    var widget = this;
		    widget.gauges['cpu'].redraw(cpu);
		    widget.gauges['storage'].redraw(storage);
		    widget.gauges['network'].redraw(network);
		    widget.gauges['memory'].redraw(memory);
               },
               plotHostStats: function(cpu, storage, network, memory) {
                  var widget = this;
                  var gauges = [];
			
                  function createGauge(name, label, min, max) {
			var config = {
					size: 150,
					label: label,
					min: undefined != min ? min : 0,
					max: undefined != max ? max : 100,
					minorTicks: 5
				     }
				
			var range = config.max - config.min;
			config.yellowZones = [{ from: config.min + range*0.75, to: config.min + range*0.9 }];
			config.redZones = [{ from: config.min + range*0.9, to: config.max }];
				
			gauges[name] = new Gauge(name + "HostGaugeContainer", config);
			gauges[name].render();
                        widget.gauges = gauges;
		}
			
		function createGauges()	{
			createGauge("memory", "Memory");
			createGauge("cpu", "CPU");
			createGauge("network", "Network");
			createGauge("storage", "Storage");
		}
			
	        createGauges();
                widget.updateStats(cpu, storage, network, memory);
               },
               postCreate: function () {
                   var widget = this;
                   widget.host = this.host;
                   this.domNode.id = this.host.ipaddress + "_content";
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);
                   widget.plotHostStats(78, 83, 45, 26);
                   setTimeout(function() { 
                       widget.updateStats(79, 93, 15, 56);
                   }, 6000);
                   widget.plotContainerBar([[[0, 45]], [[1, 3]], [[2, 5]]]);
               }
           });
});
