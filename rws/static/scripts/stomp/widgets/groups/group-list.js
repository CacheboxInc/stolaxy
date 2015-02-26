define("stomp/widgets/groups/group-list", [
    "dojo/_base/declare",
    "dojo/text!./group-list.html",
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
    "stomp/widgets/groups/group-opr",
    "stomp/widgets/groups/group-row",
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
       oprGroup,
       rowGroup
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   topic.subscribe("/stomp/group_create", lang.hitch(widget, 'groupCreate'));
                   topic.subscribe("/stomp/group_change", lang.hitch(widget, 'groupChange'));
                   topic.subscribe("/stomp/group_delete", lang.hitch(widget, 'groupDelete'));
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   
                   xhr('/group/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           dojo.forEach(response.groups, function (group, index) {
                              new rowGroup({
                                            'group': group,
                                            'node': 'group_list',
                                            'pos': 'last'
                                          }); 
                           });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onCreate : function () {
                   var widget = this;
                   xhr('/user/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           var users = response.users;
                           new oprGroup({'id': 'dialog',
                                         'users': users,
                                         'opr': 'create'
                                        });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onChange : function(evt) {
                   var widget = this;
                   var op = evt.target.name;
                   var checkbox = dojo.query("#group_list_table input[type=checkbox]:checked");
                   var groups = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   if (groups.length == 0) {
                       new msgbox({
                           'id': 'dialog',
                           'msg': "No group selected",
                       });
                       return; 
                   }
                   if (groups.length > 1) {
                       new msgbox({
                           'id': 'dialog',
                           'msg': "Please select only one group to modify.",
                       });
                       return; 
                   }

                   var group_name = $("#"+ groups[0] + "_group_row_name").attr("name");
                   var group_users = ($("#" + groups[0] + "_group_row_users").attr("name")).split(",");

                   xhr('/user/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           var users = response.users;
                           new oprGroup({'id': 'dialog',
                                         'users': users,
                                         'opr': 'modify',
                                         'group_name': group_name,
                                         'group_id': groups[0]
                                        });
                           dojo.forEach(group_users, function(user, index) {
                               $("#" + user).attr("checked", true);
                          });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onDelete : function(evt) {
                   var widget = this;
                   var op = evt.target.name;
                   var checkbox = dojo.query("#group_list_table input[type=checkbox]:checked");
                   var groups = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   if (groups.length == 0) {
                       new msgbox({
                           'id': 'dialog',
                           'msg': "No group selected",
                       });
                       return; 
                   }
                   xhr('/group/delete', {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       }
                   }).then(
                       function (response) {
                           var title = '<h3>Succussfully deleted</h3>';
                           var body = '<p>' + response.msg + '</p>';
                           topic.publish("/stomp/info", title + body);
                           dojo.forEach(groups, function(group, index) {
                               dc.destroy(group + "_app_row");
                           });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               groupCreate : function(data) {
                   var title = '<h3>Succussfully created</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.groups, function (group, index) {
                          new rowGroup({
                                        'group': group,
                                        'node': 'group_list',
                                        'pos': 'last'
                                      }); 
                   });
               },
               groupChange : function(data) {
                   var title = '<h3>Succussfully updated</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.groups, function (group, index) {
                          new rowGroup({
                                        'group': group,
                                        'node': group.id + '_group_row',
                                        'pos': 'replace'
                                      }); 
                   });
               },
               groupDelete : function(response, group) {
                   var title = '<h3>Succussfully deleted</h3>';
                   var body = '<p>' + response.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dc.destroy(group.id + "_group_row");
               }
           });
});
