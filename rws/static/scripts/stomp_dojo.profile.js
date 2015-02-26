dependencies = {
	stripConsole: "normal",
	selectorEngine:"acme",
	layers: [
		{
			name: "dojo.js",
			dependencies: [
				"dojo/dom-construct",
				"dojo/topic",
				"dojo/text",
				"dojo/fx",
				"dojo/fx/Toggler",
				"dojo/ready",
				"dojo/request/script",
				"dojo/request/xhr",
				"dijit/_base/manager",
				"dijit/_WidgetBase",
				"dijit/registry",
				"dojox/dtl",
				"dojox/dtl",
				"dojox/dtl/_Templated",
				"dojox/dtl/Context",
				"dojox/dtl/tag/logic",
				"dojox/widget/Toaster",
				"dojo/dom-style"
			]
		}
	],

	prefixes: [
		[ "dijit", "../dijit" ],
		[ "dojox", "../dojox" ]
	]
}
