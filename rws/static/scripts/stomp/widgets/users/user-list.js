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
    "stomp/widgets/users/user-row",
    "stomp/widgets/users/user-content-row",
    "stomp/widgets/users/user-content"
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
       rowUser,
       rowUserContent,
       userContent
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   topic.subscribe("/stomp/user_create", lang.hitch(widget, 'userCreate'));
                   topic.subscribe("/stomp/user_change", lang.hitch(widget, 'userChange'));
                   topic.subscribe("/stomp/user_delete", lang.hitch(widget, 'userDelete'));
                   topic.subscribe("/stomp/users_content", lang.hitch(widget, 'usersContent'));
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   var roles = JSON.parse(JSON.stringify(widget.roles));
                   xhr('/user/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           new userContent({
                                        'node': 'users',
                                        'roles': widget.roles,
                                        'opr': 'show-all',
                                        'users': response.users,
                                        'pos': 'only'
                           });
                           dojo.forEach(response.users, function (user, index) {
                               new rowUser({
                                           'user': user,
                                           'node': 'user_list',
                                           'pos': 'last',
                                           'roles': roles
                                         });
                               new rowUserContent({
                                           'user': user,
                                           'node': 'ulist_body',
                                           'pos': 'last',
                                           'roles': roles
                               });
                           });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onCreate : function () {
                   var widget = this; 
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
                                         'opr': 'create',
                                         'roles': roles
                                        });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
                   $(document).on("keyup", "#user_email", function(e){
                       widget.autoFillUsername($(this).val());
                   });

               },
               userCreate : function(data) {
                   if (!data.error)
                       var title = '<h3>Succussfully created</h3>';
                   else
                       var title = '<h3>Error</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   if (!data.error) {
                       dojo.forEach(data.users, function (user, index) {
                           new rowUser({
                                       'user': user,
                                       'node': 'user_list',
                                       'pos': 'last',
                                       'roles': data.roles
                                     });
                           new rowUserContent({
                                       'user': user,
                                       'node': 'ulist_body',
                                       'pos': 'last'
                                     });
                       });
                   }
               },
               userChange : function(data) {
                   if (!data.error)
                       var title = '<h3>Succussfully updated</h3>';
                   else
                       var title = '<h3>Error</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   if (!data.error) {
                       dojo.forEach(data.users, function (user, index) {
                           new rowUser({
                                    'user': user,
                                    'node': user.id + '_user_row',
                                    'pos': 'replace',
                                    'roles': data.roles
                                  });
                       });
                   }
               },
               userDelete : function(response, user) {
                   var title = '<h3>Succussfully deleted</h3>';
                   var body = '<p>' + response.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dc.destroy(user.id + "_user_row");
                   dojo.query("."+user.id+"_user_content_row").forEach(dojo.destroy);
               },
               usersContent : function(data) {
                   var widget = this;
                   xhr('/user/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           new userContent({
                                        'node': 'users',
                                        'roles': widget.roles,
                                        'opr': 'show-all',
                                        'users': response.users,
                                        'pos': 'only'
                           });
                           dojo.forEach(response.users, function (user, index) {
                               new rowUserContent({
                                           'user': user,
                                           'node': 'ulist_body',
                                           'pos': 'last',
                                           'roles': roles
                               });
                           });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });

               },
               autoFillUsername: function(data) {
                   //Do not allow special characters.
                   //Stop append after '@'
                   var pattern = /[&\/\\#,+()@$~%.'":*?<>{}]/g;
                   if (data.indexOf('@') == -1)
                       $("#user_name").val(data.replace(pattern, ''));
               }
           });
});
