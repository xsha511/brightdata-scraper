// extension/utils/api.js
/**
 * API client for communicating with the server.
 */

const DEFAULT_SERVER_URL = 'http://localhost:8000';

class APIClient {
  constructor(serverUrl = DEFAULT_SERVER_URL) {
    this.serverUrl = serverUrl;
  }

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
      console.error('Failed to send product:', error);
      throw error;
    }
  }

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
      console.error('Failed to send batch:', error);
      throw error;
    }
  }
}

// Export for use in content scripts
if (typeof window !== 'undefined') {
  window.APIClient = APIClient;
}
