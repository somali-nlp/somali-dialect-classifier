/**
 * LocalStorage Cache Layer
 *
 * Persistent caching across browser sessions with:
 * - TTL-based expiration
 * - Version tracking for cache invalidation
 * - Graceful degradation on quota errors
 * - Automatic cleanup of expired entries
 *
 * @version 2.0
 * @author Frontend Team
 * @created 2025-11-08
 */

export class LocalStorageCache {
  constructor(namespace = 'pipeline_cache', version = '2.0') {
    this.namespace = namespace;
    this.version = version;
    this.DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes in milliseconds

    // Clean up expired entries on initialization
    this.cleanup();
  }

  /**
   * Store a value in localStorage with TTL and version
   * @param {string} key - Cache key
   * @param {any} value - Value to cache (will be JSON.stringify'd)
   * @param {number} ttl - Time to live in milliseconds (default: 5 min)
   * @returns {boolean} True if successful, false if quota exceeded
   */
  set(key, value, ttl = this.DEFAULT_TTL) {
    try {
      const item = {
        value,
        timestamp: Date.now(),
        ttl,
        version: this.version
      };

      const storageKey = `${this.namespace}:${key}`;
      localStorage.setItem(storageKey, JSON.stringify(item));

      console.log(`[LocalStorageCache] Set ${key} (TTL: ${ttl}ms, v${this.version})`);
      return true;

    } catch (error) {
      // Handle quota exceeded error
      if (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED') {
        console.warn('[LocalStorageCache] Quota exceeded, attempting cleanup...');
        this.cleanup(true); // Force cleanup of all expired items

        // Try again after cleanup
        try {
          const storageKey = `${this.namespace}:${key}`;
          const item = { value, timestamp: Date.now(), ttl, version: this.version };
          localStorage.setItem(storageKey, JSON.stringify(item));
          return true;
        } catch (retryError) {
          console.error('[LocalStorageCache] Failed to set after cleanup:', retryError);
          return false;
        }
      }

      console.error('[LocalStorageCache] Error setting cache:', error);
      return false;
    }
  }

  /**
   * Retrieve a value from localStorage
   * @param {string} key - Cache key
   * @returns {any|null} Cached value or null if not found/expired/invalid version
   */
  get(key) {
    try {
      const storageKey = `${this.namespace}:${key}`;
      const itemStr = localStorage.getItem(storageKey);

      if (!itemStr) {
        console.log(`[LocalStorageCache] Miss: ${key} (not found)`);
        return null;
      }

      const item = JSON.parse(itemStr);

      // Version check - invalidate if mismatch
      if (item.version !== this.version) {
        console.log(`[LocalStorageCache] Miss: ${key} (version mismatch: ${item.version} !== ${this.version})`);
        this.delete(key);
        return null;
      }

      // TTL check - invalidate if expired
      const age = Date.now() - item.timestamp;
      if (age > item.ttl) {
        console.log(`[LocalStorageCache] Miss: ${key} (expired: ${age}ms > ${item.ttl}ms)`);
        this.delete(key);
        return null;
      }

      console.log(`[LocalStorageCache] Hit: ${key} (age: ${age}ms)`);
      return item.value;

    } catch (error) {
      console.error(`[LocalStorageCache] Error getting ${key}:`, error);
      // Try to delete corrupted cache entry
      this.delete(key);
      return null;
    }
  }

  /**
   * Delete a specific cache entry
   * @param {string} key - Cache key to delete
   */
  delete(key) {
    try {
      const storageKey = `${this.namespace}:${key}`;
      localStorage.removeItem(storageKey);
      console.log(`[LocalStorageCache] Deleted: ${key}`);
    } catch (error) {
      console.error(`[LocalStorageCache] Error deleting ${key}:`, error);
    }
  }

  /**
   * Check if a key exists and is valid
   * @param {string} key - Cache key
   * @returns {boolean} True if exists and valid
   */
  has(key) {
    return this.get(key) !== null;
  }

  /**
   * Clear all cache entries for this namespace
   * @param {boolean} versionedOnly - If true, only clear entries with matching version
   */
  clear(versionedOnly = false) {
    try {
      const keysToDelete = [];

      for (let i = 0; i < localStorage.length; i++) {
        const storageKey = localStorage.key(i);

        if (storageKey && storageKey.startsWith(this.namespace + ':')) {
          if (versionedOnly) {
            try {
              const item = JSON.parse(localStorage.getItem(storageKey));
              if (item.version === this.version) {
                keysToDelete.push(storageKey);
              }
            } catch (e) {
              // Corrupted entry, delete it anyway
              keysToDelete.push(storageKey);
            }
          } else {
            keysToDelete.push(storageKey);
          }
        }
      }

      keysToDelete.forEach(key => localStorage.removeItem(key));
      console.log(`[LocalStorageCache] Cleared ${keysToDelete.length} entries${versionedOnly ? ' (version ' + this.version + ')' : ''}`);

    } catch (error) {
      console.error('[LocalStorageCache] Error clearing cache:', error);
    }
  }

  /**
   * Remove all expired cache entries
   * @param {boolean} force - If true, also remove entries from old versions
   */
  cleanup(force = false) {
    try {
      const now = Date.now();
      const keysToDelete = [];

      for (let i = 0; i < localStorage.length; i++) {
        const storageKey = localStorage.key(i);

        if (storageKey && storageKey.startsWith(this.namespace + ':')) {
          try {
            const item = JSON.parse(localStorage.getItem(storageKey));

            // Delete if expired
            const age = now - item.timestamp;
            if (age > item.ttl) {
              keysToDelete.push(storageKey);
            }

            // Delete if old version (when force=true)
            if (force && item.version !== this.version) {
              keysToDelete.push(storageKey);
            }

          } catch (e) {
            // Corrupted entry, delete it
            keysToDelete.push(storageKey);
          }
        }
      }

      keysToDelete.forEach(key => localStorage.removeItem(key));

      if (keysToDelete.length > 0) {
        console.log(`[LocalStorageCache] Cleanup removed ${keysToDelete.length} entries`);
      }

    } catch (error) {
      console.error('[LocalStorageCache] Error during cleanup:', error);
    }
  }

  /**
   * Get cache statistics
   * @returns {Object} Statistics object with counts and sizes
   */
  getStats() {
    try {
      let totalEntries = 0;
      let validEntries = 0;
      let expiredEntries = 0;
      let totalSize = 0;
      const now = Date.now();

      for (let i = 0; i < localStorage.length; i++) {
        const storageKey = localStorage.key(i);

        if (storageKey && storageKey.startsWith(this.namespace + ':')) {
          totalEntries++;

          try {
            const itemStr = localStorage.getItem(storageKey);
            totalSize += itemStr.length * 2; // Rough estimate (UTF-16)

            const item = JSON.parse(itemStr);
            const age = now - item.timestamp;

            if (age > item.ttl || item.version !== this.version) {
              expiredEntries++;
            } else {
              validEntries++;
            }

          } catch (e) {
            expiredEntries++;
          }
        }
      }

      return {
        totalEntries,
        validEntries,
        expiredEntries,
        totalSizeBytes: totalSize,
        totalSizeKB: Math.round(totalSize / 1024 * 10) / 10,
        namespace: this.namespace,
        version: this.version
      };

    } catch (error) {
      console.error('[LocalStorageCache] Error getting stats:', error);
      return null;
    }
  }

  /**
   * Set cache version (triggers invalidation of old cache entries)
   * @param {string} newVersion - New version string
   */
  setVersion(newVersion) {
    const oldVersion = this.version;
    this.version = newVersion;
    console.log(`[LocalStorageCache] Version updated: ${oldVersion} → ${newVersion}`);

    // Cleanup old version entries
    this.cleanup(true);
  }
}

// Export singleton instance with default namespace
export const localStorageCache = new LocalStorageCache();
