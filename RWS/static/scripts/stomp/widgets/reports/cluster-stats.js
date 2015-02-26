var STATS_INTERVAL = 60000;

define("stomp/widgets/reports/cluster-stats", [
    "dojo/_base/declare",
    "dojo/text!./cluster-stats.html",
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
               plotWorkLoadBar : function(app_stats) {
                    var widget = this;
                    widget.barOpts = graphUtils.getGraphOptions("bar");
                    widget.barOpts.yaxis.axisLabel = '<span class="fa" style="font-size:10px;"># Workloads</span>';
                    widget.barOpts.series.bars.barWidth = 1;
                    widget.barOpts.series.bars.zero = false;
                    widget.barOpts.xaxis.axisLabelPadding = 100;
                    widget.barOpts.xaxis.ticks = [
                           [-1, '<i class="fa fa-play"></i>'],
                           [1, '<i class="fa fa-pause"></i>'],
                           [3, '<i class="fa fa-stop"></i>']
                    ];

                    var plot = $.plot($("#application_distribution"), app_stats, widget.barOpts);
               },
               plotRadial : function(cpu, storage, network, memory) {
                   var widget = this;
                   var cpu_div = d3.select(document.getElementById('cpu_usage'));
                   var storage_div =d3.select(document.getElementById('storage_usage'));
                   var network_div = d3.select(document.getElementById('network_usage'));
                   var memory_div = d3.select(document.getElementById('memory_usage'));

                   function applyClass(div, value) {
                       if (value > 80) {
                           $("#" + div).removeClass("green");
                           $("#" + div).removeClass("orange");
                           $("#" + div).addClass("red");
                           return; 
                       } else if (value > 60) {
                           $("#" + div).removeClass("green");
                           $("#" + div).removeClass("red");
                           $("#" + div).addClass("orange");
                           return;
                       } else if (value > 30) {
                           $("#" + div).removeClass("red");
                           $("#" + div).removeClass("orange");
                           $("#" + div).addClass("green");
                           return;
                       }

                       $("#" + div).removeClass("green");
                       $("#" + div).removeClass("orange");
                       $("#" + div).removeClass("red");
                       return;
                   }

                   applyClass("cpu_usage", cpu);
                   applyClass("storage_usage", storage);
                   applyClass("network_usage", network);
                   applyClass("memory_usage", memory);

                   function labelFunction(val,min,max) {

                   }

                   function deselect() {
                   }


                   var rp1 = radialProgress(document.getElementById('cpu_usage'))
                       .label("CPU USAGE")
                       .diameter(150) 
                       .minValue(0)
                       .maxValue(100)
                       .value(cpu)
                       .render();

                   var rp2 = radialProgress(document.getElementById('storage_usage'))
                       .label("STORAGE USED")
                       .diameter(150)
                       .minValue(0)
                       .maxValue(100)
                       .value(storage)
                       .render();

                   var rp3 = radialProgress(document.getElementById('network_usage'))
                       .label("NETWORK USAGE")
                       .diameter(150)
                       .minValue(0)
                       .maxValue(100)
                       .value(network)
                       .render();

                   var rp4 = radialProgress(document.getElementById('memory_usage'))
                       .label("MEMORY USED")
                       .diameter(150)
                       .minValue(0)
                       .maxValue(100)
                       .value(memory)
                       .render();

               },
               updateStats: function(cpu, storage, network, memory) {
                    var widget = this;
		    widget.gauges['cpu'].redraw(cpu);
		    widget.gauges['storage'].redraw(storage);
		    widget.gauges['network'].redraw(network);
		    widget.gauges['memory'].redraw(memory);
               },
               plotClusterStats: function(cpu, storage, network, memory) {
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
				
			gauges[name] = new Gauge(name + "GaugeContainer", config);
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
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   widget.plotClusterStats(78, 83, 45, 26);
                   setTimeout(function() { 
                       widget.updateStats(79, 93, 15, 56);
                   }, 6000);
                   widget.plotWorkLoadBar([[[0, 45]], [[1, 3]], [[2, 5]]]);
               }
           });
});
