define("stomp/widgets/groups/group-row", [
    "dojo/_base/declare",
    "dojo/text!./group-row.html",
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
       oprGroup
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.group = this.group;
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);
               },    
               onChange : function(evt) {
                   var widget = this;
                   var group = widget.group;
                   var group_id = widget.group.id;
                   var group_name = widget.group.name;
                   var group_users = widget.group.users.split(",");

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
                                         'group': group,
                                         'group_name': group_name,
                                         'group_id': group_id
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
                   var group = widget.group;

                   new oprGroup({'id': 'dialog',
                                 'opr': 'delete',
                                 'group': group
                               });

               }
           });
});
