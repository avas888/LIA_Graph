export interface StorageLike {
  readonly length?: number;
  clear?: () => void;
  getItem: (key: string) => string | null;
  key?: (index: number) => string | null;
  removeItem: (key: string) => void;
  setItem: (key: string, value: string) => void;
}

function createFallbackStorage(): StorageLike {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key) ?? null : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(String(key));
    },
    setItem(key: string, value: string) {
      store.set(String(key), String(value));
    },
  };
}

const fallbackLocalStorage = createFallbackStorage();
const fallbackSessionStorage = createFallbackStorage();

export function createInMemoryStorage(): StorageLike {
  return createFallbackStorage();
}

function isStorageLike(value: unknown): value is StorageLike {
  return Boolean(
    value &&
      typeof value === "object" &&
      typeof (value as StorageLike).getItem === "function" &&
      typeof (value as StorageLike).setItem === "function" &&
      typeof (value as StorageLike).removeItem === "function"
  );
}

export function resolveStorage(storage: unknown, fallback: StorageLike): StorageLike {
  return isStorageLike(storage) ? storage : fallback;
}

export function getLocalStorage(): StorageLike {
  return resolveStorage(typeof window !== "undefined" ? window.localStorage : null, fallbackLocalStorage);
}

export function getSessionStorage(): StorageLike {
  return resolveStorage(typeof window !== "undefined" ? window.sessionStorage : null, fallbackSessionStorage);
}

export function readStorageValue(storage: StorageLike, key: string): string | null {
  try {
    return storage.getItem(key);
  } catch (_error) {
    return null;
  }
}

export function writeStorageValue(storage: StorageLike, key: string, value: string): void {
  try {
    storage.setItem(key, value);
  } catch (_error) {
    // Ignore storage failures.
  }
}

export function removeStorageValue(storage: StorageLike, key: string): void {
  try {
    storage.removeItem(key);
  } catch (_error) {
    // Ignore storage failures.
  }
}

export function clearStorage(storage: StorageLike): void {
  if (typeof storage.clear === "function") {
    try {
      storage.clear();
      return;
    } catch (_error) {
      // Fall through to key-by-key removal.
    }
  }

  const keys = listStorageKeys(storage);
  keys.forEach((key) => removeStorageValue(storage, key));
}

export function listStorageKeys(storage: StorageLike): string[] {
  const total = Number(storage.length ?? 0);
  if (!Number.isFinite(total) || total <= 0 || typeof storage.key !== "function") {
    return [];
  }

  const keys: string[] = [];
  for (let index = 0; index < total; index += 1) {
    try {
      const key = storage.key(index);
      if (key) {
        keys.push(key);
      }
    } catch (_error) {
      break;
    }
  }
  return keys;
}
