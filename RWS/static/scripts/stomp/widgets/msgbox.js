define("stomp/widgets/msgbox", [
    "dojo/_base/declare",
    "dojo/text!./templates/msgbox.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "stomp/widgets/util"
],
       function (
       declare,
       template,
       WidgetBase,
       TemplatedMixin,
       dtl,
       Context,
       util
       ) {
           return declare([WidgetBase, TemplatedMixin], {

               onclose: function () {
                   $('#msgbox').trigger('close');
               },
               postCreate: function () {
                   this.placeAt(dojo.byId("dialog"));
                   this.showMessagePopup();
               },
               showMessagePopup: function () {
                   $('#msgbox').lightbox_me({
                       onClose: function () {
                           dijit.byId("dialog").destroy();
                       },
                       centered: true,
                       destroyOnClose: true
                   });
               },
               templateString: template 
           });
});
