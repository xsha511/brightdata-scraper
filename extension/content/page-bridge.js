// extension/content/page-bridge.js
/**
 * 这个脚本会被注入到页面上下文中执行
 * 用于读取页面 JavaScript 变量（如 window.rawData）
 * 通过 CustomEvent 将数据传回 content script
 */

(function() {
  'use strict';

  // 收集页面数据
  function collectPageData() {
    const data = {
      rawData: null,
      __INITIAL_STATE__: null,
      __PRELOADED_STATE__: null,
      _rawData: null,
      __allShadowRoots: null,
      __capturedResponses: null,
    };

    // 尝试读取各种可能的数据源
    try {
      if (window.rawData) {
        data.rawData = window.rawData;
      }
    } catch (e) {}

    try {
      if (window.__INITIAL_STATE__) {
        data.__INITIAL_STATE__ = window.__INITIAL_STATE__;
      }
    } catch (e) {}

    try {
      if (window.__PRELOADED_STATE__) {
        data.__PRELOADED_STATE__ = window.__PRELOADED_STATE__;
      }
    } catch (e) {}

    try {
      if (window._rawData) {
        data._rawData = window._rawData;
      }
    } catch (e) {}

    // 收集早期 hook 捕获的网络请求
    try {
      const responses = window.__capturedResponses;
      console.log('[PageBridge] __capturedResponses exists:', !!responses, 'length:', responses?.length);
      if (responses && responses.length > 0) {
        // 只保留关键信息，避免数据过大
        data.__capturedResponses = responses.map(r => ({
          type: r.type,
          url: (r.url || '').substring(0, 200),
          status: r.status,
          timestamp: r.timestamp,
          dataType: r.dataType,
          // 只保留数据的摘要
          dataKeys: r.data ? Object.keys(r.data).slice(0, 20) : null,
          dataSample: r.textSample?.substring(0, 300)
        }));
        console.log('[PageBridge] Copied responses (simplified):', data.__capturedResponses.length);
      } else {
        data.__capturedResponses = [];
      }
    } catch (e) {
      console.error('[PageBridge] Error reading __capturedResponses:', e);
      data.__capturedResponsesError = e.message;
    }

    // 收集被 hook 的 shadow roots 数据
    try {
      if (window.__allShadowRoots && window.__allShadowRoots.length > 0) {
        data.__allShadowRoots = window.__allShadowRoots.map(item => {
          const sr = item.root;
          const host = item.host;
          return {
            hostClass: host?.className || '',
            hostTag: host?.tagName || '',
            originalMode: item.originalMode,
            innerHTML: sr?.innerHTML?.substring(0, 10000) || '',
            textContent: sr?.textContent?.substring(0, 5000) || ''
          };
        });
      }
    } catch (e) {
      data.__shadowRootsError = e.message;
    }

    return data;
  }

  // 发送数据到 content script
  function sendToContentScript(data) {
    window.dispatchEvent(new CustomEvent('TEMU_PAGE_DATA', {
      detail: JSON.stringify(data)
    }));
  }

  // 等待页面数据加载完成
  function waitAndCollect() {
    let attempts = 0;
    const maxAttempts = 20; // 最多等待 10 秒

    function check() {
      attempts++;
      const data = collectPageData();

      // 检查是否有任何数据
      const hasData = data.rawData || data.__INITIAL_STATE__ ||
                      data.__PRELOADED_STATE__ || data._rawData;

      // 也检查是否有捕获的网络请求
      const hasCaptured = data.__capturedResponses && data.__capturedResponses.length > 0;

      if ((hasData && hasCaptured) || attempts >= maxAttempts) {
        // 最后再收集一次，确保获取最新数据
        const finalData = collectPageData();
        sendToContentScript({
          success: !!hasData,
          attempts: attempts,
          data: finalData,
          url: window.location.href,
          timestamp: new Date().toISOString()
        });
      } else if (hasData && !hasCaptured && attempts < 10) {
        // 有页面数据但还没有捕获请求，再等等
        setTimeout(check, 500);
      } else {
        setTimeout(check, 500);
      }
    }

    check();
  }

  // 页面可能还在加载数据，等待一下
  if (document.readyState === 'complete') {
    setTimeout(waitAndCollect, 1000);
  } else {
    window.addEventListener('load', () => {
      setTimeout(waitAndCollect, 1000);
    });
  }
})();
