'use strict';
// jsnes 2.1.0 declares type:module but its require export is a UMD bundle.
// Load that exact browser bundle with explicit CommonJS bindings on Node 24.
const fs = require('fs'), vm = require('vm');
const corePath = require.resolve('jsnes');
const output = { exports: {} };
const factory = vm.runInThisContext('(function(module,exports){\n' + fs.readFileSync(corePath, 'utf8') + '\n})', { filename: corePath });
factory(output, output.exports);
module.exports = { ...output.exports, corePath };
