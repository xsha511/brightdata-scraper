// extension/background/service-worker.js
/**
 * Background service worker for batch uploads and heartbeat.
 */

import { DataQueue } from '../utils/storage.js';

const queue = new DataQueue();
const BATCH_INTERVAL_MINUTES = 1;
const DEFAULT_SERVER_URL = 'http://localhost:8000';

async function getServerUrl() {
  const result = await chrome.storage.local.get('serverUrl');
  return result.serverUrl || DEFAULT_SERVER_URL;
}

// Set up periodic batch upload
chrome.alarms.create('batchUpload', { periodInMinutes: BATCH_INTERVAL_MINUTES });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'batchUpload') {
    await processBatchUpload();
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
      console.error('Batch upload failed, items re-queued');
    } else {
      console.log(`Batch uploaded ${items.length} items`);
    }
  } catch (error) {
    // Re-queue on network error
    for (const item of items) {
      await queue.enqueue(item);
    }
    console.error('Batch upload error:', error);
  }
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'PRODUCT_COLLECTED') {
    queue.enqueue(message.data).then(() => {
      sendResponse({ success: true });
    });
    return true; // Async response
  }
});
