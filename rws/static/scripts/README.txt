COMPILING DOJO FOR CACHEADVANCE :

This document describes the steps required to build dojo for CacheAdvance. Dojo
built using the following method SHOULD be copied in the current directory before
building webapp package.

ca_dojo.profile.js :

This file contains all the dojo, dijit and dojox layers that are referenced by
by CacheAdvance webapp scripts and widgets along with scripts and widgets under
MySQL webapp and MongoDB webapp. Whenever a new layer is required to be added in
CacheAdvance scripts, the layer should be added under this file and dojo should 
be re-build.

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

BUILDING DOJO :

To build dojo the dojo scripts and dojo build utility is required.

1) Copy ca_dojo.profile.js under dojo/util/buildscripts/profiles/.

2) From dojo/util/ run the following command:
   ./build.sh profile=ca_dojo action=release

3) A release director will be created at dojo - dojo/release/


Copy release/dojo/dojo/dojo.js in webapp/scripts/.

NOTE : To build dojo Java is required.
