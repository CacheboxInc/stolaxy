define("stomp/widgets/users/user-list", [
    "dojo/_base/declare",
    "dojo/text!./user-list.html",
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
    "stomp/widgets/users/user-row"
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
       oprUser,
       rowUser
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   topic.subscribe("/stomp/user_create", lang.hitch(widget, 'userCreate'));
                   topic.subscribe("/stomp/user_change", lang.hitch(widget, 'userChange'));
                   topic.subscribe("/stomp/user_delete", lang.hitch(widget, 'userDelete'));
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   
                   xhr('/user/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           dojo.forEach(response.users, function (user, index) {
                              new rowUser({
                                           'user': user,
                                           'node': 'user_list',
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
                                         'opr': 'create'
                                        });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               userCreate : function(data) {
                   var title = '<h3>Succussfully created</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.users, function (user, index) {
                          new rowUser({
                                       'user': user,
                                       'node': 'user_list',
                                       'pos': 'last'
                                     });
                   });
               },
               userChange : function(data) {
                   var title = '<h3>Succussfully updated</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.users, function (user, index) {
                       new rowUser({
                                    'user': user,
                                    'node': user.id + '_user_row',
                                    'pos': 'replace'
                                  });
                   });
               },
               userDelete : function(response, user) {
                   var title = '<h3>Succussfully deleted</h3>';
                   var body = '<p>' + response.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dc.destroy(user.id + "_user_row");
               },
           });
});
