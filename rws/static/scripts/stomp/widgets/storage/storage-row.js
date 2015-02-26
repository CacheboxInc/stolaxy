define("stomp/widgets/storage/storage-row", [
    "dojo/_base/declare",
    "dojo/text!./storage-row.html",
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
    "stomp/widgets/storage/storage-opr"
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
       oprStorage
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.storage = this.storage;
                   if (widget.role != 'admin') {
                       widget.role = null;
                   }
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);

               },
               onChange : function(evt) {
                   var widget = this;
                   var storage = widget.storage;
                   var storage_id = widget.storage.id;
                   var storage_name = widget.storage.name;
                   var storage_volumes = widget.storage.backing_volume.split(",");

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
                                           'opr': 'modify',
                                           'storage': storage,
                                           'storage_name': storage_name,
                                           'storage_id': storage_id
                                        });
                           dojo.forEach(storage_volumes, function(volume, index) {
                               $("#" + volume).attr("checked", true);
                          });
                       },
                       function (error) {
                               console.error(error.response.data.msg);
                       });
               },
               onDelete : function(evt) {
                   var widget = this;
                   var storage = widget.storage;
                   new oprStorage({'id': 'dialog',
                                   'opr': 'delete',
                                   'storage': storage,
                                 });
              }
           });
});
