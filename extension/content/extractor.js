// extension/content/extractor.js
/**
 * Data extractor - 直接从 window.rawData 提取 Temu 商品数据
 */

class DataExtractor {
  constructor() {
    // 不需要配置，直接从 rawData 提取
  }

  // 查找商品数据源
  findGoodsData() {
    // 尝试多种可能的数据源
    const sources = [
      () => window.rawData?.store?.goods,
      () => window.rawData?.goods,
      () => window.__INITIAL_STATE__?.goods,
      () => window.__PRELOADED_STATE__?.goods,
      () => window._rawData?.store?.goods,
      () => {
        // 从 script 标签中查找
        const scripts = document.querySelectorAll('script:not([src])');
        for (const script of scripts) {
          const text = script.textContent || '';
          const match = text.match(/window\.rawData\s*=\s*(\{[\s\S]*?\});?\s*(?:window\.|<\/script>)/);
          if (match) {
            try {
              const data = JSON.parse(match[1]);
              return data?.store?.goods || data?.goods;
            } catch (e) {}
          }
        }
        return null;
      }
    ];

    for (const source of sources) {
      try {
        const goods = source();
        if (goods && goods.goodsId) {
          return { goods, rawData: window.rawData || window._rawData };
        }
      } catch (e) {}
    }
    return { goods: null, rawData: null };
  }

  // 主提取方法
  extractAll() {
    const result = {
      url: window.location.href,
      extracted_at: new Date().toISOString(),
      page_type: 'product_detail',
    };

    const failedFields = [];

    try {
      // 查找数据源
      const { goods, rawData } = this.findGoodsData();
      const store = rawData?.store;
      const mall = store?.mall;
      const localInfo = store?.localInfo;

      if (!goods) {
        console.warn('[Extractor] window.rawData.store.goods not found');
        // 尝试从 URL 提取 product_id
        const urlMatch = window.location.href.match(/g-(\d+)\.html/);
        result.product_id = urlMatch ? urlMatch[1] : null;
        failedFields.push('product_id', 'title', 'current_price');
        return { data: result, failedFields, success: false };
      }

      // 提取所有字段
      result.product_id = String(goods.goodsId || '');
      result.title = goods.goodsName || document.querySelector('h1')?.textContent?.trim() || '';
      result.current_price = goods.minPrice ? goods.minPrice / 100 : null;
      result.original_price = goods.marketPrice ? goods.marketPrice / 100 : null;
      result.currency = localInfo?.currencySymbol || '£';
      result.sold_count = goods.sales || null;
      result.rating = goods.goodsRating || null;
      result.review_count = goods.reviewNum || null;
      result.main_image = goods.hdThumbUrl || '';
      result.images = this.extractGalleryUrls(goods.gallery);
      result.seller_name = mall?.mallName || '';
      result.seller_id = mall?.mallId ? String(mall.mallId) : '';

      // 检查关键字段
      if (!result.product_id) failedFields.push('product_id');
      if (!result.title) failedFields.push('title');
      if (result.current_price === null) failedFields.push('current_price');

      console.log('[Extractor] Extracted from rawData:', {
        goodsId: result.product_id,
        title: result.title?.substring(0, 50),
        price: result.current_price,
        images: result.images?.length,
      });

    } catch (e) {
      console.error('[Extractor] Error extracting data:', e);
      failedFields.push('product_id', 'title', 'current_price');
    }

    return {
      data: result,
      failedFields,
      success: failedFields.length === 0,
    };
  }

  // 从 gallery 提取图片 URL
  extractGalleryUrls(gallery) {
    if (!Array.isArray(gallery)) return [];
    return gallery
      .map(g => g.url || g.hdUrl || g)
      .filter(u => u && typeof u === 'string' && u.startsWith('http'));
  }

  // Get HTML sample for debugging
  getHtmlSample(maxLength = 50000) {
    const html = document.documentElement.outerHTML;
    const bodyStart = html.indexOf('<body');
    if (bodyStart > 0) {
      return html.substring(bodyStart, bodyStart + maxLength);
    }
    return html.substring(0, maxLength);
  }

  // Get full HTML for analysis
  getFullHtml() {
    return document.documentElement.outerHTML;
  }
}

// Export
if (typeof globalThis !== 'undefined') {
  globalThis.DataExtractor = DataExtractor;
}
