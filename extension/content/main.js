// extension/content/main.js
/**
 * Content script main entry point.
 * Detects page type and extracts product data.
 */

(function() {
  'use strict';

  // Detect page type
  function getPageType() {
    const url = window.location.href;
    if (url.includes('/goods.html') || url.match(/\/[\w-]+-g-\d+\.html/)) {
      return 'product_detail';
    }
    if (url.includes('/search_result')) {
      return 'search';
    }
    if (url.includes('/channel/')) {
      return 'category';
    }
    return 'unknown';
  }

  // Extract product data from __NEXT_DATA__
  function extractFromNextData() {
    const script = document.getElementById('__NEXT_DATA__');
    if (!script) return null;

    try {
      const data = JSON.parse(script.textContent);
      const pageProps = data.props?.pageProps;

      if (!pageProps) return null;

      // Try different data paths
      const goodsInfo = pageProps.goodsInfo || pageProps.goods || pageProps.product;
      if (!goodsInfo) return null;

      return {
        product_id: String(goodsInfo.goodsId || goodsInfo.goods_id || goodsInfo.id || ''),
        title: goodsInfo.goodsName || goodsInfo.title || goodsInfo.name || '',
        url: window.location.href,
        current_price: parsePrice(goodsInfo.price || goodsInfo.salePrice),
        original_price: parsePrice(goodsInfo.originalPrice || goodsInfo.marketPrice),
        currency: 'GBP',
        sold_count: parseInt(goodsInfo.soldNum || goodsInfo.sold_count || 0),
        rating: parseFloat(goodsInfo.rating || 0),
        review_count: parseInt(goodsInfo.reviewNum || goodsInfo.review_count || 0),
        images: extractImages(goodsInfo),
        seller_id: goodsInfo.mallId || goodsInfo.seller_id || '',
        seller_name: goodsInfo.mallName || goodsInfo.seller_name || '',
        extracted_at: new Date().toISOString(),
        page_type: 'product_detail',
        raw_data: goodsInfo,
      };
    } catch (e) {
      console.error('Failed to parse __NEXT_DATA__:', e);
      return null;
    }
  }

  function parsePrice(value) {
    if (value === null || value === undefined) return null;
    if (typeof value === 'number') {
      // Temu sometimes stores price in cents
      return value > 1000 ? value / 100 : value;
    }
    if (typeof value === 'string') {
      const cleaned = value.replace(/[^0-9.]/g, '');
      return parseFloat(cleaned) || null;
    }
    return null;
  }

  function extractImages(goodsInfo) {
    const images = [];
    const imageList = goodsInfo.images || goodsInfo.imageList || goodsInfo.gallery || [];

    for (const img of imageList) {
      const url = typeof img === 'string' ? img : (img.url || img.src || '');
      if (url) {
        images.push(url.startsWith('http') ? url : `https:${url}`);
      }
    }

    return images;
  }

  // Main execution
  function main() {
    const pageType = getPageType();
    console.log('[Temu Collector] Page type:', pageType);

    if (pageType === 'product_detail') {
      // Wait for page to fully load
      setTimeout(() => {
        const productData = extractFromNextData();

        if (productData && productData.product_id) {
          console.log('[Temu Collector] Extracted product:', productData.product_id);

          // Send to background script
          chrome.runtime.sendMessage({
            type: 'PRODUCT_COLLECTED',
            data: productData,
          }, (response) => {
            if (response?.success) {
              console.log('[Temu Collector] Product queued for upload');
            }
          });
        } else {
          console.log('[Temu Collector] No product data found');
        }
      }, 2000);
    }
  }

  // Run on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
  } else {
    main();
  }
})();
