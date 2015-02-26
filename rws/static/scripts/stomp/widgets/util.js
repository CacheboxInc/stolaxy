define("stomp/widgets/util", function() {

       return {
           start_load: function (msg) {
               var loading_msg = "Please Wait...";

               if (msg != undefined && msg != null) {
                   loading_msg = msg;
               }
               $("#loading").overlay({
                   top: 300,
                   closeOnClick: false,
                   closeOnEsc: false,
                   mask: {
                       color: '#000',
                       loadSpeed: 0,
                       opacity: 0.4
                   },
                   load: true
               });
               $("#loading_msg").html(loading_msg);
               $("#loading").css('text-align', 'center');
               $("#loading").data('overlay').load();
               $("body").css('cursor', 'wait').load();
           },
           stop_load: function () {
               $("#loading").overlay().close();
               $("body").css('cursor', 'default').load();
           },
           getMegaBytes: function(data) {
               var val = data.split(" ")[0];
               var scale = data.split(" ")[1];
               if (scale == 'TB') {
                   return (parseFloat(val) * (1 << 20));
               } else if (scale == 'GB') {
                   return (parseFloat(val) * (1 << 10));
               } else if (scale == 'MB') {
                   return (parseFloat(val));
               } else if (scale == 'KB') {
                   return (parseFloat(val) % ( 1 << 10));
               }
               return (parseFloat(val) % (1 << 20));
           },
           getusize: function(data) {
               var size = parseInt(data);
               if (size >= 1 << 20) {
                   return parseFloat((size / (1 << 20))).toFixed(2) + " TB"; 
               } else if (size >= 1 << 10) {
                   return parseFloat((size / (1 << 10))).toFixed(2) + " GB"; 
               } else if (size >= 1) {
                   return (size) + " MB"; 
               } else if (size < (1 >> 10)) {
                   return (size * (1 << 10)) + " KB"; 
               }
               return size * (1 << 20) + ' B';
           }
       };
});
