// extension/utils/api.js
/**
 * API client for communicating with the server.
 */

const DEFAULT_SERVER_URL = 'http://localhost:8001';

class APIClient {
  constructor(serverUrl = DEFAULT_SERVER_URL) {
    this.serverUrl = serverUrl;
  }

  // 获取选择器配置
  async getSelectors(pageType = 'product') {
    try {
      const response = await fetch(`${this.serverUrl}/api/selectors/${pageType}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('[API] Failed to get selectors:', error);
      return null;
    }
  }

  // 发送提取的商品数据
  async sendProduct(productData) {
    try {
      const response = await fetch(`${this.serverUrl}/api/collect/product`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(productData),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[API] Failed to send product:', error);
      throw error;
    }
  }

  // 发送完整 HTML 让后端分析（选择器失效时）
  async analyzeHtml(pageUrl, htmlContent, pageType = 'product') {
    try {
      const response = await fetch(`${this.serverUrl}/api/analyze/html`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: pageUrl,
          html: htmlContent,
          page_type: pageType,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[API] Failed to analyze HTML:', error);
      throw error;
    }
  }

  // 报告提取失败（告警功能）
  async reportExtractionFailure(pageUrl, failedFields, htmlSample) {
    try {
      const response = await fetch(`${this.serverUrl}/api/alert/extraction-failed`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: pageUrl,
          failed_fields: failedFields,
          html_sample: htmlSample,
          timestamp: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[API] Failed to report failure:', error);
      // Don't throw - alerting is non-critical
    }
  }

  // 批量发送
  async sendBatch(products) {
    try {
      const response = await fetch(`${this.serverUrl}/api/collect/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ products }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[API] Failed to send batch:', error);
      throw error;
    }
  }
}

// Export for use in service worker and content scripts
if (typeof globalThis !== 'undefined') {
  globalThis.APIClient = APIClient;
}
