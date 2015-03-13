define("stomp/widgets/users/user-row", [
    "dojo/_base/declare",
    "dojo/text!./user-row.html",
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
       oprUser
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.user = this.user;
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);
               },
               onChange : function(evt) {
                   var widget = this;
                   var user = widget.user;
                   var user_group = user.group;
                   var roles = JSON.parse(JSON.stringify(widget.roles));

                   xhr('/group/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           var groups = response.groups;
                           new oprUser({'id': 'dialog',
                                         'groups': groups,
                                         'opr': 'modify',
                                         'user': user,
                                         'roles': roles
                                        });
                           dojo.forEach(user_group, function(group, index) {
                               $("#" + group).attr("checked", true);
                          });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onDelete : function(evt) {
                   var widget = this;
                   var user = widget.user;
                   new oprUser({'id': 'dialog',
                                'opr': 'delete',
                                'user': user
                               });
               }
           });
});
