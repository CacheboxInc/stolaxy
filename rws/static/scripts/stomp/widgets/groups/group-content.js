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
       oprGroup
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
               initUserSelected: function() {
                   var widget = this;
                   if ('undefined' !== typeof widget.userSelected) {
                       $.each(widget.userSelected, function(k, v){
                           var n = v[0];
                           d3.select(n[0]).style("stroke", "");
                       });
                   }
                   widget.userSelected = [];
               },
               initGroupSelected: function() {
                   var widget = this;
                   if ('undefined' !== typeof widget.groupSelected) {
                       if (widget.groupSelected) {
                           widget.groupSelected.style("stroke", "");
                       }
                   }
                   widget.groupSelected = false;
               },
               initialize: function() {
                   var widget = this;
                   widget.initGroupSelected();
                   widget.initUserSelected();
                   widget.contentWidth  = 900;
                   widget.contentHeight = 500;
                   widget.color = d3.scale.category20();
                   widget.radius = d3.scale.sqrt().range([0, 6]);
                   widget.svg = d3.select("#group-content")
                                         .append("svg")
                                         .attr("width", widget.contentWidth)
                                         .attr("height", widget.contentHeight)
                                         .style("border-left", "1px solid #ccc");
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
                   widget.force.start();
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
                                        .attr("class", "node")
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
                                            d3.select(this).on("click", function(d){
                                                             if (widget.groupSelected) {
                                                                 widget.initGroupSelected();
                                                             }
                                                             if (d.hasOwnProperty("users")) {
                                                                 widget.initUserSelected();
                                                                 widget.groupSelected = d3.select(this)
                                                                                          .style("stroke", "#000")
                                                             } else {
                                                                 //Allow selection of multiple users from one group only.
                                                                 if (widget.userSelected.length > 0) {
                                                                     var nodedata = widget.getNodeData(widget.userSelected[0]);
                                                                     if (nodedata.group.id != d.group.id) {
                                                                         widget.initUserSelected();
                                                                     }
                                                                 }
                                                                 widget.initGroupSelected();
                                                                 if (!widget.containsNode(d)) {
                                                                     widget.userSelected.push( d3.select(this)
                                                                                                 .style("stroke", "#000") );
                                                                 } else {
                                                                     d3.select(this).style("stroke", "");
                                                                     widget.removeUserOnClick(d);
                                                                 }
                                                             }
                                                         });
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
                                            d3.select(this).attr("title", function(d){
                                                               if ( d.hasOwnProperty("users") ) {
                                                                   return d.name;
                                                               } else {
                                                                   return d.fullname;
                                                               }
                                            });
                                            d3.select(this).attr("data-content", function(d){
                                                               if ( d.hasOwnProperty("users") ) {
                                                                   return widget.showGroupContent(d);
                                                               } else {
                                                                   return widget.showUserContent(d);
                                                               }
                                            });
                                        });
                   widget.force.on("tick", function() {
                       link.selectAll("line")
                           .attr("x1", function(d) { return d.source.x; })
                           .attr("y1", function(d) { return d.source.y; })
                           .attr("x2", function(d) { return d.target.x; })
                           .attr("y2", function(d) { return d.target.y; });
                       node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; })
                   });

                   //Init the popover
                   $('svg g').popover({
                       'trigger':'hover',
                       'container': 'body',
                       'placement': 'top',
                       'white-space': 'nowrap',
                       'html':'true'
                   });
               },
               showSymbols: function() {
                   var widget = this;
                   var svg = d3.select("#symbols")
                                        .append("svg")
                                        .attr("width", 50)
                                        .attr("height", 150)
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
               removeUser: function() {
                   var widget = this;
                   if (widget.userSelected.length > 0) {
                       var users = [];
                       var userids= [];
                       $.each(widget.userSelected, function(k, v){
                           users.push(widget.getNodeData(v));
                           userids.push(widget.getNodeData(v).id);
                       });
                       var user = widget.getNodeData(widget.userSelected);
                       new oprGroup({'id': 'dialog',
                                     'opr': 'removeUser',
                                     'users': users,
                                     'userids': userids
                                   });
                   } else {
                       var title = '<h3>Error</h3>';
                       var body = '<p>No user is selected to remove.</p>';
                       topic.publish("/stomp/info", title + body);
                   }
               },
               deleteGroup: function() {
                   var widget = this;
                   if ($.isEmptyObject(widget.groupSelected)) {
                       var title = '<h3>Error</h3>';
                       var body = '<p>No group is selected to delete.</p>';
                       topic.publish("/stomp/info", title + body);
                   } else {
                       var group = widget.getNodeData(widget.groupSelected);
                       new oprGroup({'id': 'dialog',
                                     'opr': 'delete',
                                     'group': group
                                   });
                   }
               },
               updateUserGroup: function() {
                   var widget = this;
                   if (widget.userSelected.length > 0) {
                       var users = [];
                       $.each(widget.userSelected, function(k, v){
                           users.push(widget.getNodeData(v));
                       });
                       xhr('/group/list', {
                           'handleAs': 'json',
                           'method': 'GET',
                           'query': {
                           }
                       }).then(
                           function (response) {
                               var groups = [];
                               $.each(response.groups, function (k, v){
                                   if (v.id != users[0].group.id) { 
                                       groups.push(v);
                                   }
                               });
                               new oprGroup({'id': 'dialog',
                                             'groups': groups,
                                             'opr': 'updateUserGroup',
                                             'users': users
                                            });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
                   } else {
                       var title = '<h3>Error</h3>';
                       var body = '<p>No user is selected to update.</p>';
                       topic.publish("/stomp/info", title + body);
                   }
               },
               showAllGroups: function() {
                   var widget = this;
                   topic.publish("/stomp/groups_content");
               },
               getNodeData: function(node) {
                   return node[0][0].__data__;
               },
               showGroupContent: function(d) {
                   var str  = '';
                       str += '<table class="table table-group-tooltip">';
                       str += '<tbody>';
                       str += '<tr>';
                       str += '<td><strong>Created On:</td>';
                       str += '<td>'+util.format_datetime(d.created)+'</td>';
                       str += '</tr>';
                       str += '</tbody>';
                       str += '</table>';
                       return str;
               },
               showUserContent: function(d) {
                   onlinestatus = '<i class="fa fa-times-circle fa-1x"></i>';
                   if (d.online)
                       onlinestatus = '<i class="fa fa-check-circle fa-1x"></i>';
                   var str  = '';
                       str += '<table class="table table-user-tooltip">';
                       str += '<tbody>';
                       str += '<tr>';
                       str += '<td><strong>Email:</td>';
                       str += '<td>'+d.email+'</td>';
                       str += '</tr>';
                       str += '<tr>';
                       str += '<td><strong>Online:</td>';
                       str += '<td>'+onlinestatus+'</td>';
                       str += '</tr>';
                       str += '</tbody>';
                       str += '</table>';
                       return str;
               },
               containsNode: function(obj) {
                   var widget = this;
                   var i, userSelected = widget.userSelected;
                   for (i = 0; i < userSelected.length; i++) {
                       var nodedata = widget.getNodeData(userSelected[i]);
                       if (nodedata == obj) {
                           return true;
                       }
                   }
                   return false;
               },
               removeUserOnClick: function(d) {
                   var widget = this;
                   widget.userSelected = $.grep(widget.userSelected, function(v, k){
                       return widget.getNodeData(v) != d;
                   });
               }
           });
});
