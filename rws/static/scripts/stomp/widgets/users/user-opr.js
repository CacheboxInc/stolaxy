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
                   var roles = JSON.parse(JSON.stringify(widget.roles));

                   if (!widget.validate()) {
                       return false;
                   }
                   var role = $('input[name=user_role]:checked', '#user_roles').val();
                   var group = $('input[name=selected_group]:checked', '#user_groups').val();
                   var email = dojo.byId("user_email").value;
                   var fullname = dojo.byId("user_fullname").value;
                   var username = dojo.byId("user_name").value;

                   var data = {
                       'role': role,
                       'email': email,
                       'group': group,
                       'username': username,
                       'fullname': fullname
                   };


                   util.start_load("Please wait while we create user");
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
                           response.roles = roles;
                           topic.publish("/stomp/user_create", response);
                           if (!response.error)
                               $('#user_opr').trigger('close');
                       },
                       function (error) {
                           util.stop_load();
                           $('#user_opr').trigger('close');
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
                   var roles = JSON.parse(JSON.stringify(widget.roles));

                   if (!widget.validate()) {
                       return false;
                   }

                   var role = $('input[name=user_role]:checked', '#user_roles').val()
                   var group = $('input[name=selected_group]:checked', '#user_groups').val()
                   var email = dojo.byId("user_email").value;
                   var userid = $("#user_id").val();
                   var fullname = dojo.byId("user_fullname").value;
                   var username = dojo.byId("user_name").value;

                   var data = {
                       'id': userid,
                       'role': role,
                       'group': group,
                       'email': email,
                       'fullname': fullname,
                       'username': username,
                   };


                   util.start_load("Please wait while we update the user");
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
                           response.roles = roles;
                           topic.publish("/stomp/user_change", response);
                           if (!response.error)
                               $('#user_opr').trigger('close');
                       },
                       function (error) {
                           util.stop_load();
                           if (!response.error)
                               $('#user_opr').trigger('close');
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
                       'id': user.id,
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
               },
               validate: function () {
                   var widget = this;
                   widget.cleanup();

                   //User email validation.
                   u_email = dojo.byId("user_email").value;
                   if ($.trim(u_email) == '') {
                       $("#user_email").addClass('err-highlight-input');
                       return false;
                   } else if (!util.is_valid_email(u_email)) {
                       $("#user_email").addClass('err-highlight-input');
                       return false;
                   }

                   //Username validation.
                   u_name = dojo.byId("user_name").value;
                   if ($.trim(u_name) == '') {
                       $("#user_name").addClass('err-highlight-input');
                       return false;
                   } else if (!util.is_valid_username(u_name)) {
                       $("#user_name").addClass('err-highlight-input');
                       return false;
                   }

                   //User role validation.
                   u_role = $("input[name=user_role]:checked", "#user_roles");
                   if (typeof u_role.val() == 'undefined') {
                       $("#user_roles").parent('div.panel').addClass("err-highlight-input");
                       return false;
                   }
                   return true;
               },
               cleanup: function () {
                   $("#user_name, #user_email").removeClass('err-highlight-input');
                   $("#user_roles").parent('div.panel').removeClass("err-highlight-input");
               }
       });
});
