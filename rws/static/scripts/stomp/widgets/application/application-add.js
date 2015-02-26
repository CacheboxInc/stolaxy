define("stomp/widgets/application/application-add", [
    "dojo/_base/declare",
    "dojo/text!./application-add.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "dojo/_base/lang",
    "dojo/request/xhr",
    "dojo/topic",
    "stomp/widgets/msgbox",
    "stomp/widgets/util"
],
       function (
       declare,
       template,
       WidgetBase,
       TemplatedMixin,
       dtl,
       Context,
       lang,
       xhr,
       topic,
       msgbox,
       util
       ) {
           return declare([WidgetBase, TemplatedMixin], {

               templateString : template,
               add: function () {
                   var widget = this;
                   var data = {
                       'app_type': dojo.byId("select_application").value,
                       'app_name': dojo.byId("application_name").value,
                       'app_storage': dojo.byId("storage_size").value
                   };
                   $('#add_application').trigger('close');

                   util.start_load("Please wait while we create application");
                   xhr('/application/create', {
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
                           topic.publish("/stomp/app_create", response);
                       },
                       function (error) {
                           util.stop_load();
                           new msgbox({
                               'id': 'dialog',
                               'msg': error.response.data.msg
                           });
                       });
               },
               onDatastoreSelect: function(evt) {
                    var selected = $(evt.target).val();
                    var storage_id = selected.split(",")[0];
                    var storage_size = selected.split(",")[1];
                    var size = util.getMegaBytes(storage_size);
                    var bucket = parseInt(size/ 5);
                    var buckets = new Array();
                    buckets[0] = bucket;
                    for (var i = 0; i < 5; i++) {
                       buckets.push(buckets[i] + bucket);
                    }
                    var storage_size = new Array()
                    for (var i = 0; i < (buckets.length - 1); i++) {
                        storage_size.push(util.getusize(buckets[i]));
                    } 
                    
                   $(".slider").slider({ 
                        min: 0, 
                        max: storage_size.length-1, 
                        value: 0
                   }).slider("pips", {
                         rest: "label",
                         labels: storage_size
                    }).on("slidechange", function(e, ui) {
                        $("#storage_size").val(storage_size[ui.value]);
                   });
               },
               onclose: function () {
                   $('#add_application').trigger('close');
               },
               postCreate: function () {
                   var widget = this;
                   widget.placeAt(dojo.byId("dialog"));
                   widget.template = new dtl.Template(widget.templateString);
                   widget.showAddApplicationPopup();
                   var storages = widget.storages;
                   var size = util.getMegaBytes(storages[0].size);
                   var bucket = parseInt(size/ 5);
                   var buckets = new Array();
                   buckets[0] = bucket;
                   for (var i = 0; i < 5; i++) {
                      buckets.push(buckets[i] + bucket);
                   }
                   var storage_size = new Array()
                   for (var i = 0; i < (buckets.length - 1); i++) {
                       storage_size.push(util.getusize(buckets[i]));
                   } 
                   // activate the slider with options
                   $(".slider").slider({ 
                        min: 0, 
                        max: storage_size.length-1, 
                        value: 0
                   }).slider("pips", {
                         rest: "label",
                         labels: storage_size
                    }).on("slidechange", function(e, ui) {
                        $("#storage_size").val(storage_size[ui.value]);
                   });
               },
               showAddApplicationPopup: function () {
                   $('#add_application').lightbox_me({
                       onClose: function () {
                           dijit.byId("dialog").destroy();
                       },
                       centered: true,
                       destroyOnClose: true
                   });
               }
       });
});
