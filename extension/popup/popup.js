// extension/popup/popup.js
/**
 * Popup script for configuration and status display.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('status');
  const queueSizeEl = document.getElementById('queueSize');
  const totalCollectedEl = document.getElementById('totalCollected');
  const serverUrlInput = document.getElementById('serverUrl');
  const saveBtn = document.getElementById('saveConfig');

  // Load saved config
  const config = await chrome.storage.local.get(['serverUrl', 'totalCollected']);
  if (config.serverUrl) {
    serverUrlInput.value = config.serverUrl;
  }
  totalCollectedEl.textContent = config.totalCollected || 0;

  // Check queue size
  const queue = await chrome.storage.local.get('temu_collector_queue');
  const queueSize = (queue.temu_collector_queue || []).length;
  queueSizeEl.textContent = queueSize;

  // Check server connection
  try {
    const response = await fetch(`${serverUrlInput.value}/health`);
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

  // Save config
  saveBtn.addEventListener('click', async () => {
    await chrome.storage.local.set({ serverUrl: serverUrlInput.value });
    alert('Configuration saved!');
  });
});
