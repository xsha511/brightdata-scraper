// extension/background/xuanpin-debugger.js
// 使用 Chrome Debugger API 访问 closed shadow DOM 获取选品助手数据

const DEBUGGER_VERSION = '1.3';

// 通过 debugger 提取选品助手数据
async function extractXuanpinViaDebugger(tabId) {
  try {
    // 附加 debugger
    await chrome.debugger.attach({ tabId }, DEBUGGER_VERSION);
    console.log('[Debugger] Attached to tab', tabId);

    // 执行 JavaScript 获取 shadow DOM 内容
    const result = await chrome.debugger.sendCommand(
      { tabId },
      'Runtime.evaluate',
      {
        expression: `
          (function() {
            // 查找选品助手的 shadow host
            const host = document.querySelector('div[class*="RvHB"], div._RvHB04Cj');
            if (!host) return { error: 'Shadow host not found' };

            // 获取 shadow root (debugger 可以访问 closed shadow root)
            const shadowRoot = host.shadowRoot;
            if (!shadowRoot) return { error: 'Shadow root not accessible' };

            // 提取数据
            const data = {};
            const items = shadowRoot.querySelectorAll('.item');

            items.forEach(item => {
              const label = item.querySelector('.label')?.textContent?.trim() || '';
              const valueEl = item.querySelector('.value');
              const value = valueEl?.textContent?.trim() || '';

              if (label.includes('品类')) {
                data.category = value;
              } else if (label.includes('销量') && !label.includes('店铺')) {
                const soldValues = item.querySelectorAll('.sold-value');
                soldValues.forEach(sv => {
                  const title = sv.getAttribute('title') || '';
                  const text = sv.textContent || '';
                  const m = title.match(/(\\d+)/);
                  if (m) {
                    if (title.includes('昨日') || text.startsWith('日')) data.sales_daily = parseInt(m[1]);
                    else if (title.includes('7天') || text.startsWith('周')) data.sales_weekly = parseInt(m[1]);
                    else if (title.includes('30天') || text.startsWith('月')) data.sales_monthly = parseInt(m[1]);
                    else if (title.includes('总') || text.startsWith('总')) data.sales_total = parseInt(m[1]);
                  }
                });
              } else if (label.includes('销售额')) {
                const soldValues = item.querySelectorAll('.sold-value');
                soldValues.forEach(sv => {
                  const title = sv.getAttribute('title') || '';
                  const m = title.match(/[£¥]([\\d.]+)/);
                  if (m) {
                    const val = parseFloat(m[1]);
                    if (title.includes('昨日')) data.revenue_daily = val;
                    else if (title.includes('7天')) data.revenue_weekly = val;
                    else if (title.includes('30天')) data.revenue_monthly = val;
                    else if (title.includes('总')) data.revenue_total = val;
                  }
                });
              } else if (label.includes('商品评分')) {
                const m = value.match(/([\\d.]+)\\s*\\/\\s*([\\d,]+)/);
                if (m) {
                  data.xp_rating = parseFloat(m[1]);
                  data.xp_review_count = parseInt(m[2].replace(/,/g, ''));
                }
              } else if (label.includes('库存')) {
                data.stock = parseInt(value.replace(/,/g, ''));
              } else if (label.includes('供货价')) {
                const m = value.match(/[¥￥]([\\d.]+)[-~]([\\d.]+)/);
                if (m) {
                  data.cost_min = parseFloat(m[1]);
                  data.cost_max = parseFloat(m[2]);
                }
              } else if (label.includes('上架时间')) {
                data.listing_time = value;
              } else if (label.includes('店铺名称')) {
                const spans = valueEl?.querySelectorAll('span');
                data.shop_name = spans?.[spans.length - 1]?.textContent?.trim() || value;
              } else if (label.includes('店铺类型')) {
                data.shop_type = value;
              } else if (label.includes('店铺总销量')) {
                data.shop_total_sales = parseInt(value.replace(/[,件]/g, ''));
              } else if (label.includes('店铺商品数')) {
                data.shop_product_count = parseInt(value.replace(/,/g, ''));
              } else if (label.includes('店铺评分')) {
                const m = value.match(/([\\d.]+)\\s*\\/\\s*([\\d,]+)/);
                if (m) {
                  data.shop_rating = parseFloat(m[1]);
                  data.shop_review_count = parseInt(m[2].replace(/,/g, ''));
                }
              } else if (label.includes('店铺粉丝')) {
                data.shop_fans = parseInt(value.replace(/,/g, ''));
              } else if (label.includes('开店时间')) {
                data.shop_age = value;
              }
            });

            // 获取商品ID
            const goodsIdEl = shadowRoot.querySelector('.goods-id');
            if (goodsIdEl) {
              const m = goodsIdEl.textContent.match(/商品ID[：:]\\s*(\\d+)/);
              if (m) data.xuanpin_goods_id = m[1];
            }

            return { success: true, data };
          })()
        `,
        returnByValue: true
      }
    );

    // 分离 debugger
    await chrome.debugger.detach({ tabId });
    console.log('[Debugger] Detached from tab', tabId);

    if (result.result?.value) {
      return result.result.value;
    }
    return { error: 'No result from evaluation' };

  } catch (error) {
    console.error('[Debugger] Error:', error);
    // 尝试分离 debugger
    try {
      await chrome.debugger.detach({ tabId });
    } catch (e) {}
    return { error: error.message };
  }
}

// 导出函数
if (typeof globalThis !== 'undefined') {
  globalThis.extractXuanpinViaDebugger = extractXuanpinViaDebugger;
}
