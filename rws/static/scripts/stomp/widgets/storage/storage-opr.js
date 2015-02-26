define("stomp/widgets/storage/storage-opr", [
    "dojo/_base/declare",
    "dojo/text!./storage-add.html",
    "dojo/text!./storage-modify.html",
    "dojo/text!./storage-delete.html",
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
                   var checkbox = dojo.query("#storage_volumes input[type=checkbox]:checked");
                   var volumes = array.map(checkbox, function (checked) {
                             return checked.value;
                   });
                   var data = {
                       'storage_name': dojo.byId("storage_name").value,
                       'storage_volumes': volumes
                   };

                   $('#storage_opr').trigger('close');

                   util.start_load("Please wait while we create application");
                   xhr('/storage/create', {
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
                           topic.publish("/stomp/storage_create", response);
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
                   var div= $('#storage_volumes');
                   // toggle checked prop and trigger change event
                   $('div input:checkbox', div).prop('checked', checked).change();
               },
               update: function() {
                   var widget = this;
                   var checkbox = dojo.query("#storage_volumes input[type=checkbox]:checked");
                   var volumes = array.map(checkbox, function (checked) {
                             return checked.value;
                   });

                   var storage_id = $("#storage_id").val();

                   var data = {
                       'storage_name': dojo.byId("storage_name").value,
                       'storage_volumes': volumes,
                       'storage_id': storage_id
                   };

                   $('#storage_opr').trigger('close');

                   util.start_load("Please wait while we create application");
                   xhr('/storage/update', {
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
                           topic.publish("/stomp/storage_change", response);
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
                   var storage = widget.storage;

                   var data = {
                       'storage_id': storage.id
                   };

                   $('#storage_opr').trigger('close');

                   util.start_load("Please wait while we remove the storage");
                   xhr('/storage/delete', {
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
                           topic.publish("/stomp/storage_delete", response, storage);
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
                   $('#storage_opr').trigger('close');
               },
               postMixInProperties: function() {
                   var widget = this;
                   if (widget.opr == 'create') {
                       widget.templateString = template_add;
                   } else if(widget.opr == 'modify') {
                       widget.templateString = template_modify;
                   } else if(widget.opr == 'delete') {
                       widget.templateString = template_delete;
                   }
               },
               postCreate: function () {
                   var widget = this;
                   widget.storage = this.storage;
                   widget.placeAt(dojo.byId("dialog"));
                   widget.template = new dtl.Template(widget.templateString);
                   widget.showStorageOprPopup();
               },
               showStorageOprPopup: function () {
                   $('#storage_opr').lightbox_me({
                       onClose: function () {
                           dijit.byId("dialog").destroy();
                       },
                       centered: true,
                       destroyOnClose: true
                   });
               }
       });
});
