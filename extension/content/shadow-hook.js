// extension/content/shadow-hook.js
// 在页面脚本执行前注入，拦截 attachShadow 把 closed 改成 open

(function() {
  'use strict';

  // 保存原始的 attachShadow
  const originalAttachShadow = Element.prototype.attachShadow;

  // 存储所有被强制打开的 shadow roots
  window.__openedShadowRoots = window.__openedShadowRoots || new Map();

  // 重写 attachShadow
  Element.prototype.attachShadow = function(options) {
    // 强制使用 open 模式
    const newOptions = { ...options, mode: 'open' };

    console.log('[Shadow Hook] Intercepted attachShadow:', {
      original: options.mode,
      forced: 'open',
      element: this.tagName,
      class: this.className
    });

    const shadowRoot = originalAttachShadow.call(this, newOptions);

    // 保存引用
    window.__openedShadowRoots.set(this, shadowRoot);

    return shadowRoot;
  };

  console.log('[Shadow Hook] attachShadow interceptor installed');
})();
