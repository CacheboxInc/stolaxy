define("stomp/widgets/groups/group-opr", [
    "dojo/_base/declare",
    "dojo/text!./group-add.html",
    "dojo/text!./group-modify.html",
    "dojo/text!./group-delete.html",
    "dojo/text!./group-remove-user.html",
    "dojo/text!./group-update-user.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "dojo/_base/lang",
    "dojo/request/xhr",
    "dojo/topic",
    "dojo/_base/array",
    "stomp/widgets/msgbox",
    "stomp/widgets/util"
],
       function (
       declare,
       template_add,
       template_modify,
       template_delete,
       template_remove,
       template_modifyusergroup,
       WidgetBase,
       TemplatedMixin,
       dtl,
       Context,
       lang,
       xhr,
       topic,
       array,
       msgbox,
       util
       ) {
           return declare([WidgetBase, TemplatedMixin], {

               add: function () {
                   var widget = this;
                   if (!widget.validate()) {
                       return false;
                   }
                   var checkbox = dojo.query("#group_users input[type=checkbox]:checked");
                   var users = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   var data = {
                       'name': dojo.byId("group_name").value,
                       'users': users
                   };


                   util.start_load("Please wait while we create group");
                   xhr('/group/create', {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       },
                       data: dojo.toJson(data)
                   }).then(
                       function (response) {
                           if (!response.error)
                               $('#group_opr').trigger('close');
                           util.stop_load();
                           topic.publish("/stomp/group_create", response);
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               selectall: function(evt) {
                   var checked = $(evt.target).attr('checked');
                   if (!checked) {
                       checked = false;
                   }
                   var div= $('#group_users');
                   // toggle checked prop and trigger change event
                   $('div input:checkbox', div).prop('checked', checked).change();
               },
               update: function() {
                   var widget = this;
                   if (!widget.validate()) {
                       return false;
                   }
                   var checkbox = dojo.query("#group_users input[type=checkbox]:checked");
                   var users = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   var group_id = $("#group_id").val();

                   var data = {
                       'name': dojo.byId("group_name").value,
                       'users': users,
                       'id': group_id
                   };


                   util.start_load("Please wait while we update the group");
                   xhr('/group/update', {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       },
                       data: dojo.toJson(data)
                   }).then(
                       function (response) {
                           util.stop_load();
                           topic.publish("/stomp/group_change", response);
                           if (!response.error)
                               $('#group_opr').trigger('close');
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               del: function () {
                   var widget = this;
                   var group = widget.group;

                   util.start_load("Please wait while we delete the group");
                   var data = {
                       'id': group.id
                   };

                   xhr('/group/delete', {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       },
                       data: dojo.toJson(data)
                   }).then(
                       function (response) {
                           util.stop_load();
                           topic.publish("/stomp/group_delete", response, group);
                           $('#group_opr').trigger('close');
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               removeUserFromGroup: function () {
                   var widget = this;
                   var users = widget.users;
                   var userids = widget.userids;

                   util.start_load("Please wait while we remove user from group");
                   var data = {
                       'id': users[0].group.id,
                       'users': userids
                   };

                   xhr('/group/removeuser', {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       },
                       data: dojo.toJson(data)
                   }).then(
                       function (response) {
                           util.stop_load();
                           topic.publish("/stomp/groups_content", response);
                           $('#group_opr').trigger('close');
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               updateUserGroup: function() {
                   var widget = this;
                   var checkbox = dojo.query("#group_users_list input[type=checkbox]:checked");
                   var users = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   var group_id = $('input[name=group_id]:checked', '#user_groups_list').val();

                   var data = {
                       'users': users,
                       'id': group_id
                   };


                   util.start_load("Please wait while we update the user's group");
                   xhr('/group/addusertogroup', {
                       'handleAs': 'json',
                       'method': 'POST',
                       'headers': {
                                   'Content-Type': "application/json; charset=utf-8"
                       },
                       'query': {
                       },
                       data: dojo.toJson(data)
                   }).then(
                       function (response) {
                           util.stop_load();
                           topic.publish("/stomp/groups_content", response);
                           if (!response.error)
                               $('#group_opr').trigger('close');
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               onclose: function () {
                   $('#group_opr').trigger('close');
               },
               postMixInProperties: function() {
                   var widget = this;
                   if (widget.opr == 'create') {
                       widget.templateString = template_add;
                   } else if (widget.opr == 'modify'){
                       widget.templateString = template_modify;
                   } else if (widget.opr == 'delete'){
                       widget.templateString = template_delete;
                   } else if (widget.opr == 'removeUser'){
                       widget.templateString = template_remove;
                   } else if (widget.opr == 'updateUserGroup'){
                       widget.templateString = template_modifyusergroup;
                   }
               },
               postCreate: function () {
                   var widget = this;
                   widget.group = this.group;
                   widget.placeAt(dojo.byId("dialog"));
                   widget.template = new dtl.Template(widget.templateString);
                   widget.showGroupOprPopup();
               },
               showGroupOprPopup: function () {
                   $('#group_opr').lightbox_me({
                       onClose: function () {
                           dijit.byId("dialog").destroy();
                       },
                       centered: true,
                       destroyOnClose: true
                   });
               },
               validate: function() {
                   var widget = this;
                   widget.cleanup();
                   group_name = dojo.byId("group_name").value;
                   if ($.trim(group_name) == '') {
                       $("#group_name").addClass('err-highlight-input');
                       return false;
                   }
                   return true; 
               },
               cleanup: function() {
                   $("#group_name").removeClass('err-highligh-input');
               }
       });
});
