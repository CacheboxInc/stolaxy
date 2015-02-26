define("stomp/widgets/storage/storage-list", [
    "dojo/_base/declare",
    "dojo/text!./storage-list.html",
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
    "stomp/widgets/storage/storage-opr",
    "stomp/widgets/storage/storage-row",
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
       oprStorage,
       rowStorage
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   if (widget.role != 'admin') {
                       widget.role = null;
                   }
                   topic.subscribe("/stomp/storage_create", lang.hitch(widget, 'storageCreate'));
                   topic.subscribe("/stomp/storage_change", lang.hitch(widget, 'storageChange'));
                   topic.subscribe("/stomp/storage_delete", lang.hitch(widget, 'storageDelete'));
                   widget.placeAt(this.node);
                   widget.template = new dtl.Template(widget.templateString);
                   
                   xhr('/storage/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           dojo.forEach(response.storages, function (storage, index) {
                               new rowStorage({
                                               'storage': storage,
                                               'role': widget.role,
                                               'node': 'datastore_list',
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
                   xhr('/storage/volume/list', {
                       'handleAs': 'json',
                       'method': 'GET',
                       'query': {
                       }
                   }).then(
                       function (response) {
                           var volumes = response.volumes;
                           new oprStorage({'id': 'dialog',
                                           'volumes': volumes,
                                           'opr': 'create'
                                        });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               storageCreate : function(data) {
                   var widget = this;
                   var title = '<h3>Succussfully created</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.storages, function (storage, index) {
                       new rowStorage({
                                       'storage': storage,
                                       'role': widget.role,
                                       'node': 'datastore_list',
                                       'pos': 'last'
                                     });
                   });
               },
               storageChange : function(data) {
                   var widget = this;
                   var title = '<h3>Succussfully updated</h3>';
                   var body = '<p>' + data.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dojo.forEach(data.storages, function (storage, index) {
                       new rowStorage({
                                       'storage': storage,
                                       'role': widget.role,
                                       'node': storage.id + '_storage_row',
                                       'pos': 'replace'
                                     });
                   });
               },
               storageDelete : function(response, storage) {
                   var title = '<h3>Succussfully deleted</h3>';
                   var body = '<p>' + response.msg + '</p>';
                   topic.publish("/stomp/info", title + body);
                   dc.destroy(storage.id + "_storage_row");
               }
           });
});
