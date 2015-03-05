define("stomp/widgets/hosts/host-row", [
    "dojo/_base/declare",
    "dojo/text!./host-row.html",
    "dijit/_WidgetBase",
    "dojox/dtl/_Templated",
    "dojox/dtl",
    "dojox/dtl/Context",
    "dojo/_base/lang",
    "dojo/dom-construct",
    "dojo/dom-style",
    "dojo/request/xhr",
    "dojo/topic",
    "dojo/_base/array",
    "stomp/widgets/msgbox",
    "stomp/widgets/util",
    "stomp/widgets/hosts/host-opr",
    "stomp/widgets/hosts/host-content"
], function (
       declare,
       template,
       WidgetBase,
       TemplatedMixin,
       dtl,
       Context,
       lang,
       dc,
       domStyle,
       xhr,
       topic,
       array,
       msgbox,
       util,
       oprHost,
       contentHost
       ) {
           return declare([WidgetBase, TemplatedMixin], {
               templateString : template,
               postCreate: function () {
                   var widget = this;
                   widget.host = this.host;
                   widget.placeAt(this.node, this.pos);
                   widget.template = new dtl.Template(widget.templateString);
               },
               hostChange : function(evt) {
                   var widget = this;
                   var host = widget.host;

                   new oprHost({'id': 'dialog',
                                'opr': 'modify',
                                'host': host
                              });
               },
               hostDelete : function(evt) {
                   var widget = this;
                   var host = widget.host;
                   new oprHost({'id': 'dialog',
                                'opr': 'delete',
                                'host': host
                              });
               },
               showHost : function(evt) {
                   var widget = this;
                   var host = widget.host;
                   host.ip_unique = host.ipaddress.split('.').join("");

                   var elem = dojo.byId(host.ipaddress + '_content');
                   $("#dashcontent").children().css("display", "none");
                   if (elem) {
                       domStyle.set(elem, "display", "block");
                   } else {
                       new contentHost({'node': 'dashcontent',
                                        'host': host,
                                        'pos': 'last'
                                       });
                   }
               }
           });
});
