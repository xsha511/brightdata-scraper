// extension/content/network-hook.js
/**
 * 这个脚本在页面最早期注入，用于 hook 网络请求
 * 捕获选品助手等扩展的 API 调用
 */

(function() {
  'use strict';

  // 存储捕获的请求
  window.__capturedRequests = window.__capturedRequests || [];
  window.__capturedResponses = window.__capturedResponses || [];

  // Hook fetch
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    const startTime = Date.now();

    try {
      const response = await originalFetch.apply(this, args);

      // 检查是否是可能包含销量/趋势数据的请求
      const isInteresting = url.includes('trend') || url.includes('chart') ||
                           url.includes('sales') || url.includes('history') ||
                           url.includes('analyz') || url.includes('xuanpin') ||
                           url.includes('goods') || url.includes('product');

      if (isInteresting) {
        // 克隆响应以便读取
        const clone = response.clone();
        try {
          const data = await clone.json();
          window.__capturedResponses.push({
            type: 'fetch',
            url: url.substring(0, 500),
            status: response.status,
            timestamp: new Date().toISOString(),
            duration: Date.now() - startTime,
            data: data
          });
          console.log('[NetworkHook] Captured fetch:', url.substring(0, 100));
        } catch (e) {
          // 不是 JSON，跳过
        }
      }

      return response;
    } catch (error) {
      throw error;
    }
  };

  // Hook XMLHttpRequest
  const originalXHROpen = XMLHttpRequest.prototype.open;
  const originalXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._hookUrl = url;
    this._hookMethod = method;
    this._hookStartTime = Date.now();
    return originalXHROpen.apply(this, [method, url, ...rest]);
  };

  XMLHttpRequest.prototype.send = function(...args) {
    const xhr = this;
    const url = xhr._hookUrl || '';

    // 检查是否是感兴趣的请求
    const isInteresting = url.includes('trend') || url.includes('chart') ||
                         url.includes('sales') || url.includes('history') ||
                         url.includes('analyz') || url.includes('xuanpin') ||
                         url.includes('goods') || url.includes('product');

    if (isInteresting) {
      xhr.addEventListener('load', function() {
        try {
          const data = JSON.parse(xhr.responseText);
          window.__capturedResponses.push({
            type: 'xhr',
            url: url.substring(0, 500),
            status: xhr.status,
            timestamp: new Date().toISOString(),
            duration: Date.now() - (xhr._hookStartTime || 0),
            data: data
          });
          console.log('[NetworkHook] Captured XHR:', url.substring(0, 100));
        } catch (e) {
          // 不是 JSON，跳过
        }
      });
    }

    return originalXHRSend.apply(this, args);
  };

  // Hook attachShadow 来捕获 closed shadow DOM
  const originalAttachShadow = Element.prototype.attachShadow;
  window.__allShadowRoots = window.__allShadowRoots || [];

  Element.prototype.attachShadow = function(options) {
    const shadowRoot = originalAttachShadow.call(this, options);

    // 保存引用（即使是 closed 模式）
    window.__allShadowRoots.push({
      host: this,
      root: shadowRoot,
      originalMode: options.mode,
      createdAt: new Date().toISOString()
    });

    console.log('[NetworkHook] Shadow DOM created:', this.tagName, options.mode);

    return shadowRoot;
  };

  console.log('[NetworkHook] Hooks installed at', new Date().toISOString());
})();
