define("stomp/widgets/groups/group-opr", [
    "dojo/_base/declare",
    "dojo/text!./group-add.html",
    "dojo/text!./group-modify.html",
    "dojo/text!./group-delete.html",
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
                   var checkbox = dojo.query("#group_users input[type=checkbox]:checked");
                   var users = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   var data = {
                       'group_name': dojo.byId("group_name").value,
                       'group_users': users
                   };

                   $('#group_opr').trigger('close');

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
                   var checkbox = dojo.query("#group_users input[type=checkbox]:checked");
                   var users = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   var group_id = $("#group_id").val();

                   var data = {
                       'group_name': dojo.byId("group_name").value,
                       'group_users': users,
                       'group_id': group_id
                   };

                   $('#group_opr').trigger('close');

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
                       'group_id': group.id
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
               }
       });
});
