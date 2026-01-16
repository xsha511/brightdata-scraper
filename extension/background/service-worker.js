// extension/background/service-worker.js
/**
 * Background service worker for:
 * - Selector caching and management
 * - Batch uploads
 * - HTML analysis requests
 * - Extraction failure alerts
 */

import { DataQueue } from '../utils/storage.js';

const queue = new DataQueue();
const BATCH_INTERVAL_MINUTES = 1;
const CONFIG_REFRESH_INTERVAL = 60; // 分钟
const SELECTOR_CACHE_KEY = 'selectorCache';
const SELECTOR_CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

// ============================================================
// 引导配置 URL - 这是唯一需要永久稳定的地址
// 部署时替换为你的静态托管地址，例如：
// - GitHub: https://raw.githubusercontent.com/your-repo/main/config/extension-config.json
// - CDN: https://your-cdn.com/temu/config.json
// ============================================================
const CONFIG_URL = 'http://localhost:8001/static/extension-config.json';

// 本地开发用的默认服务器地址
const DEFAULT_SERVER_URL = 'http://localhost:8001';

// In-memory selector cache
let selectorCache = {};

// 从静态配置 URL 获取配置（引导服务）
async function fetchConfigFromBootstrap() {
  try {
    const response = await fetch(CONFIG_URL, { cache: 'no-store' });
    if (response.ok) {
      const config = await response.json();
      if (config.server_url) {
        await chrome.storage.local.set({
          serverUrl: config.server_url,
          configVersion: config.version,
          configLastUpdated: Date.now()
        });
        console.log('[SW] Config updated from bootstrap:', config.server_url);
        return config;
      }
    }
  } catch (error) {
    console.error('[SW] Failed to fetch config from bootstrap:', error);
  }
  return null;
}

async function getServerUrl() {
  const result = await chrome.storage.local.get('serverUrl');
  return result.serverUrl || DEFAULT_SERVER_URL;
}

// Load cached selectors from storage
async function loadSelectorCache() {
  const result = await chrome.storage.local.get(SELECTOR_CACHE_KEY);
  if (result[SELECTOR_CACHE_KEY]) {
    selectorCache = result[SELECTOR_CACHE_KEY];
    console.log('[SW] Loaded selector cache:', Object.keys(selectorCache));
  }
}

// Save selector cache to storage
async function saveSelectorCache() {
  await chrome.storage.local.set({ [SELECTOR_CACHE_KEY]: selectorCache });
}

// Get selectors for a page type (from cache or server)
async function getSelectors(pageType) {
  const cacheKey = `selectors_${pageType}`;
  const cached = selectorCache[cacheKey];

  // Check if cache is valid
  if (cached && Date.now() - cached.timestamp < SELECTOR_CACHE_TTL) {
    console.log('[SW] Using cached selectors for:', pageType);
    return cached.data;
  }

  // Fetch from server
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/api/selectors/${pageType}`);
    if (response.ok) {
      const data = await response.json();
      selectorCache[cacheKey] = {
        data: data,
        timestamp: Date.now(),
      };
      await saveSelectorCache();
      console.log('[SW] Fetched new selectors for:', pageType);
      return data;
    }
  } catch (error) {
    console.error('[SW] Failed to fetch selectors:', error);
  }

  // Return cached even if expired, as fallback
  return cached?.data || null;
}

// Send HTML to server for LLM analysis
async function analyzeHtml(url, html, pageType) {
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/api/analyze/html`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, html, page_type: pageType }),
    });

    if (response.ok) {
      const result = await response.json();
      // Update selector cache with new selectors
      if (result.selectors) {
        const cacheKey = `selectors_${pageType}`;
        selectorCache[cacheKey] = {
          data: result.selectors,
          timestamp: Date.now(),
        };
        await saveSelectorCache();
        console.log('[SW] Updated selectors from HTML analysis');
      }
      return result;
    }
  } catch (error) {
    console.error('[SW] HTML analysis failed:', error);
  }
  return null;
}

// Report extraction failure for alerting
async function reportExtractionFailure(url, failedFields, htmlSample) {
  const serverUrl = await getServerUrl();
  try {
    await fetch(`${serverUrl}/api/alert/extraction-failed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        failed_fields: failedFields,
        html_sample: htmlSample,
        timestamp: new Date().toISOString(),
      }),
    });
    console.log('[SW] Extraction failure reported');
  } catch (error) {
    console.error('[SW] Failed to report extraction failure:', error);
  }
}

// Set up periodic batch upload and config refresh
chrome.alarms.create('batchUpload', { periodInMinutes: BATCH_INTERVAL_MINUTES });
chrome.alarms.create('configRefresh', { periodInMinutes: CONFIG_REFRESH_INTERVAL });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'batchUpload') {
    await processBatchUpload();
  } else if (alarm.name === 'configRefresh') {
    await fetchConfigFromBootstrap();
  }
});

async function processBatchUpload() {
  const items = await queue.dequeueAll(50);
  if (items.length === 0) return;

  const serverUrl = await getServerUrl();

  try {
    const response = await fetch(`${serverUrl}/api/collect/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ products: items }),
    });

    if (!response.ok) {
      // Re-queue on failure
      for (const item of items) {
        await queue.enqueue(item);
      }
      console.error('[SW] Batch upload failed, items re-queued');
    } else {
      console.log(`[SW] Batch uploaded ${items.length} items`);
    }
  } catch (error) {
    // Re-queue on network error
    for (const item of items) {
      await queue.enqueue(item);
    }
    console.error('[SW] Batch upload error:', error);
  }
}

// 使用 Chrome Debugger API 提取选品助手数据
const DEBUGGER_VERSION = '1.3';

// 解析选品助手 HTML
function parseXuanpinHTML(html) {
  const data = {};

  // 商品ID
  const goodsIdMatch = html.match(/商品ID[：:]\s*(\d+)/);
  if (goodsIdMatch) data.xuanpin_goods_id = goodsIdMatch[1];

  // 品类
  const categoryMatch = html.match(/品类[：:]?\s*<\/span>\s*<span[^>]*class="value"[^>]*>([^<]+)/);
  if (categoryMatch) data.category = categoryMatch[1].trim();

  // 销量 - 从 title 属性提取
  const salesMatches = html.matchAll(/title="(昨日|过去7天|过去30天|总)销量[：:]?\s*(\d+)/g);
  for (const m of salesMatches) {
    const period = m[1];
    const value = parseInt(m[2]);
    if (period === '昨日') data.sales_daily = value;
    else if (period === '过去7天') data.sales_weekly = value;
    else if (period === '过去30天') data.sales_monthly = value;
    else if (period === '总') data.sales_total = value;
  }

  // 销售额 - 从 title 属性提取
  const revenueMatches = html.matchAll(/title="(昨日|过去7天|过去30天|总)销售额[：:]?\s*[£¥￥]?([\d,.]+)/g);
  for (const m of revenueMatches) {
    const period = m[1];
    const value = parseFloat(m[2].replace(/,/g, ''));
    if (period === '昨日') data.revenue_daily = value;
    else if (period === '过去7天') data.revenue_weekly = value;
    else if (period === '过去30天') data.revenue_monthly = value;
    else if (period === '总') data.revenue_total = value;
  }

  // 商品评分
  const ratingMatch = html.match(/商品评分[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([\d.]+)\s*\/\s*([\d,]+)/);
  if (ratingMatch) {
    data.xp_rating = parseFloat(ratingMatch[1]);
    data.xp_review_count = parseInt(ratingMatch[2].replace(/,/g, ''));
  }

  // 库存
  const stockMatch = html.match(/库存[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([\d,]+)/);
  if (stockMatch) data.stock = parseInt(stockMatch[1].replace(/,/g, ''));

  // 供货价
  const costMatch = html.match(/供货价[^<]*<\/span>\s*<span[^>]*>[^¥￥]*[¥￥]([\d.]+)[~-]([\d.]+)/);
  if (costMatch) {
    data.cost_min = parseFloat(costMatch[1]);
    data.cost_max = parseFloat(costMatch[2]);
  }

  // 上架时间 - 从 title 属性提取精确日期
  const listingTitleMatch = html.match(/上架时间[^<]*<\/span>\s*<span[^>]*title="([^"]+)"/);
  if (listingTitleMatch) {
    data.listing_time = listingTitleMatch[1].trim();  // 如 "2025/2/20 04:20:26"
  } else {
    // 备用：提取显示文本
    const listingMatch = html.match(/上架时间[^<]*<\/span>\s*<span[^>]*>[^<]*<span[^>]*>([^<]+)/);
    if (listingMatch) data.listing_time = listingMatch[1].trim();
  }

  // 店铺名称
  const shopMatch = html.match(/店铺名称[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>.*?<span[^>]*>([^<]+)<\/span>\s*<\/span>/s);
  if (shopMatch) data.shop_name = shopMatch[1].trim();

  // 店铺类型
  const shopTypeMatch = html.match(/店铺类型[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([^<]+)/);
  if (shopTypeMatch) data.shop_type = shopTypeMatch[1].trim();

  // 店铺总销量
  const shopSalesMatch = html.match(/店铺总销量[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([\d,]+)/);
  if (shopSalesMatch) data.shop_total_sales = parseInt(shopSalesMatch[1].replace(/[,件]/g, ''));

  // 店铺商品数
  const shopCountMatch = html.match(/店铺商品数[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([\d,]+)/);
  if (shopCountMatch) data.shop_product_count = parseInt(shopCountMatch[1].replace(/,/g, ''));

  // 店铺评分
  const shopRatingMatch = html.match(/店铺评分[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([\d.]+)\s*\/\s*([\d,]+)/);
  if (shopRatingMatch) {
    data.shop_rating = parseFloat(shopRatingMatch[1]);
    data.shop_review_count = parseInt(shopRatingMatch[2].replace(/,/g, ''));
  }

  // 店铺粉丝
  const fansMatch = html.match(/店铺粉丝[^<]*<\/span>\s*<span[^>]*class="value"[^>]*>([\d,]+)/);
  if (fansMatch) data.shop_fans = parseInt(fansMatch[1].replace(/,/g, ''));

  // 开店时间 - 从 title 属性提取精确日期
  const shopAgeTitleMatch = html.match(/开店时间[^<]*<\/span>\s*<span[^>]*title="([^"]+)"/);
  if (shopAgeTitleMatch) {
    data.shop_age = shopAgeTitleMatch[1].trim();
  } else {
    // 备用：提取显示文本
    const shopAgeMatch = html.match(/开店时间[^<]*<\/span>\s*<span[^>]*>[^<]*<span[^>]*>([^<]+)/);
    if (shopAgeMatch) data.shop_age = shopAgeMatch[1].trim();
  }

  // 计算均价 = 销售额 / 销量
  if (data.sales_daily && data.revenue_daily) {
    data.avg_price_daily = Math.round(data.revenue_daily / data.sales_daily * 100) / 100;
  }
  if (data.sales_weekly && data.revenue_weekly) {
    data.avg_price_weekly = Math.round(data.revenue_weekly / data.sales_weekly * 100) / 100;
  }
  if (data.sales_monthly && data.revenue_monthly) {
    data.avg_price_monthly = Math.round(data.revenue_monthly / data.sales_monthly * 100) / 100;
  }
  if (data.sales_total && data.revenue_total) {
    data.avg_price_total = Math.round(data.revenue_total / data.sales_total * 100) / 100;
  }

  return data;
}

// 发送调试日志到服务器
async function sendDebugLogFromSW(data) {
  const serverUrl = await getServerUrl();
  try {
    await fetch(`${serverUrl}/api/debug/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        timestamp: new Date().toISOString(),
        source: 'service-worker'
      }),
    });
  } catch (e) {
    console.error('[SW] Failed to send debug log:', e);
  }
}

// 手动遍历 DOM 树查找 .goods-detail（备用方案，用于不支持 performSearch 穿透的浏览器）
function findGoodsDetailInTree(node) {
  if (!node) return null;

  // 检查当前节点是否是 .goods-detail
  if (node.attributes) {
    for (let i = 0; i < node.attributes.length; i += 2) {
      if (node.attributes[i] === 'class' && node.attributes[i + 1]?.includes('goods-detail')) {
        return node.nodeId;
      }
    }
  }

  // 递归搜索 shadow roots
  if (node.shadowRoots) {
    for (const sr of node.shadowRoots) {
      const found = findGoodsDetailInTree(sr);
      if (found) return found;
    }
  }

  // 递归搜索子节点
  if (node.children) {
    for (const child of node.children) {
      const found = findGoodsDetailInTree(child);
      if (found) return found;
    }
  }

  return null;
}

async function extractXuanpinViaDebugger(tabId, maxRetries = 3) {
  console.log('[Debugger] Starting extraction for tab', tabId);

  // 获取浏览器信息用于区分
  const browserInfo = await chrome.runtime.getBrowserInfo?.() || { name: 'unknown' };
  const userAgent = navigator.userAgent;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    console.log(`[Debugger] Attempt ${attempt}/${maxRetries}`);

    try {
      // 附加 debugger
      await chrome.debugger.attach({ tabId }, DEBUGGER_VERSION);
      console.log('[Debugger] Attached to tab', tabId);

      // 等待让选品助手有时间加载
      await new Promise(r => setTimeout(r, 1500));

      // 启用 DOM 域
      await chrome.debugger.sendCommand({ tabId }, 'DOM.enable');

      // 获取文档根节点（穿透 shadow DOM）
      const docResult = await chrome.debugger.sendCommand({ tabId }, 'DOM.getDocument', {
        depth: -1,
        pierce: true
      });

      // 统计 shadow roots 数量
      let shadowRootCount = 0;
      function countShadowRoots(node) {
        if (!node) return;
        if (node.shadowRoots && node.shadowRoots.length > 0) {
          shadowRootCount += node.shadowRoots.length;
          node.shadowRoots.forEach(sr => countShadowRoots(sr));
        }
        if (node.children) {
          node.children.forEach(child => countShadowRoots(child));
        }
      }
      countShadowRoots(docResult.root);

      // 使用 DOM.performSearch 搜索 .goods-detail
      const searchResult = await chrome.debugger.sendCommand({ tabId }, 'DOM.performSearch', {
        query: '.goods-detail',
        includeUserAgentShadowDOM: true
      });

      // 发送详细的调试日志
      sendDebugLogFromSW({
        type: 'debugger_search_detail',
        tabId: tabId,
        attempt: attempt,
        userAgent: userAgent,
        browserInfo: browserInfo,
        documentNodeId: docResult.root?.nodeId,
        documentChildCount: docResult.root?.childNodeCount,
        shadowRootCount: shadowRootCount,
        searchQuery: '.goods-detail',
        searchResultCount: searchResult.resultCount,
        searchId: searchResult.searchId
      });

      console.log(`[Debugger] Search result: ${searchResult.resultCount} elements found, shadowRoots in DOM: ${shadowRootCount}`);

      let nodeId = null;
      let searchMethod = 'performSearch';

      if (searchResult.resultCount && searchResult.resultCount > 0) {
        // performSearch 找到了，获取节点ID
        const nodesResult = await chrome.debugger.sendCommand({ tabId }, 'DOM.getSearchResults', {
          searchId: searchResult.searchId,
          fromIndex: 0,
          toIndex: searchResult.resultCount
        });
        nodeId = nodesResult.nodeIds[0];

        // 清理搜索
        await chrome.debugger.sendCommand({ tabId }, 'DOM.discardSearchResults', {
          searchId: searchResult.searchId
        });
      } else {
        // performSearch 没找到，尝试手动遍历 DOM 树（兼容旧版浏览器）
        console.log('[Debugger] performSearch failed, trying manual tree traversal...');
        searchMethod = 'treeTraversal';
        nodeId = findGoodsDetailInTree(docResult.root);

        sendDebugLogFromSW({
          type: 'debugger_fallback_traversal',
          tabId: tabId,
          attempt: attempt,
          userAgent: userAgent,
          foundNodeId: nodeId,
          shadowRootCount: shadowRootCount
        });

        console.log(`[Debugger] Tree traversal result: nodeId=${nodeId}`);
      }

      if (!nodeId) {
        await chrome.debugger.detach({ tabId });

        if (attempt < maxRetries) {
          console.log(`[Debugger] No elements found, waiting 2s before retry...`);
          await new Promise(r => setTimeout(r, 2000));
          continue;
        }

        return { error: 'No .goods-detail found in DOM (including shadow)', resultCount: 0, attempts: attempt, searchMethod };
      }

      // 获取节点的外层HTML
      const outerHTMLResult = await chrome.debugger.sendCommand({ tabId }, 'DOM.getOuterHTML', {
        nodeId: nodeId
      });

      const html = outerHTMLResult.outerHTML;

      // 解析数据
      const data = parseXuanpinHTML(html);

      // 尝试获取 ECharts 图表数据
      let chartData = null;
      let networkData = [];
      try {
        // 启用 Runtime 和 Network 域
        await chrome.debugger.sendCommand({ tabId }, 'Runtime.enable');
        await chrome.debugger.sendCommand({ tabId }, 'Network.enable');

        // 获取已缓存的网络请求（选品助手可能已经请求过数据）
        // 尝试从 Performance 获取资源
        try {
          const perfResult = await chrome.debugger.sendCommand({ tabId }, 'Runtime.evaluate', {
            expression: `
              JSON.stringify(
                performance.getEntriesByType('resource')
                  .filter(r => r.name.includes('api') || r.name.includes('xuanpin') || r.name.includes('temu'))
                  .map(r => ({ name: r.name, type: r.initiatorType }))
                  .slice(-20)
              )
            `,
            returnByValue: true
          });
          if (perfResult.result?.value) {
            networkData = JSON.parse(perfResult.result.value);
          }
        } catch (e) {
          console.log('[Debugger] Performance API failed:', e);
        }

        // 尝试获取 localStorage 和 sessionStorage 中的选品助手数据
        try {
          const storageResult = await chrome.debugger.sendCommand({ tabId }, 'Runtime.evaluate', {
            expression: `
              (function() {
                const result = { localStorage: {}, sessionStorage: {} };
                // 查找与选品助手或商品相关的存储
                for (let i = 0; i < localStorage.length; i++) {
                  const key = localStorage.key(i);
                  if (key && (key.includes('xuanpin') || key.includes('goods') || key.includes('chart') || key.includes('sales') || key.includes('history'))) {
                    try {
                      result.localStorage[key] = localStorage.getItem(key)?.substring(0, 1000);
                    } catch(e) {}
                  }
                }
                for (let i = 0; i < sessionStorage.length; i++) {
                  const key = sessionStorage.key(i);
                  if (key && (key.includes('xuanpin') || key.includes('goods') || key.includes('chart') || key.includes('sales') || key.includes('history'))) {
                    try {
                      result.sessionStorage[key] = sessionStorage.getItem(key)?.substring(0, 1000);
                    } catch(e) {}
                  }
                }
                return JSON.stringify(result);
              })()
            `,
            returnByValue: true
          });
          if (storageResult.result?.value) {
            const storageData = JSON.parse(storageResult.result.value);
            if (Object.keys(storageData.localStorage).length > 0 || Object.keys(storageData.sessionStorage).length > 0) {
              networkData.push({ type: 'storage', data: storageData });
            }
          }
        } catch (e) {
          console.log('[Debugger] Storage check failed:', e);
        }

        // 检查 IndexedDB 数据库列表并读取内容
        try {
          const idbResult = await chrome.debugger.sendCommand({ tabId }, 'Runtime.evaluate', {
            expression: `
              (async function() {
                try {
                  const result = { databases: [], data: {} };
                  const dbs = await indexedDB.databases();
                  result.databases = dbs.map(db => ({ name: db.name, version: db.version }));

                  // 读取 scdb 数据库内容（可能是选品助手的数据）
                  for (const dbInfo of dbs) {
                    if (dbInfo.name === 'scdb' || dbInfo.name === 'page-info') {
                      try {
                        const db = await new Promise((resolve, reject) => {
                          const req = indexedDB.open(dbInfo.name);
                          req.onsuccess = () => resolve(req.result);
                          req.onerror = () => reject(req.error);
                        });

                        const stores = Array.from(db.objectStoreNames);
                        result.data[dbInfo.name] = { stores: stores };

                        // 读取每个 store 的数据
                        for (const storeName of stores) {
                          try {
                            const tx = db.transaction(storeName, 'readonly');
                            const store = tx.objectStore(storeName);
                            const data = await new Promise((resolve, reject) => {
                              const req = store.getAll();
                              req.onsuccess = () => resolve(req.result);
                              req.onerror = () => reject(req.error);
                            });
                            result.data[dbInfo.name][storeName] = data.slice(0, 5);
                          } catch(e) {}
                        }
                        db.close();
                      } catch(e) {
                        result.data[dbInfo.name] = { error: e.message };
                      }
                    }
                  }
                  return JSON.stringify(result);
                } catch(e) {
                  return JSON.stringify({ error: e.message });
                }
              })()
            `,
            awaitPromise: true,
            returnByValue: true
          });
          if (idbResult.result?.value) {
            const idbData = JSON.parse(idbResult.result.value);
            networkData.push({ type: 'indexedDB', ...idbData });
          }
        } catch (e) {
          console.log('[Debugger] IndexedDB check failed:', e);
        }

        // 检查完整的 localStorage goods 数据
        try {
          const goodsResult = await chrome.debugger.sendCommand({ tabId }, 'Runtime.evaluate', {
            expression: `
              (function() {
                const allKeys = [];
                for (let i = 0; i < localStorage.length; i++) {
                  allKeys.push(localStorage.key(i));
                }
                return JSON.stringify({
                  allKeys: allKeys,
                  goods: localStorage.getItem('goods')
                });
              })()
            `,
            returnByValue: true
          });
          if (goodsResult.result?.value) {
            networkData.push({ type: 'localStorage_full', ...JSON.parse(goodsResult.result.value) });
          }
        } catch (e) {}

        // 方法1：实时监控网络请求找选品助手 API，并获取响应内容
        let capturedRequests = [];
        let capturedResponses = [];
        try {
          // 设置网络请求监听
          const requestMap = new Map();  // requestId -> url
          const requestHandler = (source, method, params) => {
            if (method === 'Network.requestWillBeSent') {
              const url = params.request?.url || '';
              requestMap.set(params.requestId, url);
            }
            if (method === 'Network.responseReceived') {
              const url = params.response?.url || '';
              // 查找可能包含销量/趋势数据的 API
              if (url.includes('trend') || url.includes('chart') || url.includes('history') ||
                  url.includes('sales') || url.includes('daily') || url.includes('analyz')) {
                capturedRequests.push({
                  requestId: params.requestId,
                  url: url.substring(0, 300),
                  status: params.response?.status,
                  mimeType: params.response?.mimeType
                });
              }
            }
            if (method === 'Network.loadingFinished') {
              const url = requestMap.get(params.requestId) || '';
              if (url.includes('trend') || url.includes('chart') || url.includes('history') ||
                  url.includes('sales') || url.includes('daily') || url.includes('analyz')) {
                // 标记这个请求已完成，稍后获取响应体
                capturedRequests.forEach(r => {
                  if (r.requestId === params.requestId) {
                    r.finished = true;
                  }
                });
              }
            }
          };

          // 注册临时监听器
          chrome.debugger.onEvent.addListener(requestHandler);

          // 等待一段时间收集网络请求
          await new Promise(r => setTimeout(r, 1000));

          // 移除网络监听器
          chrome.debugger.onEvent.removeListener(requestHandler);
        } catch (e) {
          console.log('[Debugger] Network capture failed:', e);
          networkData.push({ type: 'network_capture_error', error: e.message });
        }

        // ========== 提取当前显示的图表数据（简化版，只提取一个） ==========
        let chartHistoryData = [];
        let chartDebugInfo = { method: 'single_chart_extraction', started: true };
        console.log('[Debugger] Starting single chart extraction...');

        try {
          // 查找图表
          const chartSearch = await chrome.debugger.sendCommand({ tabId }, 'DOM.performSearch', {
            query: '.chart',
            includeUserAgentShadowDOM: true
          });

          chartDebugInfo.chartSearchCount = chartSearch.resultCount;

          let chartNodeId = null;
          if (chartSearch.resultCount > 0) {
            const chartNodes = await chrome.debugger.sendCommand({ tabId }, 'DOM.getSearchResults', {
              searchId: chartSearch.searchId,
              fromIndex: 0,
              toIndex: 1
            });
            chartNodeId = chartNodes.nodeIds[0];
            await chrome.debugger.sendCommand({ tabId }, 'DOM.discardSearchResults', { searchId: chartSearch.searchId });
          }

          if (chartNodeId) {
            const boxModel = await chrome.debugger.sendCommand({ tabId }, 'DOM.getBoxModel', { nodeId: chartNodeId });

            if (boxModel.model) {
              const content = boxModel.model.content;
              const chartX = content[0], chartY = content[1];
              const chartWidth = content[2] - content[0], chartHeight = content[5] - content[1];

              chartDebugInfo.chartPos = { x: chartX, y: chartY, width: chartWidth, height: chartHeight };

              // 启用 Input 域
              await chrome.debugger.sendCommand({ tabId }, 'Input.enable').catch(() => {});

              // 沿图表 X 轴移动鼠标采样
              const startX = chartX + 60, endX = chartX + chartWidth - 10;
              const y = chartY + chartHeight / 2;
              const numSamples = 31;
              const step = (endX - startX) / (numSamples - 1);

              chartDebugInfo.sampling = { startX, endX, y, step, numSamples };

              const tooltipSelectors = ['div[style*="z-index: 9999999"]', 'div[style*="position: absolute"][style*="left:"]'];

              for (let i = 0; i < numSamples; i++) {
                const x = startX + i * step;

                await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchMouseEvent', {
                  type: 'mouseMoved', x: Math.round(x), y: Math.round(y), button: 'none', buttons: 0
                });

                await new Promise(r => setTimeout(r, 150));

                // 搜索 tooltip
                let tooltipText = null;
                for (const selector of tooltipSelectors) {
                  try {
                    const tooltipSearch = await chrome.debugger.sendCommand({ tabId }, 'DOM.performSearch', {
                      query: selector, includeUserAgentShadowDOM: true
                    });
                    if (tooltipSearch.resultCount > 0) {
                      const tooltipNodes = await chrome.debugger.sendCommand({ tabId }, 'DOM.getSearchResults', {
                        searchId: tooltipSearch.searchId, fromIndex: 0, toIndex: 3
                      });
                      for (const nodeId of tooltipNodes.nodeIds) {
                        try {
                          const htmlResult = await chrome.debugger.sendCommand({ tabId }, 'DOM.getOuterHTML', { nodeId });
                          const text = htmlResult.outerHTML.replace(/<[^>]*>/g, ' ').trim();
                          if (text && text.length > 3 && text.length < 200 && /\d/.test(text)) {
                            tooltipText = text;
                            break;
                          }
                        } catch (e) {}
                      }
                      await chrome.debugger.sendCommand({ tabId }, 'DOM.discardSearchResults', { searchId: tooltipSearch.searchId }).catch(() => {});
                    }
                  } catch (e) {}
                  if (tooltipText) break;
                }

                if (tooltipText && !chartHistoryData.some(d => d.text === tooltipText)) {
                  const dateMatch = tooltipText.match(/(\d{1,2}[-\/]\d{1,2})/);
                  let valueMatch = tooltipText.match(/销售额[：:]\s*([\d,.]+)/) || tooltipText.match(/销量[：:]\s*([\d,]+)/) || tooltipText.match(/[：:]\s*([\d,.]+)/);
                  if (!valueMatch) {
                    const allNumbers = tooltipText.match(/[\d,.]+/g);
                    if (allNumbers && allNumbers.length > 1) valueMatch = [null, allNumbers[allNumbers.length - 1]];
                  }
                  chartHistoryData.push({
                    text: tooltipText,
                    date: dateMatch ? dateMatch[1] : null,
                    value: valueMatch ? valueMatch[1].replace(/,/g, '') : null,
                    x: Math.round(x)
                  });
                  console.log('[Debugger] Captured tooltip:', tooltipText.substring(0, 50));
                }
              }

              // 移开鼠标
              await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchMouseEvent', { type: 'mouseMoved', x: 0, y: 0 });
            }
          }

          chartDebugInfo.dataPointsCollected = chartHistoryData.length;
          console.log('[Debugger] Chart extraction complete, points:', chartHistoryData.length);
        } catch (e) {
          console.log('[Debugger] Chart extraction failed:', e);
          chartDebugInfo.error = e.message;
        }

        // 添加图表调试信息
        networkData.push({ type: 'chart_tooltip_debug', ...chartDebugInfo });
        if (chartHistoryData.length > 0) {
          networkData.push({ type: 'chart_tooltip_data', data: chartHistoryData });
        }

        // 图表数据用于返回
        chartData = { chartHistoryData, totalPoints: chartHistoryData.length };

      } catch (e) {
        console.log('[Debugger] Chart/network data collection failed:', e);
      }

      // 分离 debugger
      await chrome.debugger.detach({ tabId });
      console.log('[Debugger] Detached from tab', tabId);

      // 将选品助手完整 HTML 保存到 networkData 供分析
      // 使用我们已经获取的 html 变量（来自 .goods-detail）
      networkData.push({
        type: 'full_panel_html',
        length: html?.length,
        hasDataAttr: html?.includes('data-'),
        hasJsonData: html?.includes('"sales"') || html?.includes('"trend"') || html?.includes('chartData'),
        // 检查是否有隐藏的 script 标签或数据
        hasScript: html?.includes('<script'),
        hasCanvas: html?.includes('<canvas'),
        // 提取所有 data-* 属性
        dataAttrs: (html?.match(/data-[a-z-]+="[^"]*"/g) || []).slice(0, 20),
        // 提取可能的数字数据（日期+数值模式）
        dateValuePatterns: (html?.match(/\d{1,2}-\d{1,2}[^<]{0,50}\d+/g) || []).slice(0, 10)
      });

      // 返回原始 HTML 和图表数据用于调试分析
      return { success: true, data, htmlLength: html.length, html: html, chartData: chartData, networkData: networkData, attempts: attempt, searchMethod };

    } catch (error) {
      console.error(`[Debugger] Error on attempt ${attempt}:`, error);

      try { await chrome.debugger.detach({ tabId }); } catch (e) {}

      if (attempt < maxRetries) {
        console.log(`[Debugger] Waiting 2s before retry...`);
        await new Promise(r => setTimeout(r, 2000));
        continue;
      }

      sendDebugLogFromSW({
        type: 'debugger_error',
        tabId: tabId,
        error: error.message,
        stack: error.stack,
        attempts: attempt
      });

      return { error: error.message, attempts: attempt };
    }
  }

  return { error: 'Max retries exceeded', attempts: maxRetries };
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'GET_SELECTORS':
      getSelectors(message.pageType).then((selectors) => {
        sendResponse({ selectors });
      });
      return true; // Async response

    case 'PRODUCT_COLLECTED':
      queue.enqueue(message.data).then(() => {
        sendResponse({ success: true });
      });
      return true;

    case 'ANALYZE_HTML':
      analyzeHtml(message.url, message.html, message.pageType).then((result) => {
        sendResponse({ success: !!result, result });
      });
      return true;

    case 'EXTRACTION_FAILED':
      reportExtractionFailure(message.url, message.failedFields, message.htmlSample).then(() => {
        sendResponse({ success: true });
      });
      return true;

    case 'CLEAR_SELECTOR_CACHE':
      selectorCache = {};
      saveSelectorCache().then(() => {
        sendResponse({ success: true });
      });
      return true;

    case 'EXTRACT_XUANPIN':
      // 使用 debugger API 提取选品助手数据
      extractXuanpinViaDebugger(sender.tab.id).then((result) => {
        sendResponse(result);
      });
      return true;

    case 'DEBUG_LOG':
      // 转发调试日志到服务器
      sendDebugLogFromSW(message.data).then(() => {
        sendResponse({ success: true });
      }).catch((e) => {
        sendResponse({ success: false, error: e.message });
      });
      return true;
  }
});

// Initialize on startup
loadSelectorCache();
fetchConfigFromBootstrap(); // 从引导服务获取配置
console.log('[SW] Service worker initialized');
