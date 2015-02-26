var profile = {
        basePath: "./",
        layerOptimize: "shrinksafe.keepLines",
        releaseDir: "./release",
        hasReport: true,
        insertAbsMids: false,
        packages:[
                     {
                         name: "dojo",
                         location: "./dojo/dojo"
                     },
                     {
                         name: "dijit",
                         location: "./dojo/dijit"
                     },
                     {
                         name: "dojox",
                         location: "./dojo/dojox"
                     },
                     {
                         name: "stomp",
                         location: "./stomp"
                     }
            ],
            layers: {
                    "stomp/layers/widgets": {
                        include: [
                            "stomp/widgets/dashboard",
                            "stomp/widgets/graph-utils",
                            "stomp/widgets/msgbox",
                            "stomp/widgets/util"
                        ]
                    }
            }
};
