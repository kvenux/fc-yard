'use strict';
const fs=require('node:fs');
// Bundled Playwright Chromium works on every supported desktop OS.
const chrome=process.env.CHROME_PATH;
module.exports={headless:true,...(chrome&&fs.existsSync(chrome)?{executablePath:chrome}:{})};
