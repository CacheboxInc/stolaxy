define("stomp/widgets/groups/group-content", [
    "dojo/_base/declare",
    "dojo/text!./group-content.html",
    "dojo/text!./group-content-row.html",
    "dojo/text!./group-users-listing.html",
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
    "stomp/widgets/groups/group-opr"
], function (
       declare,
       template,
       templateResetContent,
       templateUserListing,
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
       rowOpr
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);
                   //Initialize d3 content here
                   if (widget.opr != "showGroupUsers")
                       widget.initGroupContent();
               },
               postMixInProperties: function() {
                   var widget = this;
                   if (widget.opr == "resetContainer") {
                       widget.templateString = templateResetContent;
                   } else if (widget.opr == 'showGroupUsers') {
                       widget.templateString = templateUserListing;
                   }
               },
               initialize: function() {
                   var widget = this;
                   widget.contentWidth  = 900;
                   widget.contentHeight = 500;
                   widget.color = d3.scale.category20();
                   widget.radius = d3.scale.sqrt().range([0, 6]);
                   widget.svg = d3.select("#group-content")
                                         .append("svg")
                                         .attr("width", widget.contentWidth)
                                         .attr("height", widget.contentHeight);
                   widget.force = d3.layout.force()
                                           .charge(-400)
                                           .size([widget.contentWidth, widget.contentHeight])
                                           .linkStrength(1)
                                           .linkDistance(60)
                   widget.symbol = {"group": "G", "user": "U"}
                   widget.size= {"group": 16, "user": 12}
               },
               convertToD3Json: function(data) {
                   var widget = this;
                   var nodes  = [], links = [];
                   var source = 0, target = 1;
                   $.each(data.groups, function(index, groupObj){
                       nodes.push(groupObj);
                       $.each(groupObj.users, function(index, userObj){
                           var linkObj = {};
                           linkObj.source = source;
                           linkObj.target = target;
                           nodes.push(userObj);
                           links.push(linkObj);

                           target = target+1;
                       });
                       source = target;
                       target = target+1;
                   });
                   return {"nodes": nodes, "links": links}; 
               },
               initGroupContent: function() {
                   var widget = this;
                   widget.initialize();
                   xhr("group/list", {
                       "handleAs": "json",
                       "method": "get",
                       "query": {
                       }
                   }).then(
                       function (response) {
                           //convert this JSON to D3 force readable JSON format
                           widget.json = widget.convertToD3Json(response);
                           widget.buildRelations();
                       },
                       function (error) {
                           console.error(error.response.data.msg);
                       }
                   );
               },
               buildRelations: function() {
                   var widget = this;
                   var json = widget.json;
                   //Show symbol of groups and users
                   widget.showSymbols();
                   widget.force.nodes(json.nodes);
                   widget.force.links(json.links);
                   var link = widget.svg.selectAll(".link")
                                        .data(json.links)
                                        .enter()
                                        .insert("g", ".node")
                                        .attr("class", "link")
                                        .each(function(d) {
                                            d3.select(this).append("line")
                                                           .style("stroke-width", "1px");
                                        });
                   var node = widget.svg.selectAll(".node")
                                        .data(json.nodes)
                                        .enter()
                                        .append("g")
                                        .each(function(d){
                                            d3.select(this).append("circle")
                                                           .attr("r", function(d) {
                                                               if ( d.hasOwnProperty("users") ) {
                                                                   return widget.radius(widget.size.group);
                                                               } else {
                                                                   return widget.radius(widget.size.user);
                                                               }
                                                           })
                                                           .style("fill", function(d) {
                                                               if ( d.hasOwnProperty("users") ){
                                                                   return widget.color(widget.symbol.group);
                                                               } else {
                                                                   return widget.color(widget.symbol.user);
                                                               }
                                                           });
                                            d3.select(this).on("click", function(){console.log('clicked'); });
                                            d3.select(this).append("text")
                                                           .attr("dy", ".35em")
                                                           .attr("text-anchor", "middle")
                                                           .text(function(d) { 
                                                               if ( d.hasOwnProperty("users") ){
                                                                   return "G-"+d.id;
                                                               } else {
                                                                   return "U-"+d.id;
                                                               }
                                                           });
                                            d3.select(this).call(widget.force.drag)
                                        });

                   widget.force.start();
                   widget.force.on("tick", function() {
                       link.selectAll("line")
                           .attr("x1", function(d) { return d.source.x; })
                           .attr("y1", function(d) { return d.source.y; })
                           .attr("x2", function(d) { return d.target.x; })
                           .attr("y2", function(d) { return d.target.y; });
                       node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; })
                   });
               },
               showSymbols: function() {
                   var widget = this;
                   var svg = d3.select("#symbols")
                                        .append("svg")
                                        .attr("width", 100)
                                        .attr("height", 200)
                   svg.append("g")
                      .attr("transform", "translate(25,25)")
                      .append("circle")
                      .attr("r", widget.radius(widget.size.group))
                      .style("fill", widget.color(widget.symbol.group));
                   svg.append("text")
                      .attr("dx", ".35em")
                      .attr("dy", "5em")
                      .text("Group");

                   svg.append("g")
                      .attr("transform", "translate(25,100)")
                      .append("circle")
                      .attr("r", widget.radius(widget.size.user))
                      .style("fill", widget.color(widget.symbol.user))
                   svg.append("text")
                      .attr("dx", ".75em")
                      .attr("dy", "10.5em")
                      .text("User");
               },
               showAllGroups: function() {
                   var widget = this;
                   topic.publish("/stomp/groups_content");
               }
           });
});
