define("stomp/widgets/users/user-opr", [
    "dojo/_base/declare",
    "dojo/text!./user-add.html",
    "dojo/text!./user-modify.html",
    "dojo/text!./user-delete.html",
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
                   var group = $('input[name=selected_group]:checked', '#user_groups').val()

                   var data = {
                       'user_name': dojo.byId("user_name").value,
                       'user_group': group
                   };

                   $('#user_opr').trigger('close');

                   util.start_load("Please wait while we create application");
                   xhr('/user/create', {
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
                           topic.publish("/stomp/user_create", response);
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
                   var div= $('#user_users');
                   // toggle checked prop and trigger change event
                   $('div input:radio', div).prop('checked', checked).change();
               },
               update: function() {
                   var widget = this;
                   var group = $('input[name=selected_group]:checked', '#user_groups').val()

                   var user_id = $("#user_id").val();

                   var data = {
                       'user_name': dojo.byId("user_name").value,
                       'user_group': group,
                       'user_id': user_id
                   };

                   $('#user_opr').trigger('close');

                   util.start_load("Please wait while we create the user");
                   xhr('/user/update', {
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
                           topic.publish("/stomp/user_change", response);
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               del : function(evt) {
                   var widget = this;
                   var user = widget.user;
                   var data = {
                       'user_id': user.id,
                       'user_name': user.name
                   };
                   $('#user_opr').trigger('close');

                   util.start_load("Please wait while we remove " + user.name);
                   xhr('/user/delete', {
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
                           topic.publish("/stomp/user_delete", response, user);
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
                   $('#user_opr').trigger('close');
               },
               postMixInProperties: function() {
                   var widget = this;
                   if (widget.opr == 'create') {
                       widget.templateString = template_add;
                   } else if (widget.opr == 'modify') {
                       widget.templateString = template_modify;
                   } else if (widget.opr == 'delete') {
                       widget.templateString = template_delete;
                   }
               },
               postCreate: function () {
                   var widget = this;
                   widget.user = this.user;
                   widget.placeAt(dojo.byId("dialog"));
                   widget.template = new dtl.Template(widget.templateString);
                   widget.showUserOprPopup();
               },
               showUserOprPopup: function () {
                   $('#user_opr').lightbox_me({
                       onClose: function () {
                           dijit.byId("dialog").destroy();
                       },
                       centered: true,
                       destroyOnClose: true
                   });
               }
       });
});
