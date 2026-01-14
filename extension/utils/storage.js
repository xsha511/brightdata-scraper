// extension/utils/storage.js
/**
 * Local storage queue for offline data collection.
 */

class DataQueue {
  constructor(storageKey = 'temu_collector_queue') {
    this.storageKey = storageKey;
  }

  async enqueue(item) {
    const queue = await this.getQueue();
    queue.push({
      ...item,
      queuedAt: new Date().toISOString(),
    });
    await chrome.storage.local.set({ [this.storageKey]: queue });
  }

  async dequeueAll(limit = 50) {
    const queue = await this.getQueue();
    const items = queue.splice(0, limit);
    await chrome.storage.local.set({ [this.storageKey]: queue });
    return items;
  }

  async getQueue() {
    const result = await chrome.storage.local.get(this.storageKey);
    return result[this.storageKey] || [];
  }

  async getQueueSize() {
    const queue = await this.getQueue();
    return queue.length;
  }

  async clear() {
    await chrome.storage.local.set({ [this.storageKey]: [] });
  }
}

// Export for ES modules
export { DataQueue };
