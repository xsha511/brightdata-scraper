// extension/content/main.js
/**
 * Content script - 提取 Temu 商品数据
 */

(function() {
  'use strict';

  const LOG_PREFIX = '[Temu Collector]';

  // 检测页面类型
  function getPageType() {
    const url = window.location.href;
    if (url.includes('/goods.html') || url.match(/\/[\w-]+-g-\d+\.html/)) {
      return 'product';
    }
    return 'unknown';
  }

  // 多路径提取器 - 尝试多种可能的字段名
  function tryPaths(obj, paths) {
    for (const path of paths) {
      try {
        const parts = path.split('.');
        let value = obj;
        for (const part of parts) {
          if (value == null) break;
          value = value[part];
        }
        if (value != null && value !== '') return value;
      } catch (e) {}
    }
    return null;
  }

  // 从 gallery 提取图片 URL
  function extractGalleryUrls(gallery) {
    if (!Array.isArray(gallery)) return [];
    return gallery
      .map(g => g.url || g.hdUrl || g)
      .filter(u => u && typeof u === 'string' && u.startsWith('http'));
  }

  // 注入脚本到页面上下文获取 window.rawData
  function injectPageScript() {
    return new Promise((resolve) => {
      window.addEventListener('TEMU_PAGE_DATA', function handler(event) {
        window.removeEventListener('TEMU_PAGE_DATA', handler);
        try {
          resolve(JSON.parse(event.detail));
        } catch (e) {
          resolve({ success: false, error: e.message });
        }
      });

      const script = document.createElement('script');
      script.src = chrome.runtime.getURL('content/page-bridge.js');
      script.onload = () => script.remove();
      (document.head || document.documentElement).appendChild(script);

      setTimeout(() => resolve({ success: false, error: 'timeout' }), 15000);
    });
  }

  // 从页面数据提取商品信息
  function extractFromPageData(pageData) {
    const result = {
      url: window.location.href,
      extracted_at: new Date().toISOString(),
      page_type: 'product_detail',
    };
    const failedFields = [];

    const d = pageData.data || {};
    const rawData = d.rawData || d._rawData || d.__INITIAL_STATE__ || d.__PRELOADED_STATE__ || {};
    const store = rawData.store || rawData;
    const goods = store?.goods || rawData?.goods || {};
    const mall = store?.mall || goods?.mall || {};
    const review = store?.review || goods?.review || {};
    const localInfo = store?.localInfo || rawData?.localInfo || {};
    const sku = store?.sku || goods?.sku || {};

    // 商品ID
    result.product_id = String(tryPaths({ goods, store, sku }, [
      'goods.goodsId', 'goods.goods_id', 'goods.productId', 'goods.itemId', 'store.goodsId'
    ]) || '');

    if (!result.product_id) {
      const urlMatch = window.location.href.match(/g-(\d+)\.html/);
      result.product_id = urlMatch ? urlMatch[1] : '';
    }

    // 标题
    result.title = tryPaths({ goods, store }, [
      'goods.goodsName', 'goods.goods_name', 'goods.title', 'goods.productName', 'store.title'
    ]) || '';

    // 价格
    let price = tryPaths({ goods, sku, store }, [
      'goods.minOnSalePrice', 'goods.minPrice', 'goods.price', 'goods.salePrice', 'sku.price'
    ]);
    result.current_price = price ? (price > 100 ? price / 100 : price) : null;

    let origPrice = tryPaths({ goods, sku }, [
      'goods.marketPrice', 'goods.originalPrice', 'goods.maxPrice'
    ]);
    result.original_price = origPrice ? (origPrice > 100 ? origPrice / 100 : origPrice) : null;

    result.currency = tryPaths({ localInfo, store }, ['localInfo.currencySymbol', 'localInfo.currency']) || '£';

    // 销量
    result.sold_count = tryPaths({ goods, store }, [
      'goods.soldQuantity', 'goods.sales', 'goods.soldCount', 'goods.totalSales'
    ]);

    // 评分
    result.rating = tryPaths({ goods, review }, [
      'goods.goodsRating', 'goods.rating', 'review.goodsReviewScore', 'review.score'
    ]);

    result.review_count = tryPaths({ goods, review }, [
      'goods.reviewNum', 'goods.reviewCount', 'review.goodsReviewNum', 'review.count'
    ]);

    // 图片
    result.main_image = tryPaths({ goods }, [
      'goods.hdThumbUrl', 'goods.thumbUrl', 'goods.mainImage', 'goods.imageUrl'
    ]) || '';

    const gallery = tryPaths({ goods }, ['goods.gallery', 'goods.images', 'goods.imageList']);
    result.images = extractGalleryUrls(gallery);

    // 卖家
    result.seller_name = tryPaths({ mall, goods, store }, [
      'mall.mallName', 'mall.shopName', 'goods.mallName', 'store.mall.mallName'
    ]) || '';

    const mallId = tryPaths({ mall, goods }, ['mall.mallId', 'goods.mallId', 'mall.id']);
    result.seller_id = mallId ? String(mallId) : '';

    // 商品属性 (Material, Power Supply, etc.)
    const goodsProperty = goods.goodsProperty || [];
    result.attributes = {};
    for (const prop of goodsProperty) {
      if (prop.key && prop.values && prop.values.length > 0) {
        result.attributes[prop.key] = prop.values.join(', ');
      }
    }

    // 商品描述
    const productDetail = store.productDetail;
    result.description = '';
    if (productDetail && productDetail.floorList) {
      const texts = [];
      for (const floor of productDetail.floorList) {
        if (floor.items) {
          for (const item of floor.items) {
            if (item.text) texts.push(item.text);
          }
        }
      }
      result.description = texts.join(' ');
    }

    // 分类ID路径
    result.category_ids = [goods.catId, goods.catId1, goods.catId2, goods.catId3, goods.catId4].filter(Boolean);

    // 检查关键字段
    if (!result.product_id) failedFields.push('product_id');
    if (!result.title) failedFields.push('title');
    if (result.current_price === null) failedFields.push('current_price');

    return { data: result, failedFields, success: failedFields.length === 0 };
  }

  // 发送调试日志（通过 service worker，使用配置的服务器地址）
  function sendDebugLog(data) {
    console.log(LOG_PREFIX, 'Sending debug log:', data.type || 'extraction');
    chrome.runtime.sendMessage({
      type: 'DEBUG_LOG',
      data: data
    }, (res) => {
      if (res?.success) console.log(LOG_PREFIX, 'Debug log sent successfully');
      else console.error(LOG_PREFIX, 'Failed to send debug log:', res?.error);
    });
  }

  // 主提取逻辑
  async function extractAndSend() {
    const pageType = getPageType();
    console.log(LOG_PREFIX, 'Page type:', pageType);

    if (pageType !== 'product') {
      console.log(LOG_PREFIX, 'Not a product page, skipping');
      return;
    }

    // 获取页面数据
    console.log(LOG_PREFIX, 'Injecting page script...');
    const pageData = await injectPageScript();
    console.log(LOG_PREFIX, 'Page data received:', {
      success: pageData.success,
      hasRawData: !!pageData.data?.rawData,
      capturedResponses: pageData.data?.__capturedResponses?.length || 0,
      shadowRoots: pageData.data?.__allShadowRoots?.length || 0
    });

    // 提取商品数据
    const result = extractFromPageData(pageData);

    // 发送调试日志（包含 rawData 结构分析）
    const d = pageData.data || {};
    const rawData = d.rawData || d._rawData || d.__INITIAL_STATE__ || d.__PRELOADED_STATE__ || {};
    const store = rawData.store || rawData;
    const goods = store?.goods || rawData?.goods || {};

    sendDebugLog({
      type: 'raw_data_structure',
      url: window.location.href,
      timestamp: new Date().toISOString(),
      success: result.success,
      failedFields: result.failedFields,
      data: result.data,
      pageDataReceived: !!pageData.data,
      rawDataExists: !!pageData.data?.rawData,
      // 记录完整的键结构以便分析
      rawDataKeys: Object.keys(rawData || {}),
      storeKeys: Object.keys(store || {}),
      goodsKeys: Object.keys(goods || {}),
      // 商品属性和详情
      goodsProperty: goods.goodsProperty || null,
      productDetail: store.productDetail || null,
      detailList: goods.detailList || null,
      extraProperty: goods.extraProperty || null,
      catIds: [goods.catId, goods.catId1, goods.catId2, goods.catId3, goods.catId4].filter(Boolean),
      // 早期 hook 捕获的数据 - 直接从 page-bridge 注入脚本读取
      capturedResponsesCount: pageData.data?.__capturedResponses?.length || 0,
      capturedResponses: pageData.data?.__capturedResponses || [],
      shadowRootsCount: pageData.data?.__allShadowRoots?.length || 0,
      // 额外：记录 pageData 中的所有键
      pageDataKeys: Object.keys(pageData.data || {}),
    });

    console.log(LOG_PREFIX, 'Extraction result:', {
      success: result.success,
      productId: result.data.product_id,
      title: result.data.title?.substring(0, 50),
      price: result.data.current_price,
    });

    if (result.success) {
      chrome.runtime.sendMessage({
        type: 'PRODUCT_COLLECTED',
        data: result.data,
      }, (res) => {
        if (res?.success) console.log(LOG_PREFIX, 'Product queued for upload');
      });
    }

    // 8秒后尝试提取选品助手数据（等待选品助手完全加载）
    setTimeout(() => {
      console.log(LOG_PREFIX, 'Requesting xuanpin data via debugger...');
      chrome.runtime.sendMessage({ type: 'EXTRACT_XUANPIN' }, (response) => {
        console.log(LOG_PREFIX, 'Debugger response:', response);

        // 无论成功失败都发送调试日志
        sendDebugLog({
          type: 'xuanpin_attempt',
          product_id: result.data.product_id,
          url: window.location.href,
          timestamp: new Date().toISOString(),
          success: response?.success || false,
          error: response?.error || null,
          xuanpin: response?.data || null,
          html: response?.html || null,  // 保存完整 HTML 用于分析
          chartData: response?.chartData || null,  // ECharts 图表数据
          networkData: response?.networkData || null,  // 网络请求记录
          source: 'debugger'
        });

        if (response && response.success && response.data) {
          console.log(LOG_PREFIX, 'Xuanpin data extracted successfully:', Object.keys(response.data));
        } else {
          console.warn(LOG_PREFIX, 'Xuanpin extraction failed:', response?.error || 'No response');
        }
      });
    }, 8000);
  }

  // 主函数
  function main() {
    console.log(LOG_PREFIX, 'Content script loaded');
    setTimeout(() => {
      console.log(LOG_PREFIX, 'Starting extraction...');
      extractAndSend();
    }, 2000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
  } else {
    main();
  }
})();
