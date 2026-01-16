// extension/popup/popup.js
/**
 * Popup script for configuration and status display.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('status');
  const queueSizeEl = document.getElementById('queueSize');
  const totalCollectedEl = document.getElementById('totalCollected');
  const serverUrlEl = document.getElementById('serverUrl');
  const configTimeEl = document.getElementById('configTime');
  const refreshBtn = document.getElementById('refreshConfig');
  const versionEl = document.getElementById('version');

  // 显示版本号
  const manifest = chrome.runtime.getManifest();
  versionEl.textContent = `v${manifest.version}`;

  // Load saved config
  async function loadConfig() {
    const config = await chrome.storage.local.get(['serverUrl', 'totalCollected', 'configLastUpdated']);

    serverUrlEl.textContent = config.serverUrl || 'http://localhost:8001 (默认)';
    totalCollectedEl.textContent = config.totalCollected || 0;

    if (config.configLastUpdated) {
      const date = new Date(config.configLastUpdated);
      configTimeEl.textContent = date.toLocaleString();
    } else {
      configTimeEl.textContent = '未同步';
    }

    // Check queue size
    const queue = await chrome.storage.local.get('temu_collector_queue');
    const queueSize = (queue.temu_collector_queue || []).length;
    queueSizeEl.textContent = queueSize;

    // Check server connection
    try {
      const serverUrl = config.serverUrl || 'http://localhost:8001';
      const response = await fetch(`${serverUrl}/health`);
      if (response.ok) {
        statusEl.textContent = 'Connected to server';
        statusEl.className = 'status connected';
      } else {
        throw new Error('Server unhealthy');
      }
    } catch (e) {
      statusEl.textContent = 'Server not available';
      statusEl.className = 'status disconnected';
    }
  }

  // 引导配置 URL（与 service-worker.js 中保持一致）
  const CONFIG_URL = 'http://localhost:8001/static/extension-config.json';

  // Refresh config from bootstrap service
  async function refreshConfig() {
    refreshBtn.disabled = true;
    refreshBtn.textContent = 'Refreshing...';

    try {
      const response = await fetch(CONFIG_URL, { cache: 'no-store' });
      if (response.ok) {
        const newConfig = await response.json();
        await chrome.storage.local.set({
          serverUrl: newConfig.server_url,
          configVersion: newConfig.version,
          configLastUpdated: Date.now()
        });
        await loadConfig();
        alert('Config refreshed!');
      } else {
        throw new Error('Failed to fetch config');
      }
    } catch (e) {
      alert('Failed to refresh config: ' + e.message);
    } finally {
      refreshBtn.disabled = false;
      refreshBtn.textContent = 'Refresh Config';
    }
  }

  // Initial load
  await loadConfig();

  // Refresh button
  refreshBtn.addEventListener('click', refreshConfig);
});
