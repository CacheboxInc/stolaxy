define("stomp/widgets/graph-utils", function() {

    return {

       getGraphOptions: function (type) {
           var options;
           switch(type) {
               case "gauge":
                   options = {
                       maxValue: 15,
                       animationSpeed: 32,
                       lines: 19,
                       angle: 0.15,
                       lineWidth: 0.34, // The line thickness
                       pointer: {
                           length: 1, // The radius of the inner circle
                           strokeWidth: 0.027, // The rotation offset
                           color: '#000000'
                       },
                       percentColors: [
                           [0.0, "#ff0000" ],
                           [0.50, "#f9c802"],
                           [1.0, "#a9d70b"]
                       ],
                       strokeColor: '#E0E0E0',
                       generateGradient: true
                   };
                   break;
               case "line":
                   options = {
                       series: {
                           lines: {
                               show: !0,
                               lineWidth: 1,
                               fill: !0
                           },
                           points: {
                               show: !1,
                               lineWidth: 2,
                               radius: 3
                           },
                           shadowSize: 0,
                           stack: !0
                       },
                       grid: {
                           hoverable: !0,
                           clickable: !0,
                           tickColor: "#f9f9f9",
                           borderWidth: 0
                       },
                       legend: {
                           show: !0,
                           position: "nw",
                           labelBoxBorderColor: "#fff"
                       },
                       colors: ["#a7b5c5", "#30a0eb"],
                       crosshair: { mode: "x, y", color: '#95BDDE' },
                       xaxis: {
                           mode: "time",
                           axisLabel: 'Time (H:M)',
                           tickSize: [1, "minute"],
                           axisLabelUseCanvas: true,
                           axisLabelFontSizePixels: 11,
                           axisLabelFontFamily: 'Open Sans, Arial',
                           axisLabelPadding: 8,
                           font: {
                               size: 12,
                               family: "Open Sans, Arial",
                               color: "#697695"
                           },
                       },
                       yaxis: {
                           min: 0,
                           axisLabelUseCanvas: true,
                           axisLabelFontSizePixels: 11,
                           axisLabelFontFamily: 'Open Sans, Arial',
                           axisLabelPadding: 10,
                           tickDecimals: 0,
                           font: {
                               size: 12,
                               color: "#9da3a9"
                           }
                       }
                   };
                   break;
               case "bar":
                   options = {
                           series: {
                               bars: {
                                   show: !0,
                                   barWidth: 0.13,
                                   order: 1,
                                   fill: !0,
                                   fillColor: {
                                       colors: [{
                                           opacity: .1
                                       }, {
                                           opacity: .13
                                       }]
                                   }
                               }
                           },
                           grid: {
                               hoverable: !0,
                               clickable: !0,
                               tickColor: "#f9f9f9",
                               borderWidth: 0
                           },
                           xaxis: {
                               axisLabelUseCanvas: true,
                               axisLabelFontSizePixels: 11,
                               axisLabelFontFamily: 'Open Sans, Arial',
                               axisLabelPadding: 10,
                               alignTicksWithAxis: 1,
                               font: {
                                   size: 12,
                                   family: "Open Sans, Arial",
                                   color: "#697695"
                               }
                           },
                           yaxis: {
                               min:0,
                               font: {
                                   size: 12,
                                   family: "Open Sans, Arial",
                                   color: "#697695"
                               }
                           },
                           legend: {
                               show: !0,
                               position: "nw",
                               labelBoxBorderColor: "#fff"
                           }
                   };
                   break;
               case "pie":
                   options = {
                       colors: ['#bdea74', '#7ECFD7', '#e4ae60'],
                       series: {
                            pie: {
                                show: !0,
                                radius: 1,
                                label: {
                                    show: !0,
                                    radius: .75,
                                    background: {
                                        opacity: .5
                                    },
                                    formatter: function (label, series) {
                                        return '<div style="font-size:8pt;text-align:center;padding:5px;color:white;">' + Math.round(series.percent) + '%</div>';
                                    }
                                },
                            }
                        },
                        tooltip: true,
                        tooltipOpts: {
                               content: "%p.0% %s", // show percentages, rounding to 2 decimal places
                               shifts: {
                                   x: 20,
                                   y: 0
                               },
                               defaultTheme: false
                        },
                        grid: {
                           hoverable: true
                        },
                        legend: {
                            show: !0
                        }
                   };
                   break;
           }
           return options;
       },
       getusize: function (val) {
           if ((((val / 1000) / 1000) / 1000) >= 1) {
               val = String(Math.round((((val / 1000) / 1000) / 1000))) + 'G';
           } else if (((val / 1000) / 1000) >= 1) {
               val = String(Math.round((val / 1000) / 1000)) + 'M';
           } else if ((val / 1000) >= 1) {
               val = String(Math.round(val / 1000)) + 'K';
           }
           return String(val);
       },
       hoursBetween: function (first, second) {
           var one = new Date(
               first.getFullYear(),
               first.getMonth(),
               first.getDate(),
               first.getHours(),
               first.getMinutes(),
               first.getSeconds()
               );
           var two = new Date(
                   second.getFullYear(),
                   second.getMonth(),
                   second.getDate(),
                   second.getHours(),
                   second.getMinutes(),
                   second.getSeconds()
                   );

           return Math.abs(one - two) / 36e5;
       },
       getTimeTicks: function (timestamp, flag) {
           x = this.toUTC(timestamp);
           return x.strftime('%H:%M');
       },
       toUTC: function (timestamp) {
           d = new Date(timestamp);
           // get UTC time in msec
           utc = d.getTime() + (d.getTimezoneOffset() * 60000);
           // create new Date object for different city
           // using supplied offset
           x = new Date(utc + (3600000 * utc_offset));
           return x;
       }
    };
});
