// extension/content/early-injector.js
/**
 * 在 document_start 时运行，注入 hook 脚本到页面主世界
 */

(function() {
  'use strict';

  // 注入脚本到页面
  const script = document.createElement('script');
  script.src = chrome.runtime.getURL('content/early-inject.js');
  script.onload = function() {
    this.remove();
    console.log('[EarlyInjector] Hook script injected');
  };

  // 尽早注入
  (document.head || document.documentElement).appendChild(script);

  console.log('[EarlyInjector] Injecting hook script at', new Date().toISOString());
})();
