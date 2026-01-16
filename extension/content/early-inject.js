// extension/content/early-inject.js
/**
 * 在页面最早期注入，hook 网络请求和 shadow DOM
 * 运行在 MAIN world，可以直接访问页面 window
 */

(function() {
  'use strict';

  // 防止重复注入
  if (window.__temuHooksInstalled) return;
  window.__temuHooksInstalled = true;

  // 存储捕获的数据
  window.__capturedResponses = [];
  window.__allShadowRoots = [];

  console.log('[EarlyHook] Installing hooks at', new Date().toISOString());

  // ========== Hook fetch ==========
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    const startTime = Date.now();

    try {
      const response = await originalFetch.apply(this, args);

      // 捕获所有 API 请求（排除静态资源）
      const isResource = /\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2|ttf|ico)(\?|$)/i.test(url);
      const isApi = url.includes('/api/') || url.includes('api.') ||
                   !url.includes('temu.com') ||  // 非 temu 域名的请求
                   url.includes('xuanpin') || url.includes('goods');
      const isInteresting = !isResource && isApi;

      if (isInteresting) {
        const clone = response.clone();
        try {
          const text = await clone.text();
          let data = null;
          try { data = JSON.parse(text); } catch(e) {}

          window.__capturedResponses.push({
            type: 'fetch',
            url: url,
            status: response.status,
            timestamp: new Date().toISOString(),
            duration: Date.now() - startTime,
            dataType: data ? 'json' : 'text',
            data: data,
            textLength: text.length,
            textSample: text.substring(0, 500)
          });
          console.log('[EarlyHook] Captured fetch:', url.substring(0, 80));
        } catch (e) {}
      }

      return response;
    } catch (error) {
      throw error;
    }
  };

  // ========== Hook XMLHttpRequest ==========
  const originalXHROpen = XMLHttpRequest.prototype.open;
  const originalXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this.__hookUrl = url;
    this.__hookMethod = method;
    this.__hookStartTime = Date.now();
    return originalXHROpen.apply(this, [method, url, ...rest]);
  };

  XMLHttpRequest.prototype.send = function(...args) {
    const xhr = this;
    const url = xhr.__hookUrl || '';

    // 捕获所有 API 请求（排除静态资源）
    const isResource = /\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2|ttf|ico)(\?|$)/i.test(url);
    const isApi = url.includes('/api/') || url.includes('api.') ||
                 !url.includes('temu.com') ||  // 非 temu 域名的请求
                 url.includes('xuanpin') || url.includes('goods');
    const isInteresting = !isResource && isApi;

    if (isInteresting) {
      xhr.addEventListener('load', function() {
        try {
          let data = null;
          try { data = JSON.parse(xhr.responseText); } catch(e) {}

          window.__capturedResponses.push({
            type: 'xhr',
            url: url,
            status: xhr.status,
            timestamp: new Date().toISOString(),
            duration: Date.now() - (xhr.__hookStartTime || 0),
            dataType: data ? 'json' : 'text',
            data: data,
            textLength: xhr.responseText?.length,
            textSample: xhr.responseText?.substring(0, 500)
          });
          console.log('[EarlyHook] Captured XHR:', url.substring(0, 80));
        } catch (e) {}
      });
    }

    return originalXHRSend.apply(this, args);
  };

  // ========== Hook attachShadow ==========
  const originalAttachShadow = Element.prototype.attachShadow;

  Element.prototype.attachShadow = function(options) {
    const shadowRoot = originalAttachShadow.call(this, options);

    // 保存引用（即使是 closed 模式也能保存）
    window.__allShadowRoots.push({
      host: this,
      root: shadowRoot,
      originalMode: options.mode,
      hostTag: this.tagName,
      hostClass: this.className,
      createdAt: new Date().toISOString()
    });

    console.log('[EarlyHook] Shadow DOM created:', this.tagName, (this.className || '').substring(0, 50), options.mode);

    return shadowRoot;
  };

  console.log('[EarlyHook] All hooks installed successfully');
})();
