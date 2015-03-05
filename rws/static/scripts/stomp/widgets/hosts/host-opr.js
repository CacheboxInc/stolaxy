define("stomp/widgets/hosts/host-opr", [
    "dojo/_base/declare",
    "dojo/text!./host-add.html",
    "dojo/text!./host-modify.html",
    "dojo/text!./host-delete.html",
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
                   if (!widget.validate()) {
                       return false;
                   }
                   var data = {
                       'host_name': dojo.byId("host_name").value,
                       'host_ip': dojo.byId("host_ip").value
                   };

                   $('#host_opr').trigger('close');

                   util.start_load("Please wait while we add host");
                   xhr('/host/create', {
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
                           topic.publish("/stomp/host_create", response);
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               update: function() {
                   var widget = this;
                   if (!widget.validate()) {
                       return false;
                   }
                   var host_old_ip = $("#host_old_ip").val();
                   var host_ip = $("#host_ip").val();
                   var host_name = $("#host_name").val();

                   var data = {
                       'host_name': host_name,
                       'host_ip': host_ip,
                       'host_old_ip': host_old_ip
                   };

                   $('#host_opr').trigger('close');

                   util.start_load("Please wait while we update");
                   xhr('/host/update', {
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
                           topic.publish("/stomp/host_change", response);
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               del: function() {
                   var widget = this;
                   var host = widget.host;

                   var data = {
                       'host_name': host.name,
                       'host_ip': host.ipaddress
                   };

                   $('#host_opr').trigger('close');

                   util.start_load("Please wait while we remove the host");
                   xhr('/host/delete', {
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
                           topic.publish("/stomp/host_delete", response, host.ipaddress);
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
                   $('#host_opr').trigger('close');
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
                   widget.host = this.host;
                   widget.placeAt(dojo.byId("dialog"));
                   widget.template = new dtl.Template(widget.templateString);
                   widget.showHostOprPopup();
               },
               showHostOprPopup: function () {
                   $('#host_opr').lightbox_me({
                       onClose: function () {
                           dijit.byId("dialog").destroy();
                       },
                       centered: true,
                       destroyOnClose: true
                   });
               },
               validate: function(e) {
                   var widget = this
                   widget.cleanup();

                   //Write custom validation here
                   var h_name = dojo.byId("host_name").value;
                   var h_ip = dojo.byId("host_ip").value;

                   if ($.trim(h_name) == '') {
                       $("#host_name").addClass('err-highlight-input');
                       return false;
                   } else if (h_ip == '') {
                       $("#host_ip").addClass('err-highlight-input');
                       return false;
                   } else if (!util.is_valid_ip(h_ip)) {
                       $("#host_ip").addClass('err-highlight-input');
                       return false;
                   }
                   return true;
               },
               cleanup: function() {
                   //Always clear the old css modifictions.
                   $("#host_name, #host_ip").removeClass('err-highlight-input');
               }
       });
});
